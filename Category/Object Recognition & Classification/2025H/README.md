# 野生动物巡查系统 - 动态感知与复杂场景理解

基于 **香橙派 + OpenCV** 的野生动物巡查感知方案，针对从“识别”到“感知”的四大技术挑战设计。

## 核心技术挑战与对应方案

| 挑战 | 方案 |
|------|------|
| **非固定形态目标** | 不依赖固定形状匹配；使用**背景减除 + 运动前景**，用几何约束（面积、宽高比、轮廓饱满度 extent）过滤，适配动物/四足模型的肢体变化。 |
| **低信噪比环境** | **MOG2/KNN 背景建模** + **形态学开/闭运算** 去杂草/树叶小斑点、填洞，突出真实运动目标。 |
| **长距离与小目标** | 可调 `PROC_WIDTH/PROC_HEIGHT` 提高分辨率；`MIN_BBOX_SIDE`、`SMALL_TARGET_AREA_THRESH` 控制小目标检测与标注；可选多尺度精检（config 中 `MULTI_SCALE_ENABLED`）。 |
| **功耗与续航** | **降分辨率**、**降帧率**（`TARGET_FPS`）、**跳帧**（`PROCESS_EVERY_N_FRAMES`）、**空闲降频**（`IDLE_SLEEP_FRAMES`）；无屏时加 `--no-show` 减少 GPU/显示开销。 |

## 环境与依赖

- 香橙派（Orange Pi）或树莓派等 Linux 板子
- Python 3.7+
- 依赖见 `requirements.txt`：

```bash
pip install -r requirements.txt
```

- 若使用香橙派原厂摄像头或 USB 摄像头，需保证 `v4l2` 可用；必要时在 `config.py` 中修改 `CAM_INDEX`。

## 配置说明（`config.py`）

- **摄像头与分辨率**：`PROC_WIDTH`、`PROC_HEIGHT` 影响速度与远距离小目标效果。
- **帧率与功耗**：`TARGET_FPS`、`PROCESS_EVERY_N_FRAMES`、`IDLE_SLEEP_FRAMES`。
- **背景建模**：`BG_SUBTRACTOR`（MOG2/KNN/GMG）、`MOG2_VAR_THRESHOLD`、`BG_LEARNING_RATE`。
- **形态学**：`MORPH_OPEN_SIZE`、`MORPH_CLOSE_SIZE`，用于去噪与填洞。
- **目标过滤**：`MIN_FOREGROUND_AREA`、`MAX_SINGLE_TARGET_AREA`、`MIN_ASPECT_RATIO`、`MAX_ASPECT_RATIO`、`MIN_EXTENT`/`MAX_EXTENT`、`MIN_BBOX_SIDE`。

按实际场地（杂草多少、目标大小、距离）调节以上参数。

## 运行方式

### 实时摄像头（香橙派/本机）

```bash
# 默认摄像头、默认分辨率、带显示
python main.py

# 指定摄像头、分辨率，不显示窗口（SSH/无屏低功耗）
python main.py --cam 0 --width 640 --height 480 --no-show

# 只处理 500 帧（测试）
python main.py --max-frames 500
```

### 纯软件模拟（无需摄像头与硬件）

```bash
# 合成场景：程序内生成“野外”背景 + 运动椭圆目标，直接验证算法
python main.py --simulate

# 合成场景，限制 300 帧、每帧延迟 50ms
python main.py --simulate --max-frames 300 --delay 50

# 使用本地视频文件代替摄像头（如录好的巡查视频）
python main.py --video path/to/your_video.mp4

# 视频文件 + 限制帧数
python main.py --video test.mp4 --max-frames 500 --no-show
```

## 项目结构

```
2025H/
├── config.py          # 分辨率、背景建模、形态学、目标过滤、功耗相关参数
├── perception.py      # 主感知管道：采集 → 背景减除 → 形态学 → 轮廓过滤 → 输出
├── main.py            # 香橙派/模拟 主入口，支持 --video / --simulate 纯软件模拟
├── simulate.py        # 纯软件模拟：合成场景生成器 + 视频文件逐帧
├── vision/
│   ├── __init__.py
│   ├── background.py  # MOG2/KNN 背景减除 + 形态学
│   └── detector.py    # 轮廓检测与几何过滤（面积、宽高比、extent、小目标标记）
├── requirements.txt
└── README.md
```

## 输出与扩展

- 当前输出：每帧得到**目标框列表** `[( (x,y,w,h), area, is_small_target ), ...]`，可在 `main.py` 的 `on_detection` 中接入报警、录像、云台跟踪等。
- 若需更强“动物形态”区分，可在 `vision/detector.py` 后接 HOG+SVM 或轻量级 CNN 分类（需在嵌入式端做模型量化与推理优化以控制功耗）。
