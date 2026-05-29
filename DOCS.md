# Live2D 桌上自习 — 技术文档

## 项目概述

本项目是一个基于 **HTML5 Canvas 2D** 的伪 Live2D 实时渲染系统。将 PSD 拆分后的角色图层（共 18 层）在浏览器中叠加渲染，通过鼠标位置驱动角色的头部转动、身体倾斜、眼睛注视、膝盖弯曲等动态效果，全程使用 `requestAnimationFrame` 每帧重绘。

核心特性：
- 纯前端实现，零外部依赖
- 所有参数实时可调（右上角配置面板）
- 支持旋转、平移、仿射变换（倾斜/压缩）
- 鼠标穿透（`pointer-events: none`）

---

## 1. 图层系统

### 1.1 PSD 导出

使用 Python 的 `psd-tools` 库读取 `temp_input.psd`，将每个可见图层导出为带透明通道的 PNG：

```python
img = layer.composite()  # 合成图层（含透明）
img.save(f'{safe_name}.png')
```

共导出 18 个图层，同时记录每个图层的 `bbox`（边界框）到 `layers.json`，用于后续在 Canvas 中定位。

### 1.2 图层分组（Layer Group）

为了统一控制不同部位的运动，18 个图层被划分为 7 个逻辑组：

| 分组 | 包含图层 | 运动特征 |
|------|---------|---------|
| `head` | back_hair, ears, face, front_hair, headwear | 头部整体旋转+平移，与身体联动 |
| `neck` | neck | 中间层：身体与头部的插值过渡 |
| `body` | bottomwear, topwear | 围绕臀部旋转 |
| `hand` | left_hand, left_hand_front, right_hand, pen | 围绕臀部旋转 + 书写微动 |
| `leg` | legwear, footwear | 围绕臀部旋转 + 仿射变换（模拟膝盖弯曲） |
| `eye` | eyewhite, eyelash, eyebrow, nose, mouth | 跟随头部旋转，在局部坐标系中平移 |
| `pupil` | irides | 跟随头部旋转，在眼白范围内限位移动 |
| `prop` | chair, table_back, table4_back, table4_front, book | 完全静止 |

### 1.3 绘制顺序（Painter's Algorithm）

从后到前依次绘制，确保遮挡关系正确：

```
chair → back_hair → table_back → legwear → bottomwear → footwear
→ table4_back → left_hand → topwear → neck → pen → left_hand_front
→ right_hand → table4_front → book → ears → face → eyewhite → irides
→ eyelash → eyebrow → nose → mouth → front_hair → headwear
```

关键遮挡关系：
- `table_back` 在腿部之前绘制，作为桌子后沿
- `table4_back` 在腿部之后绘制，覆盖腿部下部
- `table4_front` 在双手 **之后**绘制，遮挡手部下方
- `left_hand` → `pen` → `left_hand_front` 顺序确保笔被夹在手指之间
- `right_hand` 在 `table4_front` 与 `book` 之间
- `neck` 在 `topwear` **之后**绘制，脖子覆盖在衣服领口之上

---

## 2. 鼠标跟踪系统

### 2.1 事件监听

```javascript
document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
});
```

### 2.2 坐标转换与归一化

将屏幕鼠标坐标转换为 Canvas 内部坐标（考虑响应式缩放），再计算相对于角色脸部中心的归一化偏移 `[-1, 1]`：

```javascript
function getMouseOffset() {
    // 1. 屏幕坐标 → Canvas 内部坐标
    const scaleX = CANVAS_SIZE / rect.width;
    const canvasMouseX = (mouseX - rect.left) * scaleX;

    // 2. 计算相对于脸部中心的偏移
    const dx = canvasMouseX - FACE_CENTER_X;  // FACE_CENTER ≈ (624, 258)
    const dy = canvasMouseY - FACE_CENTER_Y;

    // 3. 距离裁剪（防止鼠标在极远处时运动过度）
    const maxDist = CANVAS_SIZE * 0.6;
    const factor = Math.min(dist, maxDist) / maxDist;

    // 4. 归一化到 [-1, 1]
    return {
        x: Math.cos(angle) * factor,
        y: Math.sin(angle) * factor
    };
}
```

---

## 3. 平滑动画系统

### 3.1 动画循环

使用 `requestAnimationFrame` 实现 60fps 循环：

```javascript
function animate() {
    updateTargets();   // 根据鼠标位置计算目标值
    updateCurrent();   // Lerp 平滑过渡
    draw();            // 重绘所有图层
    requestAnimationFrame(animate);
}
```

### 3.2 Lerp 平滑插值

所有运动参数（平移、旋转）均通过线性插值实现平滑过渡，避免生硬跳变：

```javascript
function lerp(a, b, t) { return a + (b - a) * t; }

currentHeadX = lerp(currentHeadX, targetHeadX, lerpHead);  // 默认 0.08
currentEyeX  = lerp(currentEyeX,  targetEyeX,  lerpEye);   // 默认 0.12
```

- 头部/身体使用较慢的 `lerpHead`（0.08），显得沉稳
- 眼睛使用较快的 `lerpEye`（0.12），显得灵敏

