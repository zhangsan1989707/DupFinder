#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复视频检测器
Duplicate Video Detector
"""

import os
import cv2
import numpy as np
import imagehash
from PIL import Image
from typing import List, Dict, Any, Callable, Optional, Tuple
from collections import defaultdict
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pickle
import time

class DuplicateDetector:
    """重复视频检测器"""
    
    def __init__(self, similarity_threshold: float = 80.0, sample_frames: int = 5, max_workers: int = 4):
        """
        初始化检测器
        
        Args:
            similarity_threshold: 相似度阈值（百分比）
            sample_frames: 采样帧数（减少到5帧提高速度）
            max_workers: 最大工作线程数
        """
        self.similarity_threshold = similarity_threshold
        self.sample_frames = sample_frames
        self.max_workers = max_workers
        self._lock = threading.Lock()
        self._feature_cache = {}  # 特征缓存
        
    def find_duplicates(self, video_files: List[Dict[str, Any]], 
                       progress_callback: Optional[Callable] = None) -> List[List[Dict[str, Any]]]:
        """
        查找重复视频
        
        Args:
            video_files: 视频文件列表
            progress_callback: 进度回调函数
            
        Returns:
            重复视频组列表
        """
        if not video_files:
            return []
            
        # 第一步：元数据预筛选
        if progress_callback:
            progress_callback(40, "正在进行元数据预筛选...")
            
        candidate_groups = self.metadata_prescreening(video_files)
        
        # 第二步：并行提取特征和比较
        if progress_callback:
            progress_callback(60, "正在提取视频特征...")
            
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
            return duplicate_groups
        
        # 并行提取特征
        features_by_group = self._parallel_extract_features(files_to_process, progress_callback)
        
        # 比较特征找出重复组
        if progress_callback:
            progress_callback(90, "正在比较视频特征...")
            
        for candidate_group, features in features_by_group.items():
            if len(features) > 1:
                similar_groups = self.find_similar_videos(features)
                duplicate_groups.extend(similar_groups)
                
                # 标记已处理的文件
                for group in similar_groups:
                    for file_info in group:
                        processed_files.add(file_info['path'])
        
        if progress_callback:
            progress_callback(100, f"检测完成，找到 {len(duplicate_groups)} 组重复文件")
            
        return duplicate_groups
        
    def metadata_prescreening(self, video_files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        优化的元数据预筛选
        
        Args:
            video_files: 视频文件列表
            
        Returns:
            候选重复组列表
        """
        # 第一步：按文件大小快速分组（允许15%的误差，提高匹配率）
        size_groups = defaultdict(list)
        
        for file_info in video_files:
            size = file_info.get('size', 0)
            if size > 0:
                # 使用对数分组减少组数
                size_key = int(np.log10(size + 1) * 10)  # 按数量级分组
                size_groups[size_key].append(file_info)
            else:
                size_groups[-1].append(file_info)
        
        # 第二步：在每个大小组内按时长细分（允许10%误差）
        candidate_groups = []
        for size_group in size_groups.values():
            if len(size_group) < 2:
                # 单个文件的组直接跳过
                continue
                
            duration_groups = defaultdict(list)
            for file_info in size_group:
                duration = file_info.get('duration', 0)
                if duration > 0:
                    # 按时长区间分组，减少精度要求
                    duration_key = int(duration / 30)  # 每30秒一个区间
                    duration_groups[duration_key].append(file_info)
                else:
                    duration_groups[-1].append(file_info)
            
            # 只保留有多个文件的组
            for duration_group in duration_groups.values():
                if len(duration_group) >= 2:
                    candidate_groups.append(duration_group)
        
        return candidate_groups
        
    def _parallel_extract_features(self, files_to_process, progress_callback=None):
        """并行提取视频特征"""
        features_by_group = defaultdict(dict)
        processed_count = 0
        total_count = len(files_to_process)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有特征提取任务
            future_to_file = {
                executor.submit(self.extract_video_features_cached, file_info): (file_info, group)
                for file_info, group in files_to_process
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_info, candidate_group = future_to_file[future]
                try:
                    feature = future.result()
                    if feature is not None:
                        group_id = id(candidate_group)  # 使用组对象的ID作为键
                        with self._lock:
                            features_by_group[group_id][file_info['path']] = {
                                'feature': feature,
                                'file_info': file_info
                            }
                    
                    processed_count += 1
                    if progress_callback and processed_count % 5 == 0:  # 每5个文件更新一次
                        progress = 60 + int((processed_count / total_count) * 25)
                        progress_callback(progress, f"已处理 {processed_count}/{total_count} 个视频")
                        
                except Exception as e:
                    print(f"处理文件 {file_info['path']} 时发生错误: {e}")
        
        return dict(features_by_group)
        
    def extract_video_features_cached(self, file_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        带缓存的视频特征提取
        
        Args:
            file_info: 视频文件信息
            
        Returns:
            视频特征向量
        """
        file_path = file_info['path']
        file_mtime = file_info.get('mtime', 0)
        cache_key = f"{file_path}_{file_mtime}_{self.sample_frames}"
        
        # 检查缓存
        if cache_key in self._feature_cache:
            return self._feature_cache[cache_key]
        
        # 提取特征
        feature = self.extract_video_features_fast(file_info)
        
        # 缓存特征
        if feature is not None:
            self._feature_cache[cache_key] = feature
        
        return feature
    
    def extract_video_features_fast(self, file_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        快速提取视频特征（优化版本）
        
        Args:
            file_info: 视频文件信息
            
        Returns:
            视频特征向量
        """
        try:
            video_path = file_info['path']
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None
            
            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                cap.release()
                return None
            
            # 计算采样间隔，减少采样帧数提高速度
            if total_frames <= self.sample_frames:
                frame_indices = list(range(0, total_frames, max(1, total_frames // self.sample_frames)))
            else:
                # 均匀采样，但跳过开头和结尾的10%（通常是黑屏或片尾）
                start_frame = int(total_frames * 0.1)
                end_frame = int(total_frames * 0.9)
                frame_indices = np.linspace(start_frame, end_frame, self.sample_frames, dtype=int)
            
            # 提取关键帧的感知哈希
            frame_hashes = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # 缩小图像尺寸加快处理速度
                    height, width = frame.shape[:2]
                    if width > 320 or height > 240:
                        scale = min(320/width, 240/height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    # 转换为PIL图像
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # 计算感知哈希（使用更小的哈希尺寸）
                    phash = imagehash.phash(pil_image, hash_size=6)  # 从8减少到6
                    frame_hashes.append(np.array(phash.hash, dtype=np.uint8))
            
            cap.release()
            
            if frame_hashes:
                # 将所有帧哈希连接成特征向量
                feature_vector = np.concatenate(frame_hashes)
                return feature_vector
            else:
                return None
                
        except Exception as e:
            print(f"提取视频特征失败 {file_info['path']}: {e}")
            return None

    def extract_video_features(self, file_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        提取视频特征
        
        Args:
            file_info: 视频文件信息
            
        Returns:
            视频特征向量
        """
        try:
            video_path = file_info['path']
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None
                
            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if total_frames == 0:
                cap.release()
                return None
            
            # 计算采样间隔
            if total_frames <= self.sample_frames:
                frame_indices = list(range(total_frames))
            else:
                frame_indices = np.linspace(0, total_frames - 1, self.sample_frames, dtype=int)
            
            # 提取关键帧的感知哈希
            frame_hashes = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # 转换为PIL图像
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    
                    # 计算感知哈希
                    phash = imagehash.phash(pil_image, hash_size=8)
                    frame_hashes.append(np.array(phash.hash, dtype=np.uint8))
            
            cap.release()
            
            if frame_hashes:
                # 将所有帧哈希连接成特征向量
                feature_vector = np.concatenate(frame_hashes)
                return feature_vector
            else:
                return None
                
        except Exception as e:
            print(f"提取视频特征失败 {file_info['path']}: {e}")
            return None
            
    def find_similar_videos(self, features: Dict[str, Dict]) -> List[List[Dict[str, Any]]]:
        """
        查找相似视频
        
        Args:
            features: 特征字典
            
        Returns:
            相似视频组列表
        """
        similar_groups = []
        processed_paths = set()
        
        paths = list(features.keys())
        
        for i, path1 in enumerate(paths):
            if path1 in processed_paths:
                continue
                
            current_group = [features[path1]['file_info']]
            processed_paths.add(path1)
            
            for j, path2 in enumerate(paths[i+1:], i+1):
                if path2 in processed_paths:
                    continue
                    
                # 计算特征相似度
                similarity = self.calculate_similarity(
                    features[path1]['feature'], 
                    features[path2]['feature']
                )
                
                if similarity >= self.similarity_threshold:
                    # 添加相似度信息
                    file_info = features[path2]['file_info'].copy()
                    file_info['similarity'] = similarity
                    current_group.append(file_info)
                    processed_paths.add(path2)
            
            # 只有包含多个文件的组才是重复组
            if len(current_group) > 1:
                # 为第一个文件也添加相似度信息
                current_group[0]['similarity'] = 100.0
                similar_groups.append(current_group)
        
        return similar_groups
        
    def calculate_similarity(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """
        计算特征相似度
        
        Args:
            feature1: 特征向量1
            feature2: 特征向量2
            
        Returns:
            相似度百分比
        """
        try:
            if feature1.shape != feature2.shape:
                return 0.0
            
            # 计算汉明距离
            hamming_distance = np.sum(feature1 != feature2)
            total_bits = len(feature1)
            
            # 转换为相似度百分比
            similarity = (1 - hamming_distance / total_bits) * 100
            
            return max(0.0, similarity)
            
        except Exception as e:
            print(f"计算相似度失败: {e}")
            return 0.0
            
    def calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """
        计算文件哈希值（用于精确重复检测）
        
        Args:
            file_path: 文件路径
            chunk_size: 读取块大小
            
        Returns:
            文件MD5哈希值
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败 {file_path}: {e}")
            return ""
            
    def find_exact_duplicates(self, video_files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        查找完全相同的文件（基于文件哈希）
        
        Args:
            video_files: 视频文件列表
            
        Returns:
            完全重复的文件组
        """
        hash_groups = defaultdict(list)
        
        for file_info in video_files:
            file_hash = self.calculate_file_hash(file_info['path'])
            if file_hash:
                hash_groups[file_hash].append(file_info)
        
        # 只返回包含多个文件的组
        exact_duplicates = []
        for group in hash_groups.values():
            if len(group) > 1:
                # 为每个文件添加100%相似度
                for file_info in group:
                    file_info['similarity'] = 100.0
                exact_duplicates.append(group)
        
        return exact_duplicates