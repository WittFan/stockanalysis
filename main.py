"""
量化投研平台入口

用法:
    python main.py                  # 启动 Web 服务（默认端口 8888）
    python main.py --port 9000
    python main.py --no-stockpool   # 不加载股票池（仅回测功能）
"""
from web_service.server import main

if __name__ == '__main__':
    main()
