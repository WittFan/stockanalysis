from engine.proj_config import ProjConfig, AlgoConfig, from_toml
from config import DATA_DIR_PRJ
from engine.algos import *


def gen_etf_vol_portfolio():
    proj = ProjConfig()
    proj.name = 'ETF-大类资产-动量择时-风险平价'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['510300.SH',  # 沪深300
                    '159915.SZ',  # 创业板ETF
                    '511220.SH',  # 城投债
                    # '511260.SH',  # 十年国债
                    '518880.SH',  # 黄金
                    # '511880.SH',   # 银华日利
                    # '513500.SH',  # 标普500
                    '513100.SH',  # 纳指100
                    ]  # 证券池列表
    proj.benchmark = '000300.SH'
    proj.start_date = '20100101'
    proj.data_folder = 'etfs'  # 这里指定data/数据目录
    proj.names = ['roc_20']
    proj.fields = ['roc(close,20)']

    # 这里是策略算子列表
    # proj.algos.append(AlgoConfig(name=PrintDate().name))

    proj.algos.append(AlgoConfig(name=RunWeekly().name))  # 再平衡周期
    # proj.algos.append(AlgoConfig(name='SelectAll'))  # 选股,直接使用字符串，效果一样
    proj.algos.append(AlgoConfig(name='SelectBySignal', kwargs={'rules': ['roc_20<-0.02'], 'direction': 'flat'}))
    proj.algos.append(AlgoConfig(name=WeightERC().name))  # 仓位权重
    # proj.algos.append(AlgoConfig(name=WeightEqually().name))
    proj.algos.append(AlgoConfig(name='TargetVol', args=[0.07], kwargs={'exclude': ['511220.SH']}))

    # proj.algos.append(AlgoConfig(name=PrintTempData().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行再平衡

    return proj


