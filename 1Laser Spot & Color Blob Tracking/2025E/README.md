# 2025E 视觉闭环控制 - 纯软件模拟

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

## 运行方式

```bash
# 多目标切换（默认）：红/绿/蓝/黄多 blob，按键 1–4 切换锁定目标
python main.py --mode multi

# 利萨如图形轨迹跟随：目标沿利萨如运动，绿色十字 PID 跟随
python main.py --mode lissajous

# 动态环境：多目标 + 闪烁/遮挡/光照周期变化，始终追红色
python main.py --mode dynamic
```

可选 `--no-kalman` 关闭 Kalman 预测，观察遮挡时轨迹抖动差异。

## 模块说明

| 文件 | 说明 |
|------|------|
| `config.py` | 画布、HSV 多色范围、PID/Kalman、利萨如参数、干扰强度 |
| `vision_2025.py` | 多目标 HSV 检测、按颜色/编号/手势选择目标、CLAHE 光照归一化 |
| `control_2025.py` | 双轴 PID、二维 Kalman 预测、利萨如/圆周/8 字轨迹生成 |
| `sim_env.py` | 合成场景：多 blob 运动、闪烁/遮挡/光照正弦调制 |
| `main.py` | 三种模式入口与主循环 |

## 与真实硬件对接

- **摄像头**：将 `sim_env.step()` 替换为 `cv2.VideoCapture.read()`，即可用真实画面做多目标检测。  
- **云台/小车**：将 `main.py` 中 `follower_x/y` 的更新改为舵机角度或底盘速度，并增加 `config` 中像素–角度/速度的标定即可。  

本仓库为纯软件仿真，便于在无硬件条件下验证算法与参数。
