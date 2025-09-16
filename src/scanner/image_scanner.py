#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片文件扫描器
Image File Scanner
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from PIL import Image
import cv2
import numpy as np

class ImageScanner:
    """图片文件扫描器"""
    
    # 支持的图片文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif',
        '.webp', '.svg', '.heic', '.heif', '.jp2', '.j2k', '.dng'
    }
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB
        """
        初始化图片扫描器
        
        Args:
            max_file_size: 最大文件大小限制（字节）
        """
        self.max_file_size = max_file_size
        self._lock = threading.Lock()
        
    def scan_directory(self, directory_path: str, 
                      progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        扫描目录中的图片文件
        
        Args:
            directory_path: 目录路径
            progress_callback: 进度回调函数
            
        Returns:
            图片文件信息列表
        """
        image_files = []
        
        if not os.path.exists(directory_path):
            if progress_callback:
                progress_callback(0, "路径不存在")
            return image_files
        
        # 首先快速统计文件总数用于进度计算
        total_files = 0
        processed_files = 0
        
        if progress_callback:
            progress_callback(5, "正在统计文件数量...")
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d.lower() not in {'__pycache__', 'node_modules', '.git', '.svn', 
                                           'build', 'dist', 'target', 'bin', 'obj'}]
                for file in files:
                    if self._is_image_file(file):
                        total_files += 1
            
        # 遍历目录收集图片文件
        image_paths = []
        for root, dirs, files in os.walk(directory_path):
            # 跳过隐藏目录和常见的非图片目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and 
                      d.lower() not in {'__pycache__', 'node_modules', '.git', '.svn', 
                                       'build', 'dist', 'target', 'bin', 'obj'}]
            
            for file in files:
                if self._is_image_file(file):
                    file_path = os.path.join(root, file)
                    image_paths.append(file_path)
        
        # 并行处理图片文件信息
        image_files = self._parallel_get_image_info(image_paths, total_files, progress_callback)
        
        if progress_callback:
            progress_callback(95, f"扫描完成，找到 {len(image_files)} 个图片文件")
        
        return image_files
    
    def _is_image_file(self, filename: str) -> bool:
        """
        判断是否为支持的图片文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否为图片文件
        """
        _, ext = os.path.splitext(filename.lower())
        return ext in self.SUPPORTED_EXTENSIONS
    
    def _parallel_get_image_info(self, image_paths: List[str], total_files: int, 
                               progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        并行获取图片信息
        
        Args:
            image_paths: 图片文件路径列表
            total_files: 总文件数（用于进度计算）
            progress_callback: 进度回调函数
            
        Returns:
            图片文件信息列表
        """
        image_files = []
        processed_count = 0
        
        # 根据文件数量动态调整线程数
        max_workers = min(8, len(image_paths) // 10 + 1) if image_paths else 1
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_path = {
                executor.submit(self._get_image_info, path): path 
                for path in image_paths
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_info = future.result()
                    if file_info:
                        with self._lock:
                            image_files.append(file_info)
                        
                    processed_count += 1
                    if progress_callback and total_files > 0:
                        progress_percent = min(90, 10 + int((processed_count / total_files) * 80))
                        progress_callback(progress_percent, f"已扫描: {processed_count}/{total_files} - {os.path.basename(path)}")
                        
                except Exception as e:
                    print(f"处理文件 {path} 时发生错误: {e}")
        
        return image_files
    
    def _get_image_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取图片文件的详细信息
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            图片文件信息字典，如果无法处理则返回None
        """
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return None
            
            # 获取基本信息
            file_info = {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': file_size,
                'mtime': os.path.getmtime(file_path)
            }
            
            # 尝试使用PIL获取图片信息
            try:
                with Image.open(file_path) as img:
                    file_info['width'], file_info['height'] = img.size
                    file_info['format'] = img.format
                    file_info['mode'] = img.mode
            except Exception as e:
                # 如果PIL失败，尝试使用OpenCV
                try:
                    img = cv2.imread(file_path)
                    if img is not None:
                        height, width = img.shape[:2]
                        file_info['width'] = width
                        file_info['height'] = height
                        file_info['format'] = 'OpenCV'
                except Exception as cv2_err:
                    print(f"无法获取图片信息 {file_path}: {str(e)}, {str(cv2_err)}")
            
            return file_info
            
        except Exception as e:
            print(f"处理文件 {file_path} 时发生错误: {str(e)}")
            return None