import numpy as np
from autogluon.core import TabularDataset
from autogluon.tabular import TabularPredictor
from keras import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from keras.layers import Dropout
from keras.regularizers import l1, l2
from config import DATA_DIR_MODELS

class ModelBase:
    def train(self, df_train, df_test, label='label'):
        pass


class AutoGluonModel(ModelBase):
    def train(self, df_train, df_test, label='label'):
        train_data = TabularDataset(df_train)
        test_data = TabularDataset(df_test)

        predictor = TabularPredictor(label=label, path=DATA_DIR_MODELS.joinpath('autogluon').resolve()).fit(train_data)
        print(predictor.leaderboard(test_data, silent=True))


def cw(df, label):
    c0, c1 = np.bincount(df[label])
    w0 = (1 / c0) * (len(df)) / 2
    w1 = (1 / c1) * (len(df)) / 2
    return {0: w0, 1: w1}


class TfModel(ModelBase):
    def create_model(self,dim, hl=1, hu=128, dropout=False, rate=0.3,
                 regularize=False, reg=l1(0.0005),
                 optimizer=Adam(lr=0.001)):
        if not regularize:
            reg = None
        model = Sequential()
        model.add(Dense(hu, input_dim=dim,
                        activity_regularizer=reg,
                        activation='relu'))
        if dropout:
            model.add(Dropout(rate, seed=100))
        for _ in range(hl):
            model.add(Dense(hu, activation='relu',
                            activity_regularizer=reg))
            if dropout:
                model.add(Dropout(rate, seed=100))
        model.add(Dense(1, activation='sigmoid'))
        model.compile(loss='binary_crossentropy', optimizer=optimizer,
                      metrics=['accuracy'])
        return model

    def train(self, df_train, df_test, label='label'):
        cols = list(df_train.columns).copy()
        cols.remove(label)

        df_train.dropna(inplace=True)

        train_data = df_train[cols]

        mu, std = train_data.mean(), train_data.std()
        train_ = (train_data - mu) / std
        print(train_)

        model = self.create_model(dim=len(cols), hl=1, hu=128, dropout=True)
        model.fit(train_,df_train[label], epochs=50,
                  verbose=True, class_weight=cw(df_train,label))


        print('评估测试集')
        test_data = df_test[cols]
        mu, std = test_data.mean(), test_data.std()
        test_ =  (test_data - mu) / std
        print(model.evaluate(test_, df_test[label]))
