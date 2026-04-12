""" 财务报表 ORM 表定义
包含：利润表、现金流量表、资产负债表、财务指标
"""
from orm_models.base import Base
from sqlalchemy import Column, Float, String, DateTime


class IncomeStatement(Base):
    """ 利润表 (income_vip) """
    __tablename__ = "income_statement"
    # 复合主键：ts_code + end_date + report_type 拼接
    ts_code_end_date_report_type = Column(String, primary_key=True)
    # 标识字段
    ts_code     = Column(String, index=True, comment='TS股票代码')
    ann_date    = Column(DateTime, index=True, comment='公告日期')
    f_ann_date  = Column(DateTime, comment='实际公告日期')
    end_date    = Column(DateTime, index=True, comment='报告期')
    report_type = Column(String, index=True, comment='报告类型（1合并、2单季、6母公司等）')
    comp_type   = Column(String, comment='公司类型（1一般、2银行、3保险、4证券）')
    # 每股指标
    basic_eps   = Column(Float, comment='基本每股收益')
    diluted_eps = Column(Float, comment='稀释每股收益')
    # 收入
    total_revenue      = Column(Float, comment='营业总收入')
    revenue            = Column(Float, comment='营业收入')
    int_income         = Column(Float, comment='利息收入')
    prem_earned_net    = Column(Float, comment='已赚保费')
    comm_income        = Column(Float, comment='手续费及佣金收入')
    n_commis_income    = Column(Float, comment='手续费及佣金净收入')
    # 成本费用
    total_operate_cost = Column(Float, comment='营业总成本')
    operate_cost       = Column(Float, comment='营业成本')
    int_exp            = Column(Float, comment='利息支出')
    sell_exp           = Column(Float, comment='销售费用')
    admin_exp          = Column(Float, comment='管理费用')
    fin_exp            = Column(Float, comment='财务费用')
    assets_impair_loss = Column(Float, comment='资产减值损失')
    # 利润
    operate_profit     = Column(Float, comment='营业利润')
    non_oper_income    = Column(Float, comment='营业外收入')
    non_oper_exp       = Column(Float, comment='营业外支出')
    total_profit       = Column(Float, comment='利润总额')
    income_tax         = Column(Float, comment='所得税费用')
    n_income           = Column(Float, comment='净利润')
    n_income_attr_p    = Column(Float, comment='归属母公司股东的净利润')
    minority_gain      = Column(Float, comment='少数股东损益')
    # 综合收益
    oth_compr_income   = Column(Float, comment='其他综合收益')
    t_compr_income     = Column(Float, comment='综合收益总额')
    compr_inc_attr_p   = Column(Float, comment='归属母公司(或股东)的综合收益总额')
    compr_inc_attr_m_s = Column(Float, comment='归属少数股东的综合收益总额')
    # 息税前利润
    ebit               = Column(Float, comment='息税前利润')
    ebitda             = Column(Float, comment='息税折旧摊销前利润')
    # 非经常性
    non_rec_income     = Column(Float, comment='非经常性损益')


