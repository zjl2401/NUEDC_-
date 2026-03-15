# 2021D - 基于互联网的摄像机入侵检测系统（纯软件模拟）

**赛题**：2021年全国大学生电子设计竞赛 D题 - 基于互联网的摄像机入侵检测系统  
**实现方式**：香橙派 + OpenCV，纯软件模拟（摄像头可用 USB 摄像头或本地视频文件模拟）

## 功能概述

- **视频采集**：USB 摄像头或本地视频文件
- **入侵检测**：基于背景减法的运动检测，支持设定检测区域（ROI）
- **告警与联网**：检测到入侵时本地告警 + 可选的 HTTP 上报（模拟“基于互联网”）

## 环境要求

- Python 3.7+
- OpenCV (`opencv-python` 或 `opencv-contrib-python`)
- 香橙派 / Linux 或 Windows 均可运行

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 使用默认摄像头（0）运行
python main.py

# 使用视频文件模拟摄像头
python main.py --source video.mp4

# 指定摄像头索引（如 USB 摄像头为 1）
python main.py --source 1
```

## 配置说明

编辑 `config.yaml` 可调整：

- `min_area`：判定为“入侵”的最小运动区域面积（像素）
- `threshold`：二值化阈值
- `blur_ksize`：降噪高斯核大小
- 是否启用网络上报、上报地址等

## 联网告警联调（可选）

1. 在一台机器上启动告警接收服务（模拟云端/监控中心）：
   ```bash
   python alert_receiver.py
   ```
2. 在 `config.yaml` 中设置 `network.enabled: true`，并将 `network.url` 改为接收端地址（本机联调可用 `http://127.0.0.1:8080/alert`）。
3. 运行 `python main.py`，检测到入侵时会向该 URL POST 告警 JSON。

## 目录结构

```
2021D/
├── README.md
├── requirements.txt
├── config.yaml
├── main.py              # 主入口
├── detector.py          # 入侵检测核心（背景建模 + 运动检测）
├── camera.py            # 摄像头/视频采集封装
├── alert.py             # 本地告警与网络上报（模拟互联网）
└── alert_receiver.py    # 简易 HTTP 告警接收服务（联调用）
```

## 香橙派说明

在香橙派上使用 USB 摄像头时，通常设备为 `/dev/video0`。Linux 下 OpenCV 的 `VideoCapture(0)` 即对应默认摄像头，无需改代码。若需指定：

```bash
python main.py --source 0
```

若内存或算力紧张，可在 `config.yaml` 中降低分辨率或减小检测区域。
