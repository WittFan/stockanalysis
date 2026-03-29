from engine.proj_config import ProjConfig, AlgoConfig, from_toml
from config import DATA_DIR_PRJ
from engine.algos import *
from datetime import datetime

def gen_etf_vol_portfolio():
    proj = ProjConfig()
    proj.name = 'ETF-大类资产-风险平价_mytest'
    proj.commission = 0.0001
    proj.slippage = 0.0001
    proj.symbols = [
                    # '510300.SH',  # 沪深300
                    # '159915.SZ',  # 创业板ETF
                    # '159628.SZ', # 国证2000ETF
                    # '513220.SH', # 中证全球中国互联网指数(人民币)收益率
                    '511220.SH',  # 城投债
                    '511030.SH',  # 公司债
                    # '150188.SZ',  # 转债优先
                    # '511260.SH',  # 十年国债
                    # '164703.SZ',  # 汇添富纯债LOF
                    # '160513.SZ',  # 稳健债LOF
                    # '511180.SH', # 上证可转债ETF
                    '518880.SH',  # 黄金
                    # '511880.SH',   # 银华日利
                    '513500.SH',  # 标普500
                    '513100.SH',  # 纳指100
                    # '513330.SH',  # 恒生互联网ETF
                    # '161815.SZ', # 抗通胀LOF
                    ]  # 证券池列表
    # proj.benchmark = '510300.SH'
    # proj.benchmark = '511220.SH'
    proj.benchmark = '513100.SH'
    proj.benchmark = '513500.SH'
    proj.start_date = '20100101'
    proj.end_date = datetime.now().strftime('%Y%m%d')
    proj.data_folder = 'etfs'  # 这里指定data/数据目录
    proj.names = ['roc_20']
    proj.fields = ['roc(close,20)']

    # 这里是策略算子列表
    proj.algos.append(AlgoConfig(name=PrintDate().name))
    proj.algos.append(AlgoConfig(name=RunWeekly().name))  # 再平衡周期
    proj.algos.append(AlgoConfig(name='SelectAll'))  # 选股,直接使用字符串，效果一样
    # proj.algos.append(AlgoConfig(name='SelectBySignal', kwargs={'rules': ['roc_20<-0.02'], 'direction': 'flat'}))
    proj.algos.append(AlgoConfig(name=WeightERC().name))  # 仓位权重
    # proj.algos.append(AlgoConfig(name=WeightEqually().name))
    # proj.algos.append(AlgoConfig(name='TargetVol', args=[0.07], kwargs={'exclude': ['511220.SH']}))
    # proj.algos.append(AlgoConfig(name=PrintTempData().name))
    proj.algos.append(AlgoConfig(name=Rebalance().name))  # 执行再平衡
    return proj


if __name__=="__main__":
    proj = gen_etf_vol_portfolio()
    proj.to_toml(path=DATA_DIR_PRJ.resolve())
    p = from_toml(DATA_DIR_PRJ.joinpath('{}.toml'.format(proj.name)))
    from engine.strategy import Engine
    e = Engine(p)
    e.run()
    e.analysis(console=True)
