"""
线程安全的内存缓存，支持可选 TTL（秒）过期。

供各 handler 按 key 缓存计算结果（如按 period 缓存图表数据）。
设置 ttl=None 表示永不过期（程序级生命周期）。
"""
import threading
import time


class Cache:
    def __init__(self):
        self._store: dict = {}   # key → {'value': ..., 'expires_at': float|None}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at = entry.get('expires_at')
            if expires_at is not None and time.time() > expires_at:
                del self._store[key]
                return None
            return entry['value']

    def set(self, key, value, ttl: float = None):
        """
        存入缓存。
        :param ttl: 存活秒数，None 表示永不过期。
        """
        expires_at = (time.time() + ttl) if ttl is not None else None
        with self._lock:
            self._store[key] = {'value': value, 'expires_at': expires_at}

    def has(self, key) -> bool:
        """检查 key 是否存在且未过期。"""
        return self.get(key) is not None

    def clear(self):
        with self._lock:
            self._store.clear()


# 各 handler 共享的全局缓存实例
chart_cache    = Cache()   # key: period(int) → {dates, series, count}    TTL=None（股票池程序级）
industry_cache = Cache()   # key: period(int) → {dates, groups, total}    TTL=None
value_cache    = Cache()   # key: 'raw_{year}' / (year, metric) → data    TTL=3600（1小时）
