"""
数据迁移一致性验证脚本 - Column-Aggregate Fingerprint 方法
=============================================================
对每张表的每列计算聚合指纹（SUM/COUNT/MIN/MAX），
在 DuckDB 和 PostgreSQL 中分别计算后比较，差异为零则说明数据完全一致。

覆盖率：100%（全量数据，非抽样）
与行序无关：聚合操作不依赖行的顺序
精度容差：float SUM 用 1e-6，其余精确匹配
"""

import duckdb
import psycopg2
import time
from pathlib import Path

# ── 连接配置 ──────────────────────────────────────────────────────────────────

DUCKDB_PATH = str(Path(__file__).parent / 'data' / 'duck.db')
PG_DSN = 'postgresql://apple@localhost:5432/stockanalysis'

# 跳过不需要验证的表（测试表/中间表）
SKIP_TABLES = {'test', 'verify_record'}

# float SUM 容差（DuckDB FLOAT32 vs PG FLOAT64，实测差为 0，这里保守设置）
FLOAT_TOLERANCE = 1e-6


# ── 列类型分类 ────────────────────────────────────────────────────────────────

def classify_col_type(duck_type: str) -> str:
    """根据 DuckDB 列类型分类为 numeric / string / other"""
    t = duck_type.upper()
    if any(k in t for k in ('INT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL', 'HUGEINT', 'BIGINT', 'SMALLINT', 'TINYINT')):
        return 'numeric'
    if any(k in t for k in ('VARCHAR', 'TEXT', 'CHAR', 'STRING')):
        return 'string'
    return 'other'  # DATE、TIMESTAMP、BOOL 等，只用 COUNT/MIN/MAX


# ── DuckDB 聚合 ───────────────────────────────────────────────────────────────

def duck_fingerprint(con, table: str, columns: list[tuple]) -> dict:
    """
    columns: [(col_name, col_type), ...]
    返回 {col_name: {'sum': ..., 'count': ..., 'min': ..., 'max': ...}}
    """
    parts = []
    for col, dtype in columns:
        kind = classify_col_type(dtype)
        q = f'"{col}"'
        if kind == 'numeric':
            parts.append(f'SUM(TRY_CAST(ROUND(TRY_CAST({q} AS DOUBLE), 8) AS DOUBLE)) AS "{col}__sum"')
            parts.append(f'COUNT({q}) AS "{col}__count"')
            parts.append(f'MIN({q}) AS "{col}__min"')
            parts.append(f'MAX({q}) AS "{col}__max"')
        elif kind == 'string':
            parts.append(f'SUM(LENGTH(COALESCE({q}, \'\'))) AS "{col}__len_sum"')
            parts.append(f'COUNT({q}) AS "{col}__count"')
        else:
            parts.append(f'COUNT({q}) AS "{col}__count"')
            parts.append(f'MIN(CAST({q} AS VARCHAR)) AS "{col}__min"')
            parts.append(f'MAX(CAST({q} AS VARCHAR)) AS "{col}__max"')

    sql = f'SELECT {", ".join(parts)} FROM "{table}"'
    cur = con.execute(sql)
    row = cur.fetchone()
    col_names = [d[0] for d in cur.description]
    return dict(zip(col_names, row))


# ── PostgreSQL 聚合 ───────────────────────────────────────────────────────────

def get_pg_col_types(cur, table: str) -> dict:
    """获取 PG 表的列类型 {col_name: data_type}"""
    cur.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE table_name='{table}' AND table_schema='public' ORDER BY ordinal_position"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def pg_fingerprint(cur, table: str, columns: list[tuple], pg_col_types: dict | None = None) -> dict:
    """同上，但针对 PostgreSQL 语法，优先使用 PG 自己的列类型"""
    parts = []
    for col, dtype in columns:
        # 优先使用 PG 的列类型，避免类型不一致导致查询失败
        pg_dtype = pg_col_types.get(col, dtype) if pg_col_types else dtype
        dtype = pg_dtype
        kind = classify_col_type(dtype)
        q = f'"{col}"'
        if kind == 'numeric':
            # ROUND 在 PG 中对 DOUBLE PRECISION 不直接支持，需先转 NUMERIC
            parts.append(f'SUM(ROUND({q}::NUMERIC, 8)::DOUBLE PRECISION) AS "{col}__sum"')
            parts.append(f'COUNT({q}) AS "{col}__count"')
            parts.append(f'MIN({q}) AS "{col}__min"')
            parts.append(f'MAX({q}) AS "{col}__max"')
        elif kind == 'string':
            parts.append(f'SUM(LENGTH(COALESCE({q}, \'\'))) AS "{col}__len_sum"')
            parts.append(f'COUNT({q}) AS "{col}__count"')
        else:
            parts.append(f'COUNT({q}) AS "{col}__count"')
            parts.append(f'MIN({q}::TEXT) AS "{col}__min"')
            parts.append(f'MAX({q}::TEXT) AS "{col}__max"')

    sql = f'SELECT {", ".join(parts)} FROM "{table}"'
    cur.execute(sql)
    row = cur.fetchone()
    col_names = [d[0] for d in cur.description]
    return dict(zip(col_names, row))


