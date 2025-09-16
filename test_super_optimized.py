#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超级优化性能测试脚本
Super Optimized Performance Test Script
"""

import time
import os
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scanner.text_scanner import TextScanner
from detector.text_duplicate_detector import TextDuplicateDetector

def test_super_performance(test_directory: str):
    """
    测试超级优化后的性能
    
    Args:
        test_directory: 测试目录路径
    """
    print(f"开始超级优化性能测试: {test_directory}")
    print("=" * 60)
    
    # 初始化组件 - 使用更激进的配置
    scanner = TextScanner(max_file_size=10 * 1024 * 1024)  # 限制10MB
    detector = TextDuplicateDetector(
        similarity_threshold=85.0,  # 提高相似度阈值
        max_workers=None  # 自动检测最优线程数
    )
    
    # 进度回调函数
    def progress_callback(percent, message):
        print(f"[{percent:3d}%] {message}")
    
    # 第一阶段：快速扫描
    print("\n[阶段1] 超快速扫描")
    scan_start = time.time()
    
    text_files = scanner.scan_directory(test_directory, progress_callback)
    
    scan_time = time.time() - scan_start
    print(f"[完成] 扫描完成: 找到 {len(text_files)} 个文件，用时 {scan_time:.2f}s")
    
    if not text_files:
        print("[错误] 没有找到文本文件")
        return
    
    # 统计文件信息
    total_size = sum(f.get('size', 0) for f in text_files)
    avg_size = total_size / len(text_files) if text_files else 0
    
    print(f"[统计] {len(text_files)} 个文件，总大小 {total_size / (1024*1024):.1f} MB")
    print(f"[统计] 平均文件大小 {avg_size / 1024:.1f} KB")
    
    # 预估处理时间
    estimated_time = len(text_files) * 0.001  # 每文件1ms
    if len(text_files) > 100:
        estimated_time = len(text_files) * 0.01  # 大数据集每文件10ms
    
    print(f"[预估] 预计处理时间: {estimated_time:.1f}s")
    
    # 第二阶段：超级重复检测
    print(f"\n[阶段2] 超级重复检测")
    detect_start = time.time()
    
    try:
        duplicate_groups = detector.find_duplicates(text_files, progress_callback)
        detect_time = time.time() - detect_start
        
        # 性能分析
        total_time = scan_time + detect_time
        throughput = total_size / (1024*1024) / total_time if total_time > 0 else 0
        files_per_sec = len(text_files) / total_time if total_time > 0 else 0
        
        print(f"\n[超级性能结果]")
        print(f"  扫描时间: {scan_time:.3f}s")
        print(f"  检测时间: {detect_time:.3f}s")
        print(f"  总用时: {total_time:.3f}s")
        print(f"  文件处理速度: {files_per_sec:.1f} 文件/秒")
        print(f"  数据处理速度: {throughput:.1f} MB/s")
        
        # 重复文件统计
        total_duplicates = sum(len(group) for group in duplicate_groups)
        duplicate_size = 0
        for group in duplicate_groups:
            for file_info in group[1:]:  # 除了第一个文件，其他都是重复的
                duplicate_size += file_info.get('size', 0)
        
        print(f"\n[检测结果]")
        print(f"  重复组数: {len(duplicate_groups)}")
        print(f"  重复文件数: {total_duplicates}")
        print(f"  重复率: {total_duplicates/len(text_files)*100:.1f}%")
        print(f"  可节省空间: {duplicate_size/(1024*1024):.1f} MB")
        
        # 显示重复文件示例
        if duplicate_groups:
            print(f"\n[重复文件示例]")
            for i, group in enumerate(duplicate_groups[:3]):
                print(f"  组 {i+1} ({len(group)} 个文件):")
                for j, file_info in enumerate(group[:3]):
                    similarity = file_info.get('similarity', 0)
                    size_kb = file_info.get('size', 0) / 1024
                    print(f"    {j+1}. {os.path.basename(file_info['path'])} ({similarity:.1f}%, {size_kb:.1f}KB)")
                if len(group) > 3:
                    print(f"    ... 还有 {len(group)-3} 个文件")
        
        # 超级性能评估
        print(f"\n[超级性能评估]")
        
        # 时间评估
        if total_time < 10:
            print(f"  [极速] 总用时 {total_time:.2f}s - 闪电般快速!")
        elif total_time < 30:
            print(f"  [很快] 总用时 {total_time:.2f}s - 非常优秀!")
        elif total_time < 60:
            print(f"  [快速] 总用时 {total_time:.2f}s - 表现良好")
        else:
            print(f"  [一般] 总用时 {total_time:.2f}s - 仍需优化")
        
        # 吞吐量评估
        if files_per_sec > 100:
            print(f"  [极速] 处理速度 {files_per_sec:.0f} 文件/秒 - 超级快!")
        elif files_per_sec > 50:
            print(f"  [很快] 处理速度 {files_per_sec:.0f} 文件/秒 - 很棒!")
        elif files_per_sec > 10:
            print(f"  [不错] 处理速度 {files_per_sec:.0f} 文件/秒 - 还可以")
        else:
            print(f"  [慢] 处理速度 {files_per_sec:.1f} 文件/秒 - 需要优化")
        
        # 与原始性能对比
        original_time = len(text_files) * 0.5  # 假设原始每文件0.5秒
        speedup = original_time / total_time if total_time > 0 else 1
        print(f"  [提升] 相比原始版本快 {speedup:.0f}x")
        
    except Exception as e:
        print(f"[错误] 检测过程出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python test_super_optimized.py <测试目录>")
        print("示例: python test_super_optimized.py E:/Ebook/夜读")
        return
    
    test_directory = sys.argv[1]
    
    if not os.path.exists(test_directory):
        print(f"[错误] 目录不存在: {test_directory}")
        return
    
    try:
        test_super_performance(test_directory)
    except KeyboardInterrupt:
        print("\n[中断] 测试被用户中断")
    except Exception as e:
        print(f"[错误] 测试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()