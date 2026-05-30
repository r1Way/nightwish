# 🌸 桌上自习 · Live2D DeskPet

一个基于 **HTML5 Canvas 2D** 的轻量级伪 Live2D 桌面宠物。将 PSD 拆分后的角色图层实时叠加渲染，通过鼠标位置驱动角色的头部转动、身体倾斜、眼睛注视、膝盖弯曲等动态效果，全程使用 `requestAnimationFrame` 逐帧绘制。

> 零外部依赖、纯前端实现、参数实时可调、支持桌面悬浮窗与浏览器双模式运行。

---

## ✨ 功能特性

- **🖱️ 鼠标追踪**：头部、身体、眼睛、瞳孔实时跟随鼠标位置
- **🦵 仿射变换**：使用倾斜 + 压缩模拟膝盖弯曲的透视效果
- **⚙️ 实时调参**：右上角配置面板，所有动画参数即时生效
- **🪟 桌面悬浮窗**：无边框、透明背景、置顶、可拖拽、右键菜单
- **🌐 浏览器直开**：无需服务器，双击 `index.html` 即可运行
- **↔️ 水平翻转**：右键一键翻转角色朝向
- **📐 多档缩放**：25% ~ 150% 共 7 档尺寸调节

---

## 🚀 快速开始

### 方式一：桌面宠物模式（推荐）

需要 Python 3.x 与 PySide6：

```bash
pip install pyside6
python deskpet.py
```

- 窗口会自动居中，默认尺寸 420×420
- **拖拽**：按住角色拖动窗口位置
- **右键菜单**：调节大小 / 参数面板 / 水平翻转 / 退出
- **ESC**：快速退出程序

### 方式二：浏览器模式

直接用浏览器打开 `index.html`：

```bash
# 无需任何依赖，双击即可
index.html
```

- 鼠标移动即可预览全部动画效果
- 点击右上角 ⚙️ 图标展开配置面板

---

## 📦 打包为可执行文件

使用 PyInstaller 一键打包（Windows）：

```bash
pip install pyinstaller
pyinstaller DeskPet.spec
```

打包后的文件位于 `dist/DeskPet/` 目录下，可整份复制到其他电脑直接运行。

---

## 🏗️ 项目结构

```
桌上自习/
├── index.html              # 主渲染程序（Canvas + 交互 + 配置面板）
├── deskpet.py              # 桌面悬浮窗外壳（PySide6 + QWebEngineView）
├── DeskPet.spec            # PyInstaller 打包配置
├── layers/                 # PSD 导出的透明 PNG 图层（共 18+ 层）
│   ├── face.png
│   ├── eyeswhite.png
│   ├── irides.png
│   ├── ...
│   └── layers.json         # 图层位置元数据
├── DOCS.md                 # 详细技术文档
├── README.md               # 本文件
├── .gitignore
└── export_layers.py        # PSD 图层导出脚本（开发工具）
```

> 注：PSD 源文件体积较大，已加入 `.gitignore`，如需重新导出图层请自备 `temp_input.psd` 并运行 `export_layers.py`。

---

## 🎛️ 可调参数一览

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 头部最大平移 | 10 px | 头部跟随鼠标的移动范围 |
| 头部最大旋转 | 6° | 头部左右摆动的最大角度 |
| 身体最大旋转 | 2° | 上半身围绕臀部的旋转角度 |
| 腿部弯曲强度 | 60% | 仿射变换模拟膝盖弯曲的程度 |
| 颈部跟随头部 | 85% | 颈部受头部影响的比例（0=固定，1=完全跟随）|
| 眼睛最大移动 | 5 px | 眼睛在眼眶内的平移范围 |
| 瞳孔额外移动 | 3 px | 瞳孔相对于眼白的额外位移 |
| 平滑系数 | 0.08 / 0.12 | 头部与眼睛的 Lerp 插值速度 |

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 渲染引擎 | HTML5 Canvas 2D API |
| 桌面外壳 | Python 3 + PySide6 + QWebEngineView |
| 动画系统 | `requestAnimationFrame` + Lerp 平滑插值 |
| 变换系统 | 旋转 / 平移 / 仿射变换（`ctx.transform`）|
| 构建工具 | PyInstaller |

---

## 📄 开源许可

本项目仅供学习交流使用。
