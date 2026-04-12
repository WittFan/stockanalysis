"""
数据下载管理 Handler

路由（Flask API）：
  GET  /api/download/tables           → JSON [{id, label, category, last_update, row_count, description}]
  POST /api/download/start            → JSON {task_id}  Body: {tables: ['income_statement', ...]}
  GET  /api/download/status/<task_id> → JSON {status, progress, current, log}
"""
import threading
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import text, desc

from orm_models.api import data_api, engine, session
from orm_models.table_models import UpdateRecord

# ── 全局任务存储 ────────────────────────────────────────────────────────────────
_tasks: dict     = {}
_tasks_lock      = threading.Lock()

# ── 表注册表：id → {label, category, description, pull_class, model_class} ────
# pull_class 字符串（延迟导入，避免���动时加载 Tushare）
TABLE_REGISTRY = {
    # 市场基础数据
    'trade_cal':       {'label': '交易日历',     'category': '基础数据', 'description': '交易所交易日历（含节假日）',       'pull': 'TradeCalTushare',       'table': 'trade_cal'},
    'stock_basic':     {'label': '股票基本信息', 'category': '基础数据', 'description': '上市公司基本信息（代码/名称/行业）', 'pull': 'StockBasicTushare',     'table': 'stock_basic'},
    'index_basic':     {'label': '指数基本信息', 'category': '基础数据', 'description': '各类指数基本信息',                 'pull': 'IndexBasicTushare',     'table': 'index_basic'},
    'index_classify':  {'label': '申万行业分类', 'category': '基础数据', 'description': '申万一级/二级行业分类',             'pull': 'IndexClassifyTushare',  'table': 'sw_industry_detail'},
    # 行情数据
    'daily':           {'label': '股票日线',     'category': '行情数据', 'description': 'A股日线行情（OHLCV）',             'pull': 'DailyTushare',          'table': 'daily'},
    'daily_basic':     {'label': '每日指标',     'category': '行情数据', 'description': '每日市值、PE、PB 等指标',           'pull': 'DailyBasicTushare',     'table': 'daily_basic'},
    'adj_factor':      {'label': '复权因子',     'category': '行情数据', 'description': '前/后复权因子',                   'pull': 'AdjFactorTushare',      'table': 'adj_factor'},
    'index_daily':     {'label': '指数日线',     'category': '行情数据', 'description': '主要指数日线行情',                 'pull': 'IndexDailyTushare',     'table': 'index_daily'},
    'fund_daily':      {'label': '基金日线',     'category': '行情数据', 'description': '基金日线行情',                     'pull': 'FundDailyTushare',      'table': 'fund_daily'},
    'fund_nav':        {'label': '基金净值',     'category': '行情数据', 'description': '基金单位净值与累计净值',           'pull': 'FundNavTushare',        'table': 'fund_nav'},
    'fund_adj':        {'label': '基金复权净值', 'category': '行情数据', 'description': '基金复权净值',                     'pull': 'FundAdjTushare',        'table': 'fund_adj'},
    # 财务数据
    'income_statement':{'label': '利润表',       'category': '财务数据', 'description': '上市公司合并利润表（全市场季度）', 'pull': 'IncomeStatementTushare','table': 'income_statement'},
    'balance_sheet':   {'label': '资产负债表',   'category': '财务数据', 'description': '上市公司资产负债表（全市场季度）', 'pull': 'BalanceSheetTushare',   'table': 'balance_sheet'},
    'cash_flow':       {'label': '现金流量表',   'category': '财务数据', 'description': '上市公司现金流量表（全市场季度）', 'pull': 'CashFlowTushare',       'table': 'cash_flow'},
    'fina_indicator':  {'label': '财务指标',     'category': '财务数据', 'description': 'ROE/毛利率/EPS 等100+指标',       'pull': 'FinaIndicatorTushare',  'table': 'fina_indicator'},
    'fina_forecast':   {'label': '业绩预告',     'category': '财务数据', 'description': '上市公司业绩预告（净利润区间）',   'pull': 'ForecastTushare',       'table': 'fina_forecast'},
    'fina_express':    {'label': '业绩快报',     'category': '财务数据', 'description': '上市公司业绩快报（主要财务指标）', 'pull': 'ExpressTushare',        'table': 'fina_express'},
    'fina_mainbz':     {'label': '主营业务',     'category': '财务数据', 'description': '主营业务构成（按产品/地区分类）',  'pull': 'FinaMainbzTushare',     'table': 'fina_mainbz'},
    'dividend':        {'label': '分红送股',     'category': '财务数据', 'description': '分红派息及送转股方案',             'pull': 'DividendTushare',       'table': 'dividend'},
    'fina_audit':      {'label': '审计意见',     'category': '财务数据', 'description': '年报审计意见及会计事务所',         'pull': 'FinaAuditTushare',      'table': 'fina_audit'},
    'disclosure_date': {'label': '披露日期',     'category': '财务数据', 'description': '财报计划/实际披露日期',            'pull': 'DisclosureDateTushare', 'table': 'disclosure_date'},
}


