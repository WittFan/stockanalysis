"""
Kimi CLI Wire 模式桥接 Handler

通过子进程运行 `kimi --wire`，将前端的 OpenAI 格式对话请求
转换为 Wire 协议（JSON-RPC 2.0 over stdin/stdout），
并以 SSE（Server-Sent Events）流式返回响应。

Wire 协议版本：1.7
"""
import json
import os
import subprocess
import threading
import uuid
from queue import Empty, Queue

from loguru import logger


class KimiWireSession:
    """管理一个 kimi --wire 子进程的生命周期"""

    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self._msg_queue: Queue = Queue()
        self._reader_thread: threading.Thread | None = None

    def start(self):
        """启动 kimi --wire 子进程"""
        kimi_path = self._find_kimi()
        if not kimi_path:
            raise RuntimeError("找不到 kimi 命令，请先安装：curl -LsSf https://code.kimi.com/install.sh | bash")

        env = {**os.environ}
        # 确保 ~/.local/bin 在 PATH 中（uv 安装位置）
        local_bin = os.path.expanduser('~/.local/bin')
        if local_bin not in env.get('PATH', ''):
            env['PATH'] = local_bin + ':' + env.get('PATH', '')

        self.proc = subprocess.Popen(
            [kimi_path, '--wire', '--yolo'],  # --yolo 自动审批工具调用，无需人工确认
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,  # 行缓冲
        )
        logger.info(f"kimi --wire 子进程启动，PID={self.proc.pid}")

        # 后台线程持续读取 stdout
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        # kimi 进程需要约 2-3 秒初始化（加载配置、认证）
        import time
        time.sleep(3)

    def _find_kimi(self) -> str | None:
        """查找 kimi 可执行文件路径"""
        import shutil
        # 先把常见安装路径加入环境 PATH
        extra_paths = [
            os.path.expanduser('~/.local/bin'),
            os.path.expanduser('~/.cargo/bin'),
            '/usr/local/bin',
            '/opt/homebrew/bin',
        ]
        env_path = os.environ.get('PATH', '')
        extended = ':'.join(extra_paths) + ':' + env_path
        kimi = shutil.which('kimi', path=extended)
        if kimi:
            return kimi
        # 直接检查文件
        for d in extra_paths:
            p = os.path.join(d, 'kimi')
            if os.path.isfile(p):
                return p
        return None

    def _read_stdout(self):
        """后台线程：持续读取子进程 stdout，将每行 JSON 放入队列"""
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if line:
                    try:
                        msg = json.loads(line)
                        self._msg_queue.put(msg)
                    except json.JSONDecodeError:
                        logger.debug(f"非 JSON 输出: {line}")
        except Exception as e:
            logger.error(f"读取 kimi stdout 出错: {e}")
        finally:
            self._msg_queue.put(None)  # 哨兵：进程结束

    def _send(self, obj: dict):
        """向子进程 stdin 发送 JSON-RPC 消息"""
        line = json.dumps(obj, ensure_ascii=False) + '\n'
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def _recv_until_id(self, req_id: str, timeout: float = 30.0) -> dict | None:
        """等待指定 id 的响应（忽略中间的 event 通知）"""
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            try:
                msg = self._msg_queue.get(timeout=min(remaining, 1.0))
                if msg is None:
                    return None  # 进程结束
                # JSON-RPC 响应带 id
                if msg.get('id') == req_id:
                    return msg
                # 其他事件暂时丢弃（initialize 阶段）
            except Empty:
                continue
        return None

    def initialize(self):
        """发送 initialize 握手，等待响应"""
        req_id = str(uuid.uuid4())
        self._send({
            'jsonrpc': '2.0',
            'method': 'initialize',
            'id': req_id,
            'params': {
                'protocol_version': '1.7',
                'client': {'name': 'stockanalysis-assistant', 'version': '1.0.0'},
                'capabilities': {'supports_question': False},
            },
        })
        resp = self._recv_until_id(req_id, timeout=15.0)
        if resp and 'error' in resp:
            raise RuntimeError(f"initialize 失败: {resp['error']}")
        logger.info("Kimi Wire 初始化完成")
        return resp

    def prompt_stream(self, user_input: str):
        """
        发送 prompt 请求，逐个 yield ContentPart 文本块。
        遇到 TurnEnd 或 prompt 响应后结束。
        """
        req_id = str(uuid.uuid4())
        self._send({
            'jsonrpc': '2.0',
            'method': 'prompt',
            'id': req_id,
            'params': {'user_input': user_input},
        })

        while True:
            try:
                msg = self._msg_queue.get(timeout=120.0)
            except Empty:
                logger.warning("等待 kimi 响应超时（120s）")
                break

            if msg is None:
                break  # 进程结束

            method = msg.get('method')
            msg_id = msg.get('id')

            # prompt 的最终响应
            if msg_id == req_id:
                if 'error' in msg:
                    yield f"[错误: {msg['error'].get('message', '未知错误')}]"
                break

            # 事件通知
            if method == 'event':
                params = msg.get('params', {})
                event_type = params.get('type')
                payload = params.get('payload', {})

                if event_type == 'ContentPart':
                    part_type = payload.get('type')
                    if part_type == 'text':
                        text = payload.get('text', '')
                        if text:
                            yield text
                    elif part_type == 'think':
                        # 思考内容可以选择跳过或包含
                        pass

                elif event_type == 'TurnEnd':
                    break

    def close(self):
        """关闭子进程"""
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            logger.info("kimi --wire 子进程已关闭")


