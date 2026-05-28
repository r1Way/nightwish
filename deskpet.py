#!/usr/bin/env python3
"""
Live2D 桌宠 — 桌面悬浮窗程序
使用 PySide6 + QWebEngineView 加载 index.html
支持：无边框窗口 / 透明背景 / 置顶 / 鼠标拖动
"""

import sys
import os

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, QPoint, QTimer
from PySide6.QtGui import QCursor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class DeskPet(QWidget):
    def __init__(self):
        super().__init__()

        # ========== 窗口属性 ==========
        # FramelessWindowHint : 无边框
        # WindowStaysOnTopHint: 始终置顶
        # Tool                : 不显示在任务栏， Alt+Tab 中也不显示
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        # 透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        # ========== WebView ==========
        self.webview = QWebEngineView(self)
        self.webview.setAttribute(Qt.WA_TranslucentBackground)
        # 让 WebView 的背景透明（Qt6 方式）
        self.webview.page().setBackgroundColor(Qt.transparent)

        # 加载 HTML（带 deskpet 模式参数）
        html_path = os.path.join(SCRIPT_DIR, "index.html")
        url = QUrl.fromLocalFile(html_path)
        url.setQuery("mode=deskpet")
        self.webview.load(url)

        # 监听标题变化（JS → Python 通信通道）
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

        # 定时器：拖动时跟随鼠标（~60fps）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_drag_tick)
        self._timer.start(16)

        # 窗口初始大小（内部 Canvas 为 1280x1280，这里缩小显示）
        self.resize(420, 420)
        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )

    # ========== 拖动逻辑 ==========
    def _on_drag_tick(self):
        if not self._dragging:
            return
        # 计算鼠标偏移，更新窗口位置
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
        elif title.startswith("DP:RESIZE,"):
            # JS 请求调整窗口大小（未来扩展）
            pass

    # ========== 键盘退出 ==========
    def keyPressEvent(self, event):
        # 按 ESC 退出
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
