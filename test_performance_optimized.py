#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化测试脚本
Performance Optimization Test Script
"""

import time
import os
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scanner.text_scanner import TextScanner
from detector.text_duplicate_detector import TextDuplicateDetector

def test_performance(test_directory: str):
    """
    测试优化后的性能
    
    Args:
        test_directory: 测试目录路径
    """
    print(f"开始性能测试: {test_directory}")
    print("=" * 60)
    
    # 初始化组件
    scanner = TextScanner()
    detector = TextDuplicateDetector(similarity_threshold=80.0)
    
    # 进度回调函数
    def progress_callback(percent, message):
        print(f"[{percent:3d}%] {message}")
    
    # 第一阶段：扫描文件
    print("\n[阶段1] 扫描文件")
    scan_start = time.time()
    
    text_files = scanner.scan_directory(test_directory, progress_callback)
    
    scan_time = time.time() - scan_start
    print(f"[完成] 扫描完成: 找到 {len(text_files)} 个文件，用时 {scan_time:.2f}s")
    
    if not text_files:
        print("[错误] 没有找到文本文件")
        return
    
    # 统计文件信息
    total_size = sum(f.get('size', 0) for f in text_files)
    print(f"[统计] 文件统计: {len(text_files)} 个文件，总大小 {total_size / (1024*1024):.1f} MB")
    
    # 第二阶段：重复检测
    print(f"\n[阶段2] 重复检测")
    detect_start = time.time()
    
    duplicate_groups = detector.find_duplicates(text_files, progress_callback)
    
    detect_time = time.time() - detect_start
    total_time = scan_time + detect_time
    
    # 结果统计
    print(f"\n[性能结果]")
    print(f"  扫描时间: {scan_time:.2f}s")
    print(f"  检测时间: {detect_time:.2f}s")
    print(f"  总用时: {total_time:.2f}s")
    print(f"  平均每文件: {total_time/len(text_files)*1000:.1f}ms")
    print(f"  处理速度: {total_size/(1024*1024)/total_time:.1f} MB/s")
    
    # 重复文件统计
    total_duplicates = sum(len(group) for group in duplicate_groups)
    print(f"\n[检测结果]")
    print(f"  重复组数: {len(duplicate_groups)}")
    print(f"  重复文件数: {total_duplicates}")
    print(f"  重复率: {total_duplicates/len(text_files)*100:.1f}%")
    
    # 显示前几组重复文件
    if duplicate_groups:
        print(f"\n[重复文件示例]")
        for i, group in enumerate(duplicate_groups[:3]):
            print(f"  组 {i+1} ({len(group)} 个文件):")
            for file_info in group[:2]:  # 只显示前2个
                similarity = file_info.get('similarity', 0)
                size_mb = file_info.get('size', 0) / (1024*1024)
                print(f"    - {os.path.basename(file_info['path'])} ({similarity:.1f}%, {size_mb:.1f}MB)")
            if len(group) > 2:
                print(f"    ... 还有 {len(group)-2} 个文件")
    
    # 性能评估
    print(f"\n[性能评估]")
    if total_time < 60:
        print(f"  [优秀] 总用时 {total_time:.1f}s < 1分钟")
    elif total_time < 180:
        print(f"  [良好] 总用时 {total_time:.1f}s < 3分钟")
    else:
        print(f"  [需要优化] 总用时 {total_time:.1f}s > 3分钟")
    
    throughput = total_size / (1024*1024) / total_time
    if throughput > 10:
        print(f"  [优秀] 处理速度: {throughput:.1f} MB/s")
    elif throughput > 5:
        print(f"  [良好] 处理速度: {throughput:.1f} MB/s")
    else:
        print(f"  [需要优化] 处理速度: {throughput:.1f} MB/s")

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python test_performance_optimized.py <测试目录>")
        print("示例: python test_performance_optimized.py test_texts")
        return
    
    test_directory = sys.argv[1]
    
    if not os.path.exists(test_directory):
        print(f"[错误] 目录不存在: {test_directory}")
        return
    
    try:
        test_performance(test_directory)
    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
    except Exception as e:
        print(f"[错误] 测试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()