import lightgbm as lgb
import numpy as np
import pandas as pd

from engine.models.model_base import ModelBase

# Set up decay learning rate
from sklearn.metrics import accuracy_score, f1_score


def learning_rate_power(current_round):
    base_learning_rate = 0.19000424246380565
    min_learning_rate = 0.0001
    lr = base_learning_rate * np.power(0.995, current_round)
    return max(lr, min_learning_rate)


class LGBModel(ModelBase):
    def __init__(self, name, feature_cols, label_col='label', load_model=False):
        super().__init__(name, load_model)
        self.feature_cols = feature_cols
        self.label_col = label_col

    def train(self, df, split_date):
        if split_date:
            df_train = df[df.index < split_date]
            df_val = df[df.index >= split_date]

        lgb_clf = lgb.LGBMClassifier(n_jobs=4,
                                     objective='multiclass',
                                     random_state=100)
        opt_params = {'n_estimators': 500,
                      'boosting_type': 'gbdt',
                      'objective': 'multiclass',
                      'num_leaves': 2452,
                      'min_child_samples': 212,
                      }

        lgb_clf.set_params(**opt_params)

        train = df_train[self.feature_cols]
        # train = (train - train.mean())/train.std()
        val = df_val[self.feature_cols]
        # val = (val - val.mean())/val.std()

        fit_params = {'early_stopping_rounds': 400,
                      'eval_metric': 'multiclass',
                      'eval_set': [(train, df_train[self.label_col]),
                                   (val, df_val[self.label_col])],
                      'verbose': 20,
                      'callbacks': [lgb.reset_parameter(learning_rate=learning_rate_power)]}
        lgb_clf.fit(train, df_train[self.label_col], **fit_params)

        print('Training accuracy: ', accuracy_score(df_train[self.label_col], lgb_clf.predict(train)))
        print('F1 accuracy : ', f1_score(df_val[self.label_col], lgb_clf.predict(val), average='micro'))
        print('Validation accuracy: ', accuracy_score(df_val[self.label_col], lgb_clf.predict(val)))
        self.model = lgb_clf
        if self.load_model:
            self.save_model()

    def predict(self, df):
        se = self.model.predict(df[self.feature_cols])
        se = pd.Series(se)
        se.index = df.index
        return se
