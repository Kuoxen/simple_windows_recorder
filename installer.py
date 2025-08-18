#!/usr/bin/env python3
"""
一键安装脚本
自动安装依赖并启动程序
"""

import subprocess
import sys
import os

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    
    try:
        # 安装运行时依赖
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 运行时依赖安装完成")
        
        # 安装打包工具（可选）
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "build_requirements.txt"])
            print("✅ 打包工具安装完成")
        except:
            print("⚠️  打包工具安装失败（不影响程序运行）")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False
    
    return True

def check_vb_cable():
    """检查VB-Cable是否安装"""
    print("\n检查VB-Cable虚拟音频设备...")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        has_cable = False
        for device in devices:
            if 'cable' in device['name'].lower():
                has_cable = True
                break
        
        if has_cable:
            print("✅ 检测到VB-Cable设备")
        else:
            print("⚠️  未检测到VB-Cable设备")
            print("请从以下地址下载安装VB-Cable:")
            print("https://vb-audio.com/Cable/")
            
    except Exception as e:
        print(f"⚠️  设备检测失败: {e}")

def create_desktop_shortcut():
    """创建桌面快捷方式（Windows）"""
    if os.name == 'nt':  # Windows
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            path = os.path.join(desktop, "呼叫中心录音系统.lnk")
            target = os.path.join(os.getcwd(), "run_ui.py")
            wDir = os.getcwd()
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = wDir
            shortcut.save()
            
            print("✅ 桌面快捷方式创建成功")
            
        except ImportError:
            print("⚠️  创建快捷方式需要安装: pip install winshell pywin32")
        except Exception as e:
            print(f"⚠️  快捷方式创建失败: {e}")

def main():
    print("=== 呼叫中心录音系统 - 一键安装 ===\n")
    
    # 1. 安装依赖
    if not install_dependencies():
        print("安装失败，请检查网络连接和Python环境")
        input("按回车键退出...")
        return
    
    # 2. 检查VB-Cable
    check_vb_cable()
    
    # 3. 创建快捷方式
    create_desktop_shortcut()
    
    print("\n=== 安装完成 ===")
    print("启动方式:")
    print("1. 双击桌面快捷方式")
    print("2. 或运行: python run_ui.py")
    
    # 4. 询问是否立即启动
    choice = input("\n是否立即启动程序? (y/n): ").strip().lower()
    if choice == 'y':
        try:
            subprocess.Popen([sys.executable, "run_ui.py"])
            print("程序已启动！")
        except Exception as e:
            print(f"启动失败: {e}")
    
    input("按回车键退出...")

if __name__ == "__main__":
    main()