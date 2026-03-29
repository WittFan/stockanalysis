import pandas as pd
from datetime import datetime

def year_frac(start, end):
    """
    Similar to excel's yearfrac function. Returns
    a year fraction between two dates (i.e. 1.53 years).

    Approximation using the average number of seconds
    in a year.

    Args:
        * start (datetime): start date
        * end (datetime): end date

    """
    if start > end:
        raise ValueError("start cannot be larger than end")

    # obviously not perfect but good enough
    return (end - start).total_seconds() / (31557600)

def calc_stats(df_price: pd.DataFrame):
    if type(df_price) is pd.Series:
        df_price = pd.DataFrame(df_price)

    df_price.dropna(inplace=True)

    df_rates = df_price.pct_change()
    df_equity = (1 + df_rates).cumprod()

    df_equity.dropna(inplace=True)
    df_rates.dropna(inplace=True)

    # import empyrical
    # print('年化收益：', round(empyrical.annual_return(df_rates), 3))

    count = len(df_price)
    start = df_price.index[0]
    end = df_price.index[-1]

    accu_return = round(df_equity.iloc[-1] - 1, 3)
    accu_return.name = '累计收益'
    annu_ret = round((accu_return + 1) ** (252 / count) - 1, 3)
    annu_ret.name = '年化收益'

    annu_ret2 = round((accu_return+1) ** (1 / year_frac(start, end)) - 1,3)
    annu_ret2.name = 'CAGR'
    # 标准差
    std = round(df_rates.std() * (252 ** 0.5), 3)
    std.name = '年化波动率'
    # 夏普比
    sharpe = round(annu_ret / std, 3)
    sharpe.name = '夏普比率'
    # 最大回撤
    mdd = round((df_equity / df_equity.expanding(min_periods=1).max()).min() - 1, 3)
    mdd.name = '最大回撤'

    ret_2_mdd = round(annu_ret / abs(mdd), 3)
    ret_2_mdd.name = '卡玛比率'

    df_ratios = pd.concat([annu_ret, annu_ret2, mdd, ret_2_mdd, sharpe, accu_return, std], axis=1)
    df_ratios['开始时间'] = start.strftime('%Y-%m-%d')
    df_ratios['结束时间'] = end.strftime('%Y-%m-%d')
    return df_ratios.T


class PerformanceUtils(object):

    def rate2equity(self, df_rates):
        df = df_rates.copy(deep=True)
        df.dropna(inplace=True)
        for col in df.columns:
            df[col] = (df[col] + 1).cumprod()
        return df

    def equity2rate(self, df_equity):
        df = df_equity.copy(deep=True)
        df = df.pct_change()
        return df

    def calc_equity(self, df_equity):
        df_rates = self.equity2rate(df_equity)
        return self.calc_rates(df_rates)

    def calc_rates(self, df_rates):
        if type(df_rates) is pd.Series:
            df_rates = pd.DataFrame(df_rates)
        df_equity = self.rate2equity(df_rates)
        df_rates.dropna(inplace=True)
        df_equity.dropna(inplace=True)
        # 累计收益率，年化收益
        count = len(df_rates)
        accu_return = round(df_equity.iloc[-1] - 1, 3)
        annu_ret = round((accu_return + 1) ** (252 / count) - 1, 3)
        # 标准差
        std = round(df_rates.std() * (252 ** 0.5), 3)
        # 夏普比
        sharpe = round(annu_ret / std, 3)
        # 最大回撤
        mdd = round((df_equity / df_equity.expanding(min_periods=1).max()).min() - 1, 3)

        ret_2_mdd = round(annu_ret / abs(mdd), 3)

        ratios = [annu_ret, mdd, ret_2_mdd, sharpe, accu_return, std]

        # df_ratio存放这里计算结果
        df_ratios = pd.concat(ratios, axis=1)
        # df_ratios.index = list(df_rates.columns)
        df_ratios.columns = ['年化收益', '最大回撤', '卡玛比率', '夏普比', '累计收益', '波动率']

        # 相关系数矩阵
        df_corr = round(df_equity.corr(), 2)

        start_dt = df_rates.index[0]
        end_dt = df_rates.index[-1]
        if isinstance(start_dt, str):
            start_year = int(start_dt[:4])
            end_year = int(end_dt[:4])
            df_equity['trade_date'] = df_equity.index
            df_equity.index = df_equity['trade_date'].apply(lambda x: datetime.strptime(x, '%Y%m%d'))
            del df_equity['trade_date']
        else:
            start_year = start_dt.year
            end_year = end_dt.year

        '''
       
        years = []
        for year in range(start_year, end_year + 1):
            sub_df = df_equity[str(year)]
            if len(sub_df) <= 3:
                continue
            year_se = round(sub_df.iloc[-1] / sub_df.iloc[0] - 1, 3)
            year_se.name = str(year)
            years.append(year_se)
        if len(years):
            df_years = pd.concat(years, axis=1)
        else:
            df_years = None
         '''
        return df_ratios, df_corr  # df_years
