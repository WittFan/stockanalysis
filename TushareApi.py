import tushare as ts
import pandas as pd
import datetime, time
import sqlite3
import sqlite_data
from sqlite_data import DataApi
from sqlite_data import delete_table

# 下一步：continue pull_daily_stock_data, and abstract common into function.

class TushareApi:
    def __init__(self):
        self.ts_code_set = {'000001.SH': '上证指数', '000300.SH': '沪深300', '000905.SH': '中证500', '399001.SZ': '深证成指',
                        '399005.SZ': '中小100', '399006.SZ': '创业板指', '399016.SZ': '', '399300.SZ': '沪深300',
                        '000005.SH': '商业指数', '000006.SH': '地产指数', '000016.SH': '上证５０', '399905.SZ': '中证 500'}
        self.pro = ts.pro_api()


    @staticmethod
    def get_daily_data(start_date, end_date, ts_code, day_num, tushare_pro_api):
        """从tushare获取数据"""
        # day_num为tushare的接口限制
        date_delta = datetime.timedelta(days=day_num)
        mid_date = start_date + date_delta
        if end_date <= mid_date:
            # 如果数据在date_delta里，则直接取数返回结果
            df = tushare_pro_api(start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'), ts_code=ts_code)
            return df
        df = tushare_pro_api(start_date=start_date.strftime('%Y%m%d'), end_date=mid_date.strftime('%Y%m%d'), ts_code=ts_code)
        start_date = mid_date + datetime.timedelta(days=1)
        mid_date = start_date + date_delta
        while mid_date < end_date:
        # 如果mid_date没有超过end_date，就一直获取
            df2 = tushare_pro_api(start_date=start_date.strftime('%Y%m%d'), end_date=mid_date.strftime('%Y%m%d'), ts_code=ts_code)
            df = df.append(df2)
        # 如果mid_date超过了end_date，用end_date
        df2 =tushare_pro_api(start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'), ts_code=ts_code)
        df = df.append(df2)
        # 按照trade_date排序
        df = df.sort_values(by='trade_date')
        # 将排序前的序号删掉
        df = df.reset_index(drop=True)
        return df

    @staticmethod
    def write_data_csv(dataframe):
        """将tushare数据写入本地csv"""
        dataframe.to_csv('./data/index_dailybasic.csv', index=False)

    def pull_stock_basic_all(self):
        """1.股票列表stock_basic"""
        df = self.pro.stock_basic(fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs')
        delete_table('stock_basic')
        print('删除stock_basic')
        try:
            sqlite_data.write(df, 'stock_basic')
            print('stock_basic下载成功')
        except sqlite3.IntegrityError:
            print('stock_basic已经存在或%s' %sqlite3.IntegrityError)

    def pull_trade_cal_all(self):
        """2.交易日历trade_cal"""
        # 交易所SSE上交所, SZSE深交所, CFFEX中金所, SHFE上期所, CZCE郑商所, DCE大商所, INE上能源
        df = pd.DataFrame()
        for i in ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'CZCE', 'DCE', 'INE']:
            df2 = self.pro.trade_cal(exchange=i)
            df = pd.concat([df, df2], axis=0)
        df['exchange_cal_date'] = df.apply(lambda x: x['exchange'] + str(x['cal_date']), axis=1)
        delete_table('trade_cal')
        print('删除trade_cal')
        try:
            sqlite_data.write(df, 'trade_cal')
            print('trade_cal下载成功')
        except sqlite3.IntegrityError:
            print('trade_cal已经存在或%s' %sqlite3.IntegrityError)

    def pull_namechange_all(self):
        """3.股票曾用名namechange"""
        df = self.pro.namechange()
        delete_table('namechange')
        print('删除namechange')
        try:
            sqlite_data.write(df, 'namechange')
            print('namechange下载成功')
        except sqlite3.IntegrityError:
            print('namechange已经存在或%s' % sqlite3.IntegrityError)

    def pull_hs_const_all(self):
        """4.沪深股通成份股hs_const"""
        df1 = self.pro.hs_const(hs_type='SH')
        df2 = self.pro.hs_const(hs_type='SZ')
        df = pd.concat([df1, df2], axis=0)
        delete_table('hs_const')
        print('删除hs_const')
        try:
            sqlite_data.write(df, 'hs_const')
            print('hs_const下载成功')
        except sqlite3.IntegrityError:
            print('hs_const已经存在或%s' % sqlite3.IntegrityError)

    def pull_stock_company_all(self):
        """5.上市公司基本信息stock_company"""
        df1 = self.pro.stock_company(exchange='SSE',
                                fields='ts_code, exchange, chairman, manager, secretary, reg_capital,setup_date,province, city, introduction, website, email, office, employees, main_business, business_scope')
        df2 = self.pro.stock_company(exchange='SZSE',
                                fields='ts_code, exchange, chairman, manager, secretary, reg_capital, setup_date,province, city, introduction, website, email, office, employees, main_business, business_scope')
        df = pd.concat([df1, df2], axis=0)
        delete_table('stock_company')
        print('删除stock_company')
        try:
            sqlite_data.write(df, 'stock_company')
            print('stock_company下载成功')
        except sqlite3.IntegrityError:
            print('stock_company已经存在或%s' % sqlite3.IntegrityError)

    def pull_index_basic_all(self):
        """6.指数基本信息index_basic"""
        df = self.pro.index_basic(fields=["ts_code", "name", "fullname", "market", "publisher", "index_type", "category",
                                     "base_date", "base_point", "list_date", "weight_rule", "desc", "exp_date"])
        from sqlite_data import delete_table
        delete_table('index_basic')
        print('删除index_basic')
        try:
            sqlite_data.write(df, 'index_basic')
            print('index_basic下载成功')
        except sqlite3.IntegrityError:
            print('index_basic已经存在或%s' % sqlite3.IntegrityError)

    def pull_index_classify_all(self):
        """15.申万行业分类index_classify"""
        # 获取申万一级行业列表
        df1 = self.pro.index_classify(level='L1', src='SW2021',
                                 fields='index_code, industry_name, level, industry_code, is_pub, parent_code, src')
        # 获取申万二级行业列表
        df2 = self.pro.index_classify(level='L2', src='SW2021',
                                 fields='index_code, industry_name, level, industry_code, is_pub, parent_code, src')
        # 获取申万三级级行业列表
        df3 = self.pro.index_classify(level='L3', src='SW2021',
                                 fields='index_code, industry_name, level, industry_code, is_pub, parent_code, src')
        df = pd.concat([df1, df2, df3], axis=0)
        delete_table('index_classify')
        print('删除index_classify')
        try:
            sqlite_data.write(df, 'index_classify')
            print('index_classify下载成功')
        except sqlite3.IntegrityError:
            print('index_classify已经存在或%s' % sqlite3.IntegrityError)


    def pull_fx_obasic_all(self):
        df = self.pro.fx_obasic()
        delete_table('fx_obasic')
        print('删除fx_obasic')
        try:
            sqlite_data.write(df, 'fx_obasic')
            print('fx_obasic下载成功')
        except sqlite3.IntegrityError:
            print('fx_obasic已经存在或%s' % sqlite3.IntegrityError)


    def pull_stk_rewards_all_data(self):
        """管理层薪酬和持股"""
        pass

    def pull_stk_holdertrade_all_data(self):
        """股东增减持"""
        pass

    def pull_daily_basic_new_data(self):
        """每日指标"""
        data_api = DataApi()
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，并未扣除节假日。
        trade_cal = list(data_api.trade_cal(exchange='SSE', fields=['cal_date'])['cal_date'][::-1])
        # 从数据库update_date_record中查询更新daily_basic最后一个日期，再赋值下载的开始日期、结束日期
        daily_basic = data_api.daily_basic(ts_code='update_date_record', fields=['trade_date'])
        if len(daily_basic) == 0:
            start_date = '19901219'
            daily_basic_last_day = '19901219' #为了在下一个if判断有数值，该变量必须有数值
        else:
            daily_basic_last_day = daily_basic['trade_date'][daily_basic.index[-1]]
            print('上一次更新到', daily_basic_last_day)
            start_date = trade_cal[trade_cal.index(daily_basic_last_day)+1]  # 在数据库的最后一个日期再往后移动一天
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        if daily_basic_last_day == end_date:
            print(f'daily_basic已更新到今日{end_date}')
            return
        # 计算需要更新的百分比
        update_percent = round(trade_cal.index(daily_basic_last_day) / trade_cal.index(end_date) * 100, 2)
        print(f'股票每日指标daily_basic已更新： {update_percent}%，', '下一步', start_date, end_date)
        ########## 下载数据（从数据库最后日期到今天的） #############
        # 准备下载日期区间[start_date, end_date]
        if start_date == end_date:
            trade_date_list = [start_date]
        else:
            trade_date_list = trade_cal[trade_cal.index(start_date):trade_cal.index(end_date)]
        for date in trade_date_list:
            while True:
                try:
                    df = self.pro.daily_basic(trade_date=date)
                    print(f'表daily_basic，日期{date}，下载数据成功，数据长度{len(df)}')
                    break
                except:
                    print(f'在下载股票每日指标daily_basic{date}时等待5秒')
                    time.sleep(5)
            # 判断date日期下是否有数据，有数据则添加primary key，无数据则进入下一天
            if len(df) == 0:
                continue
                # 今日无数据会显示
                ##>> 股票每日指标daily_basic已更新： 99.99 %， 下一步 20230413 20230413
                ##>> 表daily_basic，日期20230413，下载数据成功，数据长度0
            else:
                # 添加primary key
                df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
                # 标记已更新日期到ts_code = update_date_record 数据上
                df2 = pd.DataFrame({'trade_date': [date]})
                df2['ts_code'] = 'update_date_record'
                df2['close'] = 0
                df2['ts_code_trade_date'] = df2.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
                df = pd.concat([df, df2], axis=0)
            # 将下载的数据插入数据库
            try:
                sqlite_data.write(df, 'daily_basic')
                print(f'表daily_basic，日期{date}，入库数据成功，数据长度{len(df)}')
            except sqlite3.IntegrityError:
                print('daily_basic已经存在或%s' % sqlite3.IntegrityError)

    def pull_stock_new_data(self, table_name):
        data_api = DataApi()
        # SSE开始于19901219 SZSE开始于19910703，因此只需要SSE。返回的交易日历仅仅是从开始时间到今年最后一天，并未扣除节假日。
        trade_cal = list(data_api.trade_cal(exchange='SSE', fields=['cal_date'])['cal_date'][::-1])
        # 从数据库update_date_record中查询更新daily_basic最后一个日期，再赋值下载的开始日期、结束日期
        ###
        updated_trade_date = data_api.query(table_name, ts_code='update_date_record', fields=['trade_date'])
        if len(updated_trade_date) == 0:
            start_date = '19901219'
            last_day = '19901219' #为了在下一个if判断有数值，该变量必须有数值
        else:
            last_day = updated_trade_date['trade_date'][updated_trade_date.index[-1]]
            print('上一次更新到', last_day)
            start_date = trade_cal[trade_cal.index(last_day)+1]  # 在数据库的最后一个日期再往后移动一天
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        if last_day == end_date:
            print(f'{table_name}已更新到今日{end_date}')
            return
        # 计算需要更新的百分比
        update_percent = round(trade_cal.index(last_day) / trade_cal.index(end_date) * 100, 2)
        print(f'表{table_name}已更新： {update_percent}%，', '下一步', start_date, end_date)

        ########## 下载数据（从数据库最后日期到今天的） #############
        # 准备下载日期区间[start_date, end_date]
        if start_date == end_date:
            trade_date_list = [start_date]
        else:
            trade_date_list = trade_cal[trade_cal.index(start_date):trade_cal.index(end_date)]
        for date in trade_date_list:
            # 如果接口有限制则等待5秒，直到可以继续调用
            while True:
                try:
                    df = self.pro.query(table_name,trade_date=date)
                    print(f'表{table_name}，日期{date}，下载数据成功，数据长度{len(df)}')
                    break
                except:
                    print(f'在下载表{table_name}{date}时等待5秒')
                    time.sleep(5)
            # 判断date日期下是否有数据，有数据则添加primary key，无数据则进入下一天
            if len(df) == 0:
                continue
                # 今日无数据会显示
                ##>> 股票每日指标daily_basic已更新： 99.99 %， 下一步 20230413 20230413
                ##>> 表daily_basic，日期20230413，下载数据成功，数据长度0
            else:
                # 添加primary key
                df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
                # 标记已更新日期到ts_code = update_date_record 数据上
                df2 = pd.DataFrame({'trade_date': [date]})
                df2['ts_code'] = 'update_date_record'
                df2['ts_code_trade_date'] = df2.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
                df = pd.concat([df, df2], axis=0)
            # 将下载的数据插入数据库
            try:
                sqlite_data.write(df, table_name)
                print(f'表{table_name}，日期{date}，入库数据成功，数据长度{len(df)}')
            except sqlite3.IntegrityError:
                print('表{table_name}已经存在或%s' % sqlite3.IntegrityError)

    def pull_stk_factor_new_data(self):
        """股票技术因子（量化因子）"""
        table_name = 'stk_factor'
        self.pull_stock_new_data(table_name)

    def pull_daily_new_data(self):
        """股票技术因子（量化因子）"""
        table_name = 'daily'
        self.pull_stock_new_data(table_name)

    def pull_weekly_all_data(self):
        """周线行情"""
        pass

    def pull_monthly_all_data(self):
        """月线行情"""
        pass

    def pull_index_daily_all_data(self):
        """
        拉取大盘指数每日指标index_daily到本地，并存储
        指数范围：self.ts_code_set
        :return:
        """
        for ts_code in self.ts_code_set:
            # 遍历IndexDailybasic的所有代码ts_code
            start_date = datetime.date(1990, 1, 1) # 开始时间
            end_date = datetime.date.today() # 结束时间
            day_num = 7900 # tushare的个数限制
            df = self.get_daily_data(start_date, end_date, ts_code, day_num, self.pro.index_daily)
            df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
            try:
                sqlite_data.write(df, 'index_daily')
                print('%s下载成功' % ts_code)
            except sqlite3.IntegrityError:
                print('%s已经存在' %ts_code)

    def pull_index_dailybasic_all_data(self):
        # 拉取大盘指数每日指标index_dailybasic到本地，并存储
        for ts_code in self.ts_code_set:
            # 遍历IndexDailybasic的所有代码ts_code
            start_date = datetime.date(2004, 1, 1) # 开始时间
            end_date = datetime.date.today() # 结束时间
            day_num = 12*360 # tushare的个数限制
            df = self.get_daily_data(start_date, end_date, ts_code, day_num, self.pro.index_dailybasic)
            df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
            try:
                sqlite_data.write(df, 'index_dailybasic')
            except sqlite3.IntegrityError:
                print('%s已经存在' %ts_code)

    def pull_index_member_all(self):
        data_api = DataApi()
        index_codes = data_api.index_classify(fields=['index_code'])
        df = self.pro.index_member(index_code=index_codes.values[0][0], fields=['index_code', 'index_name',
                                                                           'con_code', 'con_name', 'in_date',
                                                                           'out_date', 'is_new'])
        for index_code in index_codes.values[1:]:
            # 获取黄金分类的成份股
            print(index_code[0])
            while True:
                try:
                    df2 = self.pro.index_member(index_code=index_code[0])
                    break
                except:
                    print('等待5秒')
                    time.sleep(5)
            df = pd.concat([df, df2], axis=0)
        df = df.drop_duplicates()
        df['index_code_con_code_in_date'] = df.apply(lambda x: x['index_code'] + x['con_code'] + str(x['in_date']),
                                                     axis=1)
        try:
            sqlite_data.write(df, 'index_member')
            print('index_member下载成功')
        except sqlite3.IntegrityError:
            print('index_member已经存在或%s' % sqlite3.IntegrityError)

    def pull_fx_daily_all_data(self):
        pass

    def pull_stock_mx_all_data(self):
        pass

    def pull_stock_vx_all_data(self):
        pass

    def pull_all_data_basic(self):
        """
        tushare所有全量数据拉取到本地并存储，基本信息部分
        :return:
        """
        self.pull_stock_basic_all()
        self.pull_trade_cal_all()
        self.pull_namechange_all()
        self.pull_hs_const_all()
        self.pull_stock_company_all()
        self.pull_index_basic_all()
        self.pull_index_classify_all()
        self.pull_fx_obasic_all()

    def pull_all_data_detail(self):
        """
        tushare所有全量数据拉取到本地并存储，明细表部分
        :return:
        """
        self.pull_stk_rewards_all_data() #1
        self.pull_stk_holdertrade_all_data() #2
        self.pull_daily_basic_new_data() #3 完成
        self.pull_stk_factor_new_data() #4
        self.pull_daily_new_data() # 完成
        self.pull_weekly_all_data() #5
        self.pull_monthly_all_data() #6
        self.pull_index_dailybasic_all_data() #7
        self.pull_index_daily_all_data() #8
        self.pull_index_member_all() #完成
        self.pull_fx_daily_all_data() #9
        self.pull_stock_mx_all_data() #10
        self.pull_stock_vx_all_data() #12

    def pull_new_data(self):
        ### 增量数据拉取到本地，并存储
        # 读取本地数据
        date = self.read_last_day_data()
        if date == None:
            date = datetime.date(2004, 1, 1)
        # 获取线上数据
        if date < datetime.date.today():
            # 如果本地数据已经更新到今天，就不需要再下载更新了；如果没有，进行下面的操作。
            start_date = date + datetime.timedelta(days=1)
            end_date = datetime.date.today()
            df = self.get_daily_data(start_date, end_date)
            update_date = df.iloc[-1, 1]
            update_date = update_date[0:4]+'-'+update_date[4:6]+'-'+update_date[6:8]
            df['ts_code_trade_date'] = df.apply(lambda x: x['ts_code'] + str(x['trade_date']), axis=1)
            # 更新本地数据
            sqlite_data.write(df, 'index_daily')
            print('index_dailybasic成功地从%s更新到%s' %(date, update_date))
        else:
            print('index_dailybasic已经是最新%s' %(date))

    @staticmethod
    def read_last_day_data():
        """读取本地数据库最新日期的数据"""
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        sql = """select trade_date from index_dailybasic where ts_code=='000001.SH' order
         by trade_date desc limit 1;"""
        c.execute(sql)
        conn.commit()
        date = c.fetchall()
        if date == []:
            return None
        date = date[0][0]
        conn.close()
        date = datetime.date(int(date[0:4]), int(date[4:6]), int(date[6:8]))
        return date

if __name__ == '__main__':
    # from sqlite_data import delete_table
    # delete_table('stk_factor')
    # from sql_create_table import create_table
    # create_table()

    tushare_api = TushareApi()
    # tushare_api.pull_all_data_basic()
    tushare_api.pull_daily_new_data()