class KimiWireHandler:
    """
    无状态 Handler：每次请求新建一个 Wire 会话（简单方案）。
    如需跨请求保持会话，可改为按 session_id 缓存 KimiWireSession。
    """

    def chat_stream(self, messages: list[dict], system: str = '') -> str:
        """
        生成器：将 OpenAI 格式 messages 转为 kimi Wire 对话，
        yield SSE 数据行（`data: {...}\n\n` 格式）。

        由于 Wire 模式每次新建进程不保留历史，
        把完整对话历史拼为一段 user_input 发给 kimi。
        """
        session = KimiWireSession()
        try:
            session.start()
            session.initialize()

            # 将 messages 历史压缩成一次 prompt 输入
            # （Wire 模式本身有 replay 功能，但简单起见先用文本拼接）
            user_input = self._build_user_input(messages, system)

            for chunk in session.prompt_stream(user_input):
                sse_data = {
                    'choices': [{
                        'delta': {'content': chunk},
                        'index': 0,
                        'finish_reason': None,
                    }]
                }
                yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Kimi Wire 出错: {e}")
            err_data = {
                'choices': [{
                    'delta': {'content': f"\n[Kimi CLI 错误: {e}]"},
                    'index': 0,
                    'finish_reason': 'stop',
                }]
            }
            yield f"data: {json.dumps(err_data, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            session.close()

    def _build_user_input(self, messages: list[dict], system: str) -> str:
        """
        将 OpenAI 格式 messages 拼装为 kimi 能理解的单段输入。
        多轮对话时，把历史轮次作为上下文前缀。
        """
        parts = []
        if system:
            parts.append(f"[系统设定]\n{system}\n")

        # 只有一条用户消息时，直接使用
        user_msgs = [m for m in messages if m['role'] == 'user']
        assistant_msgs = [m for m in messages if m['role'] == 'assistant']

        if len(user_msgs) == 1 and not assistant_msgs:
            return (parts[0] if parts else '') + user_msgs[0]['content']

        # 多轮时，拼装对话历史
        if parts:
            parts.append('')  # 空行分隔

        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content') or ''
            if isinstance(content, list):
                # 处理多模态 content
                content = ' '.join(p.get('text', '') for p in content if p.get('type') == 'text')
            if role == 'user':
                parts.append(f"用户：{content}")
            elif role == 'assistant':
                parts.append(f"助理：{content}")
            # tool 消息暂时忽略

        return '\n'.join(parts)
