from autogluon.core import TabularDataset
from autogluon.tabular import TabularPredictor

from engine.algos import Algo
import os
from loguru import logger
from config import DATA_DIR_MODELS
from engine.models.models import ModelBase


class ModelTrainer:
    def __init__(self, df, model_path="mymodel/", train_data_percent=0.8):
        self.df = df
        self.model_path = DATA_DIR_MODELS.joinpath(model_path)
        self.train_data_percent = train_data_percent

    def train(self, model: ModelBase):
        df = self.df
        split = int(len(df) * self.train_data_percent)

        train = df.iloc[:split].copy()
        print(train.tail())
        test = df.iloc[split:].copy()
        label = 'label'

        model.train(train, test, label)


class SelectByModel(Algo):
    def __init__(self, model_path):

        model_path = DATA_DIR_MODELS.joinpath(model_path)
        self.model_path = model_path
        if os.path.exists(self.model_path):
            self.predictor = TabularPredictor.load(model_path)
        else:
            logger.error('模型不存在，请先训练模型')

    def __call__(self, target):
        df_bar = target.df_bar
        df_bar['pred'] = self.predictor.predict(df_bar)
        # print(df_bar)
        df_bar['sell'] = df_bar['pred'] == 0
        df_bar['buy'] = df_bar['pred'] == 1
        # print(df_bar)
        return True
