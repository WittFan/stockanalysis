from config import tushare_api
from models import *
import pandas as pd
import datetime, time
import sqlite3

class PullMetaData:
    def __init__(self):
        pass

    def pull_stock_basic(self):
        """1.股票列表stock_basic"""
        df = self.pro.stock_basic(fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs')
        delete_table('stock_basic')
        print('删除stock_basic')
        try:
            sqlite_data.write(df, 'stock_basic')
            print('stock_basic下载成功')
        except sqlite3.IntegrityError:
            print('stock_basic已经存在或%s' %sqlite3.IntegrityError)

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

    def pull_all_meta_data(self):
        """
        tushare所有全量数据拉取到本地并存储，基本信息部分
        :return:
        """
        self.pull_namechange_all()
        self.pull_hs_const_all()
        self.pull_stock_company_all()
        self.pull_index_classify_all()
        self.pull_fx_obasic_all()
        self.pull_index_member_all()

if __name__ == '__main__':
    PullMetaData().pull_trade_cal_all()