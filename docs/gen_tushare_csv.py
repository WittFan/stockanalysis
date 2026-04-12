"""生成 tushare-接口信息.csv"""
import csv
import os

HEADERS = [
    "分类", "子分类", "接口名称", "接口说明", "doc_id",
    "接口示例", "接口限制", "输入参数-ts_code", "输入参数-日期",
    "是否已实现", "表名", "ORM模型", "下载类", "基类", "主键字段",
    "下载逻辑", "更新频率", "验证是否不需要更新逻辑",
    "是否需要分页", "是否循环参数", "是否需要去重", "是否过滤多余列",
    "是否有update_flag", "重试逻辑", "派生表", "断点续传", "备注"
]

# ── 已实现接口（23个，全部27列） ──────────────────────────────
implemented = [
    # 1. trade_cal
    ["沪深股票", "基础数据", "trade_cal", "交易日历", "26",
     "pro.trade_cal(exchange='SSE', start_date='20180101', end_date='20181231')",
     "2000积分", "不需要", "可选(start_date/end_date)",
     "是", "trade_cal", "TradeCal", "TradeCalTushare", "MetaDataBase",
     "exchange+cal_date", "全量替换", "yearly",
     "今天<去年11月25日则跳过",
     "否", "是(7个交易所:SSE/SZSE/CFFEX/SHFE/CZCE/DCE/INE)", "否", "否",
     "否", "无", "TradeWeek/TradeMonth", "否",
     "从TradeCal派生周/月交易日历"],

    # 2. stock_basic
    ["沪深股票", "基础数据", "stock_basic", "股票列表", "25",
     "pro.stock_basic(exchange='', list_status='L')",
     "2000积分;6000行/次;50次/分钟", "可选", "不需要",
     "是", "stock_basic", "StockBasic", "StockBasicTushare", "MetaDataBase",
     "ts_code", "全量替换", "monthly",
     "今天<上次更新月下月25日则跳过",
     "否", "否", "否", "否",
     "否", "无", "无", "否", ""],

    # 3. fund_basic
    ["公募基金", "基础数据", "fund_basic", "公募基金列表", "19",
     "pro.fund_basic(market='E')",
     "2000积分", "可选", "不需要",
     "是", "fund_basic", "FundBasic", "FundBasicTushare", "MetaDataBase",
     "ts_code", "全量替换", "monthly",
     "今天<上次更新月下月25日则跳过",
     "否", "否", "否", "否",
     "否", "无", "无", "否", ""],

    # 4. index_basic
    ["指数专题", "基础数据", "index_basic", "指数基本信息", "94",
     "pro.index_basic(market='SW')",
     "2000积分", "可选", "不需要",
     "是", "index_basic", "IndexBasic", "IndexBasicTushare", "MetaDataBase",
     "ts_code", "全量替换", "monthly",
     "今天<上次更新月下月25日则跳过",
     "否", "是(7个market:MSCI/CSI/SSE/SZSE/CICC/SW/OTH)", "否", "否",
     "否", "无", "无", "否", ""],

    # 5. index_classify
    ["指数专题", "基础数据", "index_classify", "申万行业分类", "181",
     "pro.index_classify(level='L1', src='SW2021')",
     "2000积分", "不需要", "不需要",
     "是", "index_classify", "IndexClassify", "IndexClassifyTushare", "MetaDataBase",
     "index_code", "全量替换", "monthly",
     "今天<上次更新月下月25日则跳过",
     "否", "是(3个level:L1/L2/L3)", "否", "否",
     "否", "无", "无", "否", ""],

    # 6. index_member
    ["指数专题", "基础数据", "index_member", "指数成分和权重", "96",
     "pro.index_member(index_code='000300.SH')",
     "2000积分", "不需要", "可选(trade_date/start_date/end_date)",
     "是", "index_member", "IndexMember", "IndexMemberTushare", "MetaDataBase",
     "index_code+con_code+in_date+out_date", "全量替换", "monthly",
     "今天<上次更新月下月25日则跳过",
     "否", "是(所有index_code,从IndexClassify表+000016.SH)", "是(drop_duplicates全表去重)", "否",
     "否", "10s", "无", "否", ""],

    # 7. daily
    ["沪深股票", "行情数据", "daily", "A股日线行情", "27",
     "pro.daily(ts_code='000001.SZ', start_date='20180701', end_date='20180718')",
     "基础积分;500次/分钟;6000行/次", "可选", "可选(trade_date/start_date/end_date)",
     "是", "daily", "Daily", "DailyTushare", "DetailDataBase",
     "ts_code+trade_date", "日期增量", "daily",
     "last_date==最近交易日则跳过",
     "否", "否", "否", "否",
     "否", "10s", "无", "否",
     "按trade_date逐日下载全市场数据"],

    # 8. daily_basic
    ["沪深股票", "行情数据", "daily_basic", "每日指标", "32",
     "pro.daily_basic(trade_date='20180726', fields='...')",
     "2000积分;6000行/次", "可选", "可选(trade_date/start_date/end_date)",
     "是", "daily_basic", "DailyBasic", "DailyBasicTushare", "DetailDataBase",
     "ts_code+trade_date", "日期增量", "daily",
     "last_date==最近交易日则跳过",
     "否", "否", "否", "否",
     "否(但API调用传flag=1)", "10s", "无", "否",
     "API调用时传入flag=1参数"],

    # 9. adj_factor
    ["沪深股票", "行情数据", "adj_factor", "复权因子", "28",
     "pro.adj_factor(ts_code='000001.SZ')",
     "2000积分", "可选", "可选(trade_date/start_date/end_date)",
     "是", "adj_factor", "AdjFactor", "AdjFactorTushare", "DetailDataBase",
     "ts_code+trade_date", "日期增量", "daily",
     "last_date==最近交易日则跳过",
     "否", "否", "否", "否",
     "否", "10s", "无", "否", ""],

    # 10. index_daily
    ["指数专题", "行情数据", "index_daily", "指数日线行情", "95",
     "pro.index_daily(ts_code='399300.SZ', start_date='20180101', end_date='20181010')",
     "2000积分;8000行/次", "必填", "可选(trade_date/start_date/end_date)",
     "是", "index_daily", "IndexDaily", "IndexDailyTushare", "DetailDataBase",
     "ts_code+trade_date", "按ts_code+日期增量", "daily",
     "逐ts_code检查各自last_date==最近交易日则跳过该code",
     "是(limit=8000)", "是(从Excel文件tushare_index_basic_info.xls读取download=1的ts_code)", "否", "否",
     "否", "20s", "无", "否",
     "需维护Excel文件标记要下载的指数"],

    # 11. fund_daily
    ["ETF专题", "行情数据", "fund_daily", "基金日线行情", "127",
     "pro.fund_daily(trade_date='20181010')",
     "5000积分", "可选", "可选(trade_date/start_date/end_date)",
     "是", "fund_daily", "FundDaily", "FundDailyTushare", "DetailDataBase",
     "ts_code+trade_date", "日期增量", "daily",
     "last_date==最近交易日则跳过",
     "是(limit=2000)", "否", "否", "否",
     "否", "10s", "无", "否",
     "使用基金日历(1999-01-08起)"],

    # 12. fund_nav
    ["公募基金", "基础数据", "fund_nav", "公募基金净值", "119",
     "pro.fund_nav(ts_code='000001.OF')",
     "2000积分", "可选", "可选(nav_date,非trade_date)",
     "是", "fund_nav", "FundNav", "FundNavTushare", "DetailDataBase",
     "ts_code+nav_date", "日期增量(nav_date)", "daily",
     "last_date==最近日期则跳过",
     "否", "否", "是(按ts_code去重,保留update_flag最高的)", "否",
     "是(update_flag=1,按ts_code排序保留第一条即最高flag)", "10s", "无", "否",
     "使用自然日历非交易日历;日期字段是nav_date非trade_date"],

    # 13. fund_adj
    ["ETF专题", "基础数据", "fund_adj", "基金复权因子", "199",
     "pro.fund_adj(ts_code='150008.SZ')",
     "2000积分", "可选", "可选(trade_date/start_date/end_date)",
     "是", "fund_adj", "FundAdj", "FundAdjTushare", "DetailDataBase",
     "ts_code+trade_date", "日期增量", "daily",
     "last_date==最近交易日则跳过",
     "是(limit=2000)", "否", "否", "否",
     "否", "10s", "无", "否",
     "使用基金日历"],

    # 14. income_vip
    ["沪深股票", "财务数据", "income_vip", "利润表(VIP)", "33",
     "pro.income_vip(ts_code='600000.SH')",
     "VIP接口;2000积分", "必填(按ts_code查)", "不需要",
     "是", "income_statement", "IncomeStatement", "IncomeStatementTushare", "FinancialByCodeBase",
     "ts_code+end_date+report_type", "全量:按ts_code逐个(DELETE+INSERT);增量:参照disclosure_date只插入新数据", "无",
     "增量:查disclosure_date表pre_date<=今天的ts_code,若都已有该季数据则跳过;未到披露日期的ts_code直接跳过",
     "否", "是(全量:遍历所有ts_code;增量:只遍历已到披露日期且缺数据的ts_code)", "是(按ann_date+update_flag排序,drop_duplicates保留last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(全量:跳过已下载的ts_code)",
     "全量DELETE+INSERT分两个事务(DuckDB);增量只INSERT新行不删旧数据"],

    # 15. cashflow_vip
    ["沪深股票", "财务数据", "cashflow_vip", "现金流量表(VIP)", "44",
     "pro.cashflow_vip(ts_code='600000.SH')",
     "VIP接口;2000积分", "必填(按ts_code查)", "不需要",
     "是", "cash_flow", "CashFlow", "CashFlowTushare", "FinancialByCodeBase",
     "ts_code+end_date+report_type", "全量:按ts_code逐个(DELETE+INSERT);增量:参照disclosure_date只插入新数据", "无",
     "增量:查disclosure_date表pre_date<=今天的ts_code,若都已有该季数据则跳过;未到披露日期的ts_code直接跳过",
     "否", "是(全量:遍历所有ts_code;增量:只遍历已到披露日期且缺数据的ts_code)", "是(按ann_date+update_flag排序,drop_duplicates保留last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(全量:跳过已下载的ts_code)",
     "全量DELETE+INSERT分两个事务(DuckDB);增量只INSERT新行不删旧数据;API返回97列ORM定义83列需过滤"],

    # 16. balancesheet_vip
    ["沪深股票", "财务数据", "balancesheet_vip", "资产负债表(VIP)", "36",
     "pro.balancesheet_vip(ts_code='600000.SH')",
     "VIP接口;2000积分", "必填(按ts_code查)", "不需要",
     "是", "balance_sheet", "BalanceSheet", "BalanceSheetTushare", "FinancialByCodeBase",
     "ts_code+end_date+report_type", "全量:按ts_code逐个(DELETE+INSERT);增量:参照disclosure_date只插入新数据", "无",
     "增量:查disclosure_date表pre_date<=今天的ts_code,若都已有该季数据则跳过;未到披露日期的ts_code直接跳过",
     "否", "是(全量:遍历所有ts_code;增量:只遍历已到披露日期且缺数据的ts_code)", "是(按ann_date+update_flag排序,drop_duplicates保留last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(全量:跳过已下载的ts_code)",
     "全量DELETE+INSERT分两个事务(DuckDB);增量只INSERT新行不删旧数据"],

    # 17. fina_indicator_vip
    ["沪深股票", "财务数据", "fina_indicator_vip", "财务指标数据(VIP)", "79",
     "pro.fina_indicator_vip(ts_code='600000.SH')",
     "VIP接口;2000积分", "必填(按ts_code查)", "不需要",
     "是", "fina_indicator", "FinaIndicator", "FinaIndicatorTushare", "FinancialByCodeBase",
     "ts_code+end_date", "全量:按ts_code逐个(DELETE+INSERT);增量:参照disclosure_date只插入新数据", "无",
     "增量:查disclosure_date表pre_date<=今天的ts_code,若都已有该季数据则跳过;未到披露日期的ts_code直接跳过",
     "否", "是(全量:遍历所有ts_code;增量:只遍历已到披露日期且缺数据的ts_code)", "是(按ann_date+update_flag排序,drop_duplicates保留last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(全量:跳过已下载的ts_code)",
     "全量DELETE+INSERT分两个事务(DuckDB);增量只INSERT新行不删旧数据;PK只有ts_code+end_date;API返回多4列需过滤"],

    # 18. forecast_vip
    ["沪深股票", "财务数据", "forecast_vip", "业绩预告(VIP)", "45",
     "pro.forecast_vip(period='20181231')",
     "VIP接口;5000行/次", "不需要", "可选(period/ann_date)",
     "是", "fina_forecast", "FinaForecast", "ForecastTushare", "FinancialVipBase",
     "ts_code+ann_date+end_date", "按period批量", "无",
     "所有period都在UpdateRecord中→转为增量(30天ann_date);无新数据则跳过",
     "是(limit=5000)", "否", "是(按PK去重,ann_date+update_flag排序取last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(跳过已完成的period)",
     "batch500删除"],

    # 19. express_vip
    ["沪深股票", "财务数据", "express_vip", "业绩快报(VIP)", "46",
     "pro.express_vip(period='20181231')",
     "VIP接口;5000行/次", "不需要", "可选(period/ann_date)",
     "是", "fina_express", "FinaExpress", "ExpressTushare", "FinancialVipBase",
     "ts_code+ann_date+end_date", "按period批量", "无",
     "所有period都在UpdateRecord中→转为增量(30天ann_date);无新数据则跳过",
     "是(limit=5000)", "否", "是(按PK去重,ann_date+update_flag排序取last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(跳过已完成的period)",
     "batch500删除"],

    # 20. fina_mainbz_vip
    ["沪深股票", "财务数据", "fina_mainbz_vip", "主营业务构成(VIP)", "81",
     "pro.fina_mainbz_vip(period='20171231')",
     "VIP接口;5000行/次", "不需要", "可选(period)",
     "是", "fina_mainbz", "FinaMainbz", "FinaMainbzTushare", "FinancialVipBase",
     "ts_code+end_date+bz_item+curr_type", "按period批量", "无",
     "所有period都在UpdateRecord中→转为增量(30天ann_date);无新数据则跳过",
     "是(limit=5000)", "否", "是(按PK去重,ann_date+update_flag排序取last)", "是",
     "是(排序后去重保留最新)", "20s", "无", "是(跳过已完成的period)",
     "batch500删除"],

    # 21. disclosure_date
    ["沪深股票", "财务数据", "disclosure_date", "财报披露计划", "162",
     "pro.disclosure_date(end_date='20181231')",
     "2000积分", "不需要", "可选(end_date)",
     "是", "disclosure_date", "DisclosureDate", "DisclosureDateTushare", "FinancialVipBase",
     "ts_code+end_date", "按end_date批量", "无",
     "所有period都在UpdateRecord中→转为增量;无新数据则跳过",
     "否", "否", "是(按PK去重)", "是",
     "否", "20s", "无", "是(跳过已完成的period)",
     "自定义_fetch_period:用end_date而非period参数调用API"],

    # 22. dividend
    ["沪深股票", "财务数据", "dividend", "分红送股", "103",
     "pro.dividend(ts_code='600000.SH')",
     "2000积分", "可选", "可选(ann_date/record_date/ex_date/imp_ann_date)",
     "是", "dividend", "Dividend", "DividendTushare", "自定义",
     "ts_code+end_date+div_proc", "全量按ts_code+增量按ann_date", "无",
     "有UpdateRecord且增量期间(30天)无新数据→跳过",
     "否", "是(初始:遍历所有ts_code)", "是(按PK去重,batch500删除)", "否",
     "否", "20s", "无", "否",
     "初始按ts_code逐个下载全历史;增量按ann_date范围下载"],

    # 23. fina_audit
    ["沪深股票", "财务数据", "fina_audit", "审计意见", "80",
     "pro.fina_audit(ts_code='600000.SH')",
     "2000积分", "可选", "可选(ann_date)",
     "是", "fina_audit", "FinaAudit", "FinaAuditTushare", "自定义",
     "ts_code+end_date", "全量按ts_code+增量按ann_date", "无",
     "有UpdateRecord且增量期间(30天)无新数据→跳过",
     "否", "是(初始:遍历所有ts_code)", "是(按PK去重,batch500删除)", "否",
     "否", "20s", "无", "否",
     "初始按ts_code逐个下载全历史;增量按ann_date范围下载"],
]