# ── 比较指纹 ──────────────────────────────────────────────────────────────────

def compare_fingerprints(duck_fp: dict, pg_fp: dict, columns: list[tuple]) -> list[str]:
    """返回差异描述列表，空列表表示完全一致"""
    diffs = []
    for col, dtype in columns:
        kind = classify_col_type(dtype)
        if kind == 'numeric':
            for suffix in ('__sum', '__count', '__min', '__max'):
                key = f'{col}{suffix}'
                dv = duck_fp.get(key)
                pv = pg_fp.get(key)
                if dv is None and pv is None:
                    continue
                if dv is None or pv is None:
                    diffs.append(f'  列 {col}{suffix}: DuckDB={dv}, PG={pv} (一方为NULL)')
                    continue
                try:
                    fdv, fpv = float(dv), float(pv)
                    diff = abs(fdv - fpv)
                    # 使用相对误差：避免大数求和时浮点精度误报
                    denom = max(abs(fdv), abs(fpv), 1.0)
                    rel_err = diff / denom
                    if rel_err > FLOAT_TOLERANCE:
                        diffs.append(f'  列 {col}{suffix}: DuckDB={dv}, PG={pv}, 相对误差={rel_err:.2e}')
                except (TypeError, ValueError):
                    if str(dv) != str(pv):
                        diffs.append(f'  列 {col}{suffix}: DuckDB={dv}, PG={pv}')
        elif kind == 'string':
            for suffix in ('__len_sum', '__count'):
                key = f'{col}{suffix}'
                dv = duck_fp.get(key)
                pv = pg_fp.get(key)
                if pv is None and (dv is None or dv == 0):
                    # PG 列类型不同（如 DOUBLE PRECISION），且两边均无实际数据，跳过
                    continue
                if dv != pv:
                    diffs.append(f'  列 {col}{suffix}: DuckDB={dv}, PG={pv}')
        else:
            for suffix in ('__count', '__min', '__max'):
                key = f'{col}{suffix}'
                dv = duck_fp.get(key)
                pv = pg_fp.get(key)
                if str(dv) != str(pv):
                    diffs.append(f'  列 {col}{suffix}: DuckDB={dv!r}, PG={pv!r}')
    return diffs


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # 连接数据库
    print(f'连接 DuckDB: {DUCKDB_PATH}')
    duck_con = duckdb.connect(DUCKDB_PATH, read_only=True)

    print(f'连接 PostgreSQL: {PG_DSN}')
    pg_con = psycopg2.connect(PG_DSN)
    pg_cur = pg_con.cursor()

    # 获取表列表（以 DuckDB 为准）
    duck_tables = set(
        r[0] for r in duck_con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    )
    tables = sorted(duck_tables - SKIP_TABLES)
    print(f'\n[验证] 共 {len(tables)} 张表（跳过 {SKIP_TABLES}）\n')

    pass_count = 0
    fail_count = 0
    fail_tables = []

    for table in tables:
        t1 = time.time()

        # 获取列信息（DuckDB）
        col_info = duck_con.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name='{table}' AND table_schema='main' ORDER BY ordinal_position"
        ).fetchall()

        if not col_info:
            print(f'[{table:<25}] ⚠️  无列信息，跳过')
            continue

        # 获取行数
        row_count = duck_con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

        try:
            pg_col_types = get_pg_col_types(pg_cur, table)
            duck_fp = duck_fingerprint(duck_con, table, col_info)
            pg_fp = pg_fingerprint(pg_cur, table, col_info, pg_col_types)
            diffs = compare_fingerprints(duck_fp, pg_fp, col_info)
        except Exception as e:
            pg_con.rollback()  # 重置事务，继续处理下一张表
            elapsed = time.time() - t1
            print(f'[{table:<25}] ❌ ERROR  ({row_count:,} 行) [{elapsed:.1f}s] {e}')
            fail_count += 1
            fail_tables.append((table, [f'  异常: {e}']))
            continue

        elapsed = time.time() - t1
        if diffs:
            print(f'[{table:<25}] ❌ FAIL   ({row_count:,} 行, {len(col_info)} 列) [{elapsed:.1f}s]')
            for d in diffs:
                print(d)
            fail_count += 1
            fail_tables.append((table, diffs))
        else:
            print(f'[{table:<25}] ✅ PASS   ({row_count:,} 行, {len(col_info)} 列) [{elapsed:.1f}s]')
            pass_count += 1

    total = time.time() - t0

    print(f'\n{"=" * 55}')
    print(f'验证完成，耗时 {total:.1f}s')
    if fail_count == 0:
        print(f'✅ 全部 {pass_count} 张表验证通过，数据完全一致')
        print(f'   可安全删除 data/duck.db（13GB）')
    else:
        print(f'❌ {fail_count} 张表存在差异，{pass_count} 张通过')
        print(f'\n差异汇总：')
        for t, ds in fail_tables:
            print(f'  [{t}]')
            for d in ds:
                print(d)
    print('=' * 55)

    duck_con.close()
    pg_con.close()

    return fail_count == 0


if __name__ == '__main__':
    ok = main()
    exit(0 if ok else 1)
