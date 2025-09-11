#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件处理器
File Processor
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import send2trash

class FileProcessor:
    """文件处理器"""
    
    def __init__(self, backup_folder: Optional[str] = None):
        """
        初始化文件处理器
        
        Args:
            backup_folder: 备份文件夹路径（可选）
        """
        self.backup_folder = backup_folder
        
    def move_to_trash(self, file_paths: List[str]) -> int:
        """
        将文件移动到回收站
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            成功处理的文件数量
        """
        success_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    send2trash.send2trash(file_path)
                    success_count += 1
                    print(f"已移动到回收站: {file_path}")
                else:
                    print(f"文件不存在: {file_path}")
            except Exception as e:
                print(f"移动文件到回收站失败 {file_path}: {e}")
                
        return success_count
        
    def move_to_backup(self, file_paths: List[str], backup_folder: Optional[str] = None) -> int:
        """
        将文件移动到备份文件夹
        
        Args:
            file_paths: 文件路径列表
            backup_folder: 备份文件夹路径
            
        Returns:
            成功处理的文件数量
        """
        target_folder = backup_folder or self.backup_folder
        
        if not target_folder:
            raise ValueError("未指定备份文件夹")
            
        # 确保备份文件夹存在
        backup_path = Path(target_folder)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    source_path = Path(file_path)
                    
                    # 生成目标路径，保持原始文件名
                    target_path = backup_path / source_path.name
                    
                    # 如果目标文件已存在，添加序号
                    counter = 1
                    original_target = target_path
                    while target_path.exists():
                        stem = original_target.stem
                        suffix = original_target.suffix
                        target_path = backup_path / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    # 移动文件
                    shutil.move(str(source_path), str(target_path))
                    success_count += 1
                    print(f"已移动到备份文件夹: {file_path} -> {target_path}")
                else:
                    print(f"文件不存在: {file_path}")
            except Exception as e:
                print(f"移动文件到备份文件夹失败 {file_path}: {e}")
                
        return success_count
        
    def delete_permanently(self, file_paths: List[str]) -> int:
        """
        永久删除文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            成功处理的文件数量
        """
        success_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    success_count += 1
                    print(f"已永久删除: {file_path}")
                else:
                    print(f"文件不存在: {file_path}")
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
                
        return success_count
        
    def copy_to_folder(self, file_paths: List[str], target_folder: str) -> int:
        """
        复制文件到指定文件夹
        
        Args:
            file_paths: 文件路径列表
            target_folder: 目标文件夹路径
            
        Returns:
            成功处理的文件数量
        """
        # 确保目标文件夹存在
        target_path = Path(target_folder)
        target_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    source_path = Path(file_path)
                    
                    # 生成目标路径
                    dest_path = target_path / source_path.name
                    
                    # 如果目标文件已存在，添加序号
                    counter = 1
                    original_dest = dest_path
                    while dest_path.exists():
                        stem = original_dest.stem
                        suffix = original_dest.suffix
                        dest_path = target_path / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    # 复制文件
                    shutil.copy2(str(source_path), str(dest_path))
                    success_count += 1
                    print(f"已复制: {file_path} -> {dest_path}")
                else:
                    print(f"文件不存在: {file_path}")
            except Exception as e:
                print(f"复制文件失败 {file_path}: {e}")
                
        return success_count
        
    def get_total_size(self, file_paths: List[str]) -> int:
        """
        计算文件总大小
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            总大小（字节）
        """
        total_size = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
            except Exception as e:
                print(f"获取文件大小失败 {file_path}: {e}")
                
        return total_size
        
    def format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            格式化的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
        
    def validate_files(self, file_paths: List[str]) -> tuple:
        """
        验证文件是否存在
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            (存在的文件列表, 不存在的文件列表)
        """
        existing_files = []
        missing_files = []
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
                
        return existing_files, missing_files