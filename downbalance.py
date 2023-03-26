import tushare as ts
import pandas as pd

pro = ts.pro_api()
#查询主板股票列表
stock_list = pro.query('stock_basic', exchange='', list_status='L', market="主板",fields='ts_code,symbol,name,market,area,industry,list_date')

#汇总主板股票的净资产账面价值到equity_history
equity_history = pro.balancesheet(ts_code= stock_list["ts_code"][0], fields='ts_code,end_date,report_type,comp_type,total_hldr_eqy_exc_min_int')
for i in stock_list["ts_code"][1::]:
    print(i)
    df = pro.balancesheet(ts_code=i, fields='ts_code,end_date,report_type,comp_type,total_hldr_eqy_exc_min_int')
    equity_history = pd.append(df, ignore_index=True)

if __name__ == '__main__':
    pass