#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本
Launch Script
"""

import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

try:
    from main import main
    main()
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖包:")
    print("pip install -r requirements.txt")
except Exception as e:
    print(f"运行错误: {e}")
    input("按回车键退出...")