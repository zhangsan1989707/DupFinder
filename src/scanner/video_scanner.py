#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频文件扫描器
Video File Scanner
"""

import os
import cv2
from pathlib import Path
from typing import List, Dict, Any

class VideoScanner:
    """视频文件扫描器"""
    
    # 支持的视频格式
    SUPPORTED_FORMATS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', 
        '.webm', '.m4v', '.3gp', '.asf', '.rm', '.rmvb'
    }
    
    def __init__(self):
        """初始化扫描器"""
        pass
        
    def scan_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        扫描目录中的视频文件
        
        Args:
            directory_path: 目录路径
            
        Returns:
            视频文件信息列表
        """
        video_files = []
        
        try:
            directory = Path(directory_path)
            if not directory.exists():
                return video_files
                
            # 递归扫描目录
            for file_path in directory.rglob('*'):
                if file_path.is_file() and self.is_video_file(file_path):
                    file_info = self.get_video_info(file_path)
                    if file_info:
                        video_files.append(file_info)
                        
        except Exception as e:
            print(f"扫描目录 {directory_path} 时发生错误: {e}")
            
        return video_files
        
    def is_video_file(self, file_path: Path) -> bool:
        """
        判断是否为视频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为视频文件
        """
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS
        
    def get_video_info(self, file_path: Path) -> Dict[str, Any]:
        """
        获取视频文件信息
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            视频文件信息字典
        """
        try:
            # 获取基本文件信息
            stat = file_path.stat()
            file_info = {
                'path': str(file_path),
                'name': file_path.name,
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'extension': file_path.suffix.lower()
            }
            
            # 获取视频元数据
            video_metadata = self.get_video_metadata(file_path)
            file_info.update(video_metadata)
            
            return file_info
            
        except Exception as e:
            print(f"获取文件信息失败 {file_path}: {e}")
            return None
            
    def get_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        获取视频元数据
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            视频元数据字典
        """
        metadata = {
            'width': 0,
            'height': 0,
            'duration': 0,
            'fps': 0,
            'frame_count': 0
        }
        
        try:
            # 使用OpenCV获取视频信息
            cap = cv2.VideoCapture(str(file_path))
            
            if cap.isOpened():
                # 获取视频属性
                metadata['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                metadata['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                metadata['fps'] = cap.get(cv2.CAP_PROP_FPS)
                metadata['frame_count'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                # 计算时长
                if metadata['fps'] > 0:
                    metadata['duration'] = metadata['frame_count'] / metadata['fps']
                    
                cap.release()
                
        except Exception as e:
            print(f"获取视频元数据失败 {file_path}: {e}")
            
        return metadata
        
    def scan_multiple_directories(self, directory_paths: List[str]) -> List[Dict[str, Any]]:
        """
        扫描多个目录
        
        Args:
            directory_paths: 目录路径列表
            
        Returns:
            所有视频文件信息列表
        """
        all_video_files = []
        
        for directory_path in directory_paths:
            video_files = self.scan_directory(directory_path)
            all_video_files.extend(video_files)
            
        return all_video_files
        
    def filter_by_size(self, video_files: List[Dict[str, Any]], 
                      min_size: int = 0, max_size: int = None) -> List[Dict[str, Any]]:
        """
        按文件大小过滤
        
        Args:
            video_files: 视频文件列表
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            
        Returns:
            过滤后的视频文件列表
        """
        filtered_files = []
        
        for file_info in video_files:
            file_size = file_info.get('size', 0)
            
            if file_size < min_size:
                continue
                
            if max_size is not None and file_size > max_size:
                continue
                
            filtered_files.append(file_info)
            
        return filtered_files
        
    def filter_by_duration(self, video_files: List[Dict[str, Any]], 
                          min_duration: float = 0, max_duration: float = None) -> List[Dict[str, Any]]:
        """
        按视频时长过滤
        
        Args:
            video_files: 视频文件列表
            min_duration: 最小时长（秒）
            max_duration: 最大时长（秒）
            
        Returns:
            过滤后的视频文件列表
        """
        filtered_files = []
        
        for file_info in video_files:
            duration = file_info.get('duration', 0)
            
            if duration < min_duration:
                continue
                
            if max_duration is not None and duration > max_duration:
                continue
                
            filtered_files.append(file_info)
            
        return filtered_files