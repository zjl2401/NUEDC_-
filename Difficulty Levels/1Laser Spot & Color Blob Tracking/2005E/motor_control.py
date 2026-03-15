# -*- coding: utf-8 -*-
"""
2005 E题 - 电机控制接口
- 模拟模式：仅更新内部状态，用于纯软件仿真
- 香橙派模式：通过 GPIO + 步进/直流电机驱动控制拉线长度（需在 Orange Pi 上运行）
"""
import time
from typing import Tuple, Optional

# 尝试导入 GPIO（香橙派用 orangepi 或 RPi.GPIO 兼容层）
try:
    import gpiod  # 香橙派 5 等新板常用 libgpiod
    HAS_GPIO = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        HAS_GPIO = True
    except ImportError:
        HAS_GPIO = False


class MotorController:
    """双电机拉线控制：给定目标拉线长度 (L1, L2)，驱动左右电机收放线。"""

    def __init__(
        self,
        simulate: bool = True,
        steps_per_cm: float = 50.0,  # 每厘米线长对应的步数（与机械结构相关）
        max_speed_steps_per_sec: float = 200.0,
    ):
        self.simulate = simulate
        self.steps_per_cm = steps_per_cm
        self.max_speed = max_speed_steps_per_sec
        # 当前拉线长度 (cm)
        self._L1 = 0.0
        self._L2 = 0.0
        self._initialized = False

    def set_initial_lengths(self, L1: float, L2: float) -> None:
        """设置当前拉线长度（如从起始点标定）。"""
        self._L1 = L1
        self._L2 = L2
        self._initialized = True

    def get_current_lengths(self) -> Tuple[float, float]:
        """返回当前拉线长度 (L1, L2)。"""
        return (self._L1, self._L2)

    def move_to_lengths(
        self,
        target_L1: float,
        target_L2: float,
        block: bool = True,
        duration_sec: Optional[float] = None,
    ) -> None:
        """
        将拉线从当前长度移动到目标长度。
        - simulate=True: 直接更新内部状态，可选 duration_sec 模拟运动时间
        - simulate=False: 驱动真实电机（步进/直流），block 表示是否阻塞直到到位
        """
        if self.simulate:
            if duration_sec and duration_sec > 0:
                time.sleep(duration_sec)
            self._L1 = target_L1
            self._L2 = target_L2
            return
        # 真实硬件：根据 target 与当前值差计算步数，再发脉冲
        self._drive_motors(target_L1, target_L2, block)

    def _drive_motors(self, L1: float, L2: float, block: bool) -> None:
        """实际驱动电机（在非模拟模式下由子类或平台实现）。"""
        # 步数 = (目标长度 - 当前长度) * steps_per_cm
        steps1 = int((L1 - self._L1) * self.steps_per_cm)
        steps2 = int((L2 - self._L2) * self.steps_per_cm)
        # 这里可接入 GPIO：根据 steps1/steps2 正负控制方向，按步数发脉冲
        # 示例占位：仅更新状态，实际需接 L298/步进驱动
        self._L1 = L1
        self._L2 = L2
        if block and (steps1 != 0 or steps2 != 0):
            step_time = 1.0 / self.max_speed
            total_steps = max(abs(steps1), abs(steps2))
            time.sleep(total_steps * step_time)

    def close(self) -> None:
        """释放 GPIO 等资源。"""
        pass


def create_motor_controller(simulate: bool = True, **kwargs) -> MotorController:
    """工厂：创建模拟或真实电机控制器。"""
    return MotorController(simulate=simulate, **kwargs)
