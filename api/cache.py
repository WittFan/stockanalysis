"""
线程安全的内存缓存。
供各 handler 按 key 缓存计算结果（如按 period 缓存图表数据）。
"""
import threading


class Cache:
    def __init__(self):
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self._store.get(key)

    def set(self, key, value):
        with self._lock:
            self._store[key] = value

    def has(self, key) -> bool:
        with self._lock:
            return key in self._store

    def clear(self):
        with self._lock:
            self._store.clear()


# 各 handler 共享的全局缓存实例
chart_cache    = Cache()   # key: period(int) → {dates, series, count}
industry_cache = Cache()   # key: period(int) → {dates, groups, total}
value_cache    = Cache()   # key: 'raw_{year}' → DataFrame；(year, metric) → {stocks, count}
