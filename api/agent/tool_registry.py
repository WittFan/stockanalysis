"""
工具注册表 + Phase 1 内置工具

新增：
  - Schema 校验：执行前检查必填字段和类型
  - 超时控制：每个工具最多执行 30s（ThreadPoolExecutor）
"""
import ast
import concurrent.futures
import json
import operator
import re
import zoneinfo
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from loguru import logger


# ── 安全计算器 ────────────────────────────────────────────────────────────────

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}

def _safe_eval(expr: str) -> float:
    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value)}")
        if isinstance(node, ast.BinOp):
            op = _OPERATORS.get(type(node.op))
            if not op:
                raise ValueError(f"不支持的运算符: {node.op}")
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = _OPERATORS.get(type(node.op))
            if not op:
                raise ValueError(f"不支持的一元运算符: {node.op}")
            return op(_eval(node.operand))
        raise ValueError(f"不支持的表达式节点: {type(node)}")
    tree = ast.parse(expr.strip(), mode='eval')
    return _eval(tree.body)


# ── Schema 校验 ───────────────────────────────────────────────────────────────

_TYPE_MAP = {
    "string":  str,
    "integer": int,
    "number":  (int, float),
    "boolean": bool,
    "array":   list,
    "object":  dict,
}

def validate_args(tool_name: str, parameters: dict, args: dict) -> str | None:
    """
    轻量级 JSON Schema 校验（无需 jsonschema 库）。
    返回 None 表示校验通过，返回字符串表示错误描述。
    """
    if not parameters:
        return None

    props = parameters.get("properties", {})
    required = parameters.get("required", [])

    # 检查必填字段
    for field_name in required:
        if field_name not in args:
            return f"缺少必填参数 '{field_name}'"
        if args[field_name] is None or args[field_name] == "":
            return f"必填参数 '{field_name}' 不能为空"

    # 检查字段类型
    for field_name, value in args.items():
        if field_name not in props:
            continue  # 允许额外字段（宽松校验）
        schema = props[field_name]
        expected_type = schema.get("type")
        if not expected_type or value is None:
            continue
        py_type = _TYPE_MAP.get(expected_type)
        if py_type and not isinstance(value, py_type):
            return (f"参数 '{field_name}' 类型错误：期望 {expected_type}，"
                    f"实际是 {type(value).__name__}")

        # enum 校验
        if "enum" in schema and value not in schema["enum"]:
            allowed = ", ".join(str(v) for v in schema["enum"])
            return f"参数 '{field_name}' 值 '{value}' 不在允许范围内（{allowed}）"

    return None


# ── 工具基类 ──────────────────────────────────────────────────────────────────

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict           # JSON Schema（OpenAI 格式）
    fn: Callable               # (args: dict) -> str
    timeout: float = 30.0      # 单次执行超时秒数


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_definitions(self) -> list[dict]:
        """返回 OpenAI function calling 格式的工具列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, args: dict) -> str:
        """
        执行工具，包含：
          1. 工具存在性检查
          2. Schema 参数校验
          3. 超时控制（ThreadPoolExecutor）
          4. 异常捕获
        """
        tool = self.get(name)
        if not tool:
            return f"错误：未知工具 '{name}'"

        # Week 2: Schema 校验
        err = validate_args(name, tool.parameters, args)
        if err:
            logger.warning(f"工具 {name} 参数校验失败: {err}")
            return f"[参数校验失败] {err}"

        # Week 3: 超时执行
        return self._execute_with_timeout(tool, args)

    def _execute_with_timeout(self, tool: Tool, args: dict) -> str:
        """在独立线程中执行工具，超时则强制返回错误"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool.fn, args)
            try:
                result = future.result(timeout=tool.timeout)
                return str(result)
            except concurrent.futures.TimeoutError:
                logger.warning(f"工具 {tool.name} 执行超时（>{tool.timeout}s）")
                return f"[超时] 工具 {tool.name} 执行超过 {tool.timeout:.0f}s，已中止"
            except Exception as e:
                logger.warning(f"工具 {tool.name} 执行出错: {e}")
                return f"[执行错误] {e}"


# ── Phase 1 工具实现 ──────────────────────────────────────────────────────────

def _get_current_time(_args: dict) -> str:
    tz = zoneinfo.ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz)
    return now.strftime("%Y年%m月%d日 %H:%M:%S（北京时间）")


def _calculate(args: dict) -> str:
    expr = args.get("expression", "").strip()
    try:
        result = _safe_eval(expr)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return f"{expr} = {result}"
    except Exception as e:
        return f"计算出错: {e}"