class CashFlow(Base):
    """ 现金流量表 (cashflow_vip) """
    __tablename__ = "cash_flow"
    ts_code_end_date_report_type = Column(String, primary_key=True)
    # 标识字段
    ts_code     = Column(String, index=True, comment='TS股票代码')
    ann_date    = Column(DateTime, index=True, comment='公告日期')
    f_ann_date  = Column(DateTime, comment='实际公告日期')
    end_date    = Column(DateTime, index=True, comment='报告期')
    report_type = Column(String, index=True, comment='报告类型')
    comp_type   = Column(String, comment='公司类型')
    # 经营活动
    net_profit          = Column(Float, comment='净利润')
    finan_exp           = Column(Float, comment='财务费用')
    c_fr_sale_sg        = Column(Float, comment='销售商品、提供劳务收到的现金')
    recp_tax_rends      = Column(Float, comment='收到的税费返还')
    c_paid_goods_s      = Column(Float, comment='购买商品、接受劳务支付的现金')
    c_paid_to_for_empl  = Column(Float, comment='支付给职工及为职工支付的现金')
    c_paid_for_taxes    = Column(Float, comment='支付的各项税费')
    n_cashflow_act      = Column(Float, comment='经营活动产生的现金流量净额')
    # 投资活动
    oth_recp_ral_inv_act     = Column(Float, comment='收到其他与投资活动有关的现金')
    c_disp_withdrwl_invest   = Column(Float, comment='收回投资收到的现金')
    c_recp_return_invest     = Column(Float, comment='取得投资收益收到的现金')
    c_pay_acq_const_fiolta   = Column(Float, comment='购建固定资产、无形资产等支付的现金')
    c_paid_invest            = Column(Float, comment='投资支付的现金')
    n_cashflow_inv_act       = Column(Float, comment='投资活动产生的现金流量净额')
    # 筹资活动
    c_recp_borrow            = Column(Float, comment='取得借款收到的现金')
    proc_issue_bonds         = Column(Float, comment='发行债券收到的现金')
    c_repay_bonds            = Column(Float, comment='偿还债务支付的现金')
    c_pay_dist_dpcp_int_exp  = Column(Float, comment='分配股利、利润或偿付利息支付的现金')
    n_cash_flows_fnc_act     = Column(Float, comment='筹资活动产生的现金流量净额')
    # 汇率影响 & 净增加
    eff_fx_flu_cash          = Column(Float, comment='汇率变动对现金的影响')
    net_incr_cash_cash_equ   = Column(Float, comment='现金及现金等价物净增加额')
    cash_cash_equ_beg_period = Column(Float, comment='期初现金及现金等价物余额')
    cash_cash_equ_end_period = Column(Float, comment='期末现金及现金等价物余额')
    # 自由现金流
    free_cashflow            = Column(Float, comment='企业自由现金流量')


class BalanceSheet(Base):
    """ 资产负债表 (balancesheet_vip) """
    __tablename__ = "balance_sheet"
    ts_code_end_date_report_type = Column(String, primary_key=True)
    # 标识字段
    ts_code     = Column(String, index=True, comment='TS股票代码')
    ann_date    = Column(DateTime, index=True, comment='公告日期')
    f_ann_date  = Column(DateTime, comment='实际公告日期')
    end_date    = Column(DateTime, index=True, comment='报告期')
    report_type = Column(String, index=True, comment='报告类型')
    comp_type   = Column(String, comment='公司类型')
    # 流动资产
    money_cap        = Column(Float, comment='货币资金')
    trad_asset       = Column(Float, comment='交易性金融资产')
    notes_receiv     = Column(Float, comment='应收票据')
    accounts_receiv  = Column(Float, comment='应收账款')
    oth_receiv       = Column(Float, comment='其他应收款')
    prepayment       = Column(Float, comment='预付款项')
    inventories      = Column(Float, comment='存货')
    total_cur_assets = Column(Float, comment='流动资产合计')
    # 非流动资产
    fix_assets       = Column(Float, comment='固定资产')
    cip              = Column(Float, comment='在建工程')
    goodwill         = Column(Float, comment='商誉')
    intan_assets     = Column(Float, comment='无形资产')
    r_and_d          = Column(Float, comment='研发支出')
    lt_invest        = Column(Float, comment='长期股权投资')
    total_nca        = Column(Float, comment='非流动资产合计')
    total_assets     = Column(Float, comment='资产总计')
    # 流动负债
    st_borr          = Column(Float, comment='短期借款')
    notes_payable    = Column(Float, comment='应付票据')
    accounts_payable = Column(Float, comment='应付账款')
    adv_receipts     = Column(Float, comment='预收款项')
    total_cur_liab   = Column(Float, comment='流动负债合计')
    # 非流动负债
    lt_borr          = Column(Float, comment='长期借款')
    bond_payable     = Column(Float, comment='应付债券')
    total_ncl        = Column(Float, comment='非流动负债合计')
    total_liab       = Column(Float, comment='负债合计')
    # 所有者权益
    total_hldr_eqy_exc_min_int = Column(Float, comment='归属母公司股东权益合计')
    minority_int               = Column(Float, comment='少数股东权益')
    total_hldr_eqy_inc_min_int = Column(Float, comment='股东权益合计（含少数股东权益）')
    total_liab_hldr_eqy        = Column(Float, comment='负债及股东权益总计')