# ── 未实现接口（只填前10列，后17列为空） ──────────────────────
def unimpl(cat, subcat, api, desc, doc_id, example="", limit="", ts_code="", date_param=""):
    """创建未实现接口行"""
    return [cat, subcat, api, desc, str(doc_id), example, limit, ts_code, date_param,
            "否", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]

not_implemented = [
    # ── 沪深股票-基础数据 ──
    unimpl("沪深股票", "基础数据", "new_share", "IPO新股列表", 123, "pro.new_share(start_date='20180901', end_date='20181018')", "2000积分", "不需要", "可选(start_date/end_date)"),
    unimpl("沪深股票", "基础数据", "namechange", "股票曾用名", 100, "pro.namechange(ts_code='600848.SH')", "", "可选", "可选(start_date/end_date)"),
    unimpl("沪深股票", "基础数据", "stock_company", "上市公司基本信息", 112, "pro.stock_company(exchange='SZSE')", "120积分", "可选", "不需要"),
    unimpl("沪深股票", "基础数据", "stk_managers", "管理层", 193, "pro.stk_managers(ts_code='000001.SZ')", "", "可选", "不需要"),
    unimpl("沪深股票", "基础数据", "stk_rewards", "管理层薪酬和持股", 194, "pro.stk_rewards(ts_code='000001.SZ')", "", "可选", "可选(end_date)"),
    unimpl("沪深股票", "基础数据", "bak_daily", "备用行情", 255, "pro.bak_daily(trade_date='20181018')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "基础数据", "hs_const", "沪深股通成分股", 398, "pro.hs_const(hs_type='SH')", "", "不需要", "不需要"),
    unimpl("沪深股票", "基础数据", "stk_premarket", "股票盘前数据", 329, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "基础数据", "stk_surv", "ST股票列表", 397, "", "", "可选", "不需要"),
    unimpl("沪深股票", "基础数据", "stk_limit_risk", "ST风险警示板", 423, "", "", "可选", "不需要"),
    unimpl("沪深股票", "基础数据", "bse_code_map", "北交所代码映射", 375, "", "", "可选", "不需要"),
    unimpl("沪深股票", "基础数据", "stock_basic_hist", "历史股票列表", 262, "", "", "不需要", "可选(trade_date)"),

    # ── 沪深股票-行情数据 ──
    unimpl("沪深股票", "行情数据", "daily_real", "实时日线", 372, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "行情数据", "mins", "历史分钟数据", 370, "", "5000积分", "必填", "可选(start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "mins_real", "实时分钟数据", 374, "", "5000积分", "必填", "不需要"),
    unimpl("沪深股票", "行情数据", "weekly", "周线行情", 144, "pro.weekly(ts_code='000001.SZ')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "monthly", "月线行情", 145, "pro.monthly(ts_code='000001.SZ')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "stk_factor", "股票技术因子(复权)", 146, "pro.stk_factor(ts_code='000001.SZ')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "wm_daily_update", "周月日线更新", 336, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "行情数据", "stk_factor_update", "复权周月日线更新", 365, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "行情数据", "pro_bar", "通用行情接口", 109, "ts.pro_bar(ts_code='000001.SZ', adj='qfq')", "", "必填", "可选(start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "stk_limit", "每日涨跌停价格", 183, "pro.stk_limit(trade_date='20190802')", "2000积分;4000行/次", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "suspend_d", "每日停复牌信息", 214, "pro.suspend_d(trade_date='20200513')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "hsgt_top10", "沪深股通十大成交股", 48, "pro.hsgt_top10(trade_date='20180725')", "2000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "行情数据", "hk_hold", "港股通每日成交统计", 196, "pro.hk_hold(trade_date='20190625')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "行情数据", "ggt_top10", "港股通十大成交股", 49, "pro.ggt_top10(trade_date='20180727')", "2000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "行情数据", "ggt_monthly", "港股通每月成交统计", 197, "pro.ggt_monthly()", "2000积分", "不需要", "可选(month/start_month/end_month)"),
    unimpl("沪深股票", "行情数据", "realtime_tick", "实时tick爬虫", 315, "", "", "必填", "不需要"),
    unimpl("沪深股票", "行情数据", "realtime_list", "实时交易爬虫", 316, "", "", "不需要", "不需要"),
    unimpl("沪深股票", "行情数据", "realtime_rank", "实时排名爬虫", 317, "", "", "不需要", "不需要"),

    # ── 沪深股票-财务数据(未实现部分) ──
    unimpl("沪深股票", "财务数据", "income", "利润表(标准)", 33, "pro.income(ts_code='600000.SH')", "2000积分", "必填", "不需要"),
    unimpl("沪深股票", "财务数据", "balancesheet", "资产负债表(标准)", 36, "pro.balancesheet(ts_code='600000.SH')", "2000积分", "必填", "不需要"),
    unimpl("沪深股票", "财务数据", "cashflow", "现金流量表(标准)", 44, "pro.cashflow(ts_code='600000.SH')", "2000积分", "必填", "不需要"),
    unimpl("沪深股票", "财务数据", "forecast", "业绩预告(标准)", 45, "pro.forecast(ann_date='20190101')", "2000积分", "不需要", "可选(ann_date/period)"),
    unimpl("沪深股票", "财务数据", "express", "业绩快报(标准)", 46, "pro.express(ts_code='600000.SH')", "2000积分", "可选", "可选(ann_date/period)"),
    unimpl("沪深股票", "财务数据", "fina_indicator", "财务指标(标准)", 79, "pro.fina_indicator(ts_code='600000.SH')", "2000积分", "必填", "不需要"),
    unimpl("沪深股票", "财务数据", "fina_mainbz", "主营业务构成(标准)", 81, "pro.fina_mainbz(ts_code='000001.SZ')", "2000积分", "可选", "可选(period)"),

    # ── 沪深股票-参考数据 ──
    unimpl("沪深股票", "参考数据", "top10_holders", "前十大股东", 61, "pro.top10_holders(ts_code='600000.SH')", "2000积分", "必填", "可选(period/ann_date)"),
    unimpl("沪深股票", "参考数据", "top10_floatholders", "前十大流通股东", 62, "pro.top10_floatholders(ts_code='600000.SH')", "2000积分", "必填", "可选(period/ann_date)"),
    unimpl("沪深股票", "参考数据", "pledge_stat", "股权质押统计", 110, "pro.pledge_stat(ts_code='000001.SZ')", "2000积分", "可选", "不需要"),
    unimpl("沪深股票", "参考数据", "pledge_detail", "股权质押明细", 111, "pro.pledge_detail(ts_code='000001.SZ')", "2000积分", "可选", "不需要"),
    unimpl("沪深股票", "参考数据", "repurchase", "股票回购", 124, "pro.repurchase(ann_date='20181018')", "2000积分", "不需要", "可选(ann_date/start_date/end_date)"),
    unimpl("沪深股票", "参考数据", "share_float", "限售股解禁", 160, "pro.share_float(ts_code='000001.SZ')", "2000积分", "可选", "可选(ann_date/float_date)"),
    unimpl("沪深股票", "参考数据", "block_trade", "大宗交易", 161, "pro.block_trade(trade_date='20181015')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "参考数据", "stk_holdernumber", "股东人数", 166, "pro.stk_holdernumber(ts_code='300199.SZ')", "2000积分", "可选", "可选(enddate)"),
    unimpl("沪深股票", "参考数据", "stk_holdertrade", "股东增减持", 175, "pro.stk_holdertrade(ts_code='600000.SH')", "2000积分", "可选", "可选(ann_date/start_date/end_date)"),
    unimpl("沪深股票", "参考数据", "stk_abnormal", "个股异动", 451, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "参考数据", "stk_abnormal_severe", "严重异动", 452, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "参考数据", "stk_risk_warning", "风险警示证券", 453, "", "", "可选", "可选(trade_date)"),

    # ── 沪深股票-特色数据 ──
    unimpl("沪深股票", "特色数据", "broker_recommend", "券商盈利预测", 292, "", "5000积分", "可选", "可选(month)"),
    unimpl("沪深股票", "特色数据", "cyq_perf", "每日筹码及胜率", 293, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "cyq_chips", "每日筹码分布", 294, "", "5000积分", "必填", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "特色数据", "stk_factor_pro", "股票技术因子Pro", 328, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "ccass_hold", "中央结算持股统计", 295, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "ccass_hold_detail", "中央结算持股明细", 274, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "hk_hold", "沪深港股通持股", 188, "", "2000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "stk_auction", "开盘集合竞价", 353, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "特色数据", "stk_auction_c", "收盘集合竞价", 354, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "特色数据", "stk_mj9", "魔力九转指标", 364, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "ah_comparisons", "AH股价差", 399, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "特色数据", "stk_surv", "机构调研", 275, "", "5000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "特色数据", "broker_monthly", "券商月度金股", 267, "", "5000积分", "不需要", "可选(month)"),

    # ── 沪深股票-两融及转融通 ──
    unimpl("沪深股票", "两融及转融通", "margin", "融资融券交易汇总", 58, "pro.margin(trade_date='20180802')", "2000积分", "不需要", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "两融及转融通", "margin_detail", "融资融券交易明细", 59, "pro.margin_detail(trade_date='20180802')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "两融及转融通", "margin_target", "融资融券标的(盘前)", 326, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "两融及转融通", "slb_len_mm", "转融通融出汇总(停)", 332, "", "", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "两融及转融通", "slb_len", "转融通融资汇总", 331, "", "", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "两融及转融通", "slb_sec_mm", "转融通融出明细(停)", 333, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "两融及转融通", "slb_sec", "做市借券汇总(停)", 334, "", "", "不需要", "可选(trade_date)"),

    # ── 沪深股票-资金流向 ──
    unimpl("沪深股票", "资金流向", "moneyflow", "个股资金流向", 170, "pro.moneyflow(trade_date='20190102')", "2000积分;6000行/次", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_ths", "个股资金流向(同花顺)", 348, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_dc", "个股资金流向(东财)", 349, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_ind_ths", "行业资金流向(同花顺)", 343, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_ind_dc", "板块资金流向(东财)", 344, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_mkt_dc", "大盘资金流向(东财)", 345, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_hsgt", "沪深港通资金流向", 47, "pro.moneyflow_hsgt(trade_date='20180725')", "2000积分", "不需要", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "资金流向", "moneyflow_ind_ths_sector", "板块资金流向(同花顺)", 371, "", "5000积分", "不需要", "可选(trade_date)"),

    # ── 沪深股票-打板专题 ──
    unimpl("沪深股票", "打板专题", "top_list", "龙虎榜每日明细", 106, "pro.top_list(trade_date='20180928')", "2000积分;5000行/次", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "top_inst", "龙虎榜机构交易明细", 107, "pro.top_inst(trade_date='20180928')", "2000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "ths_hot", "同花顺App热榜", 320, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "打板专题", "dc_hot", "东财App热榜", 321, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "打板专题", "limit_list_d", "涨跌停统计", 298, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "stk_limit_ths", "涨停排名(同花顺)", 355, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "limit_step", "连板股统计", 356, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "limit_sec_strong", "最强板块统计", 357, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "ths_index", "同花顺概念和行业指数", 260, "pro.ths_index()", "2000积分", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "ths_daily", "同花顺概念行业日线", 259, "pro.ths_daily(ts_code='885760.TI')", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("沪深股票", "打板专题", "ths_member", "同花顺概念行业成分", 261, "pro.ths_member(ts_code='885760.TI')", "2000积分", "必填", "不需要"),
    unimpl("沪深股票", "打板专题", "dc_index", "东财概念和行业指数", 382, "", "", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "dc_concept", "东财概念板块", 362, "", "", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "dc_member", "东财概念成分", 363, "", "", "必填", "不需要"),
    unimpl("沪深股票", "打板专题", "stk_auction_o", "开盘集合竞价当日", 369, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "hot_trader", "热门游资登记", 311, "", "5000积分", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "hot_trader_daily", "游资每日交易", 312, "", "5000积分", "不需要", "可选(trade_date)"),
    unimpl("沪深股票", "打板专题", "tdx_index", "通达信板块信息", 376, "", "", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "tdx_member", "通达信板块成分", 377, "", "", "必填", "不需要"),
    unimpl("沪深股票", "打板专题", "tdx_daily", "通达信板块行情", 378, "", "", "可选", "可选(trade_date)"),
    unimpl("沪深股票", "打板专题", "top_list_lunch", "龙虎榜(午间)", 347, "", "5000积分", "不需要", "必填(trade_date)"),
    unimpl("沪深股票", "打板专题", "ths_member_lunch", "题材成分(午间)", 351, "", "5000积分", "必填", "不需要"),
    unimpl("沪深股票", "打板专题", "dc_theme", "东财题材数据", 421, "", "", "不需要", "不需要"),
    unimpl("沪深股票", "打板专题", "dc_theme_member", "东财题材成分", 422, "", "", "必填", "不需要"),

    # ── ETF专题 ──
    unimpl("ETF专题", "基础数据", "etf_basic", "ETF基本信息", 385, "", "8000积分", "可选", "不需要"),
    unimpl("ETF专题", "基础数据", "etf_benchmark", "ETF基准指数", 386, "", "", "可选", "不需要"),
    unimpl("ETF专题", "行情数据", "etf_mins_real", "ETF实时分钟", 416, "", "5000积分", "必填", "不需要"),
    unimpl("ETF专题", "行情数据", "etf_mins", "ETF历史分钟", 387, "", "5000积分", "必填", "可选(start_date/end_date)"),
    unimpl("ETF专题", "行情数据", "etf_daily_real", "ETF实时日线", 400, "", "", "可选", "可选(trade_date)"),
    unimpl("ETF专题", "行情数据", "etf_daily", "ETF日线行情", 127, "", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("ETF专题", "基础数据", "etf_adj", "ETF复权因子", 199, "", "", "可选", "可选(trade_date)"),
    unimpl("ETF专题", "基础数据", "etf_scale", "ETF基金规模", 408, "", "", "可选", "可选(trade_date)"),
    unimpl("ETF专题", "行情数据", "etf_iopv_real", "ETF实时参考", 454, "", "", "必填", "不需要"),

    # ── 指数专题(未实现部分) ──
    unimpl("指数专题", "行情数据", "index_daily_real", "指数实时日线", 403, "", "", "可选", "可选(trade_date)"),
    unimpl("指数专题", "行情数据", "index_mins_real", "指数实时分钟", 420, "", "5000积分", "必填", "不需要"),
    unimpl("指数专题", "行情数据", "index_weekly", "指数周线行情", 171, "pro.index_weekly(ts_code='000001.SH')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "行情数据", "index_mins", "指数历史分钟", 419, "", "5000积分", "必填", "可选(start_date/end_date)"),
    unimpl("指数专题", "行情数据", "index_monthly", "指数月线行情", 172, "pro.index_monthly(ts_code='000001.SH')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "基础数据", "index_dailybasic", "大盘指数每日指标", 128, "pro.index_dailybasic(trade_date='20181018')", "400积分;3000行/次", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "基础数据", "sw_daily", "申万行业指数日线", 327, "", "2000积分", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "基础数据", "sw_member_tiered", "申万行业成分(分级)", 335, "", "", "可选", "不需要"),
    unimpl("指数专题", "行情数据", "sw_real", "申万实时行情", 417, "", "", "不需要", "不需要"),
    unimpl("指数专题", "基础数据", "ci_member", "中信行业成分", 373, "", "", "可选", "不需要"),
    unimpl("指数专题", "行情数据", "ci_daily", "中信行业指数日线", 308, "", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "行情数据", "index_global", "国际主要指数", 211, "pro.index_global(ts_code='XIN9')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("指数专题", "特色数据", "index_factor_pro", "指数技术因子Pro", 358, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("指数专题", "基础数据", "sz_daily_info", "深圳市场每日交易统计", 268, "", "", "不需要", "可选(trade_date)"),
    unimpl("指数专题", "基础数据", "daily_info", "沪深每日交易统计", 215, "pro.daily_info(trade_date='20181213')", "", "不需要", "可选(trade_date/start_date/end_date)"),

    # ── 公募基金(未实现部分) ──
    unimpl("公募基金", "基础数据", "fund_manager", "基金经理", 118, "pro.fund_manager(ts_code='000001.OF')", "", "可选", "不需要"),
    unimpl("公募基金", "基础数据", "fund_manager_info", "基金经理个人信息", 208, "", "", "不需要", "不需要"),
    unimpl("公募基金", "基础数据", "fund_share", "基金规模", 207, "pro.fund_share(ts_code='150008.SZ')", "", "可选", "可选(trade_date)"),
    unimpl("公募基金", "基础数据", "fund_div", "基金分红", 120, "pro.fund_div(ts_code='150008.SZ')", "400积分", "可选", "可选(ann_date/ex_date/pay_date/imp_ann_date)"),
    unimpl("公募基金", "基础数据", "fund_portfolio", "基金持仓", 121, "pro.fund_portfolio(ts_code='000001.OF')", "2000积分", "必填", "可选(start_date/end_date)"),
    unimpl("公募基金", "特色数据", "fund_factor_pro", "基金技术因子Pro", 359, "", "5000积分", "可选", "可选(trade_date)"),

    # ── 期货数据 ──
    unimpl("期货数据", "基础数据", "fut_basic", "期货合约信息", 135, "pro.fut_basic(exchange='DCE', fut_type='1')", "", "不需要", "不需要"),
    unimpl("期货数据", "基础数据", "trade_cal_fut", "期货交易日历", 137, "pro.trade_cal(exchange='DCE')", "", "不需要", "可选(start_date/end_date)"),
    unimpl("期货数据", "行情数据", "fut_daily", "期货日线行情", 138, "pro.fut_daily(ts_code='CU1811.SHF')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "行情数据", "fut_wm_daily", "期货周月行情日更", 337, "", "", "可选", "可选(trade_date)"),
    unimpl("期货数据", "行情数据", "fut_mins", "期货历史分钟", 313, "", "5000积分", "必填", "可选(start_date/end_date)"),
    unimpl("期货数据", "行情数据", "fut_mins_real", "期货实时分钟", 340, "", "5000积分", "必填", "不需要"),
    unimpl("期货数据", "基础数据", "fut_wsr", "仓单日报", 140, "pro.fut_wsr(trade_date='20181113')", "", "不需要", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "基础数据", "fut_settle", "每日结算参数", 141, "pro.fut_settle(trade_date='20181114')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "行情数据", "fut_tick", "历史tick数据", 314, "", "5000积分", "必填", "可选(trade_date)"),
    unimpl("期货数据", "基础数据", "fut_holding", "每日成交持仓排名", 139, "pro.fut_holding(trade_date='20181113')", "", "不需要", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "行情数据", "index_nh", "南华期货指数行情", 155, "pro.index_nh(ts_code='NH0100')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "基础数据", "fut_mapping", "期货主力与连续合约", 189, "pro.fut_mapping(ts_code='CU.SHF')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("期货数据", "基础数据", "fut_weekly_detail", "期货周报主要品种", 216, "pro.fut_weekly_detail(week='20181207')", "", "不需要", "可选(week/prd/start_week/end_week)"),
    unimpl("期货数据", "基础数据", "fut_stk_limit", "期货每日涨跌停价格", 368, "", "", "可选", "可选(trade_date)"),

    # ── 现货数据 ──
    unimpl("现货数据", "基础数据", "sge_basic", "上海金基本信息", 284, "pro.sge_basic()", "", "可选", "不需要"),
    unimpl("现货数据", "行情数据", "sge_daily", "上海金日行情", 285, "pro.sge_daily(ts_code='Au99.99')", "", "可选", "可选(trade_date/start_date/end_date)"),

    # ── 期权数据 ──
    unimpl("期权数据", "基础数据", "opt_basic", "期权合约信息", 158, "pro.opt_basic(exchange='SSE')", "", "不需要", "不需要"),
    unimpl("期权数据", "行情数据", "opt_daily", "期权日线行情", 159, "pro.opt_daily(ts_code='10000001.SH')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("期权数据", "行情数据", "opt_mins", "期权分钟数据", 341, "", "5000积分", "必填", "可选(start_date/end_date)"),

    # ── 债券专题 ──
    unimpl("债券专题", "基础数据", "cb_basic", "可转债基本信息", 185, "pro.cb_basic()", "", "可选", "不需要"),
    unimpl("债券专题", "基础数据", "cb_issue", "可转债发行", 186, "pro.cb_issue()", "", "可选", "不需要"),
    unimpl("债券专题", "基础数据", "cb_call", "可转债赎回", 269, "", "", "可选", "不需要"),
    unimpl("债券专题", "基础数据", "cb_rate", "可转债票面利率", 305, "", "", "可选", "不需要"),
    unimpl("债券专题", "行情数据", "cb_daily", "可转债行情", 187, "pro.cb_daily(ts_code='113527.SH')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("债券专题", "特色数据", "cb_factor_pro", "可转债技术因子Pro", 392, "", "5000积分", "可选", "可选(trade_date)"),
    unimpl("债券专题", "基础数据", "cb_price_chg", "可转债转股价变动", 246, "pro.cb_price_chg(ts_code='128013.SZ')", "", "可选", "不需要"),
    unimpl("债券专题", "基础数据", "cb_share", "可转债转股结果", 247, "pro.cb_share(ts_code='128013.SZ')", "", "可选", "不需要"),
    unimpl("债券专题", "行情数据", "repo_daily", "债券回购日行情", 256, "pro.repo_daily(trade_date='20181024')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("债券专题", "行情数据", "bond_blk", "债券大宗交易", 271, "", "", "可选", "可选(trade_date)"),
    unimpl("债券专题", "行情数据", "bond_blk_detail", "债券大宗交易明细", 272, "", "", "可选", "可选(trade_date)"),
    unimpl("债券专题", "基础数据", "yc_cb", "国债收益率曲线", 201, "pro.yc_cb(ts_code='1001.CB', curve_type='0')", "", "必填", "可选(trade_date)"),
    unimpl("债券专题", "行情数据", "eco_cal", "全球财经事件", 233, "pro.eco_cal(start_date='20181101', end_date='20181201')", "", "不需要", "可选(start_date/end_date)"),
    unimpl("债券专题", "行情数据", "bond_otc_quote", "柜台流通式债券行情", 322, "", "", "可选", "可选(trade_date)"),
    unimpl("债券专题", "行情数据", "bond_otc_best", "柜台流通式债券最优报价", 323, "", "", "可选", "可选(trade_date)"),

    # ── 外汇数据(未实现部分) ──
    unimpl("外汇数据", "基础数据", "fx_obasic", "外汇基本信息", 178, "pro.fx_obasic(exchange='FXCM')", "2000积分", "可选", "不需要"),
    unimpl("外汇数据", "行情数据", "fx_daily", "外汇日线行情", 179, "pro.fx_daily(ts_code='USDCNH.FXCM')", "", "可选", "可选(trade_date/start_date/end_date)"),

    # ── 港股数据 ──
    unimpl("港股数据", "基础数据", "hk_basic", "港股基本信息", 191, "pro.hk_basic()", "", "可选", "不需要"),
    unimpl("港股数据", "基础数据", "hk_tradecal", "港股交易日历", 250, "", "", "不需要", "可选(start_date/end_date)"),
    unimpl("港股数据", "行情数据", "hk_daily", "港股日线行情", 192, "pro.hk_daily(ts_code='00001.HK')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("港股数据", "行情数据", "hk_daily_adj", "港股复权行情", 339, "", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("港股数据", "基础数据", "hk_adj_factor", "港股复权因子", 401, "", "", "可选", "可选(trade_date)"),
    unimpl("港股数据", "行情数据", "hk_mins", "港股分钟数据", 304, "", "5000积分", "必填", "可选(start_date/end_date)"),
    unimpl("港股数据", "行情数据", "hk_daily_real", "港股实时日线", 383, "", "", "可选", "可选(trade_date)"),
    unimpl("港股数据", "财务数据", "hk_income", "港股利润表", 389, "", "", "必填", "可选(period)"),
    unimpl("港股数据", "财务数据", "hk_balance", "港股资产负债表", 390, "", "", "必填", "可选(period)"),
    unimpl("港股数据", "财务数据", "hk_cashflow", "港股现金流量表", 391, "", "", "必填", "可选(period)"),
    unimpl("港股数据", "财务数据", "hk_fina_indicator", "港股财务指标", 388, "", "", "必填", "可选(period)"),

    # ── 美股数据 ──
    unimpl("美股数据", "基础数据", "us_basic", "美股基本信息", 252, "pro.us_basic()", "", "可选", "不需要"),
    unimpl("美股数据", "基础数据", "us_tradecal", "美股交易日历", 253, "", "", "不需要", "可选(start_date/end_date)"),
    unimpl("美股数据", "行情数据", "us_daily", "美股日线行情", 254, "pro.us_daily(ts_code='AAPL')", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("美股数据", "行情数据", "us_daily_adj", "美股复权行情", 338, "", "", "可选", "可选(trade_date/start_date/end_date)"),
    unimpl("美股数据", "基础数据", "us_adj_factor", "美股复权因子", 402, "", "", "可选", "可选(trade_date)"),
    unimpl("美股数据", "财务数据", "us_income", "美股利润表", 394, "", "", "必填", "可选(period)"),
    unimpl("美股数据", "财务数据", "us_balance", "美股资产负债表", 395, "", "", "必填", "可选(period)"),
    unimpl("美股数据", "财务数据", "us_cashflow", "美股现金流量表", 396, "", "", "必填", "可选(period)"),
    unimpl("美股数据", "财务数据", "us_fina_indicator", "美股财务指标", 393, "", "", "必填", "可选(period)"),

    # ── 行业经济 ──
    unimpl("行业经济", "基础数据", "tw_monthly_revenue", "台湾电子月营收", 88, "", "", "不需要", "可选(month)"),
    unimpl("行业经济", "基础数据", "tw_revenue_detail", "台湾电子营收明细", 87, "", "", "可选", "可选(month)"),
    unimpl("行业经济", "基础数据", "bo_monthly", "电影月度票房", 113, "pro.bo_monthly(date='201811')", "", "不需要", "可选(date)"),
    unimpl("行业经济", "基础数据", "bo_weekly", "电影周度票房", 114, "pro.bo_weekly(date='20181015')", "", "不需要", "可选(date)"),
    unimpl("行业经济", "基础数据", "bo_daily", "电影日度票房", 115, "pro.bo_daily(date='20181015')", "", "不需要", "可选(date)"),
    unimpl("行业经济", "基础数据", "bo_cinema", "影院日度票房", 116, "pro.bo_cinema(date='20181015')", "", "不需要", "可选(date)"),
    unimpl("行业经济", "基础数据", "film_record", "全国拍摄制作电影备案", 156, "", "", "不需要", "不需要"),
    unimpl("行业经济", "基础数据", "tv_record", "全国电视剧备案", 180, "", "", "不需要", "不需要"),

    # ── 宏观经济-国内 ──
    unimpl("宏观经济", "国内宏观", "shibor", "上海银行同业拆借利率", 149, "pro.shibor(start_date='20180101', end_date='20181101')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "shibor_quote", "Shibor报价", 150, "pro.shibor_quote(date='20181101')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "shibor_lpr", "LPR贷款基准利率", 151, "pro.shibor_lpr(start_date='20180101')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "libor", "Libor利率", 152, "pro.libor(curr_type='USD')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "hibor", "Hibor利率", 153, "pro.hibor(start_date='20180810')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "wz_index", "温州民间借贷利率", 173, "pro.wz_index(start_date='20180101')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "gz_index", "广州民间借贷利率", 174, "pro.gz_index(start_date='20180101')", "", "不需要", "可选(start_date/end_date/date)"),
    unimpl("宏观经济", "国内宏观", "cn_gdp", "GDP", 227, "pro.cn_gdp(q='2018Q1')", "", "不需要", "可选(q/start_q/end_q)"),
    unimpl("宏观经济", "国内宏观", "cn_cpi", "CPI", 228, "pro.cn_cpi(m='201801')", "", "不需要", "可选(m/start_m/end_m)"),
    unimpl("宏观经济", "国内宏观", "cn_ppi", "PPI", 245, "pro.cn_ppi(m='201801')", "", "不需要", "可选(m/start_m/end_m)"),
    unimpl("宏观经济", "国内宏观", "cn_m", "货币供应量月报", 242, "pro.cn_m(m='201801')", "", "不需要", "可选(m/start_m/end_m)"),
    unimpl("宏观经济", "国内宏观", "sf_month", "社会融资月报", 310, "", "", "不需要", "可选(m/start_m/end_m)"),
    unimpl("宏观经济", "国内宏观", "cn_pmi", "PMI", 325, "", "", "不需要", "可选(m/start_m/end_m)"),

    # ── 宏观经济-国际 ──
    unimpl("宏观经济", "国际宏观", "us_tycr", "美国国债收益率曲线", 219, "", "", "不需要", "可选(date)"),
    unimpl("宏观经济", "国际宏观", "us_trycr", "美国实际国债收益率", 220, "", "", "不需要", "可选(date)"),
    unimpl("宏观经济", "国际宏观", "us_tbr", "美国短期国债利率", 221, "", "", "不需要", "可选(date)"),
    unimpl("宏观经济", "国际宏观", "us_tltr", "美国长期国债利率", 222, "", "", "不需要", "可选(date)"),
    unimpl("宏观经济", "国际宏观", "us_trltr", "美国长期国债利率均值", 223, "", "", "不需要", "可选(date)"),

    # ── 大模型语料 ──
    unimpl("大模型语料", "基础数据", "gov_policy", "政府政策库", 406, "", "8000积分", "不需要", "可选(start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "report_rc", "券商研究报告", 415, "", "8000积分", "可选", "可选(start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "news", "新闻快讯", 143, "pro.news(src='sina')", "2000积分", "不需要", "可选(start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "major_news", "新闻长文", 195, "", "2000积分", "不需要", "可选(start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "cctv_news", "新闻联播稿", 154, "pro.cctv_news(date='20190101')", "", "不需要", "可选(date/start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "anns", "上市公司公告", 176, "", "2000积分", "可选", "可选(ann_date/start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "irm_qa_sse", "上交所e互动问答", 366, "", "", "可选", "可选(start_date/end_date)"),
    unimpl("大模型语料", "基础数据", "irm_qa_szse", "深交所互动易问答", 367, "", "", "可选", "可选(start_date/end_date)"),

    # ── 财富管理 ──
    unimpl("财富管理", "基础数据", "fund_sales_ratio", "公募基金销售保有", 265, "", "", "不需要", "可选(quarter)"),
    unimpl("财富管理", "基础数据", "fund_sales_vol", "销售机构基金保有规模", 266, "", "", "不需要", "可选(quarter)"),
]

# ── 写入 CSV ──────────────────────────────────────────────
output_path = os.path.join(os.path.dirname(__file__), "tushare-接口信息.csv")

with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(HEADERS)
    for row in implemented:
        assert len(row) == len(HEADERS), f"列数不匹配: {len(row)} vs {len(HEADERS)}, 接口: {row[2]}"
        writer.writerow(row)
    for row in not_implemented:
        assert len(row) == len(HEADERS), f"列数不匹配: {len(row)} vs {len(HEADERS)}, 接口: {row[2]}"
        writer.writerow(row)

total = len(implemented) + len(not_implemented)
print(f"✅ 已生成 {output_path}")
print(f"   已实现接口: {len(implemented)} 行")
print(f"   未实现接口: {len(not_implemented)} 行")
print(f"   总计: {total} 行, {len(HEADERS)} 列")
