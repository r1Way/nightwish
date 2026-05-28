#!/usr/bin/env python3
"""
Live2D 桌宠 — 桌面悬浮窗程序
使用 PySide6 + QWebEngineView 加载 index.html
支持：无边框窗口 / 透明背景 / 置顶 / 鼠标拖动 / 右键菜单 / 调节大小
"""

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QMenu,
    QSpinBox, QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QPoint, QTimer
from PySide6.QtGui import QCursor, QAction

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class SizePanel(QWidget):
    """调节窗口大小的浮动面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("调节大小")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 宽度
        w_layout = QHBoxLayout()
        w_layout.addWidget(QLabel("宽度:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(parent.width() if parent else 420)
        self.width_spin.valueChanged.connect(self.on_value_changed)
        w_layout.addWidget(self.width_spin)
        layout.addLayout(w_layout)

        # 高度
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("高度:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(parent.height() if parent else 420)
        self.height_spin.valueChanged.connect(self.on_value_changed)
        h_layout.addWidget(self.height_spin)
        layout.addLayout(h_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._parent = parent

    def showEvent(self, event):
        """显示时同步当前窗口大小"""
        if self._parent:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(self._parent.width())
            self.height_spin.setValue(self._parent.height())
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
            # 定位到主窗口右下方
            pos = self._parent.pos() + QPoint(self._parent.width() + 10, 0)
            self.move(pos)
        super().showEvent(event)

    def on_value_changed(self):
        if self._parent:
            self._parent.resize(self.width_spin.value(), self.height_spin.value())


class DeskPet(QWidget):
    def __init__(self):
        super().__init__()

        # ========== 窗口属性 ==========
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        # ========== WebView ==========
        self.webview = QWebEngineView(self)
        self.webview.setAttribute(Qt.WA_TranslucentBackground)
        self.webview.page().setBackgroundColor(Qt.transparent)

        html_path = os.path.join(SCRIPT_DIR, "index.html")
        url = QUrl.fromLocalFile(html_path)
        url.setQuery("mode=deskpet")
        self.webview.load(url)

        self.webview.titleChanged.connect(self.on_title_changed)

        # ========== 布局 ==========
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.webview)

        # ========== 拖动状态 ==========
        self._dragging = False
        self._drag_start_global = None
        self._window_start_pos = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_drag_tick)
        self._timer.start(16)

        # 调节大小面板
        self._size_panel = SizePanel(self)

        # 初始大小和位置
        self.resize(420, 420)
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

    # ========== 右键菜单 ==========
    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        size_action = QAction("调节大小", self)
        size_action.triggered.connect(self.toggle_size_panel)
        menu.addAction(size_action)

        menu.addSeparator()

        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        menu.exec(global_pos)

    def toggle_size_panel(self):
        if self._size_panel.isVisible():
            self._size_panel.close()
        else:
            self._size_panel.show()
            self._size_panel.raise_()
            self._size_panel.activateWindow()

    # ========== 拖动逻辑 ==========
    def _on_drag_tick(self):
        if not self._dragging:
            return
        diff = QCursor.pos() - self._drag_start_global
        self.move(self._window_start_pos + diff)

    def on_title_changed(self, title: str):
        """JS 通过修改 document.title 向 Python 发送指令"""
        if title == "DP:DRAG_START":
            self._dragging = True
            self._drag_start_global = QCursor.pos()
            self._window_start_pos = self.pos()
        elif title == "DP:DRAG_END":
            self._dragging = False
            self._drag_start_global = None
            self._window_start_pos = None
        elif title == "DP:CONTEXT_MENU":
            self.show_context_menu(QCursor.pos())

    # ========== 键盘退出 ==========
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    pet = DeskPet()
    pet.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