# 示例-资产配置-再平衡
def gen_portfolio_rebalance():
    proj = ProjConfig()
    proj.name = '示例-资产配置-再平衡'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['000300.SH', '399006.SZ']  # 证券池列表
    proj.benchmark = '000300.SH'
    proj.start_date = '20100101'
    proj.data_folder = 'index'  # 这里指定data/数据目录

    # 这里是策略算子列表
    proj.algos.append(AlgoConfig(name=PrintDate().name))

    proj.algos.append(AlgoConfig(name=RunWeekly().name))  # 再平衡周期
    proj.algos.append(AlgoConfig(name='SelectAll'))  # 选股,直接使用字符串，效果一样
    proj.algos.append(AlgoConfig(name=WeightEqually().name))  # 仓位权重

    proj.algos.append(AlgoConfig(name=PrintTempData().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行再平衡

    return proj


# Dual Thrust策略
def gen_dual_thrust():
    proj = ProjConfig()
    proj.name = 'Dual Thrust策略'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['B0']  # 证券池列表
    proj.benchmark = 'B0'
    proj.start_date = '20100101'
    proj.data_folder = 'futures'  # 这里指定data/数据目录

    fields = ["shift(max(high,10),1)", 'shift(min(close,10),1)', "shift(max(close,10),1)", 'shift(min(low,10),1)']
    fields.append('greater(HH-LC,HC-LL)')
    fields.append('open+range*0.1')
    fields.append('open-range*0.1')
    fields.append('close>buyline')
    fields.append('close<sellline')
    names = ["HH", "LC", 'HC', 'LL', 'range', 'buyline', 'sellline', 'long', 'short']
    proj.fields = fields
    proj.names = names

    # 这里是策略算子列表

    proj.algos.append(AlgoConfig(name=SelectBySignal().name, kwargs={'rules': ['long'], 'direction': 'long'}))
    proj.algos.append(AlgoConfig(name=SelectBySignal().name, kwargs={'rules': ['short'], 'direction': 'short'}))

    proj.algos.append(AlgoConfig(name=WeightEqually().name))  # 生成调仓表

    proj.algos.append(AlgoConfig(name=PrintDate().name))
    proj.algos.append(AlgoConfig(name=PrintOrder().name))
    proj.algos.append(AlgoConfig(name=PrintTempData().name))

    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行调仓操作

    return proj


# ETF动量轮动
def gen_etf_rolling():
    proj = ProjConfig()
    proj.name = 'ETF趋势交易_动量轮动'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = symbols = [
        '159915.SZ',  # 创业板ETF
        '510300.SH',  # 沪深300ETF
        '518880.SH',  # 黄金ETF
        '513110.SH',  # 纳指100指数
        '513520.SH',  # 日经ETF
    ]  # 证券池列表

    proj.fields = ['roc(close,20)', 'slope_pair(high,low,18)']
    proj.names = ['roc_20', 'rsrs']
    proj.benchmark = '000300.SH'
    proj.start_date = '20100101'
    proj.data_folder = 'etfs'  # 这里指定data/数据目录

    # 这里是策略算子列表
    proj.algos.append(AlgoConfig(name=SelectBySignal().name,
                                 kwargs={'rules_buy': ['roc_20>0.02'], 'buy_at_least_count': 1,
                                         'rules_sell': ['roc_20<-0.02']}))  # 选股,直接使用字符串，效果一样

    # 选股,直接使用字符串，效果一样
    proj.algos.append(AlgoConfig(name=WeightEqually().name))  # 仓位权重
    # proj.algos.append(AlgoConfig(name=PrintTempData().name))

    # proj.algos.append(AlgoConfig(name=PrintDate().name))
    # proj.algos.append(AlgoConfig(name=PrintOrder().name))
    # proj.algos.append(AlgoConfig(name=PrintTempData().name))

    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行再平衡

    return proj


# 静待花开的聚宝盆
def gen_flower():
    proj = ProjConfig()
    proj.name = '静待花开的聚宝盘'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = [
        '511220.SH',  # 城投债
        '512010.SH',  # 医药
        '518880.SH',  # 黄金
        '163415.SZ',  # 兴全商业
        '159928.SZ',  # 消费
        '161903.SZ',  # 万家行业优选
        '513100.SH'  # 纳指
    ]  # 证券池列表
    proj.benchmark = '000300.SH'
    proj.start_date = '20100101'
    proj.data_folder = 'etfs'  # 这里指定data/数据目录，这里的数据在etfs下

    proj.fields = ['roc(close,20)']
    proj.names = ['roc_20']

    # 这里是策略算子列表
    # proj.algos.append(AlgoConfig(name=PrintDate().name))
    proj.algos.append(AlgoConfig(name='RunDays', args=[5]))  # 再平衡周期

    proj.algos.append(AlgoConfig(name=SelectBySignal().name, kwargs={'rules_buy': ['roc_20>0.02'], 'rules_sell': [
        'roc_20<-0.02']}))  # 选股,直接使用字符串，效果一样

    proj.algos.append(AlgoConfig(name=WeightEqually().name))  # 仓位权重
    # proj.algos.append(AlgoConfig(name=PrintTempData().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行再平衡

    return proj


def gen_turtle():
    proj = ProjConfig()
    proj.name = '海龟交易系统'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['399006.SZ']  # 证券池列表
    proj.benchmark = '000300.SH'
    proj.start_date = '20100101'
    proj.data_folder = 'index'  # 这里指定data/数据目录

    fields = ["shift(max(high,20),1)", 'shift(min(low,20),1)', 'ta_atr(high,low,close,14)', 'roc(close,20)']

    names = ["high_N", "low_N", 'atr', 'roc_20']
    proj.fields = fields
    proj.names = names

    # 这里是策略算子列表
    proj.algos.append(AlgoConfig(name=AlgoTurtle().name))

    return proj


def gen_rolling():
    proj = ProjConfig()
    proj.name = '大小盘轮动策略'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['159915.SZ', '510300.SH']  # 证券池列表
    proj.benchmark = '000300.SH'
    proj.start_date = '20100528'
    proj.data_folder = 'etfs'  # 这里指定data/数据目录

    fields = ['roc(close,20)']
    names = ['roc_20']
    proj.fields = fields
    proj.names = names

    # 这里是策略算子列表
    proj.algos.append(
        AlgoConfig(name=SelectBySignal().name, kwargs={'rules_buy': ['roc_20>0.02'], 'rules_sell': ['roc_20<-0.02']})

    )
    proj.algos.append(
        AlgoConfig(name=SelectTopK().name, kwargs={'factor_name': 'roc_20'})
    )
    proj.algos.append(AlgoConfig(name=WeightEqually().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))

    return proj

def gen_cy_picktime():
    proj = ProjConfig()
    proj.name = '创业板动量择时'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = ['159915.SZ']  # 证券池列表
    proj.benchmark = '159915.SZ'
    proj.start_date = '20100101'
    proj.data_folder = 'etfs'  # 这里指定data/数据目录

    fields = ['roc(close,20)']
    names = ['roc_20']
    proj.fields = fields
    proj.names = names

    # 这里是策略算子列表
    proj.algos.append(
        AlgoConfig(name=SelectBySignal().name, kwargs={'rules_buy': ['roc_20>0.08'], 'rules_sell': ['roc_20<-0.0']})

    )
    #proj.algos.append(
    #    AlgoConfig(name=SelectTopK().name, kwargs={'factor_name': 'roc_20'})
    #)
    proj.algos.append(AlgoConfig(name=WeightEqually().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))

    return proj


proj = gen_cy_picktime()
# proj = gen_etf_rolling()
# 保存到目录

proj.to_toml(path=DATA_DIR_PRJ.resolve())
proj.l
p = from_toml(DATA_DIR_PRJ.joinpath('{}.toml'.format(proj.name)))
from engine.strategy import Engine
e = Engine(p)
e.run()
e.analysis(console=True)
