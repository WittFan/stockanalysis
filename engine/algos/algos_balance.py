import numpy as np
import pandas as pd

from .algo_base import Algo
from loguru import logger


class Rebalance(Algo):

    def __init__(self):
        super(Rebalance, self).__init__()

    def __call__(self, target):
        if "weights" not in target.temp.keys():
            print('没有计划权重！')
            return True

        target_weights = target.temp["weights"]
        if type(target_weights) is pd.Series:
            target_weights = target_weights.to_dict()

        # 这里只根据当前调仓表调仓，比如当前开多单，本期无信号的，不进行调仓，这也符合我们的常识。


        target.rebalance(target.ctxs, target_weights)


        return True
