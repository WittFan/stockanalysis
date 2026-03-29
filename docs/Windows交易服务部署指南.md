# Windows 交易服务部署指南

## 概述

本文档说明如何在 Windows 环境下部署 QMT 实盘交易服务，以及 Mac 端如何连接和监控。

**架构图：**

```
┌─────────────────────┐         ┌─────────────────────────────┐
│   Mac (开发/监控)    │ ◀─────▶ │   Windows (交易服务器)       │
│                     │  HTTP   │                             │
│  - 策略开发          │         │  - MiniQMT 客户端            │
│  - 监控看板          │         │  - Backtrader Cerebro        │
│  - 数据管理          │         │  - REST API 服务             │
└─────────────────────┘         └─────────────────────────────┘
```

---

## 目录结构

```
windows_service/
├── config.py                  # 配置文件
├── qmt_trading_service.py     # 主交易服务
├── api_server.py              # REST API 服务
├── run_service.py             # 启动脚本
├── mac_client_example.py      # Mac端监控客户端
├── check_env.py               # 环境检查脚本
└── README.md                  # 快速参考
```

---

## Windows 端部署步骤

### 1. 前提条件

- Windows 操作系统（Win10/Win11）
- MiniQMT 客户端已安装并可以正常运行
- Python 3.7+ 已安装
- 已开通 MiniQMT 交易权限

### 2. 安装依赖

```bash
pip install backtrader flask flask-cors loguru requests pandas numpy
```

### 3. 复制 xtquant 模块（如果未安装）

MiniQMT 自带的 `xtquant` 需要复制到项目中：

```bash
# 找到 MiniQMT 安装目录，复制 xtquant 文件夹
xcopy /E "D:\迅投极速交易终端\xtquant" .\xtquant\
```

或者将 MiniQMT 的 xtquant 路径添加到 PYTHONPATH。

### 4. 配置服务

编辑 `windows_service/config.py`：

```python
# 修改为实际的 MiniQMT 路径
QMT_PATH = r'D:\迅投极速交易终端\userdata_mini'

# 修改为实际的资金账号
QMT_ACCOUNT = '1000000365'

# 交易标的列表
STOCK_LIST = [
    '511220.SH',  # 城投债ETF
    '518880.SH',  # 黄金ETF
    '159915.SZ',  # 创业板ETF
    '510300.SH',  # 沪深300ETF
]

# API 配置（供Mac连接）
API_HOST = '0.0.0.0'  # 0.0.0.0 允许外部连接
API_PORT = 8080
```

### 5. 检查环境

```bash
cd windows_service
python check_env.py
```

检查输出确认：
- ✅ Python 版本 >= 3.7
- ✅ 依赖包已安装
- ✅ xtquant 模块可导入
- ✅ QMT 路径存在

### 6. 启动 MiniQMT 客户端

1. 打开 MiniQMT 客户端
2. 登录资金账号
3. 确认可以正常交易

### 7. 启动交易服务

#### 方式一：仅交易服务（命令行模式）

```bash
python run_service.py
```

#### 方式二：交易服务 + REST API（推荐）

```bash
python run_service.py --with-api
```

#### 方式三：指定参数

```bash
# 使用回测模式
python run_service.py --mode backtest --with-api

# 指定API端口
python run_service.py --with-api --api-port 8888

# 仅启动API（测试用）
python run_service.py --with-api --no-trading
```

### 8. 防火墙配置

如果 Mac 无法连接，需要在 Windows 防火墙中放行端口：

**方式一：PowerShell 管理员权限**

```powershell
New-NetFirewallRule -DisplayName "QMT Trading API" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

**方式二：命令提示符管理员权限**

```cmd
netsh advfirewall firewall add rule name="QMT Trading API" dir=in action=allow protocol=tcp localport=8080
```

---

## Mac 端连接步骤

### 1. 获取 Windows IP 地址

在 Windows 上执行：

```cmd
ipconfig
```

找到局域网 IP，例如：`192.168.1.100`

### 2. 修改客户端配置

编辑 `mac_client_example.py`：

```python
WINDOWS_HOST = '192.168.1.100'  # 替换为 Windows 实际 IP
WINDOWS_PORT = 8080              # 替换为实际端口
```

### 3. 运行监控客户端

```bash
python mac_client_example.py
```

### 4. 交互式命令

| 命令 | 说明 |
|------|------|
| `s` | 显示完整状态 |
| `a` | 显示账户信息 |
| `p` | 显示持仓 |
| `o` | 显示委托 |
| `r` | 开启/关闭自动刷新 |
| `q` | 退出 |

---

## REST API 接口说明

### 基础接口

#### 健康检查
```bash
GET http://{windows_ip}:8080/health
```

响应：
```json
{
  "status": "healthy",
  "running": true
}
```

### 查询接口

#### 获取完整状态
```bash
GET http://{windows_ip}:8080/api/status
```

响应：
```json
{
  "status": "running",
  "mode": "live",
  "start_time": "2024-01-15T09:30:00",
  "last_update": "2024-01-15T14:30:00",
  "cash": 100000.00,
  "total_value": 150000.00,
  "positions": {
    "511220.SH": {
      "size": 1000,
      "price": 1.05,
      "value": 1050.00
    }
  },
  "orders": [
    {
      "time": "2024-01-15T10:30:00",
      "ref": 1,
      "symbol": "511220.SH",
      "side": "buy",
      "size": 100,
      "price": 1.05,
      "status": "completed"
    }
  ],
  "error_msg": null
}
```

#### 获取账户信息
```bash
GET http://{windows_ip}:8080/api/account
```

响应：
```json
{
  "cash": 100000.00,
  "total_value": 150000.00,
  "available": 95000.00
}
```

#### 获取持仓
```bash
GET http://{windows_ip}:8080/api/positions
```

响应：
```json
{
  "511220.SH": {
    "size": 1000,
    "price": 1.05,
    "value": 1050.00
  },
  "518880.SH": {
    "size": 500,
    "price": 3.50,
    "value": 1750.00
  }
}
```

#### 获取当日委托
```bash
GET http://{windows_ip}:8080/api/orders
```

响应：
```json
[
  {
    "time": "2024-01-15T10:30:00",
    "ref": 1,
    "symbol": "511220.SH",
    "side": "buy",
    "size": 100,
    "price": 1.05,
    "status": "completed"
  }
]
```

### 控制接口

#### 发送命令
```bash
POST http://{windows_ip}:8080/api/command
Content-Type: application/json

