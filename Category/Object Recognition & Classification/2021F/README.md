# 智能送药车 — 香橙派 + OpenCV

基于 **NUEDC 2021** 相关赛题的智能送药车系统：**香橙派** 作为主控，**OpenCV** 做视觉，实现循线、房号与标志物识别、路径记录与原路返回。

## 技术维度概览

| 维度       | 内容 |
|------------|------|
| 视觉识别   | 房号识别（门口数字）、红线/色块（停止线） |
| 运动控制   | 黑色引导线循线、规定区域内厘米级停靠 |
| 路径规划   | 路径记录、路口转向、送药后原路返回 |
| 硬件协同   | 电机 PID、转向控制、多传感器融合 |

详见 [DESIGN.md](./DESIGN.md)。

## 环境与依赖（香橙派）

- **系统**：Armbian / Ubuntu（ARM64），Python 3.8+
- **安装**：
  ```bash
  cd 2021F
  pip install -r requirements.txt
  ```
- **可选**：房号 OCR 需安装 Tesseract  
  `sudo apt install tesseract-ocr`，并 `pip install pytesseract`

## 运行方式

在项目根目录 `2021F` 下：

```bash
python run.py              # 默认送药到 1 号房
python run.py --room 2     # 送药到 2 号房
python run.py --no-camera  # 不接摄像头，仅循线/传感器
python run.py --sim        # 纯软件仿真（无需硬件，自动弹窗显示模拟摄像头与俯视图）
python run.py --sim --no-sim-window   # 仿真但不显示窗口
python run.py --real-hal   # 启用真实 HAL（关闭 mock，需先按你的硬件实现 hal）
```

主循环默认 50 Hz，可通过 `--hz` 修改。**仿真模式**下赛道、巡线、房号与红线均由程序模拟，可在 PC 上直接验证逻辑与视觉算法。

## 目录结构

```
2021F/
├── DESIGN.md       # 技术拆解与架构
├── README.md       # 本说明
├── run.py          # 香橙派运行入口
├── requirements.txt
├── src/
│   ├── main.py     # 主循环与状态机
│   ├── config_loader.py
│   ├── vision/     # OpenCV：房号 + 红线/色块
│   ├── motion/     # 循线 + 停靠
│   ├── path/       # 路径记录与返回
│   └── hal/        # 摄像头、电机、传感器
├── config/
│   └── default.yaml  # PID、HSV、ROI、GPIO 等
└── tools/          # 标定与调试（可选）
```

## 配置说明

- **config/default.yaml**：循线 PID、停靠速度、红色 HSV、房号 ROI、路口阈值、摄像头设备号、GPIO 引脚（香橙派 BCM 编号）。根据实际接线与场地修改。
- **HAL**：`hal/motor.py`、`hal/sensor.py` 默认 **mock 模式**（不驱动真实电机/GPIO），便于在 PC 上跑通逻辑；接好硬件后用 `--real-hal` 关闭 mock 并实现对应 GPIO/PWM。

## 实机硬件清单

- 香橙派（主控）+ USB 摄像头
- 双电机底盘 + 电机驱动板（L298N/DRV8833 等）
- 巡线传感器阵列、可选编码器/测距
- 独立电池与电源管理、共地连接

## 实机配置步骤

1. 先用 `python run.py --sim` 验证状态机与视觉流程；
2. 在 `src/hal/motor.py`、`src/hal/sensor.py` 中接入你的 GPIO/PWM/传感器读取；
3. 修改 `config/default.yaml` 的相机、PID、HSV、阈值参数；
4. 执行 `python run.py --real-hal --room 2` 上车联调；
5. 根据停靠误差与路口误判，回调 `docking` 和 `junction` 参数。

## 实现顺序建议

1. 循线 + 基础路口转向  
2. 路口识别与路径记录  
3. 房号识别与目标匹配  
4. 红线/色块检测与精准停靠  
5. 原路返回与“送药”动作  

---

*本仓库为 2021F 赛题相关设计与代码框架。*
