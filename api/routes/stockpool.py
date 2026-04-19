"""
股票池 CRUD API

GET    /api/stockpool          → 列表（支持 ?q=搜索关键字）
POST   /api/stockpool          → 新增
PUT    /api/stockpool/<id>     → 修改
DELETE /api/stockpool/<id>     → 删除
POST   /api/stockpool/import   → 从 stockpool.xlsx 重新导入（覆盖）
"""
from flask import Blueprint, jsonify, request
from loguru import logger

from orm_models.api import session
from orm_models.table_models.stockpool import StockPool
from sqlalchemy import or_

bp = Blueprint('stockpool', __name__)


def _row_to_dict(row: StockPool) -> dict:
    return {
        'id': row.id,
        'ts_code': row.ts_code,
        'name': row.name,
        'in_date': row.in_date,
        'out_date': row.out_date,
        'created_at': row.created_at.strftime('%Y-%m-%d %H:%M:%S') if row.created_at else None,
        'updated_at': row.updated_at.strftime('%Y-%m-%d %H:%M:%S') if row.updated_at else None,
    }


@bp.route('/stockpool', methods=['GET'])
def list_stockpool():
    """获取股票池列表，支持按 ts_code 或 name 模糊搜索"""
    q = request.args.get('q', '').strip()
    query = session.query(StockPool)
    if q:
        query = query.filter(
            or_(
                StockPool.ts_code.ilike(f'%{q}%'),
                StockPool.name.ilike(f'%{q}%'),
            )
        )
    rows = query.order_by(StockPool.id.desc()).all()
    return jsonify({'data': [_row_to_dict(r) for r in rows], 'count': len(rows)})


@bp.route('/stockpool', methods=['POST'])
def create_stock():
    """新增股票"""
    body = request.get_json(force=True, silent=True) or {}
    ts_code = (body.get('ts_code') or '').strip()
    name = (body.get('name') or '').strip()
    if not ts_code or not name:
        return jsonify({'error': 'ts_code 和 name 不能为空'}), 400

    existing = session.query(StockPool).filter_by(ts_code=ts_code).first()
    if existing:
        return jsonify({'error': f'股票 {ts_code} 已存在'}), 409

    row = StockPool(
        ts_code=ts_code,
        name=name,
        in_date=body.get('in_date'),
        out_date=body.get('out_date'),
    )
    session.add(row)
    session.commit()
    logger.info(f'[stockpool] 新增 {ts_code} {name}')
    return jsonify({'data': _row_to_dict(row)}), 201


@bp.route('/stockpool/<int:pk>', methods=['PUT'])
def update_stock(pk):
    """修改股票"""
    body = request.get_json(force=True, silent=True) or {}
    row = session.query(StockPool).filter_by(id=pk).first()
    if not row:
        return jsonify({'error': '记录不存在'}), 404

    new_code = (body.get('ts_code') or '').strip()
    if new_code and new_code != row.ts_code:
        dup = session.query(StockPool).filter_by(ts_code=new_code).first()
        if dup:
            return jsonify({'error': f'股票 {new_code} 已存在'}), 409
        row.ts_code = new_code

    if body.get('name'):
        row.name = body['name'].strip()
    if 'in_date' in body:
        row.in_date = body['in_date']
    if 'out_date' in body:
        row.out_date = body['out_date']

    session.commit()
    logger.info(f'[stockpool] 修改 id={pk}')
    return jsonify({'data': _row_to_dict(row)})


@bp.route('/stockpool/<int:pk>', methods=['DELETE'])
def delete_stock(pk):
    """删除股票"""
    row = session.query(StockPool).filter_by(id=pk).first()
    if not row:
        return jsonify({'error': '记录不存在'}), 404
    session.delete(row)
    session.commit()
    logger.info(f'[stockpool] 删除 id={pk} {row.ts_code}')
    return jsonify({'message': '删除成功'})


@bp.route('/stockpool/import', methods=['POST'])
def import_stockpool():
    """从 stockpool.xlsx 重新导入（全量覆盖）"""
    import pandas as pd
    from pathlib import Path

    xlsx_path = Path(__file__).parent.parent.parent / 'stockpool.xlsx'
    if not xlsx_path.exists():
        return jsonify({'error': 'stockpool.xlsx 不存在'}), 404

    df = pd.read_excel(str(xlsx_path), sheet_name='出入池时间表A股')
    # 清理旧数据
    session.query(StockPool).delete()
    session.commit()

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
    logger.info(f'[stockpool] 从 xlsx 导入 {added} 条记录')
    return jsonify({'message': f'导入成功，共 {added} 条'})
