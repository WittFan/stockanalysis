import sqlite3

def create_table():
    """创建表"""
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    # 1.创建股票列表stock_basic
    sql = """create table if not exists stock_basic(
        ts_code varchar(32) PRIMARY KEY not null,
        symbol varchar(32) not null,
        name varchar(32) not null,
        area varchar(32) not null,
        industry varchar(32) not null,
        fullname varchar(32) not null,
        enname varchar(32) not null,
        cnspell varchar(32) not null,
        market varchar(32) not null,
        exchange varchar(32) not null,
        curr_type varchar(32) not null,
        list_status varchar(32) not null,
        list_date varchar(32) not null,
        delist_date varchar(32) not null,
        is_hs varchar(32) not null);"""
    c.execute(sql)

    # 2.创建交易日历trade_cal
    sql = """create table if not exists trade_cal(
        exchange_cal_date varchar(32) PRIMARY KEY not null,
        exchange varchar(32) not null,
        cal_date varchar(32) not null,
        is_open varchar(32) not null,
        pretrade_date varchar(32) not null);"""
    c.execute(sql)

    # 3.创建股票曾用名namechange
    sql = """create table if not exists namechange(
        ts_code_ann_date varchar(32) PRIMARY KEY not null,
        name varchar(32) not null,
        start_date varchar(32) not null,
        end_date varchar(32) not null,
        ann_date varchar(32) not null,
        change_reason varchar(32) not null);"""
    c.execute(sql)
    # 4.创建沪深股通成份股hs_const
    sql = """create table if not exists hs_const(
        ts_code_in_date_out_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        hs_type varchar(32) not null,
        in_date varchar(32) not null,
        out_date varchar(32) not null,
        is_new varchar(32) not null);"""
    c.execute(sql)

    # 5.上市公司基本信息stock_company
    sql = """create table if not exists stock_company(
        ts_code varchar(32) PRIMARY KEY not null,
        exchange varchar(32) not null,
        chairman varchar(32) not null,
        manager varchar(32) not null,
        secretary varchar(32) not null,
        reg_capital float not null,
        setup_date varchar(32) not null,
        province varchar(32) not null,
        city varchar(32) not null,
        introduction varchar(32) not null,
        website varchar(32) not null,
        email varchar(32) not null,
        office varchar(32) not null,
        employees float not null,
        main_business varchar(32) not null,
        business_scope varchar(32) not null);"""
    c.execute(sql)

    # 6.管理层薪酬和持股stk_rewards
    sql = """create table if not exists stk_rewards(
        ts_code_name_title_ann_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        ann_date varchar(32) not null,
        end_date varchar(32) not null,
        name varchar(32) not null,
        title varchar(32) not null,
        reward float not null,
        hold_vol float not null);"""
    c.execute(sql)
    # 7.股东增减持stk_holdertrade
    sql = """create table if not exists stk_holdertrade(
        ts_code_ann_date_holder_name varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        ann_date varchar(32) not null,
        holder_name varchar(32) not null,
        holder_type varchar(32) not null,
        in_de varchar(32) not null,
        change_vol float not null,
        change_ratio float not null,
        after_share float not null,
        after_ratio float not null,
        avg_price float not null,
        total_share float not null,
        begin_date varchar(32) not null,
        close_date varchar(32) not null);"""
    c.execute(sql)
    # 8.每日指标daily_basic
    sql = """create table if not exists daily_basic(
        ts_code_trade_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        trade_date varchar(32) not null,
        close float not null,
        turnover_rate float not null,
        turnover_rate_f float not null,
        volume_ratio float not null,
        pe float not null,
        pe_ttm float not null,
        pb float not null,
        ps float not null,
        ps_ttm float not null,
        dv_ratio float not null,
        dv_ttm float not null,
        total_share float not null,
        float_share float not null,
        free_share float not null,
        total_mv float not null,
        circ_mv float not null);"""
    c.execute(sql)
    # 9.股票技术因子（量化因子）stk_factor
    sql = """create table if not exists stk_factor(
        ts_code_trade_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        trade_date varchar(32) not null,
        close float not null,
        open float not null,
        high float not null,
        low float not null,
        pre_close not null,
        change float not null,
        pct_change float not null,
        vol float not null,
        amount float not null,
        adj_factor float not null,
        open_hfq float not null,
        open_qfq float not null,
        close_hfq float not null,
        close_qfq float not null,
        high_hfq float not null,
        high_qfq float not null,
        low_hfq float not null,
        low_qfq float not null,
        pre_close_hfq float not null,
        pre_close_qfq float not null,
        macd_dif float not null,
        macd_dea float not null,
        macd float not null,
        kdj_k float not null,
        kdj_d float not null,
        kdj_j float not null,
        rsi_6 float not null,
        rsi_12 float not null,
        rsi_24 float not null,
        boll_upper float not null,
        boll_mid float not null,
        boll_lower float not null,
        cci float not null);"""
    c.execute(sql)
    # 10.周线行情weekly
    sql = """create table if not exists weekly(
            ts_code_trade_date varchar(32) PRIMARY KEY not null,
            ts_code varchar(32) not null,
            trade_date varchar(32) not null,
            close float not null,
            open float not null,
            high float not null,
            low float not null,
            pre_close float not null,
            change float not null,
            pct_chg float not null,
            vol float not null,
            amount float not null);"""
    c.execute(sql)
    # 11.月线行情monthly
    sql = """create table if not exists monthly(
            ts_code_trade_date varchar(32) PRIMARY KEY not null,
            ts_code varchar(32) not null,
            trade_date varchar(32) not null,
            close float not null,
            open float not null,
            high float not null,
            low float not null,
            pre_close float not null,
            change float not null,
            pct_chg float not null,
            vol float not null,
            amount float not null);"""
    c.execute(sql)
    # 12.指数日线行情index_daily表
    sql = """create table if not exists index_daily(
        ts_code_trade_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        trade_date varchar(32) not null,
        close float not null,
        open float not null,
        high float not null,
        low float not null,
        pre_close float not null,
        change float not null,
        pct_chg float not null,
        vol float not null,
        amount float not null);"""
    # 名称	类型	描述
    # ts_code	str	TS指数代码
    # trade_date	str	交易日
    # close	float	收盘点位
    # open	float	开盘点位
    # high	float	最高点位
    # low	float	最低点位
    # pre_close	float	昨日收盘点
    # change	float	涨跌点
    # pct_chg	float	涨跌幅（%）
    # vol	float	成交量（手）
    # amount	float	成交额（千元）
    c.execute(sql)
    # 13.大盘指数每日指标index_dailybasic表
    sql = """create table if not exists index_dailybasic(
        ts_code_trade_date varchar(32) PRIMARY KEY not null,
        ts_code varchar(32) not null,
        trade_date varchar(32) not null,
        total_mv float not null,
        float_mv float not null,
        total_share float not null,
        float_share float not null,
        free_share float not null,
        turnover_rate float not null,
        turnover_rate_f float not null,
        pe float not null,
        pe_ttm float not null,
        pb float not null);"""
    # 'TS代码+交易日期' 'TS代码' '交易日期'  '当日总市值（元）'
    # '当日流通市值（元）'   '当日总股本（股）' '当日流通股本（股）' '当日自由流通股本（股）'
    # '换手率' '换手率（基于自由流通股本）' '市盈率' '市盈率TTM' '市净率'
    c.execute(sql)
    # 14.申万行业分类index_classify
    sql = """create table if not exists index_classify(
            industry_code varchar(32) PRIMARY KEY not null,
            index_code varchar(32) not null,
            industry_name varchar(32) not null,
            parent_code varchar(32) not null,
            level varchar(32) not null,
            is_pub varchar(32) not null,
            src float not null);"""
    c.execute(sql)
    # 15.申万行业分类index_member
    sql = """create table if not exists index_member(
            index_code_con_code_in_date varchar(32) PRIMARY KEY not null,
            index_code varchar(32) not null,
            index_name varchar(32) not null,
            con_code varchar(32) not null,
            con_name varchar(32) not null,
            in_date varchar(32) not null,
            out_date varchar(32) not null,
            is_new varchar(32) not null);"""
    c.execute(sql)
    # 16.外汇基础信息（海外）fx_obasic
    sql = """create table if not exists fx_obasic(
            ts_code varchar(32) PRIMARY KEY not null,
            name varchar(32) not null,
            classify varchar(32) not null,
            exchange varchar(32) not null,
            min_unit float not null,
            max_unit float not null,
            pip float not null,
            pip_cost float not null,
            traget_spread float not null,
            min_stop_distance float not null,
            trading_hours varchar(32) not null,
            break_time varchar(32) not null);"""
    c.execute(sql)
    # 17.外汇日线行情fx_daily
    sql = """create table if not exists fx_daily(
            index_code_con_code_in_date varchar(32) PRIMARY KEY not null,
            index_code varchar(32) not null,
            index_name varchar(32) not null,
            con_code varchar(32) not null,
            con_name varchar(32) not null,
            in_date varchar(32) not null,
            out_date varchar(32) not null,
            is_new varchar(32) not null);"""
    c.execute(sql)
    # 18.动能因子stock_mx
    sql = """create table if not exists stock_mx(
             ts_code_trade_date varchar(32) PRIMARY KEY not null,
             ts_code varchar(32) not null,
             trade_date varchar(32) not null,
             mx_grade int(1) not null,
             com_stock varchar(32) not null,
             evd_v varchar(32) not null,
             zt_sum_z varchar(32) not null,
             wma250_z varchar(32) not null);"""
    c.execute(sql)
    # 19.估值因子stock_vx
    sql = """create table if not exists stock_vx(
             ts_code_trade_date varchar(32) PRIMARY KEY not null,
             ts_code varchar(32) not null,
             trade_date varchar(32) not null,
             level1 varchar(32) not null,
             level2 varchar(32) not null,
             vx_life_v_l4 varchar(32) not null,
             vx_3excellent_v_l4 varchar(32) not null,
             vx_past_5q_avg_l4 varchar(32) not null,
             vx_grow_worse_v_l4 varchar(32) not null,
             vx_life_v_l8 varchar(32) not null,
             vx_3excellent_v_l8 varchar(32) not null,
             vx_past_5q_avg_l8 varchar(32) not null,
             vx_grow_worse_v_l8 varchar(32) not null,
             vxx varchar(32) not null,
             vs varchar(32) not null,
             vz11 varchar(32) not null,
             vz24 varchar(32) not null,
             vz_lms varchar(32) not null);"""
    c.execute(sql)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_table()