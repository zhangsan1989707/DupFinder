#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框
Settings Dialog
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QLabel, QSpinBox, QSlider, QComboBox,
                             QLineEdit, QPushButton, QCheckBox, QGroupBox,
                             QFileDialog, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from utils.config import config

class SettingsDialog(QDialog):
    """设置对话框"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 检测设置选项卡
        self.create_detection_tab(tab_widget)
        
        # 文件处理选项卡
        self.create_processing_tab(tab_widget)
        
        # 界面设置选项卡
        self.create_ui_tab(tab_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 重置按钮
        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # 确定和取消按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept_settings)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def create_detection_tab(self, tab_widget):
        """创建检测设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 相似度设置组
        similarity_group = QGroupBox("相似度设置")
        similarity_layout = QFormLayout(similarity_group)
        
        # 相似度阈值
        self.similarity_threshold_slider = QSlider(Qt.Horizontal)
        self.similarity_threshold_slider.setRange(50, 100)
        self.similarity_threshold_slider.valueChanged.connect(self.update_similarity_label)
        
        self.similarity_threshold_label = QLabel("80%")
        
        similarity_threshold_layout = QHBoxLayout()
        similarity_threshold_layout.addWidget(self.similarity_threshold_slider)
        similarity_threshold_layout.addWidget(self.similarity_threshold_label)
        
        similarity_layout.addRow("相似度阈值:", similarity_threshold_layout)
        
        # 采样帧数
        self.sample_frames_spin = QSpinBox()
        self.sample_frames_spin.setRange(5, 50)
        self.sample_frames_spin.setSuffix(" 帧")
        similarity_layout.addRow("采样帧数:", self.sample_frames_spin)
        
        layout.addWidget(similarity_group)
        
        # 文件过滤设置组
        filter_group = QGroupBox("文件过滤")
        filter_layout = QFormLayout(filter_group)
        
        # 最小文件大小
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 10000)
        self.min_size_spin.setSuffix(" MB")
        filter_layout.addRow("最小文件大小:", self.min_size_spin)
        
        # 最小时长
        self.min_duration_spin = QSpinBox()
        self.min_duration_spin.setRange(0, 3600)
        self.min_duration_spin.setSuffix(" 秒")
        filter_layout.addRow("最小视频时长:", self.min_duration_spin)
        
        layout.addWidget(filter_group)
        
        layout.addStretch()
        tab_widget.addTab(tab, "检测设置")
        
    def create_processing_tab(self, tab_widget):
        """创建文件处理选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 处理方式设置组
        processing_group = QGroupBox("文件处理方式")
        processing_layout = QFormLayout(processing_group)
        
        # 处理模式
        self.processing_mode_combo = QComboBox()
        self.processing_mode_combo.addItem("移动到回收站", "trash")
        self.processing_mode_combo.addItem("移动到备份文件夹", "backup")
        self.processing_mode_combo.addItem("永久删除", "delete")
        self.processing_mode_combo.currentIndexChanged.connect(self.on_processing_mode_changed)
        processing_layout.addRow("处理方式:", self.processing_mode_combo)
        
        # 备份文件夹
        backup_layout = QHBoxLayout()
        self.backup_folder_edit = QLineEdit()
        backup_browse_btn = QPushButton("浏览...")
        backup_browse_btn.clicked.connect(self.browse_backup_folder)
        backup_layout.addWidget(self.backup_folder_edit)
        backup_layout.addWidget(backup_browse_btn)
        
        self.backup_folder_label = QLabel("备份文件夹:")
        processing_layout.addRow(self.backup_folder_label, backup_layout)
        
        layout.addWidget(processing_group)
        
        # 安全设置组
        safety_group = QGroupBox("安全设置")
        safety_layout = QVBoxLayout(safety_group)
        
        self.confirm_delete_check = QCheckBox("删除前确认")
        self.confirm_delete_check.setChecked(True)
        safety_layout.addWidget(self.confirm_delete_check)
        
        self.backup_before_delete_check = QCheckBox("删除前自动备份")
        safety_layout.addWidget(self.backup_before_delete_check)
        
        layout.addWidget(safety_group)
        
        layout.addStretch()
        tab_widget.addTab(tab, "文件处理")
        
    def create_ui_tab(self, tab_widget):
        """创建界面设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 界面设置组
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout(ui_group)
        
        # 主题
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "深色", "浅色"])
        ui_layout.addRow("主题:", self.theme_combo)
        
        # 语言
        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en_US")
        ui_layout.addRow("语言:", self.language_combo)
        
        layout.addWidget(ui_group)
        
        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout(display_group)
        
        self.show_preview_check = QCheckBox("显示视频预览")
        display_layout.addWidget(self.show_preview_check)
        
        self.auto_expand_groups_check = QCheckBox("自动展开重复组")
        self.auto_expand_groups_check.setChecked(True)
        display_layout.addWidget(self.auto_expand_groups_check)
        
        layout.addWidget(display_group)
        
        layout.addStretch()
        tab_widget.addTab(tab, "界面设置")
        
    def update_similarity_label(self, value):
        """更新相似度标签"""
        self.similarity_threshold_label.setText(f"{value}%")
        
    def on_processing_mode_changed(self, index):
        """处理模式改变"""
        mode = self.processing_mode_combo.itemData(index)
        is_backup_mode = mode == "backup"
        self.backup_folder_label.setVisible(is_backup_mode)
        self.backup_folder_edit.setVisible(is_backup_mode)
        self.backup_folder_edit.parent().layout().itemAt(1).widget().setVisible(is_backup_mode)
        
    def browse_backup_folder(self):
        """浏览备份文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择备份文件夹")
        if folder:
            self.backup_folder_edit.setText(folder)
            
    def load_settings(self):
        """加载设置"""
        # 检测设置
        self.similarity_threshold_slider.setValue(config.get('similarity_threshold', 80))
        self.sample_frames_spin.setValue(config.get('sample_frames', 10))
        self.min_size_spin.setValue(config.get('min_file_size', 1024*1024) // (1024*1024))
        self.min_duration_spin.setValue(config.get('min_duration', 5))
        
        # 文件处理设置
        processing_mode = config.get('processing_mode', 'trash')
        for i in range(self.processing_mode_combo.count()):
            if self.processing_mode_combo.itemData(i) == processing_mode:
                self.processing_mode_combo.setCurrentIndex(i)
                break
                
        self.backup_folder_edit.setText(config.get('backup_folder', ''))
        # 使用当前索引而不是处理模式字符串
        self.on_processing_mode_changed(self.processing_mode_combo.currentIndex())
        
        # 界面设置
        theme = config.get('ui_theme', 'default')
        theme_map = {'default': '默认', 'dark': '深色', 'light': '浅色'}
        theme_text = theme_map.get(theme, '默认')
        index = self.theme_combo.findText(theme_text)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        language = config.get('language', 'zh_CN')
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == language:
                self.language_combo.setCurrentIndex(i)
                break
                
    def accept_settings(self):
        """接受设置"""
        try:
            # 保存检测设置
            config.set('similarity_threshold', self.similarity_threshold_slider.value())
            config.set('sample_frames', self.sample_frames_spin.value())
            config.set('min_file_size', self.min_size_spin.value() * 1024 * 1024)
            config.set('min_duration', self.min_duration_spin.value())
            
            # 保存文件处理设置
            processing_mode = self.processing_mode_combo.currentData()
            if processing_mode is None:
                processing_mode = 'trash'
            config.set('processing_mode', processing_mode)
            config.set('backup_folder', self.backup_folder_edit.text())
            
            # 保存界面设置
            theme_map = {'默认': 'default', '深色': 'dark', '浅色': 'light'}
            theme = theme_map.get(self.theme_combo.currentText(), 'default')
            config.set('ui_theme', theme)
            
            language = self.language_combo.currentData()
            if language is None:
                language = 'zh_CN'
            config.set('language', language)
            
            # 保存配置到文件
            config.save_config()
            
            # 发出设置改变信号
            self.settings_changed.emit()
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
            
    def reset_to_default(self):
        """重置为默认设置"""
        reply = QMessageBox.question(self, "确认重置", 
                                   "确定要重置所有设置为默认值吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            config.reset_to_default()
            self.load_settings()
            QMessageBox.information(self, "重置完成", "设置已重置为默认值")