#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片重复检测器
Image Duplicate Detector
"""

import os
from typing import List, Dict, Any, Optional, Callable, Tuple
from collections import defaultdict
import imagehash
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

class ImageDuplicateDetector:
    """图片重复检测器"""
    
    def __init__(self, similarity_threshold: float = 80.0, max_workers: int = 4):
        """
        初始化图片重复检测器
        
        Args:
            similarity_threshold: 相似度阈值（百分比）
            max_workers: 最大工作线程数
        """
        self.similarity_threshold = similarity_threshold
        self.max_workers = max_workers
        self._lock = threading.Lock()
        self._feature_cache = {}  # 特征缓存，提高重复检测效率
        
        # 将相似度阈值转换为哈希差异阈值
        # 80%的相似度大约对应64位哈希中13个或更少的不同位
        self.hash_diff_threshold = self._calculate_hash_diff_threshold(similarity_threshold)
        
    def _calculate_hash_diff_threshold(self, similarity_percent: float) -> int:
        """
        将相似度百分比转换为哈希差异阈值
        
        Args:
            similarity_percent: 相似度百分比（0-100）
            
        Returns:
            哈希差异阈值
        """
        # 64位哈希的情况下
        max_diff = 64
        min_diff = 0
        
        # 线性映射：0%相似度对应64个不同位，100%相似度对应0个不同位
        hash_diff = int(max_diff * (1 - similarity_percent / 100))
        
        # 确保结果在合理范围内
        return max(min_diff, min(max_diff, hash_diff))
    
    def find_duplicates(self, image_files: List[Dict[str, Any]], 
                       progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        查找重复图片
        
        Args:
            image_files: 图片文件列表
            progress_callback: 进度回调函数
            
        Returns:
            重复图片组列表
        """
        if not image_files:
            return []
            
        # 第一步：元数据预筛选（基于文件大小、尺寸等）
        if progress_callback:
            progress_callback(40, "正在进行元数据预筛选...")
            
        candidate_groups = self.metadata_prescreening(image_files)
        
        # 第二步：并行提取特征和比较
        if progress_callback:
            progress_callback(60, "正在提取图片特征...")
            
        duplicate_groups = []
        processed_files = set()
        
        # 收集所有需要处理的文件
        files_to_process = []
        for candidate_group in candidate_groups:
            if len(candidate_group) >= 2:
                for file_info in candidate_group:
                    if file_info['path'] not in processed_files:
                        files_to_process.append((file_info, candidate_group))
        
        if not files_to_process:
            if progress_callback:
                progress_callback(100, "未找到重复图片")
            return duplicate_groups
        
        # 并行提取特征
        features_by_group = self._parallel_extract_features(files_to_process, progress_callback)
        
        # 比较特征找出重复组
        if progress_callback:
            progress_callback(90, "正在比较图片特征...")
            
        for candidate_group, features in features_by_group.items():
            if len(features) > 1:
                similar_groups = self.find_similar_images(features)
                duplicate_groups.extend(similar_groups)
                
                # 标记已处理的文件
                for group in similar_groups:
                    for file_info in group:
                        processed_files.add(file_info['path'])
        
        if progress_callback:
            progress_callback(100, f"检测完成，找到 {len(duplicate_groups)} 组重复文件")
            
        return duplicate_groups
        
    def metadata_prescreening(self, image_files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        根据元数据对图片进行预筛选
        
        Args:
            image_files: 图片文件列表
            
        Returns:
            预筛选后的候选组列表
        """
        # 使用文件大小和尺寸信息进行预筛选
        metadata_groups = defaultdict(list)
        
        for file_info in image_files:
            # 创建元数据键：文件大小（相差不超过5%）和尺寸
            size_key = file_info['size'] // 1024  # 按KB分组
            
            # 尺寸信息可能不存在，使用默认值
            width = file_info.get('width', 0)
            height = file_info.get('height', 0)
            
            # 尺寸相近的图片（相差不超过10%）
            width_key = width // 100
            height_key = height // 100
            
            # 组合键
            metadata_key = (size_key, width_key, height_key)
            metadata_groups[metadata_key].append(file_info)
        
        # 只保留可能包含重复文件的组（至少有2个文件）
        return [group for group in metadata_groups.values() if len(group) >= 2]
        
    def _parallel_extract_features(self, files_to_process: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]], 
                                 progress_callback: Optional[Callable] = None) -> Dict[int, List[Tuple[Dict[str, Any], str]]]:
        """
        并行提取图片特征
        
        Args:
            files_to_process: 需要处理的文件列表
            progress_callback: 进度回调函数
            
        Returns:
            按候选组组织的特征列表
        """
        features_by_group = defaultdict(list)
        processed_count = 0
        total_count = len(files_to_process)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self._extract_image_hash, file_info): (file_info, group) 
                for file_info, group in files_to_process
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_info, group = future_to_file[future]
                try:
                    image_hash = future.result()
                    if image_hash:
                        # 使用组的ID作为键
                        group_id = id(group)
                        features_by_group[group_id].append((file_info, image_hash))
                    
                    processed_count += 1
                    if progress_callback:
                        progress = 60 + int((processed_count / total_count) * 30)  # 特征提取占30%进度
                        progress_callback(progress, f"已提取 {processed_count}/{total_count} 个图片特征")
                        
                except Exception as e:
                    print(f"提取文件特征 {file_info['path']} 时发生错误: {e}")
        
        return features_by_group
        
    def _extract_image_hash(self, file_info: Dict[str, Any]) -> Optional[str]:
        """
        提取图片的感知哈希
        
        Args:
            file_info: 图片文件信息
            
        Returns:
            图片哈希字符串，如果无法处理则返回None
        """
        file_path = file_info['path']
        
        # 检查缓存
        if file_path in self._feature_cache:
            return self._feature_cache[file_path]
        
        try:
            # 打开图片并计算感知哈希
            with Image.open(file_path) as img:
                # 调整图片大小以提高性能
                img = img.resize((256, 256), Image.LANCZOS)
                
                # 计算多种哈希以提高准确性
                ahash = imagehash.average_hash(img)
                phash = imagehash.phash(img)
                
                # 组合哈希值
                combined_hash = f"{ahash}{phash}"
                
                # 缓存结果
                with self._lock:
                    self._feature_cache[file_path] = combined_hash
                
                return combined_hash
                
        except Exception as e:
            print(f"计算图片哈希 {file_path} 时发生错误: {e}")
            return None
        
    def find_similar_images(self, features: List[Tuple[Dict[str, Any], str]]) -> List[List[Dict[str, Any]]]:
        """
        查找相似图片
        
        Args:
            features: 包含图片信息和哈希的列表
            
        Returns:
            相似图片组列表
        """
        if not features or len(features) < 2:
            return []
            
        similar_groups = []
        processed_indices = set()
        
        # 比较所有图片对
        for i in range(len(features)):
            if i in processed_indices:
                continue
                
            current_file, current_hash = features[i]
            current_group = [current_file]
            processed_indices.add(i)
            
            # 将当前哈希转换为imagehash对象
            current_ahash = imagehash.hex_to_hash(current_hash[:16])  # 前16个字符是平均哈希
            current_phash = imagehash.hex_to_hash(current_hash[16:])  # 后16个字符是感知哈希
            
            for j in range(i + 1, len(features)):
                if j in processed_indices:
                    continue
                    
                compare_file, compare_hash = features[j]
                
                # 将比较哈希转换为imagehash对象
                compare_ahash = imagehash.hex_to_hash(compare_hash[:16])
                compare_phash = imagehash.hex_to_hash(compare_hash[16:])
                
                # 计算哈希差异
                ahash_diff = current_ahash - compare_ahash
                phash_diff = current_phash - compare_phash
                
                # 取两种哈希的平均差异
                avg_diff = (ahash_diff + phash_diff) / 2
                
                # 如果差异小于阈值，则认为是相似图片
                if avg_diff <= self.hash_diff_threshold:
                    current_group.append(compare_file)
                    processed_indices.add(j)
            
            # 如果组中有多个文件，则添加到结果中
            if len(current_group) >= 2:
                similar_groups.append(current_group)
        
        return similar_groups
        
    def clear_cache(self):
        """
        清空特征缓存
        """
        with self._lock:
            self._feature_cache.clear()