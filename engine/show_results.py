import pandas as pd
from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.models import HoverTool, DatetimeTickFormatter, Div
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.palettes import Category10
from bokeh.resources import CDN
from bokeh.embed import file_html
import numpy as np

np.random.seed(55)


class ShowResults:

    def _show_table(self, df, title):
        data_table = DataTable(
            columns=[TableColumn(field=Ci, title=Ci) for Ci in df.columns],
            source=ColumnDataSource(df),
            index_position=None,
        )
        title = Div(text="<h3>{}</h3>".format(title))
        layout = column(title, data_table)
        return layout

    def show(self, df_equities, df_metrics, df_orders, return_html=True):
        if isinstance(df_equities, pd.Series):
            df_equities = pd.DataFrame(df_equities)

        # 使用原生 Bokeh 绘制收益曲线（替代 pandas_bokeh，兼容 Bokeh 3.x）
        p_equity = figure(
            title="投资组合市值",
            x_axis_type="datetime",
            width=800,
            height=400,
        )
        colors = Category10[max(3, len(df_equities.columns))]
        for i, col_name in enumerate(df_equities.columns):
            p_equity.line(
                df_equities.index, df_equities[col_name],
                legend_label=str(col_name),
                color=colors[i],
                line_width=1.5,
            )
        p_equity.legend.location = "top_left"
        p_equity.legend.click_policy = "hide"
        p_equity.xaxis.formatter = DatetimeTickFormatter(years=["%Y"])

        # 绩效指标表
        cols = list(df_metrics.columns)
        cols.insert(0, '指标')
        df_metrics['指标'] = df_metrics.index
        df_metrics = df_metrics.reindex(columns=cols)
        table_metrics = self._show_table(df_metrics, '绩效指标')

        # 交易记录表
        df_orders = df_orders.copy().reset_index()
        if 'date' in df_orders.columns:
            df_orders['date'] = df_orders['date'].apply(
                lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
        table_orders = self._show_table(df_orders, '交易记录')

        layout = column(p_equity, table_metrics, table_orders, sizing_mode='scale_width')

        if return_html:
            return file_html(layout, resources=CDN, title="回测结果")
        return layout
