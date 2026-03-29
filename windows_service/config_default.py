"""
Windows 交易服务配置模板（已上传 GitHub）
==========================================
首次部署步骤：
  copy config_default.py config.py
  # 编辑 config.py，填入实际值
"""
import os

# =============================================================================
# QMT 连接配置（必须根据实际环境修改）
# =============================================================================

# MiniQMT userdata_mini 路径（Windows 绝对路径）
QMT_PATH    = r'C:\迅投极速交易终端\userdata_mini'
# 资金账号
QMT_ACCOUNT = ''
# 会话ID（同一台机器上多个策略使用不同 ID 以区分）
QMT_SESSION = 123456

# =============================================================================
# REST API 配置
# =============================================================================

# 监听地址：0.0.0.0 允许外部（Mac 端）访问，127.0.0.1 仅本机
API_HOST  = '0.0.0.0'
API_PORT  = 8080

# API 认证 Token：强烈建议设置，防止局域网内其他设备调用下单接口
# 与 Mac 端 config.py 中 QMT_SERVICE_TOKEN 保持一致
# 生成示例：python -c "import secrets; print(secrets.token_hex(32))"
API_TOKEN = ''   # ← 必须填写，不能留空

# =============================================================================
# 日志
# =============================================================================

LOG_LEVEL = 'INFO'

# =============================================================================
# 环境变量覆盖（优先级高于上述配置，适合生产部署）
# =============================================================================

if os.environ.get('QMT_PATH'):
    QMT_PATH = os.environ['QMT_PATH']
if os.environ.get('QMT_ACCOUNT'):
    QMT_ACCOUNT = os.environ['QMT_ACCOUNT']
if os.environ.get('QMT_SESSION'):
    QMT_SESSION = int(os.environ['QMT_SESSION'])
if os.environ.get('API_PORT'):
    API_PORT = int(os.environ['API_PORT'])
if os.environ.get('API_TOKEN'):
    API_TOKEN = os.environ['API_TOKEN']