def _get_stock_info(args: dict) -> str:
    symbol = args.get("symbol", "").strip().upper()
    # 格式校验：必须是 6位数字.2位字母
    if not re.match(r'^\d{6}\.(SH|SZ|BJ)$', symbol):
        return f"股票代码格式错误：'{symbol}'，正确格式如 600519.SH 或 000001.SZ"
    try:
        import pandas as pd
        from orm_models.api import engine
        df = pd.read_sql(
            "SELECT trade_date, open, high, low, close, vol, pct_chg "
            "FROM daily WHERE ts_code=:code ORDER BY trade_date DESC LIMIT 5",
            engine,
            params={"code": symbol},
        )
        if df.empty:
            return f"未找到 {symbol} 的行情数据（数据库中无此代码或尚未拉取数据）"
        df = df.iloc[::-1]
        lines = []
        for _, row in df.iterrows():
            td = str(row['trade_date'])[:10]
            lines.append(
                f"日期:{td}  开:{row['open']:.2f}  高:{row['high']:.2f}  "
                f"低:{row['low']:.2f}  收:{row['close']:.2f}  "
                f"量:{row['vol']:.0f}  涨跌幅:{row['pct_chg']:.2f}%"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_stock_info 出错: {e}")
        return f"查询出错: {e}"


def _query_financial_data(args: dict) -> str:
    """结构化查询金融数据库，不接受裸 SQL（防注入）"""
    ALLOWED_TABLES = {"daily", "weekly", "monthly"}
    table = args.get("table", "daily").lower().strip()
    if table not in ALLOWED_TABLES:
        return f"不支持的表: {table}，可选: {', '.join(sorted(ALLOWED_TABLES))}"

    ts_code    = args.get("ts_code", "").strip()
    start_date = args.get("start_date", "")
    end_date   = args.get("end_date", "")
    columns_arg = args.get("columns", "")
    limit = min(int(args.get("limit", 30)), 100)

    # 日期格式简单校验
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if start_date and not date_pattern.match(start_date):
        return f"start_date 格式错误：'{start_date}'，正确格式如 2024-01-01"
    if end_date and not date_pattern.match(end_date):
        return f"end_date 格式错误：'{end_date}'，正确格式如 2024-12-31"

    SAFE_COLS = {"ts_code", "trade_date", "open", "high", "low", "close",
                 "pre_close", "change", "pct_chg", "vol", "amount"}
    if columns_arg:
        requested = {c.strip() for c in columns_arg.split(",")}
        cols = requested & SAFE_COLS
        if not cols:
            return "没有合法的列名，可选: " + ", ".join(sorted(SAFE_COLS))
        select_cols = ", ".join(sorted(cols))
    else:
        select_cols = "ts_code, trade_date, open, high, low, close, pct_chg, vol"

    conditions = []
    params: dict[str, Any] = {}
    if ts_code:
        conditions.append("ts_code = :ts_code")
        params["ts_code"] = ts_code
    if start_date:
        conditions.append("trade_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("trade_date <= :end_date")
        params["end_date"] = end_date

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT {select_cols} FROM {table} {where} ORDER BY trade_date DESC LIMIT :limit"
    params["limit"] = limit

    try:
        import pandas as pd
        from sqlalchemy import text
        from orm_models.api import engine
        df = pd.read_sql(text(sql), engine, params=params)
        if df.empty:
            return "查询结果为空"
        df = df.iloc[::-1]
        if "trade_date" in df.columns:
            df["trade_date"] = df["trade_date"].astype(str).str[:10]
        total = len(df)
        result = df.to_string(index=False, max_rows=50)
        note = f"\n（共 {total} 行）" if total < limit else f"\n（显示最近 {limit} 行）"
        return result + note
    except Exception as e:
        logger.warning(f"query_financial_data 出错: {e}")
        return f"查询出错: {e}"


# ── 注册表工厂 ────────────────────────────────────────────────────────────────

def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(Tool(
        name="get_current_time",
        description="获取当前北京时间（日期和时间）",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=_get_current_time,
        timeout=5.0,
    ))

    registry.register(Tool(
        name="calculate",
        description="计算数学表达式，支持加减乘除、幂运算、取模。不支持 sqrt 等函数。",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '(100 + 200) * 3 / 4'",
                }
            },
            "required": ["expression"],
        },
        fn=_calculate,
        timeout=5.0,
    ))

    registry.register(Tool(
        name="get_stock_info",
        description="查询A股股票最近5日行情（开高低收、成交量、涨跌幅）",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，格式如 600519.SH 或 000001.SZ",
                }
            },
            "required": ["symbol"],
        },
        fn=_get_stock_info,
        timeout=30.0,
    ))

    registry.register(Tool(
        name="query_financial_data",
        description=(
            "查询金融数据库行情数据。支持 daily/weekly/monthly 表，"
            "可按股票代码、日期范围过滤，最多返回100行。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "enum": ["daily", "weekly", "monthly"],
                    "description": "数据表名",
                },
                "ts_code": {
                    "type": "string",
                    "description": "股票代码，如 600519.SH（可选）",
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期 YYYY-MM-DD（可选）",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期 YYYY-MM-DD（可选）",
                },
                "columns": {
                    "type": "string",
                    "description": "逗号分隔的列名，如 'ts_code,trade_date,close,pct_chg'（可选）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回行数上限，最大100，默认30",
                },
            },
            "required": ["table"],
        },
        fn=_query_financial_data,
        timeout=30.0,
    ))

    return registry
