"""
将 stockpool.xlsx 导入 PostgreSQL 数据库
用法：python scripts/import_stockpool.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from orm_models.api import session, init_db
from orm_models.table_models.stockpool import StockPool


def main():
    init_db()
    xlsx_path = ROOT / 'stockpool.xlsx'
    if not xlsx_path.exists():
        print(f'❌ 文件不存在：{xlsx_path}')
        sys.exit(1)

    df = pd.read_excel(str(xlsx_path), sheet_name='出入池时间表A股')
    print(f'📊 读取到 {len(df)} 行数据')

    # 清理旧数据
    session.query(StockPool).delete()
    session.commit()

    # 按股票代码去重：保留最新的一条（按入池时间倒序）
    df = df.sort_values('入池时间', ascending=False).drop_duplicates(subset='股票代码', keep='first')
    print(f'📊 去重后 {len(df)} 行数据')

    added = 0
    for _, r in df.iterrows():
        code = str(r.get('股票代码', '')).strip()
        name = str(r.get('标的名称', '')).strip()
        if not code or not name:
            continue
        in_date = r.get('入池时间')
        out_date = r.get('出池时间')
        row = StockPool(
            ts_code=code,
            name=name,
            in_date=in_date.strftime('%Y-%m-%d') if pd.notna(in_date) else None,
            out_date=out_date.strftime('%Y-%m-%d') if pd.notna(out_date) else None,
        )
        session.add(row)
        added += 1

    session.commit()
    print(f'✅ 导入完成，共 {added} 条记录')


if __name__ == '__main__':
    main()
