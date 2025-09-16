#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller 打包脚本
Build script for creating executable
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """清理构建目录"""
    print("清理构建目录...")
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已删除: {dir_name}")

def create_spec_file():
    """创建PyInstaller spec文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 添加必要的数据文件
        ('src/gui', 'gui'),
        ('src/scanner', 'scanner'),
        ('src/detector', 'detector'),
        ('src/processor', 'processor'),
        ('src/utils', 'utils'),
    ],
    hiddenimports=[
        # PyQt5相关模块
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        # OpenCV相关模块
        'cv2',
        'numpy',
        # 其他隐藏导入
        'imagehash',
        'videohash',
        'ffmpeg',
        'send2trash',
        'tqdm',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DupFinder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径
    version_info={
        'version': (1, 0, 0, 0),
        'description': '视频文件智能查重工具',
        'product_name': 'DupFinder',
        'file_version': (1, 0, 0, 0),
        'product_version': (1, 0, 0, 0),
        'company_name': '',
        'copyright': '',
    }
)
'''
    
    with open('DupFinder.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("已创建: DupFinder.spec")

def build_exe():
    """构建exe文件"""
    print("开始构建exe文件...")
    
    # 运行PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'DupFinder.spec'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功!")
        print(result.stdout)
        
        # 检查生成的文件
        exe_path = Path('dist/DupFinder.exe')
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"生成的exe文件: {exe_path}")
            print(f"文件大小: {size_mb:.1f} MB")
        else:
            print("警告: exe文件未找到")
            
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    
    return True

def create_installer_info():
    """创建安装说明"""
    info_content = """# DupFinder 视频查重工具

## 系统要求
- Windows 10 或更高版本
- 64位系统

## 安装说明
1. 下载 DupFinder.exe
2. 双击运行即可使用，无需安装

## 使用说明
1. 点击"添加路径"选择要扫描的视频文件夹
2. 调整相似度阈值（建议80%）
3. 点击"开始扫描"
4. 扫描完成后查看重复文件列表
5. 选择要保留的文件（未选中的将被删除）
6. 点击"执行处理"完成清理

## 支持的视频格式
- MP4, AVI, MKV, MOV, WMV, FLV

## 注意事项
- 首次运行可能被杀毒软件拦截，请添加信任
- 删除的文件会被移动到回收站，可以恢复
- 大量文件扫描需要较长时间，请耐心等待

## 技术支持
如有问题请联系开发者
"""
    
    with open('dist/使用说明.txt', 'w', encoding='utf-8') as f:
        f.write(info_content)
    print("已创建: dist/使用说明.txt")

def main():
    """主函数"""
    print("=== DupFinder 打包工具 ===")
    
    # 检查是否在项目根目录
    if not os.path.exists('src/main.py'):
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 检查是否安装了依赖
    try:
        import PyInstaller
    except ImportError:
        print("错误: 请先安装PyInstaller")
        print("运行: pip install pyinstaller")
        sys.exit(1)
    
    try:
        # 1. 清理构建目录
        clean_build_dirs()
        
        # 2. 创建spec文件
        create_spec_file()
        
        # 3. 构建exe
        if build_exe():
            # 4. 创建使用说明
            create_installer_info()
            print("\n=== 打包完成 ===")
            print("exe文件位置: dist/DupFinder.exe")
            print("使用说明: dist/使用说明.txt")
        else:
            print("\n=== 打包失败 ===")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n用户取消操作")
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()