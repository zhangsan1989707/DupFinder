#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本查重功能测试脚本
"""

import sys
import os
sys.path.append('src')

from scanner.text_scanner import TextScanner
from detector.text_duplicate_detector import TextDuplicateDetector

def test_text_duplicate_detection():
    """测试文本查重功能"""
    print("开始测试文本查重功能...")
    
    # 初始化扫描器和检测器
    scanner = TextScanner()
    detector = TextDuplicateDetector(similarity_threshold=80.0)
    
    # 扫描测试目录
    test_dir = "test_texts"
    if not os.path.exists(test_dir):
        print(f"测试目录 {test_dir} 不存在")
        return
    
    print(f"扫描目录: {test_dir}")
    text_files = scanner.scan_directory(test_dir)
    
    print(f"找到 {len(text_files)} 个文本文件:")
    for file_info in text_files:
        print(f"  - {file_info['name']}: {file_info['size']} 字节, {file_info['line_count']} 行, {file_info['char_count']} 字符")
    
    if len(text_files) < 2:
        print("文件数量不足，无法进行重复检测")
        return
    
    # 检测重复文件
    print("\n开始检测重复文件...")
    duplicate_groups = detector.find_duplicates(text_files)
    
    print(f"找到 {len(duplicate_groups)} 组重复文件:")
    
    for i, group in enumerate(duplicate_groups):
        print(f"\n重复组 {i+1} ({len(group)} 个文件):")
        for file_info in group:
            similarity = file_info.get('similarity', 100)
            match_type = file_info.get('match_type', 'unknown')
            print(f"  - {file_info['name']}: {similarity:.1f}% 相似度 ({match_type})")
    
    # 测试详细相似度分析
    if len(text_files) >= 2:
        print(f"\n详细相似度分析 (前两个文件):")
        file1 = detector._preprocess_text(text_files[0])
        file2 = detector._preprocess_text(text_files[1])
        
        if file1 and file2:
            details = detector.get_similarity_details(file1, file2)
            print(f"  序列相似度: {details['sequence_similarity']:.1f}%")
            print(f"  词汇相似度: {details['vocabulary_similarity']:.1f}%")
            print(f"  结构相似度: {details['structure_similarity']:.1f}%")

if __name__ == "__main__":
    test_text_duplicate_detection()