def _get_pull_class(class_name: str):
    """ 延迟导入拉取类，避免循环导入 """
    from pull_tushare.tushare_tables import (
        TradeCalTushare, StockBasicTushare, IndexBasicTushare, IndexClassifyTushare,
        DailyTushare, DailyBasicTushare, AdjFactorTushare, IndexDailyTushare,
        FundDailyTushare, FundNavTushare, FundAdjTushare,
        IncomeStatementTushare, BalanceSheetTushare, CashFlowTushare,
        FinaIndicatorTushare, ForecastTushare, ExpressTushare, FinaMainbzTushare,
        DividendTushare, FinaAuditTushare, DisclosureDateTushare,
    )
    return locals()[class_name]


def _get_table_row_count(table_name: str) -> int:
    """ 查询表行数 """
    try:
        with engine.connect() as con:
            result = con.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar() or 0
    except Exception:
        return -1


def _get_table_last_update(table_name: str) -> str:
    """ 从 UpdateRecord 查最后更新时间 """
    try:
        query_magic = session.query(UpdateRecord.data_datetime).filter(
            UpdateRecord.table_name == table_name
        ).order_by(desc(UpdateRecord.data_datetime)).limit(1)
        df = data_api.query(query_magic)
        if df.empty or df.iloc[0, 0] is None:
            return None
        val = df.iloc[0, 0]
        if hasattr(val, 'strftime'):
            return val.strftime('%Y-%m-%d')
        return str(val)[:10]
    except Exception:
        return None


def _update_task(task_id: str, **kwargs):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].update(kwargs)


def _append_log(task_id: str, line: str):
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id]['log'].append(line)


def _run_download(task_id: str, table_ids: list):
    """ 后台线程：串行执行选中的拉取类 """
    total = len(table_ids)
    for idx, tid in enumerate(table_ids):
        if tid not in TABLE_REGISTRY:
            _append_log(task_id, f'[WARN] 未知表 {tid}，跳过')
            continue
        entry = TABLE_REGISTRY[tid]
        class_name = entry['pull']
        label = entry['label']
        _update_task(task_id, current=label, progress=round(idx / total, 2))
        _append_log(task_id, f'[{idx+1}/{total}] 开始下载：{label}（{tid}）')
        try:
            cls = _get_pull_class(class_name)
            cls().pull()
            _append_log(task_id, f'[{idx+1}/{total}] ✓ {label} 完成')
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            _append_log(task_id, f'[{idx+1}/{total}] ✗ {label} 失败: {e}')
            logger.error(f'download {tid} error: {err}')

    _update_task(task_id, status='done', progress=1.0, current='')
    _append_log(task_id, f'所有 {total} 张表下载完成')
    logger.info(f'[download task {task_id}] 完成')


class DownloadHandler:

    def handle_tables(self) -> tuple:
        """ GET /api/download/tables """
        result = []
        for tid, entry in TABLE_REGISTRY.items():
            table_name = entry['table']
            row_count = _get_table_row_count(table_name)
            last_update = _get_table_last_update(table_name)
            result.append({
                'id':          tid,
                'label':       entry['label'],
                'category':    entry['category'],
                'description': entry['description'],
                'last_update': last_update,
                'row_count':   row_count,
            })
        return 200, {'tables': result}

    def handle_start(self, body: dict) -> tuple:
        """ POST /api/download/start """
        table_ids = body.get('tables', [])
        if not table_ids:
            return 400, {'error': '请至少选择一张表'}

        task_id = str(uuid.uuid4())[:8]
        with _tasks_lock:
            _tasks[task_id] = {
                'status':   'running',
                'progress': 0.0,
                'current':  '',
                'log':      [],
                'start_time': datetime.now().isoformat(),
            }

        t = threading.Thread(
            target=_run_download,
            args=(task_id, table_ids),
            daemon=True,
        )
        t.start()
        logger.info(f'[download] 任务 {task_id} 启动，共 {len(table_ids)} 张表')
        return 200, {'task_id': task_id}

    def handle_status(self, task_id: str) -> tuple:
        """ GET /api/download/status/<task_id> """
        with _tasks_lock:
            task = _tasks.get(task_id)
        if task is None:
            return 404, {'error': f'任务 {task_id} 不存在'}
        return 200, {
            'status':   task['status'],
            'progress': task['progress'],
            'current':  task.get('current', ''),
            'log':      task.get('log', []),
        }