{
  "command": "start" | "stop" | "status"
}
```

响应：
```json
{
  "success": true,
  "message": "Command executed"
}
```

---

## 策略开发

### 修改策略逻辑

编辑 `qmt_trading_service.py` 中的 `LiveStrategy` 类：

```python
class LiveStrategy(bt.Strategy):
    """实盘策略"""
    
    def next(self):
        """每根K线调用"""
        # 在这里实现你的策略逻辑
        
        # 示例：简单的买入持有
        for d in self.datas:
            pos = self.getposition(d)
            if len(pos) == 0:  # 无持仓
                self.buy(data=d, size=100)
```

### 添加自定义参数

在 `config.py` 中添加：

```python
STRATEGY_PARAMS = {
    'lookback_days': 60,
    'rebalance_freq': 'W-FRI',
    'risk_budget': 'equal',
}
```

---

## 常见问题

### Q1: 连接失败（Connection Refused）

**原因**：
- Windows 防火墙阻挡
- API_HOST 设置为 `127.0.0.1` 而非 `0.0.0.0`
- 服务未启动

**解决**：
1. 检查防火墙设置
2. 确认 `config.py` 中 `API_HOST = '0.0.0.0'`
3. 确认服务已启动并监听端口

### Q2: xtquant 导入失败

**原因**：
- xtquant 模块未找到

**解决**：
1. 复制 xtquant 到项目目录
2. 或将 MiniQMT 的 xtquant 路径添加到 PYTHONPATH

### Q3: QMTStore 连接失败

**原因**：
- MiniQMT 未启动
- QMT_PATH 配置错误
- 资金账号错误

**解决**：
1. 确认 MiniQMT 客户端已启动并登录
2. 检查 `QMT_PATH` 是否为正确的 `userdata_mini` 路径
3. 确认 `QMT_ACCOUNT` 正确

### Q4: 策略不执行交易

**原因**：
- 非交易时间
- 资金不足
- 委托被拒绝

**解决**：
1. 查看日志文件 `logs/trading_*.log`
2. 确认在交易时间内（9:30-11:30, 13:00-15:00）
3. 确认账户有足够资金

---

## 日志查看

### Windows 端日志

日志文件位置：`windows_service/logs/`

```bash
# 实时查看日志
tail -f logs/trading_20240115.log
```

日志内容包括：
- 服务启动/停止
- QMT 连接状态
- 订单提交/成交
- 错误信息

### 日志级别配置

在 `config.py` 中修改：

```python
LOG_LEVEL = 'DEBUG'  # DEBUG/INFO/WARNING/ERROR
```

---

## 环境变量配置

可通过环境变量覆盖配置文件：

```bash
# Windows CMD
set QMT_PATH=D:\迅投极速交易终端\userdata_mini
set QMT_ACCOUNT=1000000365
set API_PORT=8888
set TRADING_MODE=live

# Windows PowerShell
$env:QMT_PATH="D:\迅投极速交易终端\userdata_mini"
$env:QMT_ACCOUNT="1000000365"
```

---

## 生产环境建议

### 1. 安全性

- 修改默认的 `API_TOKEN`
- 使用 HTTPS（通过反向代理）
- 限制 API 访问 IP

### 2. 稳定性

- 使用进程管理器（如 pm2、nssm）保持服务运行
- 配置自动重启
- 设置监控告警

### 3. 备份

- 定期备份交易日志
- 备份策略配置
- 记录每日持仓快照

---

## 相关文档

- [xtdata API 参考](./xtdata.md)
- [xttrader API 参考](./xttrader.md)
- [项目计划](./项目计划.md)

---

## 技术支持

如有问题，请检查：
1. 日志文件中的错误信息
2. MiniQMT 客户端状态
3. 网络连接是否正常
