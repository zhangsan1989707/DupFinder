#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理
Configuration Management
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        'similarity_threshold': 80,
        'sample_frames': 10,
        'min_file_size': 1024 * 1024,  # 1MB
        'min_duration': 5,  # 5秒
        'max_duration': None,
        'supported_formats': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
        'processing_mode': 'trash',  # 'trash', 'backup', 'delete'
        'backup_folder': '',
        'ui_theme': 'default',
        'language': 'zh_CN'
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        if config_file is None:
            # 使用默认配置文件路径
            config_dir = Path.home() / '.dupfinder'
            config_dir.mkdir(exist_ok=True)
            self.config_file = config_dir / 'config.json'
        else:
            self.config_file = Path(config_file)
            
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            
    def save_config(self):
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value
        
    def update(self, config_dict: Dict[str, Any]):
        """
        批量更新配置
        
        Args:
            config_dict: 配置字典
        """
        self.config.update(config_dict)
        
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
        
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()

# 全局配置实例
config = Config()