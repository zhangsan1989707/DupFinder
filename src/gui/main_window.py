#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
Main Window GUI
"""

import os
import time
import subprocess
import platform
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QProgressBar,
                             QTabWidget, QTreeWidget, QTreeWidgetItem, QComboBox,
                             QSlider, QSpinBox, QGroupBox, QCheckBox, QTextEdit,
                             QFileDialog, QMessageBox, QSplitter, QFrame, QGridLayout,
                             QMenu, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

from scanner.video_scanner import VideoScanner
from scanner.text_scanner import TextScanner
from scanner.image_scanner import ImageScanner
from detector.duplicate_detector import DuplicateDetector
from detector.text_duplicate_detector import TextDuplicateDetector
from detector.image_duplicate_detector import ImageDuplicateDetector
from processor.file_processor import FileProcessor
from gui.settings_dialog import SettingsDialog
from utils.config import config

class ScanWorker(QThread):
    """扫描工作线程"""
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    scan_completed = pyqtSignal(list, dict)  # 扫描完成信号
    error_occurred = pyqtSignal(str)  # 错误发生信号
    stats_updated = pyqtSignal(dict)  # 统计信息更新信号
    
    def __init__(self, paths, similarity_threshold=80, scan_mode='video'):
        super().__init__()
        self.paths = paths
        self.similarity_threshold = similarity_threshold
        self.scan_mode = scan_mode  # 'video' or 'text' or 'image'
        self.is_cancelled = False
        self.start_time = None
        self.stats = {
            'scan_start_time': '',
            'total_files': 0,
            'total_size': 0,
            'elapsed_time': 0
        }
    
    def run(self):
        """运行扫描"""
        try:
            # 记录开始时间
            self.start_time = time.time()
            self.stats['scan_start_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))
            
            if self.scan_mode == 'text':
                self._run_text_scan()
            elif self.scan_mode == 'image':
                self._run_image_scan()
            else:
                self._run_video_scan()
                
        except Exception as e:
            self.error_occurred.emit(f"扫描过程中发生错误: {str(e)}")
    
    def _run_video_scan(self):
        """运行视频扫描"""
        # 初始化扫描器和检测器
        scanner = VideoScanner()
        detector = DuplicateDetector(similarity_threshold=self.similarity_threshold)
        
        # 扫描视频文件
        self.progress_updated.emit(5, "开始扫描视频文件...")
        video_files = []
        total_size = 0
        
        for i, path in enumerate(self.paths):
            if self.is_cancelled:
                return
            
            # 更新路径扫描进度
            path_progress = f"扫描路径 {i+1}/{len(self.paths)}: {os.path.basename(path)}"
            self.progress_updated.emit(5 + i * 5, path_progress)
            
            # 创建进度回调函数，实时更新统计信息
            def progress_callback_with_stats(progress, message):
                if self.is_cancelled:
                    return
                self.update_progress(progress, message)
                # 实时更新统计信息
                self.stats['total_files'] = len(video_files)
                self.stats['total_size'] = total_size
                self.stats['elapsed_time'] = int(time.time() - self.start_time)
                self.stats_updated.emit(self.stats.copy())
            
            files = scanner.scan_directory(path, progress_callback=progress_callback_with_stats)
            video_files.extend(files)
            
            # 实时计算总大小
            for file_info in files:
                if 'size' in file_info:
                    total_size += file_info['size']
        
        if not video_files:
            self.error_occurred.emit("未找到任何视频文件")
            return
        
        # 最终更新统计信息
        self.stats['total_files'] = len(video_files)
        self.stats['total_size'] = total_size
        self.stats['elapsed_time'] = int(time.time() - self.start_time)
        self.stats_updated.emit(self.stats.copy())
        
        # 检测重复文件
        self.progress_updated.emit(95, f"找到 {len(video_files)} 个视频文件，开始重复检测...")
        duplicate_groups = detector.find_duplicates(video_files, 
                                                  progress_callback=self.update_progress)
        
        if not self.is_cancelled:
            # 计算最终统计信息
            self.stats['elapsed_time'] = int(time.time() - self.start_time)
            self.scan_completed.emit(duplicate_groups, self.stats.copy())
    
    def _run_text_scan(self):
        """运行文本扫描"""
        # 初始化扫描器和检测器
        scanner = TextScanner()
        detector = TextDuplicateDetector(similarity_threshold=self.similarity_threshold)
        
        # 扫描文本文件
        self.progress_updated.emit(5, "开始扫描文本文件...")
        text_files = []
        total_size = 0
        
        for i, path in enumerate(self.paths):
            if self.is_cancelled:
                return
            
            # 更新路径扫描进度
            path_progress = f"扫描路径 {i+1}/{len(self.paths)}: {os.path.basename(path)}"
            self.progress_updated.emit(5 + i * 5, path_progress)
            
            # 创建进度回调函数，实时更新统计信息
            def progress_callback_with_stats(progress, message):
                if self.is_cancelled:
                    return
                self.update_progress(progress, message)
                # 实时更新统计信息
                self.stats['total_files'] = len(text_files)
                self.stats['total_size'] = total_size
                self.stats['elapsed_time'] = int(time.time() - self.start_time)
                self.stats_updated.emit(self.stats.copy())
            
            files = scanner.scan_directory(path, progress_callback=progress_callback_with_stats)
            text_files.extend(files)
            
            # 实时计算总大小
            for file_info in files:
                if 'size' in file_info:
                    total_size += file_info['size']
        
        if not text_files:
            self.error_occurred.emit("未找到任何文本文件")
            return
        
        # 最终更新统计信息
        self.stats['total_files'] = len(text_files)
        self.stats['total_size'] = total_size
        self.stats['elapsed_time'] = int(time.time() - self.start_time)
        self.stats_updated.emit(self.stats.copy())
        
        # 检测重复文件
        self.progress_updated.emit(95, f"找到 {len(text_files)} 个文本文件，开始重复检测...")
        duplicate_groups = detector.find_duplicates(text_files, 
                                                  progress_callback=self.update_progress)
        
        if not self.is_cancelled:
            # 计算最终统计信息
            self.stats['elapsed_time'] = int(time.time() - self.start_time)
            self.scan_completed.emit(duplicate_groups, self.stats.copy())
    
    def update_progress(self, progress, message):
        """更新进度"""
        if not self.is_cancelled:
            self.progress_updated.emit(progress, message)
            # 更新统计信息
            if self.start_time:
                self.stats['elapsed_time'] = int(time.time() - self.start_time)
                self.stats_updated.emit(self.stats.copy())
    
    def _run_image_scan(self):
        """运行图片扫描"""
        # 初始化扫描器和检测器
        scanner = ImageScanner()
        detector = ImageDuplicateDetector(similarity_threshold=self.similarity_threshold)
        
        # 扫描图片文件
        self.progress_updated.emit(5, "开始扫描图片文件...")
        image_files = []
        total_size = 0
        
        for i, path in enumerate(self.paths):
            if self.is_cancelled:
                return
            
            # 更新路径扫描进度
            path_progress = f"扫描路径 {i+1}/{len(self.paths)}: {os.path.basename(path)}"
            self.progress_updated.emit(5 + i * 5, path_progress)
            
            # 创建进度回调函数，实时更新统计信息
            def progress_callback_with_stats(progress, message):
                if self.is_cancelled:
                    return
                self.update_progress(progress, message)
                # 实时更新统计信息
                self.stats['total_files'] = len(image_files)
                self.stats['total_size'] = total_size
                self.stats['elapsed_time'] = int(time.time() - self.start_time)
                self.stats_updated.emit(self.stats.copy())
            
            files = scanner.scan_directory(path, progress_callback=progress_callback_with_stats)
            image_files.extend(files)
            
            # 实时计算总大小
            for file_info in files:
                if 'size' in file_info:
                    total_size += file_info['size']
        
        if not image_files:
            self.error_occurred.emit("未找到任何图片文件")
            return
        
        # 最终更新统计信息
        self.stats['total_files'] = len(image_files)
        self.stats['total_size'] = total_size
        self.stats['elapsed_time'] = int(time.time() - self.start_time)
        self.stats_updated.emit(self.stats.copy())
        
        # 检测重复文件
        self.progress_updated.emit(95, f"找到 {len(image_files)} 个图片文件，开始重复检测...")
        duplicate_groups = detector.find_duplicates(image_files, 
                                                  progress_callback=self.update_progress)
        
        if not self.is_cancelled:
            # 计算最终统计信息
            self.stats['elapsed_time'] = int(time.time() - self.start_time)
            self.scan_completed.emit(duplicate_groups, self.stats.copy())
    
    def cancel(self):
        """取消扫描"""
        self.is_cancelled = True

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.scan_worker = None
        self.duplicate_groups = []
        self.scan_stats = {}
        self.current_mode = 'video'  # 'video' or 'text' or 'image'
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("智能文件查重工具 v1.0")
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
        
        # 模式选择
        toolbar_layout.addWidget(QLabel("扫描模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["视频查重", "文本查重", "图片查重"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        toolbar_layout.addWidget(self.mode_combo)
        
        toolbar_layout.addWidget(QLabel("  "))  # 分隔符
        
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
        
        # 统计信息区域
        stats_layout = QGridLayout()
        
        # 扫描开始时间
        stats_layout.addWidget(QLabel("开始时间:"), 0, 0)
        self.start_time_label = QLabel("--")
        stats_layout.addWidget(self.start_time_label, 0, 1)
        
        # 已扫描文件数
        stats_layout.addWidget(QLabel("文件数量:"), 0, 2)
        self.file_count_label = QLabel("0")
        stats_layout.addWidget(self.file_count_label, 0, 3)
        
        # 已扫描文件大小
        stats_layout.addWidget(QLabel("文件大小:"), 1, 0)
        self.file_size_label = QLabel("0 B")
        stats_layout.addWidget(self.file_size_label, 1, 1)
        
        # 已用时间
        stats_layout.addWidget(QLabel("已用时间:"), 1, 2)
        self.elapsed_time_label = QLabel("0秒")
        stats_layout.addWidget(self.elapsed_time_label, 1, 3)
        
        progress_layout.addLayout(stats_layout)
        parent.addWidget(progress_group)
        
    def create_results_section(self, parent):
        """创建结果区域"""
        results_group = QGroupBox("重复文件")
        results_layout = QVBoxLayout(results_group)
        
        # 结果树
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["文件路径", "大小", "属性1", "属性2", "相似度"])
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_tree.customContextMenuRequested.connect(self.show_context_menu)
        results_layout.addWidget(self.results_tree)
        
        parent.addWidget(results_group)
        
    def create_action_section(self, parent_layout):
        """创建底部操作区域"""
        action_layout = QHBoxLayout()
        
        # 选择策略
        action_layout.addWidget(QLabel("选择策略:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "手动选择", "保留最大尺寸", "保留最小大小", 
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
    
    def on_mode_changed(self, mode_text):
        """模式切换处理"""
        if mode_text == "视频查重":
            self.current_mode = 'video'
            self.setWindowTitle("智能文件查重工具 v1.0 - 视频模式")
        elif mode_text == "文本查重":
            self.current_mode = 'text'
            self.setWindowTitle("智能文件查重工具 v1.0 - 文本模式")
        else:
            self.current_mode = 'image'
            self.setWindowTitle("智能文件查重工具 v1.0 - 图片模式")
        
        # 清空当前结果
        self.results_tree.clear()
        self.duplicate_groups = []
        self.process_btn.setEnabled(False)
        
    def start_scan(self):
        """开始扫描"""
        if self.path_list.count() == 0:
            QMessageBox.warning(self, "警告", "请先添加要扫描的路径")
            return
            
        # 获取路径列表
        paths = [self.path_list.item(i).text() for i in range(self.path_list.count())]
        
        # 创建并启动扫描线程
        self.scan_worker = ScanWorker(paths, self.similarity_slider.value(), self.current_mode)
        self.scan_worker.progress_updated.connect(self.update_progress)
        self.scan_worker.scan_completed.connect(self.scan_completed)
        self.scan_worker.error_occurred.connect(self.scan_error)
        self.scan_worker.stats_updated.connect(self.update_stats)
        
        # 更新UI状态
        self.start_scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.process_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_tree.clear()
        
        # 重置统计信息显示
        self.reset_stats_display()
        
        # 根据模式设置状态文本
        mode_text = {"video": "视频", "text": "文本", "image": "图片"}.get(self.current_mode, "文件")
        self.status_label.setText(f"准备扫描{mode_text}...")
        
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
        
    def scan_completed(self, duplicate_groups, stats):
        """扫描完成"""
        self.duplicate_groups = duplicate_groups
        self.scan_stats = stats
        self.display_results(duplicate_groups)
        self.reset_ui_state()
        self.process_btn.setEnabled(len(duplicate_groups) > 0)
        
        # 显示完成消息
        total_duplicates = sum(len(group) for group in duplicate_groups)
        elapsed_time = self.format_time(stats.get('elapsed_time', 0))
        file_size = self.format_size(stats.get('total_size', 0))
        
        QMessageBox.information(self, "扫描完成", 
                              f"扫描完成！\n"
                              f"扫描文件: {stats.get('total_files', 0)} 个\n"
                              f"文件大小: {file_size}\n"
                              f"用时: {elapsed_time}\n"
                              f"找到重复组: {len(duplicate_groups)} 组\n"
                              f"重复文件: {total_duplicates} 个")
        
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
        
    def reset_stats_display(self):
        """重置统计信息显示"""
        self.start_time_label.setText("--")
        self.file_count_label.setText("0")
        self.file_size_label.setText("0 B")
        self.elapsed_time_label.setText("0秒")
        
    def update_stats(self, stats):
        """更新统计信息显示"""
        self.start_time_label.setText(stats.get('scan_start_time', '--'))
        self.file_count_label.setText(str(stats.get('total_files', 0)))
        self.file_size_label.setText(self.format_size(stats.get('total_size', 0)))
        self.elapsed_time_label.setText(self.format_time(stats.get('elapsed_time', 0)))
        
    def format_time(self, seconds):
        """格式化时间"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds//60}分{seconds%60}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}时{minutes}分{secs}秒"
            
    def show_context_menu(self, position):
        """显示右键上下文菜单"""
        item = self.results_tree.itemAt(position)
        if item is None:
            return
            
        # 只为文件项显示菜单（不是组项）
        if item.parent() is None:
            return
            
        file_path = item.text(0)
        if not file_path or not os.path.exists(file_path):
            return
            
        menu = QMenu(self)
        
        # 打开文件
        open_file_action = QAction("打开文件", self)
        open_file_action.triggered.connect(lambda: self.open_file(file_path))
        menu.addAction(open_file_action)
        
        # 打开文件所在目录
        open_folder_action = QAction("打开文件所在目录", self)
        open_folder_action.triggered.connect(lambda: self.open_file_location(file_path))
        menu.addAction(open_folder_action)
        
        menu.exec_(self.results_tree.mapToGlobal(position))
        
    def open_file(self, file_path):
        """打开文件"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件: {str(e)}")
            
    def open_file_location(self, file_path):
        """打开文件所在目录"""
        try:
            if platform.system() == 'Windows':
                subprocess.run(['explorer', '/select,', file_path])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                folder_path = os.path.dirname(file_path)
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件所在目录: {str(e)}")
        
    def display_results(self, duplicate_groups):
        """显示结果"""
        self.results_tree.clear()
        
        # 更新列标题
        if self.current_mode == 'text':
            self.results_tree.setHeaderLabels(["文件路径", "大小", "行数", "字符数", "相似度"])
        elif self.current_mode == 'image':
            self.results_tree.setHeaderLabels(["文件路径", "大小", "分辨率", "格式", "相似度"])
        else:  # video
            self.results_tree.setHeaderLabels(["文件路径", "大小", "分辨率", "时长", "相似度"])
        
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
                
                if self.current_mode == 'text':
                    # 文本文件显示行数和字符数
                    file_item.setText(2, str(file_info.get('line_count', 'N/A')))
                    file_item.setText(3, str(file_info.get('char_count', 'N/A')))
                elif self.current_mode == 'image':
                    # 图片文件显示分辨率和格式
                    file_item.setText(2, f"{file_info.get('width', 'N/A')}x{file_info.get('height', 'N/A')}")
                    file_item.setText(3, file_info.get('format', 'N/A'))
                else:
                    # 视频文件显示分辨率和时长
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
        
        if strategy == "保留最大尺寸":
            if self.current_mode == 'text':
                # 文本模式：选择字符数最多的文件
                return max(children, key=lambda x: self.parse_number(x.text(3)))
            else:
                # 图片和视频模式：选择分辨率最大的文件
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
    
    def parse_number(self, number_text):
        """解析数字"""
        try:
            if number_text == 'N/A':
                return 0
            return int(number_text)
        except:
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