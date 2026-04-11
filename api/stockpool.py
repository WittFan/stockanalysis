"""
股票池工具

提供 load_stockpool()，供 chart_handler 和 value_matrix_handler 共享使用，
避免跨 handler 直接导入。
"""
import pandas as pd
from loguru import logger


def load_stockpool(xlsx_path: str) -> dict:
    """读取 stockpool.xlsx，返回去重后的 {股票代码: 标的名称} 字典。"""
    df = pd.read_excel(xlsx_path, sheet_name='出入池时间表A股')
    stocks = (
        df[['标的名称', '股票代码']]
        .dropna(subset=['股票代码'])
        .drop_duplicates(subset=['股票代码'])
    )
    code_to_name = dict(
        zip(
            stocks['股票代码'].astype(str).str.strip(),
            stocks['标的名称'].astype(str).str.strip(),
        )
    )
    logger.info(f"股票池：原始 {len(df)} 行 → 去重后 {len(code_to_name)} 只")
    return code_to_name
