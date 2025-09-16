#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本重复检测器
Text Duplicate Detector
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Callable, Set
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import unicodedata
import multiprocessing

class TextDuplicateDetector:
    """文本重复检测器（高性能优化版本）"""
    
    def __init__(self, similarity_threshold: float = 80.0, max_workers: int = None):
        """
        初始化文本重复检测器
        
        Args:
            similarity_threshold: 相似度阈值（百分比）
            max_workers: 最大工作线程数（None表示自动检测）
        """
        self.similarity_threshold = similarity_threshold
        
        # 自动检测最优线程数
        if max_workers is None:
            cpu_count = multiprocessing.cpu_count() or 4
            self.max_workers = min(cpu_count * 3, 16)  # 增加线程数
        else:
            self.max_workers = max_workers
            
        self._lock = threading.Lock()
        
        # 超级性能配置
        self.config = {
            'batch_size': 50,  # 减小批处理大小，提高响应速度
            'max_content_size': 20000,  # 减少内容读取大小
            'quick_check_threshold': 0.5,  # 提高快速检查阈值
            'sample_positions': 3,  # 减少采样位置
            'chunk_size': 300,  # 减小文本块大小
            'max_comparisons': 10000,  # 最大比较次数限制
        }
        
        # 缓存机制
        self._hash_cache = {}
        self._feature_cache = {}
        
    def find_duplicates(self, text_files: List[Dict[str, Any]], 
                       progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        查找重复文本文件
        
        Args:
            text_files: 文本文件列表
            progress_callback: 进度回调函数
            
        Returns:
            重复文本组列表
        """
        if not text_files:
            return []
        
        import time
        start_time = time.time()
        
        # 第一步：精确重复检测（基于MD5）
        if progress_callback:
            progress_callback(10, f"正在检测完全相同的文件... ({len(text_files)} 个文件)")
        
        exact_duplicates = self.find_exact_duplicates(text_files)
        processed_paths = set()
        
        # 标记已处理的文件
        for group in exact_duplicates:
            for file_info in group:
                processed_paths.add(file_info['path'])
        
        if progress_callback:
            elapsed = time.time() - start_time
            progress_callback(30, f"精确匹配完成，找到 {len(exact_duplicates)} 组，用时 {elapsed:.1f}s")
        
        # 第二步：相似度检测
        remaining_files = [f for f in text_files if f['path'] not in processed_paths]
        
        if len(remaining_files) < 2:
            if progress_callback:
                progress_callback(100, f"检测完成，找到 {len(exact_duplicates)} 组重复文件")
            return exact_duplicates
        
        if progress_callback:
            progress_callback(40, f"开始相似度分析... ({len(remaining_files)} 个待分析文件)")
        
        try:
            similar_duplicates = self.find_similar_texts(remaining_files, progress_callback)
        except Exception as e:
            print(f"相似度检测出错: {e}")
            similar_duplicates = []
        
        # 合并结果
        all_duplicates = exact_duplicates + similar_duplicates
        
        if progress_callback:
            total_elapsed = time.time() - start_time
            progress_callback(100, f"检测完成！找到 {len(all_duplicates)} 组重复文件，总用时 {total_elapsed:.1f}s")
        
        return all_duplicates
    
    def find_exact_duplicates(self, text_files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        查找完全相同的文本文件（基于MD5哈希）- 延迟计算版本
        
        Args:
            text_files: 文本文件列表
            
        Returns:
            完全重复的文件组
        """
        # 避免循环导入，直接实现延迟加载逻辑
        scanner = None
        
        hash_groups = defaultdict(list)
        
        for file_info in text_files:
            # 延迟加载文件详细信息
            if not self._ensure_file_details(file_info):
                continue
                
            content_hash = file_info.get('content_hash', '')
            if content_hash:
                hash_groups[content_hash].append(file_info)
        
        # 只返回包含多个文件的组
        exact_duplicates = []
        for group in hash_groups.values():
            if len(group) > 1:
                # 为每个文件添加100%相似度
                for file_info in group:
                    file_info['similarity'] = 100.0
                    file_info['match_type'] = 'exact'
                exact_duplicates.append(group)
        
        return exact_duplicates
    
    def find_similar_texts(self, text_files: List[Dict[str, Any]], 
                          progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        查找相似的文本文件（优化版本 - 流式处理）
        
        Args:
            text_files: 文本文件列表
            progress_callback: 进度回调函数
            
        Returns:
            相似文本组列表
        """
        if len(text_files) < 2:
            return []
        
        # 第一步：快速预过滤 - 基于文件大小和基本特征
        if progress_callback:
            progress_callback(50, "正在预过滤文件...")
        
        filtered_files = self._pre_filter_files(text_files)
        if len(filtered_files) < 2:
            return []
        
        # 第二步：分批处理相似度计算，避免内存爆炸
        if progress_callback:
            progress_callback(60, "正在计算文本相似度...")
        
        similar_groups = self._batch_similarity_check(filtered_files, progress_callback)
        
        return similar_groups
    
    def _pre_filter_files(self, text_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        超级预过滤 - 激进的文件筛选策略
        
        Args:
            text_files: 文本文件列表
            
        Returns:
            过滤后的文件列表
        """
        # 第一层：按文件大小精确分组（±5%范围内）
        size_groups = defaultdict(list)
        
        for file_info in text_files:
            size = file_info.get('size', 0)
            if size > 0:
                # 更精确的大小分组 - 按5%范围分组
                size_bucket = int(size / (size * 0.05 + 1))  # 5%容差分组
                size_groups[size_bucket].append(file_info)
        
        # 第二层：按文件扩展名分组
        filtered_by_size = []
        for files in size_groups.values():
            if len(files) > 1:
                # 按扩展名进一步分组
                ext_groups = defaultdict(list)
                for file_info in files:
                    ext = file_info.get('extension', '').lower()
                    ext_groups[ext].append(file_info)
                
                # 只保留同扩展名且有多个文件的组
                for ext_files in ext_groups.values():
                    if len(ext_files) > 1:
                        filtered_by_size.extend(ext_files)
        
        # 第三层：按修改时间快速筛选（相近时间的文件更可能重复）
        if len(filtered_by_size) > 100:  # 只对大数据集应用时间过滤
            time_filtered = []
            filtered_by_size.sort(key=lambda x: x.get('mtime', 0))
            
            for i, file_info in enumerate(filtered_by_size):
                # 检查前后5个文件的时间差
                has_nearby = False
                for j in range(max(0, i-5), min(len(filtered_by_size), i+6)):
                    if i != j:
                        time_diff = abs(file_info.get('mtime', 0) - filtered_by_size[j].get('mtime', 0))
                        if time_diff < 86400:  # 24小时内
                            has_nearby = True
                            break
                
                if has_nearby:
                    time_filtered.append(file_info)
            
            return time_filtered
        
        return filtered_by_size
    
    def _preprocess_text_lazy(self, file_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        懒加载预处理文本内容 - 只提取轻量级特征
        
        Args:
            file_info: 文件信息
            
        Returns:
            预处理后的文件信息
        """
        try:
            file_path = file_info.get('path', '')
            if not file_path:
                return None
            
            # 只提取轻量级特征，不读取完整内容
            lightweight_features = self._extract_lightweight_features(file_path, file_info.get('encoding', 'utf-8'))
            if not lightweight_features:
                return None
            
            # 复制原始信息并添加轻量级特征
            processed_info = file_info.copy()
            processed_info.update({
                'lightweight_features': lightweight_features
            })
            
            return processed_info
            
        except Exception as e:
            print(f"预处理文本失败 {file_info.get('path', 'unknown')}: {e}")
            return None
    
    def _read_file_content_for_analysis(self, file_path: str, encoding: str) -> Optional[str]:
        """
        读取文件内容用于相似度分析
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件内容，如果读取失败返回None
        """
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
                
            # 过滤掉过短的文件（少于10个字符）
            if len(content.strip()) < 10:
                return None
                
            return content
            
        except Exception as e:
            print(f"读取文件内容失败 {file_path}: {e}")
            return None
    
    def _normalize_text(self, text: str) -> str:
        """
        标准化文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本
        """
        # Unicode标准化
        text = unicodedata.normalize('NFKC', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除行首行尾空白
        lines = [line.strip() for line in text.splitlines()]
        text = '\n'.join(lines)
        
        # 转换为小写（用于相似度比较，但保留原始大小写用于显示）
        normalized = text.lower()
        
        return normalized
    
    def _extract_lightweight_features(self, file_path: str, encoding: str) -> Optional[Dict[str, Any]]:
        """
        提取轻量级文本特征 - 流式处理，不加载完整内容到内存
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            轻量级特征字典
        """
        try:
            features = {
                'word_count': 0,
                'line_count': 0,
                'char_count': 0,
                'first_lines_hash': '',
                'last_lines_hash': '',
                'word_set_sample': set(),
                'line_length_pattern': []
            }
            
            first_lines = []
            last_lines = []
            word_sample = set()
            line_lengths = []
            
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                # 流式读取，只保留关键信息
                chunk_size = 8192
                buffer = ""
                line_count = 0
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    features['char_count'] += len(chunk)
                    
                    # 处理完整的行
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line_count += 1
                        
                        # 收集前10行和后10行用于快速比较
                        if line_count <= 10:
                            first_lines.append(line.strip())
                        last_lines.append(line.strip())
                        if len(last_lines) > 10:
                            last_lines.pop(0)
                        
                        # 统计行长度模式
                        line_lengths.append(len(line))
                        if len(line_lengths) > 100:
                            line_lengths.pop(0)
                        
                        # 采样词汇（每10行采样一次）
                        if line_count % 10 == 0:
                            words = re.findall(r'\b\w+\b', line.lower())
                            word_sample.update(words[:5])  # 只取前5个词
                            features['word_count'] += len(words)
                        
                        # 限制内存使用
                        if len(word_sample) > 100:
                            break
                
                # 处理剩余的buffer
                if buffer.strip():
                    line_count += 1
                    last_lines.append(buffer.strip())
            
            # 生成特征哈希
            features.update({
                'line_count': line_count,
                'first_lines_hash': hashlib.md5('\n'.join(first_lines).encode('utf-8')).hexdigest()[:16],
                'last_lines_hash': hashlib.md5('\n'.join(last_lines).encode('utf-8')).hexdigest()[:16],
                'word_set_sample': word_sample,
                'avg_line_length': sum(line_lengths) / max(len(line_lengths), 1),
                'line_length_variance': self._calculate_variance(line_lengths)
            })
            
            return features
            
        except Exception as e:
            print(f"提取轻量级特征失败 {file_path}: {e}")
            return None
    
    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _smart_file_selection(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        智能文件选择 - 优先处理最可能重复的文件
        
        Args:
            files: 文件列表
            
        Returns:
            筛选后的文件列表
        """
        # 按文件大小分组，优先处理有多个相同大小文件的组
        size_groups = defaultdict(list)
        for file_info in files:
            size = file_info.get('size', 0)
            size_groups[size].append(file_info)
        
        # 优先级排序：相同大小的文件数量越多，优先级越高
        priority_files = []
        for size, file_list in sorted(size_groups.items(), key=lambda x: len(x[1]), reverse=True):
            if len(file_list) > 1:  # 只处理有多个文件的大小组
                priority_files.extend(file_list)
                if len(priority_files) >= 300:  # 限制处理文件数量
                    break
        
        # 如果优先文件不够，添加一些单独文件（按大小排序）
        if len(priority_files) < 200:
            single_files = []
            for size, file_list in size_groups.items():
                if len(file_list) == 1:
                    single_files.extend(file_list)
            
            # 按文件大小排序，优先处理大文件
            single_files.sort(key=lambda x: x.get('size', 0), reverse=True)
            priority_files.extend(single_files[:200-len(priority_files)])
        
        return priority_files
    
    def _ensure_file_details(self, file_info: Dict[str, Any]) -> bool:
        """
        确保文件详细信息已加载（本地实现）
        
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
                content_hash = self._calculate_file_hash_local(file_path, file_info['encoding'])
                if content_hash is None:
                    return False
                file_info['content_hash'] = content_hash
            
            return True
            
        except Exception as e:
            print(f"加载文件详细信息失败 {file_info.get('path', 'unknown')}: {e}")
            return False
    
    def _detect_encoding_fast(self, file_path: str) -> Optional[str]:
        """
        快速检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的编码
        """
        try:
            import chardet
            
            # 只读取文件前1KB来检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read(1024)
                
            if not raw_data:
                return 'utf-8'
            
            # 首先尝试常见编码
            for test_encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    raw_data.decode(test_encoding)
                    return test_encoding
                except UnicodeDecodeError:
                    continue
            
            # 使用chardet检测
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            if confidence < 0.5:
                return 'utf-8'
                        
            return encoding
            
        except Exception as e:
            print(f"编码检测失败 {file_path}: {e}")
            return 'utf-8'
    
    def _calculate_file_hash_local(self, file_path: str, encoding: str) -> Optional[str]:
        """
        计算文件内容哈希（带缓存）
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件内容的MD5哈希值
        """
        try:
            # 检查缓存
            import os
            stat = os.stat(file_path)
            cache_key = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            
            if cache_key in self._hash_cache:
                return self._hash_cache[cache_key]
            
            hash_md5 = hashlib.md5()
            
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                # 对大文件只读取前面部分计算哈希
                max_read = min(stat.st_size, 100000)  # 最多读取100KB
                content = f.read(max_read)
                hash_md5.update(content.encode('utf-8'))
            
            result = hash_md5.hexdigest()
            
            # 缓存结果（限制缓存大小）
            if len(self._hash_cache) < 1000:
                self._hash_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"计算文件哈希失败 {file_path}: {e}")
            return None
    
    def _batch_similarity_check(self, filtered_files: List[Dict[str, Any]], 
                               progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        批处理相似度计算 - 优化内存使用和计算效率
        
        Args:
            filtered_files: 过滤后的文件列表
            progress_callback: 进度回调函数
            
        Returns:
            相似文本组列表
        """
        similar_groups = []
        processed_paths = set()
        
        # 智能批处理 - 根据文件数量动态调整
        total_files = len(filtered_files)
        
        # 对于大数据集，进一步限制处理范围
        if total_files > 500:
            # 只处理最有可能重复的文件
            filtered_files = self._smart_file_selection(filtered_files)
            total_files = len(filtered_files)
            if progress_callback:
                progress_callback(65, f"智能筛选后剩余 {total_files} 个高概率重复文件")
        
        batch_size = self.config['batch_size']
        total_batches = (total_files - 1) // batch_size + 1
        total_comparisons = 0
        max_comparisons = self.config['max_comparisons']
        
        for batch_idx, batch_start in enumerate(range(0, total_files, batch_size)):
            # 检查是否超过最大比较次数
            if total_comparisons > max_comparisons:
                if progress_callback:
                    progress_callback(95, f"达到最大比较次数限制，停止处理")
                break
                
            batch_end = min(batch_start + batch_size, total_files)
            batch_files = filtered_files[batch_start:batch_end]
            
            if progress_callback:
                progress = 60 + int((batch_idx / total_batches) * 35)
                progress_callback(progress, f"批次 {batch_idx + 1}/{total_batches}: 预筛选 {len(batch_files)} 个文件")
            
            # 第一阶段：快速预筛选
            try:
                candidate_pairs = self._fast_pre_screening(batch_files)
                total_comparisons += len(candidate_pairs)
                
                if progress_callback and candidate_pairs:
                    progress_callback(progress + 2, f"批次 {batch_idx + 1}: 找到 {len(candidate_pairs)} 个候选对")
                
                # 第二阶段：详细相似度计算（只对候选对进行）
                if candidate_pairs:
                    batch_groups = self._detailed_similarity_check(candidate_pairs, progress_callback)
                    similar_groups.extend(batch_groups)
                    
            except Exception as e:
                print(f"批次 {batch_idx + 1} 处理失败: {e}")
                continue
        
        return similar_groups
    
    def _fast_pre_screening(self, files: List[Dict[str, Any]]) -> List[tuple]:
        """
        快速预筛选 - 基于轻量级特征快速排除明显不相似的文件对
        
        Args:
            files: 文件列表
            
        Returns:
            候选文件对列表
        """
        candidate_pairs = []
        
        # 为每个文件提取轻量级特征
        files_with_features = []
        for file_info in files:
            features = self._preprocess_text_lazy(file_info)
            if features:
                files_with_features.append(features)
        
        # 快速比较轻量级特征
        for i in range(len(files_with_features)):
            for j in range(i + 1, len(files_with_features)):
                file1, file2 = files_with_features[i], files_with_features[j]
                
                # 快速相似度检查
                if self._quick_similarity_check(file1, file2):
                    candidate_pairs.append((file1, file2))
        
        return candidate_pairs
    
    def _quick_similarity_check(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> bool:
        """
        超级快速相似度检查 - 激进的跳过策略
        
        Args:
            file1: 文件1信息
            file2: 文件2信息
            
        Returns:
            是否可能相似
        """
        # 第一层：基本信息快速排除
        size1 = file1.get('size', 0)
        size2 = file2.get('size', 0)
        
        # 文件大小差异检查（差异超过20%则跳过）
        if size1 > 0 and size2 > 0:
            size_ratio = min(size1, size2) / max(size1, size2)
            if size_ratio < 0.8:  # 提高到80%相似度
                return False
        
        # 文件名相似度快速检查
        name1 = file1.get('name', '').lower()
        name2 = file2.get('name', '').lower()
        
        # 如果文件名完全不同且大小差异较大，直接跳过
        if name1 != name2:
            name_similarity = self._quick_name_similarity(name1, name2)
            if name_similarity < 0.3 and size_ratio < 0.9:
                return False
        
        # 第二层：轻量级特征检查
        features1 = file1.get('lightweight_features', {})
        features2 = file2.get('lightweight_features', {})
        
        if not features1 or not features2:
            # 如果没有特征，只有在文件大小非常接近时才继续
            return size_ratio > 0.95
        
        # 行数差异检查（更严格）
        lines1 = features1.get('line_count', 0)
        lines2 = features2.get('line_count', 0)
        if lines1 > 0 and lines2 > 0:
            line_ratio = min(lines1, lines2) / max(lines1, lines2)
            if line_ratio < 0.7:  # 提高到70%
                return False
        
        # 首尾行哈希检查（快速匹配）
        if (features1.get('first_lines_hash') == features2.get('first_lines_hash') or
            features1.get('last_lines_hash') == features2.get('last_lines_hash')):
            return True
        
        # 词汇重叠检查（更严格）
        words1 = features1.get('word_set_sample', set())
        words2 = features2.get('word_set_sample', set())
        if words1 and words2:
            overlap = len(words1 & words2) / len(words1 | words2)
            if overlap > 0.5:  # 提高到50%
                return True
        
        # 平均行长度检查
        avg_len1 = features1.get('avg_line_length', 0)
        avg_len2 = features2.get('avg_line_length', 0)
        if avg_len1 > 0 and avg_len2 > 0:
            len_ratio = min(avg_len1, avg_len2) / max(avg_len1, avg_len2)
            if len_ratio < 0.5:
                return False
        
        return False
    
    def _quick_name_similarity(self, name1: str, name2: str) -> float:
        """
        快速文件名相似度计算
        
        Args:
            name1: 文件名1
            name2: 文件名2
            
        Returns:
            相似度（0-1）
        """
        if not name1 or not name2:
            return 0.0
        
        # 移除扩展名
        name1 = name1.rsplit('.', 1)[0] if '.' in name1 else name1
        name2 = name2.rsplit('.', 1)[0] if '.' in name2 else name2
        
        # 简单的字符重叠计算
        set1 = set(name1.lower())
        set2 = set(name2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        return len(set1 & set2) / len(set1 | set2)
    
    def _detailed_similarity_check(self, candidate_pairs: List[tuple], 
                                 progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        详细相似度计算 - 只对候选对进行完整的相似度分析
        
        Args:
            candidate_pairs: 候选文件对列表
            progress_callback: 进度回调函数
            
        Returns:
            相似文件组列表
        """
        similarities = {}
        total_pairs = len(candidate_pairs)
        
        # 并行计算详细相似度
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_pair = {
                executor.submit(self._calculate_detailed_similarity, pair[0], pair[1]): pair
                for pair in candidate_pairs
            }
            
            completed = 0
            for future in as_completed(future_to_pair):
                pair = future_to_pair[future]
                try:
                    similarity = future.result()
                    if similarity >= self.similarity_threshold:
                        similarities[pair] = similarity
                    
                    completed += 1
                    if progress_callback and completed % 50 == 0:
                        progress_callback(85, f"详细分析: {completed}/{total_pairs}")
                        
                except Exception as e:
                    print(f"详细相似度计算失败: {e}")
        
        # 构建相似度图
        similarity_graph = defaultdict(list)
        for (file1, file2), similarity in similarities.items():
            similarity_graph[file1['path']].append((file2, similarity))
            similarity_graph[file2['path']].append((file1, similarity))
        
        # 找出相似文件组
        similar_groups = []
        processed_paths = set()
        
        for pair in candidate_pairs:
            file1, file2 = pair
            if file1['path'] in processed_paths:
                continue
            
            group = self._find_similar_group(file1, similarity_graph, processed_paths)
            if len(group) > 1:
                similar_groups.append(group)
        
        return similar_groups
    
    def _find_similar_group(self, start_file: Dict[str, Any], 
                           similarity_graph: Dict[str, List], 
                           processed_paths: Set[str]) -> List[Dict[str, Any]]:
        """
        使用DFS找出相似文件组
        
        Args:
            start_file: 起始文件
            similarity_graph: 相似度图
            processed_paths: 已处理的文件路径集合
            
        Returns:
            相似文件组
        """
        group = []
        stack = [start_file]
        visited = set()
        
        while stack:
            current_file = stack.pop()
            current_path = current_file['path']
            
            if current_path in visited or current_path in processed_paths:
                continue
            
            visited.add(current_path)
            processed_paths.add(current_path)
            group.append(current_file)
            
            # 添加相似文件到栈中
            for similar_file, similarity in similarity_graph.get(current_path, []):
                if similar_file['path'] not in visited:
                    # 为文件添加相似度信息
                    similar_file_copy = similar_file.copy()
                    similar_file_copy['similarity'] = similarity
                    similar_file_copy['match_type'] = 'similar'
                    stack.append(similar_file_copy)
        
        # 为起始文件也添加相似度信息
        if group:
            group[0]['similarity'] = 100.0
            group[0]['match_type'] = 'similar'
        
        return group
    
    def _calculate_detailed_similarity(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> float:
        """
        计算详细的文本相似度 - 按需加载内容
        
        Args:
            file1: 文件1信息
            file2: 文件2信息
            
        Returns:
            相似度百分比
        """
        try:
            # 如果内容哈希相同，则完全相同
            hash1 = file1.get('content_hash')
            hash2 = file2.get('content_hash')
            if hash1 and hash2 and hash1 == hash2:
                return 100.0
            
            # 按需读取和处理文件内容
            content1 = self._read_and_normalize_content(file1)
            content2 = self._read_and_normalize_content(file2)
            
            if not content1 or not content2:
                return 0.0
            
            # 使用更高效的相似度算法
            similarity = self._fast_text_similarity(content1, content2)
            return similarity
            
        except Exception as e:
            print(f"计算详细相似度失败: {e}")
            return 0.0
    
    def _read_and_normalize_content(self, file_info: Dict[str, Any]) -> Optional[str]:
        """
        按需读取并标准化文件内容
        
        Args:
            file_info: 文件信息
            
        Returns:
            标准化后的内容
        """
        try:
            file_path = file_info.get('path', '')
            encoding = file_info.get('encoding', 'utf-8')
            
            # 对大文件只读取前面部分进行比较
            max_chars = 50000  # 最多读取50K字符
            
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read(max_chars)
            
            if len(content) < 10:
                return None
            
            # 简化的标准化处理
            content = re.sub(r'\s+', ' ', content.lower().strip())
            return content
            
        except Exception as e:
            print(f"读取文件内容失败 {file_info.get('path', 'unknown')}: {e}")
            return None
    
    def _fast_text_similarity(self, text1: str, text2: str) -> float:
        """
        快速文本相似度计算 - 使用优化的算法
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度百分比
        """
        try:
            # 1. 长度相似度检查
            len1, len2 = len(text1), len(text2)
            if len1 == 0 or len2 == 0:
                return 0.0
            
            length_ratio = min(len1, len2) / max(len1, len2)
            if length_ratio < 0.3:
                return 0.0
            
            # 2. 使用滑动窗口进行快速比较
            if len1 > 1000 or len2 > 1000:
                # 对长文本使用采样比较
                similarity = self._sample_based_similarity(text1, text2)
            else:
                # 对短文本使用完整比较
                similarity = SequenceMatcher(None, text1, text2).ratio() * 100
            
            return max(0.0, min(100.0, similarity))
            
        except Exception as e:
            print(f"快速相似度计算失败: {e}")
            return 0.0
    
    def _sample_based_similarity(self, text1: str, text2: str) -> float:
        """
        基于采样的相似度计算 - 用于大文件
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度百分比
        """
        # 将文本分成多个段落进行比较
        chunk_size = 500
        similarities = []
        
        # 从开头、中间、结尾各取几段进行比较
        positions = [0, len(text1)//4, len(text1)//2, 3*len(text1)//4, max(0, len(text1)-chunk_size)]
        
        for pos in positions:
            if pos >= len(text1):
                continue
            
            chunk1 = text1[pos:pos+chunk_size]
            
            # 在text2中找最相似的段落
            best_similarity = 0.0
            for pos2 in range(0, len(text2), chunk_size//2):
                if pos2 >= len(text2):
                    break
                
                chunk2 = text2[pos2:pos2+chunk_size]
                similarity = SequenceMatcher(None, chunk1, chunk2).ratio()
                best_similarity = max(best_similarity, similarity)
            
            similarities.append(best_similarity)
        
        # 返回平均相似度
        if similarities:
            return sum(similarities) / len(similarities) * 100
        
        return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度
        """
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    def get_similarity_details(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> Dict[str, float]:
        """
        获取详细的相似度分析结果
        
        Args:
            file1: 文件1信息
            file2: 文件2信息
            
        Returns:
            详细相似度分析结果
        """
        content1 = file1.get('normalized_content', '')
        content2 = file2.get('normalized_content', '')
        features1 = file1.get('features', {})
        features2 = file2.get('features', {})
        
        details = {}
        
        # 序列相似度
        details['sequence_similarity'] = SequenceMatcher(None, content1, content2).ratio() * 100
        
        # 词汇相似度
        words1 = set(features1.get('word_freq', {}).keys())
        words2 = set(features2.get('word_freq', {}).keys())
        if words1 or words2:
            details['vocabulary_similarity'] = len(words1 & words2) / len(words1 | words2) * 100
        else:
            details['vocabulary_similarity'] = 0.0
        
        # 结构相似度
        struct_features1 = [
            features1.get('sentence_count', 0),
            features1.get('avg_sentence_length', 0),
            features1.get('word_count', 0) / max(features1.get('char_count', 1), 1)
        ]
        struct_features2 = [
            features2.get('sentence_count', 0),
            features2.get('avg_sentence_length', 0),
            features2.get('word_count', 0) / max(features2.get('char_count', 1), 1)
        ]
        details['structure_similarity'] = self._cosine_similarity(struct_features1, struct_features2) * 100
        
        return details