class FinaIndicator(Base):
    """ 财务指标数据 (fina_indicator_vip) """
    __tablename__ = "fina_indicator"
    ts_code_end_date = Column(String, primary_key=True)
    # 标识字段
    ts_code  = Column(String, index=True, comment='TS股票代码')
    ann_date = Column(DateTime, index=True, comment='公告日期')
    end_date = Column(DateTime, index=True, comment='报告期')
    # 每股指标
    eps          = Column(Float, comment='基本每股收益')
    dt_eps       = Column(Float, comment='稀释每股收益（扣非）')
    bps          = Column(Float, comment='每股净资产')
    ocfps        = Column(Float, comment='每股经营现金流')
    revenue_ps   = Column(Float, comment='每股营业收入')
    capital_rese_ps = Column(Float, comment='每股资本公积金')
    surplus_rese_ps = Column(Float, comment='每股盈余公积')
    undist_profit_ps = Column(Float, comment='每股未分配利润')
    # 盈利能力
    net_profit       = Column(Float, comment='净利润（元）')
    dt_net_profit    = Column(Float, comment='扣除非经常性损益后的净利润')
    gross_margin     = Column(Float, comment='毛利率（%）')
    netprofit_margin = Column(Float, comment='净利率（%）')
    roe              = Column(Float, comment='净资产收益率（%）')
    roe_yearly       = Column(Float, comment='年化净资产收益率（%）')
    roe_dt           = Column(Float, comment='扣非净资产收益率（%）')
    roa              = Column(Float, comment='总资产报酬率（%）')
    roic             = Column(Float, comment='投入资本回报率（%）')
    # 偿债能力
    current_ratio    = Column(Float, comment='流动比率')
    quick_ratio      = Column(Float, comment='速动比率')
    cash_ratio       = Column(Float, comment='保守速动比率')
    debt_to_assets   = Column(Float, comment='资产负债率（%）')
    assets_to_eqt    = Column(Float, comment='权益乘数')
    # 营运能力
    inv_turn         = Column(Float, comment='存货周转率（次）')
    inv_turndays     = Column(Float, comment='存货周转天数')
    ar_turn          = Column(Float, comment='应收账款周转率（次）')
    ar_turndays      = Column(Float, comment='应收账款周转天数')
    assets_turn      = Column(Float, comment='总资产周转率（次）')
    # 成长能力
    revenue_yoy      = Column(Float, comment='营业收入同比增长（%）')
    netprofit_yoy    = Column(Float, comment='净利润同比增长（%）')
    assets_yoy       = Column(Float, comment='资产增长率（%）')
    eqt_yoy          = Column(Float, comment='净资产增长率（%）')
    # 单季度指标
    q_eps            = Column(Float, comment='每股收益（单季度）')
    q_dt_eps         = Column(Float, comment='每股收益（扣非单季度）')
    q_roe            = Column(Float, comment='净资产收益率（单季度）')
    q_dt_roe         = Column(Float, comment='净资产收益率（扣非单季度）')
    q_revenue        = Column(Float, comment='营业收入（单季度）')
    q_revenue_qoq    = Column(Float, comment='营业收入（单季度环比）')
    q_netprofit      = Column(Float, comment='净利润（单季度）')
    q_netprofit_qoq  = Column(Float, comment='净利润（单季度环比）')
    q_ocf_to_sales   = Column(Float, comment='经营现金流/营业收入（单季度）')
    # 估值辅助
    peg              = Column(Float, comment='市盈率相对盈利增长比率')
    net_profit_after_nr_lp = Column(Float, comment='扣除非经常性损益后的净利润（元）')
