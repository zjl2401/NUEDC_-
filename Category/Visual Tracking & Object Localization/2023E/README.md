# 激光追踪系统（OpenCV + 香橙派）

二自由度云台激光笔：摄像头识别红/绿激光点，控制绿点追踪红点或在屏幕上画圈。

## 功能

- **复位对齐**：绿点自动对准屏幕中心
- **定点追踪**：识别红色目标点，绿点叠加上去
- **动态追踪**：红点移动时绿点紧跟（带线性预测）
- **自主画圈**：沿屏幕中心圆周轨迹扫描

## 环境

- Python 3.7+
- OpenCV、NumPy
- 香橙派（Armbian / 官方镜像）：安装 `RPi.GPIO` 或 `OrangePi.GPIO` 驱动舵机

## 安装

```bash
cd 2023E运动目标控制与自动追踪系统
pip install -r requirements.txt
# 香橙派上：
# sudo pip3 install RPi.GPIO  或  sudo pip3 install OrangePi.GPIO
```

## 使用

```bash
# 动态追踪（默认）
python main.py --mode dynamic

# 定点追踪
python main.py --mode track

# 复位：绿点对准屏幕中心
python main.py --mode reset

# 自主画圈
python main.py --mode circle

# 不接舵机时用模拟（仅打印角度）
python main.py --mode track --dummy

# 纯软件模拟：无需摄像头和舵机，在窗口里看红点动、绿点追的效果
python main.py --mode dynamic --simulate
python main.py --mode reset --simulate
python main.py --mode circle --simulate

# 不做透视校正（摄像头正对屏幕时可用）
python main.py --mode track --no-perspective
```

## 配置

编辑 `config.py`：

- **摄像头**：`CAMERA_INDEX`、分辨率、`EXPOSURE`（降低曝光避免激光过曝）
- **HSV**：红/绿激光的 HSV 范围，室内可微调
- **死区**：`DEADZONE_PX` 减小云台抖动
- **PID**：`PID_KP/KI/KD` 调追踪响应
- **舵机**：`PAN_CENTER/TILT_CENTER`、`SCREEN_TO_PAN/TILT` 需标定
- **香橙派引脚**：`hardware.create_servo(pan_pin=7, tilt_pin=11)` 按板子引脚图修改

## 标定建议

1. 先降低摄像头曝光，使背景偏黑、激光点清晰。
2. 复位模式下调绿点到屏幕中心，记下此时舵机角度，写入 `PAN_CENTER`、`TILT_CENTER`。
3. 再移动绿点到屏幕四角，根据像素差与角度差得到 `SCREEN_TO_PAN`、`SCREEN_TO_TILT`。

## 项目结构

```
config.py    # 参数
vision.py    # HSV 双色、透视校正、质心
control.py   # 增量 PID、死区、预测
hardware.py  # 舵机（Dummy / 香橙派 GPIO PWM）
main.py      # 主流程与四种模式
```

## 注意事项

- 透视校正需画面中有黑框四边形，否则用 `--no-perspective` 或先标定四个角点。
- 绿点追上红点后可能颜色混合，可依赖质心或面积过滤区分。
- 现场光照强时可在镜头加偏振片或收紧 HSV 与面积过滤。
