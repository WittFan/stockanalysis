"""
DuckDB → PostgreSQL 数据迁移脚本

用法：python migrate_duckdb_to_pg.py

说明：
  - 从 data/duck.db 读取所有表数据
  - 写入 PostgreSQL（config.py 中的 DB_URI）
  - 分批写入（chunksize=10000），适合大表
  - 跳过已有数据的表（if_exists='append'），可重复运行
"""
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger
import time

# PostgreSQL 引擎（从 config 获取）
from config import DB_URI
pg_engine = create_engine(DB_URI)

# DuckDB 只读连接
duck_con = duckdb.connect('data/duck.db', read_only=True)

# 获取所有表
tables = duck_con.execute("SHOW TABLES").fetchall()
table_names = [t[0] for t in tables]

logger.info(f"共 {len(table_names)} 张表需要迁移: {table_names}")

for i, table_name in enumerate(table_names):
    start = time.time()

    # 检查 PostgreSQL 中是否已有数据
    try:
        with pg_engine.connect() as con:
            existing = con.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        if existing > 0:
            logger.info(f"[{i+1}/{len(table_names)}] {table_name} 已有 {existing} 行，跳过")
            continue
    except Exception:
        pass  # 表可能不存在（ORM 中没有的表）

    # 从 DuckDB 读取
    try:
        total = duck_con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        if total == 0:
            logger.info(f"[{i+1}/{len(table_names)}] {table_name} 空表，跳过")
            continue

        logger.info(f"[{i+1}/{len(table_names)}] {table_name} 开始迁移（{total} 行）...")

        # 分批读取和写入，避免内存溢出
        batch_size = 50000
        written = 0
        offset = 0

        while offset < total:
            df = duck_con.execute(
                f'SELECT * FROM "{table_name}" LIMIT {batch_size} OFFSET {offset}'
            ).fetchdf()

            if df.empty:
                break

            df.to_sql(table_name, pg_engine, if_exists='append', index=False, chunksize=10000)
            written += len(df)
            offset += batch_size

            if written % 100000 == 0 or written == total:
                elapsed = time.time() - start
                logger.info(f"  {table_name}: {written}/{total} 行，已用时 {elapsed:.1f}s")

        elapsed = time.time() - start
        # 验证
        with pg_engine.connect() as con:
            pg_count = con.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        logger.info(f"  ✅ {table_name} 迁移完成: DuckDB={total}, PG={pg_count}, 耗时 {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"  ❌ {table_name} 迁移失败: {e}")

duck_con.close()
logger.info("迁移完成！")
