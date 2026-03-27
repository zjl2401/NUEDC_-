# 2017 电赛 C 题：四旋翼自主飞行器探测跟踪系统

香橙派 + OpenCV：地面标志搜索、运动目标跟踪；飞控通过 **MAVLink** 抽象接口连接（仿真 / 实机）。

## 快速运行（纯软件模拟，无需摄像头）

- **双击 `run.bat`** 或  
- 在 2017C 目录下执行：`pip install -r requirements.txt` 后 `python main.py --mode simulate`  
按 **Q** 退出。

详见 **运行说明.md**。

---

## 实机硬件清单

| 部件 | 说明 |
|------|------|
| 上位机 | Orange Pi / 树莓派等，运行本程序与 OpenCV |
| 摄像头 | USB 或 CSI，建议可调曝光、避免过曝 |
| 飞控 | 支持 MAVLink 的四旋翼（如 Pixhawk + ArduPilot Copter） |
| 数传/连线 | USB 数传、TTL 数传，或机载 WiFi 转发 UDP（如 `udp:IP:14550`） |
| 地面站（推荐） | Mission Planner / QGC，用于模式检查、紧急停止 |

---

## 实机软件依赖

```bash
pip install -r requirements.txt
```

实机飞控需 **pymavlink**（已写入 `requirements.txt`）。

---

## 实机配置（config.py）

- **摄像头**：`CAMERA_INDEX`、`FRAME_WIDTH/HEIGHT`、`EXPOSURE`
- **MAVLink 连接**（二选一）  
  - `FLIGHT_CONNECTION_STRING = ""` 时使用 `FLIGHT_SERIAL_PORT` + `FLIGHT_BAUD`  
  - 或设置 `FLIGHT_CONNECTION_STRING = "udp:127.0.0.1:14550"` 等  
- **速度缩放**：`FLIGHT_VEL_MAX_MS`（PID 输出 [-1,1] 乘该系数得机体系速度 m/s）  
- **偏航**：`FLIGHT_YAW_RATE_RADS`（跟踪中 yaw_rate 通道缩放）

---

## 实机运行命令

**仅视觉（不接速度指令，安全调试识别）：**

```bash
python main.py --mode vision --vision-mode track --camera-index 0
```

**完整任务 + 实机飞控（务必在安全场地、螺旋桨防护到位）：**

```bash
python main.py --mode full --real --camera-index 0 --connection COM3 --baud 57600
```

- Linux 串口示例：`--connection /dev/ttyUSB0 --baud 57600`  
- UDP 示例：`--connection udp:127.0.0.1:14550`  
- 只跑识别与速度环、**跳过起飞降落**（飞控由地面站手动起飞进入 GUIDED 后）：`--real --skip-flight`

等价写法（与 `--real` 相同）：`--no-simulate`

---

## 飞控与安全说明

- 本仓库实机类 `flight/mavlink_real.py` 面向 **ArduPilot Copter GUIDED** 发送 **机体系速度**（`MAV_FRAME_BODY_NED`）。PX4 / 其他栈需改模式与消息序列。  
- 首次上机请降低 `FLIGHT_VEL_MAX_MS`，并随时准备地面站切回 **RTL / Land**。  
- 解锁、起飞、降落为示例指令序列，因固件版本差异可能需要你在地面站侧微调。

---

## 项目结构（摘要）

```
2017C/
├── main.py           # full / vision / simulate
├── config.py
├── camera.py
├── flight/
│   ├── interface.py      # SimulateFlightInterface / create_flight_interface
│   └── mavlink_real.py   # MAVLink 实机
├── vision/ , control/ , simulate.py
└── README.md , 运行说明.md
```
