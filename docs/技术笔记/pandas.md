

多行合并
```python
df = pd.concat([df, df2], axis=0)
```
 
查询
```python
df.query('Embarked == "S"')
df[df['Embarked'] == 'S']
```

累计求值计算：cumsum、cummin、cummax、cumpod;

