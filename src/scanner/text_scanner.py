#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本文件扫描器
Text File Scanner
"""

import os
import hashlib
import chardet
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

class TextScanner:
    """文本文件扫描器"""
    
    # 支持的文本文件扩展名
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.html', '.htm', '.css', '.xml', '.json',
        '.csv', '.log', '.conf', '.cfg', '.ini', '.yml', '.yaml', '.sql',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go',
        '.rs', '.swift', '.kt', '.scala', '.pl', '.sh', '.bat', '.ps1',
        '.tex', '.rtf', '.rst', '.wiki', '.adoc', '.asciidoc'
    }
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024):  # 50MB
        """
        初始化文本扫描器
        
        Args:
            max_file_size: 最大文件大小限制（字节）
        """
        self.max_file_size = max_file_size
        
    def scan_directory(self, directory_path: str, 
                      progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        扫描目录中的文本文件
        
        Args:
            directory_path: 目录路径
            progress_callback: 进度回调函数
            
        Returns:
            文本文件信息列表
        """
        text_files = []
        
        if not os.path.exists(directory_path):
            return text_files
        
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
                    if self._is_text_file(file):
                        total_files += 1
            
        # 遍历目录
        for root, dirs, files in os.walk(directory_path):
            # 跳过隐藏目录和常见的非文档目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and 
                      d.lower() not in {'__pycache__', 'node_modules', '.git', '.svn', 
                                       'build', 'dist', 'target', 'bin', 'obj'}]
            
            for file in files:
                if self._is_text_file(file):
                    file_path = os.path.join(root, file)
                    file_info = self._get_file_info(file_path)
                    
                    if file_info:
                        text_files.append(file_info)
                    
                    processed_files += 1
                    if progress_callback and total_files > 0:
                        progress_percent = min(90, 10 + int((processed_files / total_files) * 80))
                        progress_callback(progress_percent, f"已扫描: {processed_files}/{total_files} - {os.path.basename(file)}")
        
        if progress_callback:
            progress_callback(95, f"扫描完成，找到 {len(text_files)} 个文本文件")
        
        return text_files
    
    def _is_text_file(self, filename: str) -> bool:
        """
        判断是否为支持的文本文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否为文本文件
        """
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.SUPPORTED_EXTENSIONS
    
    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息（超级优化版本）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典，如果文件无法访问则返回None
        """
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            
            # 检查文件大小限制
            if file_size > self.max_file_size:
                return None
            
            # 跳过空文件和过小文件
            if file_size < 10:
                return None
            
            # 延迟编码检测和哈希计算 - 只在需要时进行
            return {
                'path': file_path,
                'name': os.path.basename(file_path),
                'size': file_size,
                'mtime': stat.st_mtime,
                'extension': Path(file_path).suffix.lower(),
                # 延迟计算的字段
                'encoding': None,  # 将在需要时计算
                'line_count': None,  # 将在需要时计算
                'char_count': None,  # 将在需要时计算
                'content_hash': None  # 将在需要时计算
            }
            
        except (OSError, IOError) as e:
            print(f"无法访问文件 {file_path}: {e}")
            return None
    
    def ensure_file_details(self, file_info: Dict[str, Any]) -> bool:
        """
        确保文件详细信息已加载（延迟加载）
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            是否成功加载详细信息
        """
        try:
            file_path = file_info['path']
            
            # 如果已经有详细信息，直接返回
            if file_info.get('content_hash') is not None:
                return True
            
            # 检测编码
            if file_info.get('encoding') is None:
                encoding = self._detect_encoding_fast(file_path)
                if not encoding:
                    return False
                file_info['encoding'] = encoding
            
            # 计算哈希
            if file_info.get('content_hash') is None:
                content_hash = self._calculate_file_hash(file_path, file_info['encoding'])
                if content_hash is None:
                    return False
                file_info['content_hash'] = content_hash
            
            # 获取统计信息
            if file_info.get('line_count') is None:
                line_count, char_count = self._get_file_stats_fast(file_path, file_info['encoding'])
                file_info['line_count'] = line_count
                file_info['char_count'] = char_count
            
            return True
            
        except Exception as e:
            print(f"加载文件详细信息失败 {file_info.get('path', 'unknown')}: {e}")
            return False
    
    def _detect_encoding_fast(self, file_path: str) -> Optional[str]:
        """
        快速检测文件编码（优化版本）
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的编码，如果检测失败返回None
        """
        try:
            # 只读取文件前1KB来检测编码，减少I/O
            with open(file_path, 'rb') as f:
                raw_data = f.read(1024)  # 只读取前1KB
                
            if not raw_data:
                return 'utf-8'  # 空文件默认UTF-8
            
            # 首先尝试常见编码，避免使用chardet
            for test_encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    raw_data.decode(test_encoding)
                    return test_encoding
                except UnicodeDecodeError:
                    continue
            
            # 如果常见编码都失败，才使用chardet
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            if confidence < 0.5:  # 降低阈值，提高速度
                return 'utf-8'  # 默认编码
                        
            return encoding
            
        except Exception as e:
            print(f"编码检测失败 {file_path}: {e}")
            return 'utf-8'  # 失败时返回默认编码而非None
    
    def _get_file_stats_fast(self, file_path: str, encoding: str) -> tuple[int, int]:
        """
        快速获取文件统计信息（不读取完整内容）
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            (行数, 字符数) 元组
        """
        try:
            line_count = 0
            char_count = 0
            
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                # 分块读取避免内存问题，每次读取64KB
                chunk_size = 65536
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    char_count += len(chunk)
                    line_count += chunk.count('\n')
            
            # 如果文件不以换行符结尾，行数+1
            if char_count > 0:
                line_count += 1
                
            return line_count, char_count
            
        except Exception as e:
            print(f"获取文件统计信息失败 {file_path}: {e}")
            return 0, 0
    
    def _calculate_file_hash(self, file_path: str, encoding: str) -> Optional[str]:
        """
        计算文件内容哈希（不读取完整内容到内存）
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件内容的MD5哈希值，如果计算失败返回None
        """
        try:
            hash_md5 = hashlib.md5()
            
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                # 分块读取并计算哈希，避免大文件内存问题
                chunk_size = 65536
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_md5.update(chunk.encode('utf-8'))
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            print(f"计算文件哈希失败 {file_path}: {e}")
            return None
    
    
    def get_supported_extensions(self) -> set:
        """
        获取支持的文件扩展名
        
        Returns:
            支持的扩展名集合
        """
        return self.SUPPORTED_EXTENSIONS.copy()
    
    def add_extension(self, extension: str):
        """
        添加支持的文件扩展名
        
        Args:
            extension: 文件扩展名（包含点号，如'.txt'）
        """
        if extension.startswith('.'):
            self.SUPPORTED_EXTENSIONS.add(extension.lower())
    
    def remove_extension(self, extension: str):
        """
        移除支持的文件扩展名
        
        Args:
            extension: 文件扩展名（包含点号，如'.txt'）
        """
        self.SUPPORTED_EXTENSIONS.discard(extension.lower())