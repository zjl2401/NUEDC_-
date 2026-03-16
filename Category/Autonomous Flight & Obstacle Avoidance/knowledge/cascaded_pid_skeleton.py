"""
简化版级联 PID 控制骨架 (位置环 -> 速度环)

适用:
    - 电赛中需要从“期望位置”得到“期望速度/推力”的场景,
      例如无人机/小车沿规划路径行驶, 做一个 1D 或 2D 的简化演示。

输入 (每个控制周期):
    - 当前测量位置 pos
    - 当前测量速度 vel
    - 期望位置 pos_ref

中间操作:
    1. 位置环 PID: 根据位置误差 e_pos = pos_ref - pos, 输出期望速度 vel_ref
    2. 速度环 PID: 根据速度误差 e_vel = vel_ref - vel, 输出控制量 u (可映射到推力/电机占空比)

输出:
    - 控制量 u
"""

from dataclasses import dataclass


@dataclass
class PID:
    kp: float
    ki: float
    kd: float
    integrator: float = 0.0
    prev_error: float = 0.0

    def step(self, error: float, dt: float) -> float:
        self.integrator += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        return self.kp * error + self.ki * self.integrator + self.kd * derivative


class CascadedController1D:
    def __init__(self):
        # 参数仅用于演示, 实际需调参
        self.pos_pid = PID(kp=1.0, ki=0.0, kd=0.1)
        self.vel_pid = PID(kp=0.5, ki=0.0, kd=0.05)

    def step(self, pos_ref: float, pos: float, vel: float, dt: float) -> float:
        # 外环: 位置控制, 输出期望速度
        e_pos = pos_ref - pos
        vel_ref = self.pos_pid.step(e_pos, dt)

        # 内环: 速度控制, 输出控制量 (推力/功率等)
        e_vel = vel_ref - vel
        u = self.vel_pid.step(e_vel, dt)
        return u


if __name__ == "__main__":
    # 简单仿真: 1D 质量点, 控制其位置从 0 移动到 10
    import numpy as np

    ctrl = CascadedController1D()
    dt = 0.02
    pos = 0.0
    vel = 0.0
    pos_ref = 10.0

    positions = []
    for i in range(500):
        u = ctrl.step(pos_ref, pos, vel, dt)
        # 简化动力学: a = u, v += a*dt, x += v*dt
        acc = u
        vel += acc * dt
        pos += vel * dt
        positions.append(pos)

    print("最终位置:", pos)

