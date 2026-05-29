#!/usr/bin/env python3
"""
Live2D 桌宠 — 桌面悬浮窗程序
使用 PySide6 + QWebEngineView 加载 index.html
支持：无边框窗口 / 透明背景 / 置顶 / 鼠标拖动 / 右键菜单 / 调节大小
"""

import sys
import os

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QPoint, QTimer
from PySide6.QtGui import QCursor, QAction

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


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

        # 初始大小和位置（默认 100% = 1280×1280）
        self.resize(1280, 1280)
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

        # 全局鼠标追踪定时器 (~60fps)
        self._mouse_timer = QTimer(self)
        self._mouse_timer.timeout.connect(self._update_global_mouse)
        self._mouse_timer.start(16)

    def _update_global_mouse(self):
        """将全局鼠标坐标传递给 JS"""
        global_pos = QCursor.pos()
        local_pos = self.webview.mapFromGlobal(global_pos)
        js = f"window.onGlobalMouseMove && window.onGlobalMouseMove({local_pos.x()}, {local_pos.y()});"
        self.webview.page().runJavaScript(js)

    # ========== 右键菜单 ==========
    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        # 调节大小子菜单（基于原始画布 1280×1280 的百分比）
        size_menu = QMenu("调节大小", self)
        for label, pct in [
            ("25%", 0.25), ("33%", 1/3), ("50%", 0.5),
            ("75%", 0.75), ("100%", 1.0), ("150%", 1.5),
        ]:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, p=pct: self.resize_to_percent(p))
            size_menu.addAction(action)
        menu.addMenu(size_menu)

        menu.addSeparator()

        config_action = QAction("参数调节", self)
        config_action.triggered.connect(self.toggle_config_panel)
        menu.addAction(config_action)

        menu.addSeparator()

        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        menu.exec(global_pos)

    def toggle_config_panel(self):
        self.webview.page().runJavaScript("""
            const panel = document.getElementById('config-panel');
            if (panel) panel.classList.remove('hidden');
        """)

    def resize_to_percent(self, pct):
        """按原始画布尺寸的百分比调整窗口大小"""
        base = 1280
        size = int(base * pct)
        self.resize(size, size)

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
