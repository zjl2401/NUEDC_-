# 2025E 视觉闭环控制（仿真/真机）

基于对 2025 年电赛 E 题的预测（**基于视觉反馈的复杂环境运动控制系统**），本仓库在 **Orange Pi RK3588 + OpenCV** 技术栈下实现**纯软件模拟**，覆盖三大核心挑战：

1. **多目标协同/切换**：多运动目标中按颜色/编号/简单手势锁定并追踪  
2. **非线性轨迹跟随**：利萨如图形等数学曲线的高精度跟随  
3. **动态环境适应**：背景闪烁、遮挡、光照剧烈变化下保持追踪不丢失  

## 环境要求

- Python 3.8+
- OpenCV、NumPy（见 `requirements.txt`）

```bash
pip install -r requirements.txt
```

## 运行方式（仿真）

```bash
# 多目标切换（默认）：红/绿/蓝/黄多 blob，按键 1–4 切换锁定目标
python main.py --mode multi

# 利萨如图形轨迹跟随：目标沿利萨如运动，绿色十字 PID 跟随
python main.py --mode lissajous

# 动态环境：多目标 + 闪烁/遮挡/光照周期变化，始终追红色
python main.py --mode dynamic
```

可选 `--no-kalman` 关闭 Kalman 预测，观察遮挡时轨迹抖动差异。

## 运行方式（真机：摄像头 + 云台/舵机）

本目录已补齐真机入口（不影响原有仿真模式），通过 `--real` 启动：

```bash
# 真机多目标切换：按键 1-4 锁定不同颜色目标
python main.py --mode multi --real

# 真机动态追踪：始终追红色
python main.py --mode dynamic --real

# 真机复位回中 + （可选）透视标定（黑框）
python main.py --mode reset --real

# 真机但不接舵机/无 GPIO：只打印角度（或无 GPIO 会自动 dummy）
python main.py --mode dynamic --real --dummy
```

真机调通通常需要先在 `config.py` 里完成标定：

- **摄像头**：`CAMERA_INDEX`、`FRAME_WIDTH/FRAME_HEIGHT`、`EXPOSURE`
- **舵机中心与范围**：`PAN_CENTER/TILT_CENTER`、`PAN_MIN/MAX`、`TILT_MIN/MAX`
- **像素→角度映射**：`PIXEL_TO_PAN`、`PIXEL_TO_TILT`（方向不对就取反）

> 提示：`--mode lissajous` 主要用于纯软件验证控制性能，真机更建议用 `multi` 或 `dynamic`。

### 真机增强选项（已补齐）

- **透视矫正（黑框标定）**
  - 默认开启（`config.py` 里的 `USE_PERSPECTIVE=True`），真机运行时可按 `C` 重新标定
  - 如不需要：加 `--no-perspective`
- **ROI 加速**
  - 默认开启（`ROI_ENABLED=True`），锁定目标后只在局部区域检测以提速稳帧
  - 如需关闭：加 `--no-roi`
- **串口输出（可选）**
  - 依赖：`pip install pyserial`
  - 运行：`python main.py --mode dynamic --real --serial COM3 --baud 115200`
  - 输出内容：`pan/tilt` 与目标相对中心的误差 `ex/ey`（便于单片机/飞控使用）

## 模块说明

| 文件 | 说明 |
|------|------|
| `config.py` | 画布、HSV 多色范围、PID/Kalman、利萨如参数、干扰强度 |
| `vision_2025.py` | 多目标 HSV 检测、按颜色/编号/手势选择目标、CLAHE 光照归一化 |
| `control_2025.py` | 双轴 PID、二维 Kalman 预测、利萨如/圆周/8 字轨迹生成 |
| `sim_env.py` | 合成场景：多 blob 运动、闪烁/遮挡/光照正弦调制 |
| `main.py` | 三种模式入口与主循环 |

## 与真实硬件对接

- **摄像头**：已在 `main.py --real` 中接入 `cv2.VideoCapture.read()`。  
- **云台/小车**：已在 `main.py --real` 中将像素误差映射为舵机角度增量（需标定 `PIXEL_TO_PAN/TILT`）。  

本目录同时支持纯软件仿真与真机运行，便于在无硬件条件下先验证算法，再上板调通闭环。
