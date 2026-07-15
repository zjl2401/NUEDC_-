# 2025E · 香橙派 5 Pro 接线与标定指南

面向：**Orange Pi 5 Pro + USB 摄像头、无显示器**（也可接 HDMI）。

---

## 〇、你的情况：USB 摄像头 + 无显示器

板子只接：**Type-C 电源 + 网线/WiFi + USB 摄像头**，用电脑 **SSH** 操作。

### 最短步骤

1. 刷 Ubuntu/Debian，连上同一局域网  
2. Windows：`ssh orangepi@板子IP`（常见账号密码：`orangepi` / `orangepi`）  
3. 板子上执行：

```bash
ls /dev/video*
cd ~/NUEDC/Category/Visual\ Tracking\ \&\ Object\ Localization/2025E
pip3 install -r requirements.txt

python3 main.py --mode dynamic --real --dummy --no-show --no-perspective \
  --camera-index 0 --max-frames 100 --save-preview /tmp/preview.jpg
```

预览图拷回电脑看：

```powershell
scp orangepi@板子IP:/tmp/preview.jpg .
```

退出：`Ctrl+C`，或靠 `--max-frames` 自动结束。

> **必须加 `--no-show`**，否则无显示器会因 `imshow` 报错/卡住。  
> 建议同时加 **`--no-perspective`**（没法按 C 做黑框标定）。

---

## 一、Linux 基础

### 刷系统

1. http://www.orangepi.org/ → Orange Pi 5 Pro 镜像  
2. Etcher/Rufus 写 TF 卡  
3. **Type-C 5V/5A** 供电  
4. 无显示器：接网线 → 路由器查 IP → SSH

### SSH

```powershell
ssh orangepi@192.168.x.x
```

### 拷项目

```powershell
scp -r "C:\Users\36255\Desktop\GIT\NUEDC" orangepi@192.168.x.x:~/
```

### 常用命令

```bash
hostname -I
sudo apt update
ls /dev/video*
python3 --version
```

接舵机再装 GPIO：

```bash
sudo pip3 install RPi.GPIO
# 或 sudo pip3 install OPi.GPIO
```

---

## 二、接线

### USB 摄像头

直接插板子 USB-A 口。

### 舵机云台（以后有再接）

| 用途 | BOARD 脚 |
|------|----------|
| Pan 信号 | **16** |
| Tilt 信号 | **18** |
| GND | **6**（与舵机电源共地） |
| 舵机 VCC | **独立 5V≥2A** |

```text
独立5V+ ──┬─ Pan/Tilt VCC
独立GND ──┬─ Pan/Tilt GND ── 香橙派脚6
脚16 ────── Pan 信号
脚18 ────── Tilt 信号
```

无头 + 真舵机：

```bash
python3 main.py --mode dynamic --real --no-show --no-perspective \
  --camera-index 0 --pan-pin 16 --tilt-pin 18
```

先验证时加 `--dummy`。

---

## 三、无头标定思路

1. `--save-preview` + `scp` 确认拍到红色目标  
2. 看终端 `pan/tilt`：目标偏右 pan 应增大，否则改 `PIXEL_TO_PAN` 正负  
3. 方向对了再去掉 `--dummy`

---

## 四、常见问题

| 现象 | 处理 |
|------|------|
| 反复重启 | 换 5V/5A 电源 |
| SSH 连不上 | 查 IP、同网段 |
| 无 `/dev/video*` | 重插 USB 摄像头，试 `--camera-index 1` |
| display 相关报错 | 加 `--no-show` |
| 预览全黑 | 摘镜头盖、加灯、调 `EXPOSURE` |
