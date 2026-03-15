# 2025I 非接触式控制盘 — 香橙派 OpenCV 纯软件模拟

典型人机交互（HMI）题：通过**手势识别**与**空间位置感应**实现非接触式控制，无需摇杆/按键。

## 功能概览

| 能力 | 实现方式 |
|------|----------|
| **手势捕捉** | 手部平移、握拳/张开（肤色 YCrCb + 轮廓面积/凸包比 + 凸包缺陷） |
| **非接触映射** | 手部 2D 中心 → 归一化控制量 (nx, ny)，死区 + 指数平滑 |
| **实时反馈** | 低延迟：每帧检测 + 可调平滑系数，虚拟控制盘叠加显示 |
| **抗干扰** | 肤色分割、面积过滤、手部丢失时短时保持上一帧位置 |

## 环境

- Python 3.8+
- OpenCV、NumPy（见 `requirements.txt`）
- 香橙派或 PC；摄像头可选（支持纯软件模拟）

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 纯软件模拟：合成“虚拟手”运动，无需摄像头
python main.py --simulate

# 使用本地视频
python main.py --video path/to/video.mp4

# 实时摄像头（默认设备 0）
python main.py

# 常用参数
python main.py --width 640 --height 480 --show-mask   # 显示肤色二值图
python main.py --simulate --max-frames 300 --delay 40
python main.py --no-show   # 无屏/SSH 时不弹窗
```

## 项目结构

```
2025I/
├── config.py          # 分辨率、肤色范围、手势阈值、映射参数
├── main.py            # 入口：摄像头 / 视频 / 模拟 三种源
├── control_mapper.py  # 坐标→控制量映射、虚拟控制盘绘制
├── simulate.py        # 合成帧生成（虚拟手运动）、视频文件生成器
├── vision/
│   ├── __init__.py
│   └── hand.py        # 手部检测与握拳/张开分类
├── requirements.txt
└── README.md
```

## 参数说明（config.py）

- **肤色 YCrCb**：`SKIN_Cr_LOW/HIGH`、`SKIN_Cb_LOW/HIGH`，光照差异大时可在本机微调。
- **手势**：`FIST_EXTENT_THRESH`（轮廓/凸包面积比 ≥ 此视为握拳）、`OPEN_EXTENT_THRESH`（≤ 此视为张开）。
- **映射**：`MAP_DEADZONE` 中心死区、`MAP_SMOOTH` 平滑系数（越大越稳、延迟略增）。
- **跟踪**：`MAX_TRACK_LOST_FRAMES` 手部丢失后仍使用上一帧位置的最大帧数。

## 扩展思路

- 将 `(nx, ny)` 接到真实设备：屏幕光标、舵机角度、参数滑块等。
- 握拳/张开作为“确认/取消”或模式切换。
- 若香橙派性能允许，可接入 MediaPipe 手部关键点做更细手势（如捏合、旋转）。
