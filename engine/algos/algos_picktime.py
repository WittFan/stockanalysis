from .algo_base import *
from loguru import logger

class AlgoLong(Algo):
    def __init__(self, signal='long'):
        super(AlgoLong, self).__init__()
        self.signal = signal

    def __call__(self, target):
        df_bar = target.df_bar
        if self.signal not in list(df_bar.columns):
            logger.warning('信号列不存在{}'.format(self.signal))
            return True

        i
