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

### 四、仍建议你后续补的“工程化能力”

- 回零/限位开关：上电标定初始长度，否则 L1/L2 不可信
- 加减速规划：梯形/S 曲线，减少丢步
- 放线张力/线轮层叠误差补偿：提升长期精度与稳定性

