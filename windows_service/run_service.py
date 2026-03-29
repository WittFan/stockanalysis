#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
服务启动脚本
============
初始化 QMT 连接（MiniQMT）并启动 REST API 服务。

用法：
    python run_service.py              # 连接 QMT + 启动 API
    python run_service.py --api-port 9090
    python run_service.py --dry-run    # 不连接 QMT（用于测试 API 路由）
"""

import sys
import time
import argparse
from pathlib import Path

from loguru import logger
import config
import api_server


def setup_logging():
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format='<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | '
               '<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    )
    logger.add(
        log_dir / 'qmt_api_{time:YYYYMMDD}.log',
        rotation='1 day',
        level=config.LOG_LEVEL,
        encoding='utf-8',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} - {message}',
    )


def parse_args():
    p = argparse.ArgumentParser(description='QMT REST API Service')
    p.add_argument('--api-host', default=config.API_HOST,
                   help=f'监听地址（默认 {config.API_HOST}）')
    p.add_argument('--api-port', type=int, default=config.API_PORT,
                   help=f'监听端口（默认 {config.API_PORT}）')
    p.add_argument('--dry-run', action='store_true',
                   help='不连接 QMT，直接启动 API（用于路由测试）')
    return p.parse_args()


def main():
    args = parse_args()
    setup_logging()

    logger.info('QMT API Service 启动')
    logger.info(f'QMT路径:  {config.QMT_PATH}')
    logger.info(f'资金账号: {config.QMT_ACCOUNT}')
    logger.info(f'API地址:  http://{args.api_host}:{args.api_port}')

    store = None

    try:
        if not args.dry_run:
            # 初始化 QMT 连接（直接使用 xtquant，不依赖 Backtrader 适配层）
            from qmt_connection import QMTConnection
            store = QMTConnection(
                qmtpath=config.QMT_PATH,
                account_id=config.QMT_ACCOUNT,
                session_id=config.QMT_SESSION,
            )
            if not store.connect():
                logger.error('MiniQMT 连接失败，退出')
                sys.exit(1)
        else:
            logger.warning('dry-run 模式：跳过 QMT 连接')

        # 启动 REST API
        api_server.start_api_server(
            store=store,
            host=args.api_host,
            port=args.api_port,
        )

        logger.info('按 Ctrl+C 停止服务')
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info('收到停止信号')
    except Exception as e:
        logger.exception(f'运行异常: {e}')
    finally:
        if store:
            store.stop()
        logger.info('服务已停止')


if __name__ == '__main__':
    main()
