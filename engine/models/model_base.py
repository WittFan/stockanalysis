import abc
import os
import pandas as pd

import joblib
from config import DATA_DIR_MODELS
from loguru import logger


class ModelBase:
    def __init__(self, name, load_model):
        self.name = name
        self.load_model = load_model
        if load_model:
            path = DATA_DIR_MODELS.resolve()
            model_file = str(path) + '/{}.pkl'.format(name)
            if os.path.exists(model_file):
                self.model = joblib.load(model_file)
            else:
                logger.info('{}不存在'.format(model_file))

    def save_model(self):
        if self.load_model:
            path = str(DATA_DIR_MODELS.resolve())
            joblib.dump(self.model, path + '/{}.pkl'.format(self.name))

    @abc.abstractmethod
    def train(self, df: pd.DataFrame):
        pass

    @abc.abstractmethod
    def predict(self, data):
        pass
