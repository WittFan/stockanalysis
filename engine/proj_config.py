import importlib
from dataclasses import dataclass, asdict, field

import toml
import tomli
from loguru import logger
from datetime import datetime

from config import DATA_DIR_CSVS
from engine.engine_utils import load_data


@dataclass
class AlgoConfig:
    name: str
    args: list = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


@dataclass
class ProjConfig:
    name: str = ''
    desc: str = ''
    start_date: str = '20100101'
    end_date: str = None
    initial_capital: float = 1_000_000.0
    commission: float = 0.0001
    slippage: float = 0.0001
    benchmark: str = '000300.SH'
    symbols: list[str] = field(default_factory=list)
    data_folder: str = 'futures'
    fields: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    algos: list[AlgoConfig] = field(default_factory=list)

    def to_toml(self, path):
        data = asdict(self)
        # print(data)
        toml.dump(data, open("{}/{}.toml".format(path, self.name), "w", encoding='utf8'))

    def load_df(self):
        logger.info('开始加载数据...')
        df = load_data(self.fields, self.names, self.symbols, columns=None,
                       start_date=self.start_date, end_date=self.end_date,
                       path=DATA_DIR_CSVS.joinpath(self.data_folder).resolve())
        df['date'] = df.index
        return df

    def parse_algos(self):
        module = importlib.import_module('engine.algos')
        algos = []
        for algo_config in self.algos:
            ac = AlgoConfig(**algo_config)
            algo = getattr(module, ac.name)(*ac.args, **ac.kwargs)
            algos.append(algo)
        return algos


def from_toml(filename):
    with open(filename, "rb") as f:
        config = tomli.load(f)
        proj = ProjConfig(**config)
        proj.algos = proj.parse_algos()
        if not proj.end_date:
            proj.end_date = datetime.now().strftime('%Y%m%d')
        return proj
