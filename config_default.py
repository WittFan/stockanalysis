"""
Mac 端配置模板（已上传 GitHub）
================================
首次部署步骤：
  cp config_default.py config.py
  # 编辑 config.py，填入 TUSHARE_TOKEN 等实际值
"""
import tushare as ts
from pathlib import Path

# =============================================================================
# Tushare 数据源
# =============================================================================

TUSHARE_TOKEN = ''   # 在 https://tushare.pro 注册后获取

# 懒加载：首次调用 get_pro() 时才初始化，避免导入时产生网络调用副作用。
_pro = None

def get_pro():
    """获取 Tushare pro API 实例（单例，首次调用时初始化）。"""
    global _pro
    if _pro is None:
        ts.set_token(TUSHARE_TOKEN)
        _pro = ts.pro_api()
    return _pro

# 向后兼容：保留 pro 变量，但改为惰性代理——实际上与 get_pro() 等价。
# 若代码中存在 `from config import pro`，直接调用 pro.xxx() 仍然有效，
# 但推荐迁移到 get_pro()。
class _LazyPro:
    """代理对象，将属性访问转发给真实的 pro 实例，实现惰性初始化。"""
    def __getattr__(self, name):
        return getattr(get_pro(), name)

pro = _LazyPro()

# =============================================================================
# 数据库
# =============================================================================

WORKDIR  = Path(__file__).parent
DATA_DIR = WORKDIR / 'data'

DB_URI = f'duckdb:///{DATA_DIR}/duck.db'

# =============================================================================
# 数据目录路径常量（目录由 run.py 在启动时创建，不在导入时创建）
# =============================================================================

DATA_DIR_CSVS   = DATA_DIR / 'csvs'
DATA_DIR_PRJ    = DATA_DIR / 'projs'
DATA_DIR_MODELS = DATA_DIR / 'models'

# =============================================================================
# 性能
# =============================================================================

CPU_COUNT = 4
cpu_count = CPU_COUNT   # 向后兼容

# =============================================================================
# Windows QMT 服务地址（Mac 端调用 Windows 交易服务时使用）
# =============================================================================

QMT_SERVICE_HOST  = '192.168.1.100'   # Windows 机器局域网 IP
QMT_SERVICE_PORT  = 8080
QMT_SERVICE_TOKEN = ''                # 必须与 windows_service/config.py 中 API_TOKEN 一致

# =============================================================================
# 向后兼容
# =============================================================================

path = str(WORKDIR)