---

## 4. 变换系统（核心）

每个图层组的变换由 `getLayerTransform(group)` 统一计算，返回：

```typescript
{
    pivotX, pivotY,  // 旋转中心（世界坐标）
    angle,           // 旋转角度（弧度）
    offX, offY,      // 额外平移（世界坐标）
    skewX?, scaleY?  // 仿射变换参数（仅 leg 组）
}
```

绘制时统一应用：

```javascript
ctx.save();
ctx.translate(pivotX + offX, pivotY + offY);
ctx.rotate(angle);
if (skewX !== undefined) {
    ctx.transform(1, 0, skewX, scaleY, 0, 0);  // 倾斜 + 压缩
}
ctx.drawImage(img, pos.x - pivotX, pos.y - pivotY, pos.w, pos.h);
ctx.restore();
```

### 4.1 身体变换（`body` 组）

- **旋转中心**：`(680, 850)` —— 臀部/座位处
- **旋转角度**：`currentBodyAngle = mouseOffset.x * maxBodyAngle`
- **平移**：无独立平移，纯旋转

身体围绕臀部旋转，模拟坐姿时的上身转动。

### 4.2 头部变换（`head` 组）

头部必须与身体联动，否则会出现"头飞走了"的断裂效果。

**核心机制**：

1. **头部旋转中心先被身体旋转位移**：
   ```javascript
   const pivotDelta = getBodyRotDelta(headPivotX, headPivotY);
   // pivotDelta = 该点围绕 bodyPivot 旋转 bodyAngle 后的位移量
   ```

2. **头部总角度 = 身体角度 + 头部独立角度**：
   ```javascript
   const totalAngle = currentBodyAngle + currentHeadAngle;
   ```

3. **头部平移 = 身体带来的位移 + 头部独立平移**：
   ```javascript
   offX = pivotDelta.x + currentHeadX;
   offY = pivotDelta.y + currentHeadY;
   ```

这样当身体转动时，头部旋转中心会随身体一起弧线运动，再叠加头部自身的独立旋转和平移，视觉上始终保持连接。

### 4.3 颈部中间层（`neck` 组）

颈部既不能 rigid 跟随身体（会显得死板），也不能完全跟随头部（会断裂），因此设计为**混合变换**：

```javascript
const inf = neckHeadInfluence;  // 默认 0.85

// 旋转：身体角度 + 头部独立角度 × 影响系数
const neckAngle = currentBodyAngle + currentHeadAngle * inf;

// 平移：身体位移 + 头部独立平移 × 影响系数
offX = pivotDelta.x + currentHeadX * inf;
offY = pivotDelta.y + currentHeadY * inf;
```

- `inf = 0`：颈部完全固定于身体
- `inf = 1`：颈部完全跟随头部（刚性连接）
- `inf = 0.85`（默认）：颈部大部分跟随头部，但保留一点滞后感

### 4.4 腿部仿射变换（`leg` 组）

Canvas 2D 不支持顶点变形（mesh deformation），因此使用**仿射变换**（倾斜 + 压缩）模拟膝盖弯曲的透视效果。

**变换参数**：

```javascript
const a = currentBodyAngle;
const bend = legBendFactor;  // 默认 0.6

// 倾斜：远离旋转中心的部分产生水平偏移
const skewX = -a * bend * 12.0;

// 压缩：y 方向缩短，模拟腿部视觉缩短
const scaleY = 1 - Math.abs(a) * bend * 4.0;

// 额外位移：让膝盖区域整体移动
const legOffX = a * bend * 250;
const legOffY = Math.abs(a) * bend * 120;
```

**数学原理**：

变换顺序为 `translate → rotate → transform(skew, scale)`。

`ctx.transform(1, 0, skewX, scaleY, 0, 0)` 对应矩阵：

```
[ 1    skewX   0 ]
[ 0    scaleY  0 ]
[ 0    0       1 ]
```

在旋转后的局部坐标系中，y 轴方向每变化 Δy，x 轴方向会产生 `skewX × Δy` 的偏移。由于腿部图像在局部坐标系中的 y 范围约为 `-126 ~ -582`，远离旋转中心的小腿部分会产生最大约 `0.25 × 456 ≈ 114px` 的偏移，形成明显的"膝盖向前顶"的透视感。

### 4.5 眼睛与瞳孔（`eye` / `pupil` 组）

#### 4.5.1 局部坐标系 → 世界坐标系

眼睛的平移（注视方向）是在**头部局部坐标系**中计算的，需要旋转到世界坐标系：

```javascript
function rotateVector(vx, vy, angle) {
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    return {
        x: vx * c - vy * s,
        y: vx * s + vy * c
    };
}

// 眼睛在头部局部坐标系中的偏移
const eyeLocalX = currentEyeX;  // 最大 ±5px
const eyeLocalY = currentEyeY;

// 旋转到世界坐标系（跟随头部总角度）
const eyeWorld = rotateVector(eyeLocalX, eyeLocalY, totalAngle);
```

这样即使头部旋转了 8°，眼睛在眼眶内的移动方向仍然是相对于脸部的，不会出现"眼珠斜着跑"的问题。

