# 2021 全国大学生电子设计竞赛（国赛）G 题 — 植保飞行器

**题目类别 (Task Category):** 飞行器类 (Aircraft / UAV / Drone)  
**英文题目 (English Title):** Plant Protection Unmanned Aerial Vehicle (UAV)  
**核心任务 (Core Task):** 视觉识别与自主巡航 (Visual Recognition and Autonomous Navigation)

本仓库基于 **香橙派 (Orange Pi) + OpenCV** 实现**纯软件模拟**，无需真实无人机与场地即可验证视觉识别与自主巡航算法。

---

## 赛题要点摘要

| 要求       | 说明 |
|------------|------|
| **垂直起飞与巡航** | 在“十”字起降点垂直起飞，升空至 150±10 cm 巡航高度。 |
| **寻找作业起点** | 从 “A” 所在区块开始“撒药”作业。 |
| **全覆盖播撒**   | 360 秒内完成对所有**绿色区块**的全覆盖播撒。 |
| **精准降落**     | 作业完成后降落在起降点，飞行器中心与起降点中心偏差 ≤ ±10 cm。 |

发挥部分可选：变工作模式（非播撒区块）、条形码识别与 LED 显示、圆周降落、现场编程等。

---

## 项目结构

```
2021G/
├── README.md           # 本说明（类别 / 英文术语 / 运行方式）
├── requirements.txt    # OpenCV、NumPy 等依赖
├── config.py           # 地图尺寸、颜色 HSV、巡航高度、超时等
├── main.py             # 主循环：模拟场景 → 视觉识别 → 自主巡航 → 显示
├── scene/
│   └── world.py        # 2D 俯视世界：十字起降点、A 区块、绿色作业区、渲染与 UAV 视图
├── vision/
│   └── detector.py     # OpenCV：十字、A、绿色区块检测（HSV/轮廓）
└── uav/
    └── uav_agent.py    # 无人机逻辑：起飞 → 寻 A → 全覆盖路径 → 降落
```

---

## 运行方式（纯软件模拟）

```bash
cd "Autonomous Flight & Obstacle Avoidance/2021G"
pip install -r requirements.txt
python main.py
```

- 支持 `python main.py --mode simulate` 明确指定模拟模式。  
- 按 **Q** 退出。  
- 可选：`--no-window` 无界面运行；`--seed 42` 固定随机布局。

---

## 配置说明（config.py）

- **地图与区块**：起降区十字大小、A 与绿色区块颜色（HSV）、区块尺寸。  
- **UAV**：巡航高度（像素/比例）、最大作业时间（秒）、降落误差阈值。  
- **视觉**：十字/A/绿色 HSV 范围、最小轮廓面积过滤噪声。

---

## 扩展与实机部署

### 实机硬件清单（参考）

| 部件 | 说明 |
|------|------|
| 上位机 | Orange Pi / 树莓派 + OpenCV |
| 摄像头 | 俯视场地或标记布，建议可调曝光 |
| 飞控 + 机架 | 支持定高/航线或 GUIDED 指令的四旋翼 |
| 数传 | USB 数传、TTL 或 WiFi 透传 MAVLink |
| 可选 | 条码/LED、GPIO 模块（发挥部分） |

### 软件侧对接

- **真实硬件**：香橙派接摄像头，俯视 2D 场地图或实景；将 `scene.World` 改为从摄像头取帧，`vision.detector` 不变即可做真实视觉识别；飞控通过串口/MAVLink 对接。  
- **发挥部分**：在 `vision/` 中增加条形码检测模块，在 `uav_agent` 中增加圆周降落逻辑与 LED 闪烁输出（GPIO 或模拟）。

---

## 术语中英对照

| 中文           | English |
|----------------|---------|
| 植保飞行器     | Plant Protection UAV |
| 视觉识别       | Visual Recognition |
| 自主巡航       | Autonomous Navigation |
| 起降点         | Takeoff/Landing Point |
| 作业起点       | Work Start (Block "A") |
| 全覆盖播撒     | Full-Coverage Spraying |
| 精准降落       | Precision Landing |
