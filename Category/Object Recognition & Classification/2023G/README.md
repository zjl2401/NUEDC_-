# 2023 电赛 G 题 - 空地协同智能消防系统（纯软件模拟）

基于 **香橙派 + OpenCV** 的纯软件仿真：无人机“上帝视角”搜火源 → 无线信道下发坐标 → 地面小车避障前往并灭火。

## 核心任务拆解

| 模块       | 说明 |
|------------|------|
| **空对地引导** | 无人机俯视整张 2D 地图，用 OpenCV 检测红色火源，得到世界坐标并下发给小车。 |
| **地面协同**   | 小车接收坐标，在栅格地图上 A* 避障，行驶至火源附近。 |
| **精准打击**   | 进入灭火半径后执行“灭火”动作（持续若干帧），火源被标记为已灭。 |
| **协同机制**   | 通信层用内存队列模拟 WiFi/Lora 低延迟链路，可配置延迟帧数。 |

## 项目结构

```
2023G/
├── config.py          # 地图尺寸、火源 HSV、小车速度、通信延迟等
├── main.py             # 主循环：场景更新 → UAV 检测 → 通信 tick → 小车更新 → 显示
├── scene/
│   └── world.py        # 2D 俯视世界：障碍物栅格、火源、渲染与 UAV 视图
├── vision/
│   └── fire_detector.py # OpenCV 红色火源检测（HSV 双区间）
├── comm/
│   └── channel.py      # 模拟无线信道：UAV 发送 FireReport，小车接收
├── uav/
│   └── uav_agent.py    # 无人机逻辑：每帧俯视图检测火源并下发
├── ground/
│   └── vehicle.py      # 小车逻辑：收坐标、A* 寻路、移动、灭火
├── requirements.txt
└── README.md
```

## 运行方式

```bash
cd "3UAV Navigation Firefighting in Complex Environments/2023G"
pip install -r requirements.txt
python main.py
```

- 按 **Q** 退出。
- 可选：`python main.py --seed 42` 固定随机障碍物；`--no-window` 无界面运行。

## 配置说明（config.py）

- **火源检测**：`FIRE_HSV_LOW1/HIGH1`、`FIRE_HSV_LOW2/HIGH2` 红色双区间，`FIRE_MIN_AREA` 过滤噪声。
- **小车**：`VEHICLE_SPEED`、`FIRE_ACTION_RADIUS`、`FIRE_ACTION_DURATION`。
- **通信**：`COMM_LATENCY_FRAMES` 模拟信道延迟（帧数）。

## 扩展思路

- **真实硬件**：香橙派接摄像头作 UAV 端，另一块板或本机跑小车逻辑；将 `CommChannel` 换成 socket 或 MQTT 即可实现跨设备通信。
- **多火源**：在 `World` 中 `add_fire` 多个，小车灭完一个后根据信道中的下一个坐标继续寻路。
- **发热物体**：若用热成像模拟，可在 `fire_detector` 中改为温度/亮度阈值或简单热源模板。
