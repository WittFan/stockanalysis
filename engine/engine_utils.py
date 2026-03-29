from datafeed.dataloader import Duckdbloader
from config import DATA_DIR_CSVS


def load_data(fields=[], names=[], symbols=None, columns=None, start_date='20100101', end_date=None,
              path=DATA_DIR_CSVS.joinpath('index').resolve(), folder='/*'):
    if columns is None:
        columns = ['open', 'high', 'low', 'close', 'volume']
    loader = Duckdbloader(path=path, symbols=symbols, columns=columns,
                          start_date=start_date, end_date=end_date, folder=folder)
    # fields.append('close/shift(close,1)-1')
    # names.append('return_0')
    df = loader.load(fields=fields, names=names)

    return df
