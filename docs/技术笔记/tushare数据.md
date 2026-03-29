## 指数数据

行业指数数据当前可以用的是申万数据，接口为pro.index_daily和pro.index_daily_2014，需要拼接这两个数据。

替代方案是中证行业指数，但是，tushare的中证行业指数数据为能覆盖所有历史数据，需要自己通过指数的权重进行计算。权重接口为pro.index_weight(index_code='000016.SH')