#### 4.5.2 瞳孔限位

瞳孔（irides）在眼白（eyewhite）范围内移动，超出会穿帮。

```javascript
let extraX = (currentEyeX / maxEyeMove) * maxPupilMove;
let extraY = (currentEyeY / maxEyeMove) * maxPupilMove;

// 硬边界限制
extraX = Math.max(-pupilLimitX, Math.min(pupilLimitX, extraX));
extraY = Math.max(-pupilLimitY, Math.min(pupilLimitY, extraY));
```

- 水平限位默认 `±5px`（眼白宽 97px，瞳孔宽 85px，每边余量约 6px）
- 垂直限位默认 `0px`（眼白高 29px，瞳孔高 30px，几乎无余量）

---

## 5. 配置面板

右上角浮动面板，使用 CSS `backdrop-filter: blur` 实现毛玻璃效果。所有参数通过 `input[type=range]` 和 `input[type=number]` 绑定，**实时生效**，无需刷新。

### 5.1 参数绑定机制

通用绑定函数：

```javascript
function bindParam(id, key, fmt, suffix) {
    const el = document.getElementById('r-' + id);
    el.addEventListener('input', () => {
        params[key] = parseFloat(el.value);
        disp.textContent = fmt(params[key]) + suffix;
    });
}
```

特殊处理（如百分比参数需要 ÷100）：

```javascript
// 颈部跟随：滑块 0~100，实际存储 0~1
params.neckHeadInfluence = parseInt(el.value) / 100;
```

### 5.2 面板分组

| 分组 | 参数 |
|------|------|
| 平移 | 头部最大移动、眼睛最大移动、瞳孔额外移动 |
| 旋转 | 头部最大旋转、身体最大旋转、腿部弯曲强度、颈部跟随头部 |
| 平滑 | 头部/身体平滑系数、眼睛平滑系数 |
| 限位 | 瞳孔水平限位、瞳孔垂直限位 |

---

## 6. 调试系统

勾选"显示调试框"后，Canvas 上会叠加绘制：

- **青色圆点**：身体旋转中心 `bodyPivot`
- **黄色圆点**：头部旋转中心 `headPivot`（已被身体旋转位移后的实际位置）
- **绿色矩形**：眼白（eyewhite）边界框
- **红色矩形**：瞳孔（irides）边界框

用于实时验证：
1. 旋转中心位置是否合适
2. 瞳孔是否始终被限制在眼白范围内
3. 头颈部是否断裂

---

## 7. 参数速查表

| 参数名 | 默认值 | 范围 | 说明 |
|--------|--------|------|------|
| `maxHeadMove` | 10 | 0~30 | 头部最大平移（px） |
| `maxEyeMove` | 5 | 0~20 | 眼睛最大平移（px） |
| `maxPupilMove` | 3 | 0~10 | 瞳孔额外移动（px） |
| `maxHeadAngle` | 6° | 0~15° | 头部最大旋转 |
| `maxBodyAngle` | 2° | 0~10° | 身体最大旋转 |
| `legBendFactor` | 60% | 0~100% | 腿部仿射变换强度 |
| `neckHeadInfluence` | 85% | 0~100% | 颈部受头部影响比例 |
| `lerpHead` | 0.08 | 0.01~0.30 | 头部/身体平滑系数 |
| `lerpEye` | 0.12 | 0.01~0.30 | 眼睛平滑系数 |
| `pupilLimitX` | 5 | 0~10 | 瞳孔水平限位（px） |
| `pupilLimitY` | 0 | 0~5 | 瞳孔垂直限位（px） |
| `headPivotX/Y` | 640, 330 | — | 头部旋转中心 |
| `bodyPivotX/Y` | 680, 850 | — | 身体旋转中心（臀部） |

---

## 8. 文件结构

```
桌上自习/
├── index.html          # 主程序（渲染 + 交互 + 配置面板）
├── layers/             # PSD 导出的透明 PNG 图层
│   ├── back_hair.png
│   ├── bottomwear.png
│   ├── legwear.png
│   ├── footwear.png
│   ├── topwear.png
│   ├── neck.png
│   ├── table_back.png
│   ├── table4_back.png
│   ├── table4_front.png
│   ├── left_hand.png
│   ├── left_hand_front.png
│   ├── right_hand.png
│   ├── ears.png
│   ├── face.png
│   ├── eyewhite.png
│   ├── irides.png
│   ├── eyelash.png
│   ├── eyebrow.png
│   ├── nose.png
│   ├── mouth.png
│   ├── front_hair.png
│   ├── headwear.png
│   └── layers.json     # 图层位置元数据
├── .gitignore          # 排除 PSD 和临时文件
└── DOCS.md             # 本文档
```

---

## 9. 使用方式

直接用浏览器打开 `index.html` 即可运行。无需服务器，无需构建。

鼠标移动即可看到效果：
- 头部跟随鼠标方向转动 + 平移
- 身体围绕臀部轻微旋转
- 腿部产生仿射弯曲
- 眼睛注视鼠标位置，瞳孔在眼眶内移动
- 点击背景区域可验证 `pointer-events: none` 穿透效果
