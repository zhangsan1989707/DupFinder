#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试脚本
Performance Test Script
"""

import os
import time
import tempfile
from src.scanner.text_scanner import TextScanner

def create_test_files(num_files=100):
    """创建测试文件"""
    test_dir = tempfile.mkdtemp(prefix="dupfinder_test_")
    
    for i in range(num_files):
        file_path = os.path.join(test_dir, f"test_file_{i}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"这是测试文件 {i}\n" * (i + 1))
            f.write("一些共同的内容\n")
            f.write(f"文件编号：{i}\n")
    
    return test_dir

def test_scanning_performance():
    """测试扫描性能"""
    print("创建测试文件...")
    test_dir = create_test_files(50)  # 创建50个测试文件
    
    print(f"测试目录: {test_dir}")
    
    # 创建扫描器
    scanner = TextScanner()
    
    # 定义进度回调
    def progress_callback(progress, message):
        print(f"进度: {progress}% - {message}")
    
    # 开始扫描
    print("开始扫描...")
    start_time = time.time()
    
    files = scanner.scan_directory(test_dir, progress_callback=progress_callback)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n扫描完成!")
    print(f"扫描时间: {elapsed_time:.2f}秒")
    print(f"找到文件: {len(files)}个")
    print(f"平均每文件: {elapsed_time/len(files):.3f}秒" if files else "无文件")
    
    # 显示文件信息示例
    if files:
        print(f"\n示例文件信息:")
        file_info = files[0]
        print(f"路径: {file_info['path']}")
        print(f"大小: {file_info['size']} 字节")
        print(f"行数: {file_info['line_count']}")
        print(f"字符数: {file_info['char_count']}")
        print(f"编码: {file_info['encoding']}")
        print(f"哈希: {file_info['content_hash'][:16]}...")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir)
    print(f"\n已清理测试目录: {test_dir}")

if __name__ == "__main__":
    test_scanning_performance()