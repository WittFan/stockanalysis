# sqlalchemy的使用

## sqlalchemy 可以导入的包
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
```


## 将model读取的数据转为pandas.dataframe
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(SQLITE_URI, echo=True)
Session = sessionmaker(bind=engine)  # 这里一定要用上下文去管理session,否则会出现很多诡异的情况！！！切记
session = Session(engine)
query = session.query(MyTable).filter(MyTable.age > 21)
df = pd.read_sql(query.statement, query.session.bind)
session.close()
```
封装部分代码
```python
def query(self, query_magic):
    """用 sqlAlchemy 的 session.query 查询数据库，结合pandas.read_sql"""
    df = pd.read_sql(query_magic.statement, query_magic.session.bind)
    session.close()
    return df
# 查询数据
query_magic = session.query(Test).filter(Test.id > 1).filter(Test.exchange=='SSE')
df = query(query_magic)
```
