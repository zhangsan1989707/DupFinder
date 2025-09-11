#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
Main Window GUI
"""

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QProgressBar,
                             QTabWidget, QTreeWidget, QTreeWidgetItem, QComboBox,
                             QSlider, QSpinBox, QGroupBox, QCheckBox, QTextEdit,
                             QFileDialog, QMessageBox, QSplitter, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

from scanner.video_scanner import VideoScanner
from detector.duplicate_detector import DuplicateDetector
from processor.file_processor import FileProcessor
from gui.settings_dialog import SettingsDialog
from utils.config import config

class ScanWorker(QThread):
    """扫描工作线程"""
    progress_updated = pyqtSignal(int, str)  # 进度, 当前文件
    scan_completed = pyqtSignal(list)  # 扫描完成，返回重复组
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self, paths, similarity_threshold=80):
        super().__init__()
        self.paths = paths
        self.similarity_threshold = similarity_threshold
        self.is_cancelled = False
    
    def run(self):
        """运行扫描"""
        try:
            # 初始化扫描器和检测器
            scanner = VideoScanner()
            detector = DuplicateDetector(similarity_threshold=self.similarity_threshold)
            
            # 扫描视频文件
            self.progress_updated.emit(10, "正在扫描视频文件...")
            video_files = []
            for path in self.paths:
                if self.is_cancelled:
                    return
                files = scanner.scan_directory(path)
                video_files.extend(files)
            
            if not video_files:
                self.error_occurred.emit("未找到任何视频文件")
                return
            
            # 检测重复文件
            self.progress_updated.emit(30, f"找到 {len(video_files)} 个视频文件，开始分析...")
            duplicate_groups = detector.find_duplicates(video_files, 
                                                      progress_callback=self.update_progress)
            
            if not self.is_cancelled:
                self.scan_completed.emit(duplicate_groups)
                
        except Exception as e:
            self.error_occurred.emit(f"扫描过程中发生错误: {str(e)}")
    
    def update_progress(self, progress, message):
        """更新进度"""
        if not self.is_cancelled:
            self.progress_updated.emit(progress, message)
    
    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.scan_worker = None
        self.duplicate_groups = []
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("视频文件智能查重工具 v1.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部工具栏
        self.create_toolbar(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 创建路径管理区域
        self.create_path_section(splitter)
        
        # 创建进度区域
        self.create_progress_section(splitter)
        
        # 创建结果区域
        self.create_results_section(splitter)
        
        # 创建底部操作区域
        self.create_action_section(main_layout)
        
        # 设置分割器比例
        splitter.setSizes([200, 100, 400])
        
    def create_toolbar(self, parent_layout):
        """创建顶部工具栏"""
        toolbar_layout = QHBoxLayout()
        
        # 添加路径按钮
        self.add_path_btn = QPushButton("添加路径")
        self.add_path_btn.clicked.connect(self.add_path)
        toolbar_layout.addWidget(self.add_path_btn)
        
        # 开始扫描按钮
        self.start_scan_btn = QPushButton("开始扫描")
        self.start_scan_btn.clicked.connect(self.start_scan)
        toolbar_layout.addWidget(self.start_scan_btn)
        
        # 停止扫描按钮
        self.stop_scan_btn = QPushButton("停止扫描")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        toolbar_layout.addWidget(self.stop_scan_btn)
        
        # 设置按钮
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.show_settings)
        toolbar_layout.addWidget(self.settings_btn)
        
        # 相似度设置
        toolbar_layout.addWidget(QLabel("相似度阈值:"))
        self.similarity_slider = QSlider(Qt.Horizontal)
        self.similarity_slider.setRange(50, 100)
        self.similarity_slider.setValue(80)
        self.similarity_slider.valueChanged.connect(self.update_similarity_label)
        toolbar_layout.addWidget(self.similarity_slider)
        
        self.similarity_label = QLabel("80%")
        toolbar_layout.addWidget(self.similarity_label)
        
        toolbar_layout.addStretch()
        parent_layout.addLayout(toolbar_layout)
        
    def create_path_section(self, parent):
        """创建路径管理区域"""
        path_group = QGroupBox("扫描路径")
        path_layout = QVBoxLayout(path_group)
        
        # 路径列表
        self.path_list = QListWidget()
        self.path_list.setMaximumHeight(150)
        path_layout.addWidget(self.path_list)
        
        # 路径操作按钮
        path_btn_layout = QHBoxLayout()
        
        remove_path_btn = QPushButton("移除选中")
        remove_path_btn.clicked.connect(self.remove_selected_path)
        path_btn_layout.addWidget(remove_path_btn)
        
        clear_paths_btn = QPushButton("清空所有")
        clear_paths_btn.clicked.connect(self.clear_all_paths)
        path_btn_layout.addWidget(clear_paths_btn)
        
        path_btn_layout.addStretch()
        path_layout.addLayout(path_btn_layout)
        
        parent.addWidget(path_group)
        
    def create_progress_section(self, parent):
        """创建进度区域"""
        progress_group = QGroupBox("扫描进度")
        progress_layout = QVBoxLayout(progress_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        
        parent.addWidget(progress_group)
        
    def create_results_section(self, parent):
        """创建结果区域"""
        results_group = QGroupBox("重复文件")
        results_layout = QVBoxLayout(results_group)
        
        # 结果树
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["文件路径", "大小", "分辨率", "时长", "相似度"])
        self.results_tree.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_tree)
        
        parent.addWidget(results_group)
        
    def create_action_section(self, parent_layout):
        """创建底部操作区域"""
        action_layout = QHBoxLayout()
        
        # 选择策略
        action_layout.addWidget(QLabel("选择策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "手动选择", "保留最大分辨率", "保留最小大小", 
            "保留最新文件", "保留最旧文件"
        ])
        action_layout.addWidget(self.strategy_combo)
        
        # 应用策略按钮
        apply_strategy_btn = QPushButton("应用策略")
        apply_strategy_btn.clicked.connect(self.apply_selection_strategy)
        action_layout.addWidget(apply_strategy_btn)
        
        action_layout.addStretch()
        
        # 执行处理按钮
        self.process_btn = QPushButton("执行处理")
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        action_layout.addWidget(self.process_btn)
        
        parent_layout.addLayout(action_layout)
        
    def add_path(self):
        """添加扫描路径"""
        path = QFileDialog.getExistingDirectory(self, "选择要扫描的目录")
        if path and path not in [self.path_list.item(i).text() 
                                for i in range(self.path_list.count())]:
            self.path_list.addItem(path)
            
    def remove_selected_path(self):
        """移除选中的路径"""
        current_row = self.path_list.currentRow()
        if current_row >= 0:
            self.path_list.takeItem(current_row)
            
    def clear_all_paths(self):
        """清空所有路径"""
        self.path_list.clear()
        
    def update_similarity_label(self, value):
        """更新相似度标签"""
        self.similarity_label.setText(f"{value}%")
        
    def start_scan(self):
        """开始扫描"""
        if self.path_list.count() == 0:
            QMessageBox.warning(self, "警告", "请先添加要扫描的路径")
            return
            
        # 获取路径列表
        paths = [self.path_list.item(i).text() for i in range(self.path_list.count())]
        
        # 创建并启动扫描线程
        self.scan_worker = ScanWorker(paths, self.similarity_slider.value())
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_completed.connect(self.scan_completed)
        self.scan_worker.error_occurred.connect(self.scan_error)
        
        # 更新UI状态
        self.start_scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.process_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_tree.clear()
        
        self.scan_worker.start()
        
    def stop_scan(self):
        """停止扫描"""
        if self.scan_worker:
            self.scan_worker.cancel()
            self.scan_worker.wait()
            
        self.reset_ui_state()
        
    def update_progress(self, progress, message):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        
    def scan_completed(self, duplicate_groups):
        """扫描完成"""
        self.duplicate_groups = duplicate_groups
        self.display_results(duplicate_groups)
        self.reset_ui_state()
        self.process_btn.setEnabled(len(duplicate_groups) > 0)
        
        # 显示完成消息
        total_duplicates = sum(len(group) for group in duplicate_groups)
        QMessageBox.information(self, "扫描完成", 
                              f"扫描完成！找到 {len(duplicate_groups)} 组重复文件，"
                              f"共 {total_duplicates} 个重复文件。")
        
    def scan_error(self, error_message):
        """扫描错误"""
        QMessageBox.critical(self, "扫描错误", error_message)
        self.reset_ui_state()
        
    def reset_ui_state(self):
        """重置UI状态"""
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.status_label.setText("就绪")
        self.progress_bar.setValue(0)
        
    def display_results(self, duplicate_groups):
        """显示结果"""
        self.results_tree.clear()
        
        for i, group in enumerate(duplicate_groups):
            # 创建组节点
            group_item = QTreeWidgetItem(self.results_tree)
            group_item.setText(0, f"重复组 {i+1} ({len(group)} 个文件)")
            group_item.setExpanded(True)
            
            # 添加文件节点
            for file_info in group:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_info['path'])
                file_item.setText(1, self.format_size(file_info['size']))
                file_item.setText(2, f"{file_info.get('width', 'N/A')}x{file_info.get('height', 'N/A')}")
                file_item.setText(3, self.format_duration(file_info.get('duration', 0)))
                file_item.setText(4, f"{file_info.get('similarity', 100):.1f}%")
                file_item.setCheckState(0, Qt.Unchecked)
                
    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
        
    def format_duration(self, duration_seconds):
        """格式化时长"""
        if duration_seconds <= 0:
            return "N/A"
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
            
    def apply_selection_strategy(self):
        """应用选择策略"""
        strategy = self.strategy_combo.currentText()
        
        if strategy == "手动选择":
            return
            
        # 实现自动选择策略
        for i in range(self.results_tree.topLevelItemCount()):
            group_item = self.results_tree.topLevelItem(i)
            
            # 先取消所有选择
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                child.setCheckState(0, Qt.Unchecked)
            
            # 根据策略选择要保留的文件
            if group_item.childCount() > 0:
                selected_child = self.select_by_strategy(group_item, strategy)
                if selected_child:
                    selected_child.setCheckState(0, Qt.Checked)
                    
    def select_by_strategy(self, group_item, strategy):
        """根据策略选择文件"""
        if group_item.childCount() == 0:
            return None
            
        children = [group_item.child(i) for i in range(group_item.childCount())]
        
        if strategy == "保留最大分辨率":
            # 选择分辨率最大的文件
            return max(children, key=lambda x: self.get_resolution_score(x.text(2)))
        elif strategy == "保留最小大小":
            # 选择文件大小最小的
            return min(children, key=lambda x: self.parse_size(x.text(1)))
        elif strategy == "保留最新文件":
            # 选择修改时间最新的文件
            return max(children, key=lambda x: os.path.getmtime(x.text(0)))
        elif strategy == "保留最旧文件":
            # 选择修改时间最旧的文件
            return min(children, key=lambda x: os.path.getmtime(x.text(0)))
            
        return children[0]  # 默认选择第一个
        
    def get_resolution_score(self, resolution_text):
        """获取分辨率分数"""
        try:
            if 'x' in resolution_text:
                width, height = map(int, resolution_text.split('x'))
                return width * height
        except:
            pass
        return 0
        
    def parse_size(self, size_text):
        """解析文件大小"""
        try:
            parts = size_text.split()
            if len(parts) == 2:
                value, unit = parts
                value = float(value)
                multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                return value * multipliers.get(unit, 1)
        except:
            pass
        return 0
        
    def process_files(self):
        """处理文件"""
        # 收集要删除的文件
        files_to_process = []
        
        for i in range(self.results_tree.topLevelItemCount()):
            group_item = self.results_tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child.checkState(0) == Qt.Unchecked:  # 未选中的文件将被处理
                    files_to_process.append(child.text(0))
                    
        if not files_to_process:
            QMessageBox.information(self, "提示", "没有选择要处理的文件")
            return
            
        # 确认对话框
        reply = QMessageBox.question(self, "确认处理", 
                                   f"将要处理 {len(files_to_process)} 个文件，"
                                   f"这些文件将被移动到回收站。\n\n确定继续吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 执行文件处理
            processor = FileProcessor()
            success_count = processor.move_to_trash(files_to_process)
            
            QMessageBox.information(self, "处理完成", 
                                  f"成功处理了 {success_count} 个文件")
            
            # 清空结果
            self.results_tree.clear()
            self.process_btn.setEnabled(False)
            
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec_()
        
    def on_settings_changed(self):
        """设置改变时的处理"""
        # 更新相似度滑块
        self.similarity_slider.setValue(config.get('similarity_threshold', 80))
        QMessageBox.information(self, "设置", "设置已保存并应用")
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.scan_worker and self.scan_worker.isRunning():
            reply = QMessageBox.question(self, "确认退出", 
                                       "扫描正在进行中，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.scan_worker.cancel()
                self.scan_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()