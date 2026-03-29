import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from lightgbm import log_evaluation, early_stopping

callbacks = [log_evaluation(period=100), early_stopping(stopping_rounds=50)]


from engine.models.model_base import ModelBase


class LGBRanker(ModelBase):
    def __init__(self, name, load_model, feature_cols=None):
        super(LGBRanker, self).__init__(name, load_model)
        self.feature_cols = feature_cols
        self.label_col = 'label'

    def _prepare_groups(self, df):
        df['day'] = df.index
        group = df.groupby('day')['day'].count()
        # print(group.values)
        return group.values

    def predict(self, data):
        data = data.copy(deep=True)
        if self.feature_cols:
            data = data[self.feature_cols]

        try:
            pred = self.ranker.predict(data)
        except:
            print('error')

            pred = [None for _ in range(len(data))]
            return pred
        return pred

    def train(self, df: pd.DataFrame, split_date: str = None):
        if split_date:
            df_train = df[df.index < split_date]
            df_val = df[df.index >= split_date]

        else:
            df_train = df
            df_val = df

        query_train = self._prepare_groups(df_train.copy(deep=True))
        query_val = self._prepare_groups(df_val.copy(deep=True))

        ranker = lgb.LGBMRanker()


        ranker.fit(df_train[self.feature_cols], df_train[self.label_col], group=query_train,
                   eval_set=[(df_val[self.feature_cols], df_val[self.label_col])], eval_group=[query_val],
                   eval_at=[1, 2, 5],
                   callbacks=callbacks)

        self.ranker = ranker

        print(ranker.n_features_)
        print(ranker.feature_importances_)
        print(ranker.feature_name_)

        score, names = zip(*sorted(zip(ranker.feature_importances_, ranker.feature_name_), reverse=True))
        print(score)
        print(names)


