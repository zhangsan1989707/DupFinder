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

class DuplicateDetector:
    """重复视频检测器"""
    
    def __init__(self, similarity_threshold: float = 80.0, sample_frames: int = 10):
        """
        初始化检测器
        
        Args:
            similarity_threshold: 相似度阈值（百分比）
            sample_frames: 采样帧数
        """
        self.similarity_threshold = similarity_threshold
        self.sample_frames = sample_frames
        
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
        
        # 第二步：内容特征提取和比较
        if progress_callback:
            progress_callback(60, "正在提取视频特征...")
            
        duplicate_groups = []
        processed_files = set()
        
        total_candidates = sum(len(group) for group in candidate_groups if len(group) > 1)
        current_processed = 0
        
        for candidate_group in candidate_groups:
            if len(candidate_group) < 2:
                continue
                
            # 提取特征
            features = {}
            for file_info in candidate_group:
                if file_info['path'] not in processed_files:
                    feature = self.extract_video_features(file_info)
                    if feature is not None:
                        features[file_info['path']] = {
                            'feature': feature,
                            'file_info': file_info
                        }
                        
                current_processed += 1
                if progress_callback:
                    progress = 60 + int((current_processed / total_candidates) * 30)
                    progress_callback(progress, f"正在处理 {file_info['name']}")
            
            # 比较特征找出重复组
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
        元数据预筛选
        
        Args:
            video_files: 视频文件列表
            
        Returns:
            候选重复组列表
        """
        # 按时长分组（允许5%的误差）
        duration_groups = defaultdict(list)
        
        for file_info in video_files:
            duration = file_info.get('duration', 0)
            if duration > 0:
                # 将时长归类到5%误差范围内的组
                duration_key = int(duration / (duration * 0.05 + 1))
                duration_groups[duration_key].append(file_info)
            else:
                # 时长未知的文件单独处理
                duration_groups[-1].append(file_info)
        
        # 进一步按文件大小细分（允许10%误差）
        candidate_groups = []
        for duration_group in duration_groups.values():
            if len(duration_group) < 2:
                candidate_groups.append(duration_group)
                continue
                
            size_groups = defaultdict(list)
            for file_info in duration_group:
                size = file_info.get('size', 0)
                if size > 0:
                    # 将大小归类到10%误差范围内的组
                    size_key = int(size / (size * 0.1 + 1024))  # 至少1KB的误差
                    size_groups[size_key].append(file_info)
                else:
                    size_groups[-1].append(file_info)
            
            candidate_groups.extend(size_groups.values())
        
        return candidate_groups
        
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