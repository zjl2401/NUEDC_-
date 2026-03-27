## 2005E 悬挂运动控制系统（仿真/真机）

本目录实现双拉线悬挂系统的 **运动学（正/逆解）+ 轨迹插补 + 电机控制**，并提供 OpenCV 可视化仿真。

### 一、文件说明

- `kinematics.py`：双拉线正/逆运动学、工作空间、板面/电机常量
- `trajectory.py`：直线/圆/正方形/任意路径插补，轨迹校验，点列→(L1,L2)
- `motor_control.py`：电机控制（simulate/真机 GPIO 步进）
- `simulator.py`：仿真与演示入口（OpenCV 画布显示）
- `算法实现与知识点总结.md`：算法位置与知识点总结

### 二、软件仿真怎么看

在本目录下运行：

```bash
python simulator.py
```

- 交互键位：`1/2/3/4` 执行不同轨迹，`C` 清空画布，`Q` 退出（窗口底部也会提示）。

自动演示：

```bash
python simulator.py --demo
python simulator.py --demo --animate
```

### 三、真机怎么接（步进电机 STEP/DIR）

`motor_control.py` 已补了 **GPIO 步进脉冲驱动骨架**（`simulate=False` 时启用），默认按以下思路工作：

- 输入：目标拉线长度 `target_L1/target_L2`（cm）
- 中间：长度差 → 步数（`steps_per_cm`）→ 同步插步发脉冲
- 输出：两路步进电机收/放线，使拉线长度变化到目标值

#### 1）需要你确认/标定的参数

- **机械标定**
  - `steps_per_cm`：每厘米对应步数（与细分、线轮半径相关）
  - `max_speed_steps_per_sec`：最大步频（过高可能丢步）
- **方向**
  - `left_dir_positive` / `right_dir_positive`：正步数对应的 DIR 电平（方向不对就改这里）
- **引脚（BOARD 编号）**
  - 左电机：`left_step_pin/left_dir_pin/left_en_pin`
  - 右电机：`right_step_pin/right_dir_pin/right_en_pin`

> 不同香橙派/树莓派引脚定义不同，请以你板子的 **BOARD 引脚图**为准。

#### 2）真机运行建议

你可以在 `simulator.py` 里用 `--no-sim` 走真机（注意：仍会打开可视化窗口，但电机将真实动作）：

```bash
python simulator.py --no-sim
```

### 四、实机硬件清单

- Orange Pi / Raspberry Pi（1 路上位机控制）
- 步进电机 x2（左右卷线）
- 步进驱动器 x2（支持 STEP/DIR/EN，例如 A4988/TMC 系）
- 稳定电源（按电机规格选型，建议电机电源与主控分供）
- 悬挂线轮与拉线机构（左右对称安装）
- 连接线、限位开关（推荐）

### 五、实机接线与配置操作（推荐顺序）

1. **接线**
   - 主控 GPIO -> 驱动器 `STEP/DIR/EN`；
   - 驱动器 -> 步进电机；
   - 主控 GND 与驱动器 GND 共地；
   - 若使用 EN，引脚可在命令行传入 `--left-en-pin/--right-en-pin`。
2. **先用默认参数点动验证**
   - `python simulator.py --no-sim --demo --animate`
   - 观察两侧电机是否都转动。
3. **方向修正**
   - 方向反了就加 `--invert-left-dir` 或 `--invert-right-dir`。
4. **步距标定**
   - 先测电机转固定步数对应拉线长度，换算 `steps_per_cm`；
   - 运行时传参：`--steps-per-cm 58.3`（示例）。
5. **速度调参**
   - 从低速开始（如 `--max-speed 120`），逐步提高，避免丢步。
6. **引脚固化**
   - 按你的板子 BOARD 引脚图，把 STEP/DIR/EN 配置为固定值后再跑完整轨迹。

### 六、实机命令示例

```bash
# 1) 最小实机验证（默认引脚）
python simulator.py --no-sim --demo --animate

# 2) 自定义引脚 + 机械参数
python simulator.py --no-sim --steps-per-cm 58.3 --max-speed 180 \
  --left-step-pin 31 --left-dir-pin 33 --right-step-pin 35 --right-dir-pin 37

# 3) 一侧方向反转（常见于左右电机安装镜像）
python simulator.py --no-sim --invert-right-dir
```

### 七、仍建议你后续补的“工程化能力”

- 回零/限位开关：上电标定初始长度，否则 L1/L2 不可信
- 加减速规划：梯形/S 曲线，减少丢步
- 放线张力/线轮层叠误差补偿：提升长期精度与稳定性

