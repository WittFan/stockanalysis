#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows 环境检查脚本
====================
检查运行交易服务所需的环境和依赖

运行方式：
    python check_env.py
"""

import sys
import os
import platform
from pathlib import Path

# 将项目根目录添加到 Python 路径，以便导入 xtquant
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python():
    """检查 Python 版本"""
    print_section("Python 环境")
    
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 7:
        print("[OK] Python 版本符合要求 (>= 3.7)")
        return True
    else:
        print("[FAIL] Python 版本过低，需要 >= 3.7")
        return False


def check_dependencies():
    """检查依赖包"""
    print_section("依赖包检查")
    
    required = {
        'flask': 'Flask Web 框架',
        'flask_cors': 'Flask 跨域支持',
        'loguru': '日志库',
        'requests': 'HTTP 客户端（API测试用）',
    }
    
    optional = {
        'pandas': '数据处理',
        'numpy': '数值计算',
    }
    
    all_ok = True
    
    print("\n必需依赖:")
    for package, desc in required.items():
        try:
            __import__(package)
            print(f"  [OK] {package:15} - {desc}")
        except ImportError:
            print(f"  [FAIL] {package:15} - {desc} (未安装)")
            all_ok = False
    
    print("\n可选依赖:")
    for package, desc in optional.items():
        try:
            __import__(package)
            print(f"  [OK] {package:15} - {desc}")
        except ImportError:
            print(f"  [WARN] {package:15} - {desc} (未安装)")
    
    if not all_ok:
        print("\n安装缺失依赖:")
        print("  pip install flask flask-cors loguru requests")
    
    return all_ok


def check_xtquant():
    """检查 xtquant 安装"""
    print_section("xtquant 检查")
    
    try:
        import xtquant
        print("[OK] xtquant 模块已安装")
        
        # 检查关键子模块
        modules = ['xtdata', 'xttrader', 'xtconstant', 'xttype']
        for mod in modules:
            try:
                __import__(f'xtquant.{mod}')
                print(f"  [OK] xtquant.{mod}")
            except ImportError as e:
                print(f"  [FAIL] xtquant.{mod}: {e}")
        
        return True
        
    except ImportError:
        print("[FAIL] xtquant 未安装")
        print("\nxtquant 是 MiniQMT 自带的 Python 库，")
        print("请确保 MiniQMT 已正确安装，并将 xtquant 目录添加到 PYTHONPATH")
        print("\n或者复制 xtquant 目录到当前项目：")
        print("  xcopy /E \"%QMT_PATH%\\..\\xtquant\" .\\xtquant\\")
        return False


def check_qmt_path():
    """检查 QMT 路径"""
    print_section("QMT 路径检查")
    
    # 尝试读取配置
    try:
        import config
        qmt_path = config.QMT_PATH
    except:
        qmt_path = r'D:\迅投极速交易终端\userdata_mini'
    
    print(f"配置路径: {qmt_path}")
    
    if not os.path.exists(qmt_path):
        print("[FAIL] 路径不存在")
        print("\n请修改 config.py 中的 QMT_PATH 为正确的路径")
        return False
    
    print("[OK] 路径存在")
    
    # 检查关键文件/目录
    checks = [
        ('datadir', '数据目录'),
    ]
    
    for dirname, desc in checks:
        path = os.path.join(qmt_path, dirname)
        if os.path.exists(path):
            print(f"  [OK] {dirname}: {desc}")
        else:
            print(f"  [WARN] {dirname}: 不存在（{desc}）")
    
    return True


def check_network():
    """检查网络配置"""
    print_section("网络配置检查")
    
    import socket
    
    # 获取本机IP
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"主机名: {hostname}")
        print(f"本机IP: {ip}")
        print("\n请确保 Mac 端使用该 IP 连接")
    except Exception as e:
        print(f"[WARN] 获取IP失败: {e}")
    
    # 检查端口占用
    print("\n检查端口占用:")
    ports = [8080, 8888]
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        if result == 0:
            print(f"  [WARN] 端口 {port} 已被占用")
        else:
            print(f"  [OK] 端口 {port} 可用")
        sock.close()


def check_firewall():
    """提示防火墙配置"""
    print_section("防火墙提示")
    
    print("如果 Mac 无法连接，请检查 Windows 防火墙设置：")
    print("\n1. 打开 Windows 防火墙设置")
    print("2. 允许 Python 通过防火墙")
    print("3. 或者添加端口规则（如 8080）")
    print("\n快速命令（管理员权限运行）:")
    print(f'  netsh advfirewall firewall add rule name="QMT Trading API" '
          f'dir=in action=allow protocol=tcp localport=8080')


def print_next_steps():
    """打印下一步操作"""
    print_section("下一步操作")
    
    print("1. 编辑 config.py，修改 QMT_PATH 和 QMT_ACCOUNT")
    print("2. 启动 MiniQMT 客户端并登录")
    print("3. 运行服务：")
    print("   python run_service.py")
    print("\n4. 在 Mac 端运行：")
    print("   python mac_client_example.py")


def main():
    """主函数"""
    print("=" * 60)
    print("  Windows 交易服务环境检查")
    print("=" * 60)
    print(f"  平台: {platform.platform()}")
    print(f"  系统: {platform.system()} {platform.release()}")
    print("=" * 60)
    
    results = []
    
    results.append(("Python", check_python()))
    results.append(("依赖包", check_dependencies()))
    results.append(("xtquant", check_xtquant()))
    results.append(("QMT路径", check_qmt_path()))
    check_network()
    check_firewall()
    
    # 汇总
    print_section("检查结果汇总")
    
    all_pass = all(r[1] for r in results)
    
    for name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"  {status}: {name}")
    
    print()
    if all_pass:
        print("[PASS] 环境检查通过，可以运行交易服务！")
    else:
        print("[WARN] 部分检查未通过，请修复后再运行")
    
    print_next_steps()


if __name__ == '__main__':
    main()
