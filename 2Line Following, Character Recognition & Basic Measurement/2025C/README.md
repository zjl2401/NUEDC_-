# 2025 电赛 C 题：基于单目视觉的目标物测量装置（纯软件仿真）

基于 **Orange Pi RK3588 + OpenCV** 的单目视觉测量系统仿真，实现：

1. **物像关系建模**：像素坐标系与世界坐标系的数学映射（针孔模型 + 可选棋盘格标定）
2. **高精度边缘提取**：规则几何体（圆、矩形、多边形）的检测与亚像素级边缘
3. **单目深度/距离与尺寸计算**：在无双目/雷达条件下，利用已知参考尺寸或已知平面距离进行测距与测尺寸

## 环境

- Python 3.7+
- 依赖：`pip install -r requirements.txt`（numpy、opencv-python）

## 目录结构

```
2025C/
├── config.py              # 全局配置（焦距、参考尺寸、边缘/圆检测参数）
├── camera_calibration.py  # 物像关系：内参加载、标定、像素↔世界映射
├── edge_detection.py      # 边缘提取与圆/矩形/多边形识别
├── measurement.py         # 单目测距与几何尺寸计算
├── main.py                # 主程序：读图 → 检测 → 测量 → 可视化
├── generate_sim_image.py  # 生成仿真图（已知尺寸与距离）
├── run_calibration.py     # 棋盘格标定脚本
├── calibration/           # 标定图与 camera_params.npz
├── samples/               # 测试/仿真图像
└── requirements.txt
```

## 使用方式

### 1. 纯仿真（无相机、无图片）

生成仿真图并直接测量：

```bash
python main.py
```

会生成 `samples/sim_targets.png` 并在其上检测圆与矩形，输出 `output_sim.png` 与终端测量结果。

### 2. 使用自己的图像

```bash
python main.py path/to/your_image.jpg
```

结果保存为 `output_measurement.png`，终端打印圆/矩形的直径、边长、距离（若配置了参考尺寸或平面距离）。

### 3. 相机标定（提高真实相机精度）

将多张不同角度的棋盘格照片放入 `calibration/`，或：

```bash
python run_calibration.py calibration/img1.jpg calibration/img2.jpg ...
```

标定结果写入 `calibration/camera_params.npz`，后续 `main.py` 会自动加载。

### 4. 仅生成仿真图

```bash
python generate_sim_image.py
```

在 `samples/sim_targets.png` 生成带圆与矩形的仿真图，参数可在脚本内修改（平面距离、圆的半径、矩形宽高均为米）。

## 测量原理简述

- **物像关系**：`u = fx*x/z + cx`, `v = fy*y/z + cy`；已知平面 `z = d` 时，像素长度与世界长度关系为 `世界 = (像素 * d) / f`。
- **单目测距**：若已知某物体真实尺寸 `L` 及其在图像中的像素尺寸 `p`，则距离 `d = (L * f) / p`。
- **单目测尺寸**：若已知距离 `d`，则真实尺寸 `L = (d * p) / f`。

在 `config.py` 中可修改 `DEFAULT_CAMERA_HEIGHT_M`（默认测量平面距离）、`REFERENCE_OBJECT_REAL_HEIGHT_M`（参考物尺寸）等。

## 扩展

- 实际部署到 Orange Pi 时，可将 `main.py` 改为从摄像头 `cv2.VideoCapture(0)` 取帧并循环测量。
- 若需更稳的圆检测，可调节 `config.py` 中 `CIRCLE_PARAM1`、`CIRCLE_PARAM2`、`MIN_RADIUS`、`MAX_RADIUS`。
- 多边形在 `edge_detection.detect_polygons()` 中实现，可按赛题要求接入 `main.py` 的测量流程。
