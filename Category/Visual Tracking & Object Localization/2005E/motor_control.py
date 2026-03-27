# -*- coding: utf-8 -*-
"""
2005 E题 - 电机控制接口

- simulate=True：仅更新内部状态，用于纯软件仿真
- simulate=False：通过 GPIO 驱动两路步进电机（STEP/DIR/EN）控制拉线长度

说明：
    这里实现的是“最小可用的真机驱动骨架”，用于把仿真链路落到硬件上。
    实战中通常还需要：
      - 回零/限位开关标定初始长度
      - 梯形/S 曲线加减速，避免丢步
      - 线轮半径/层叠误差补偿
"""
import time
from typing import Tuple, Optional

# 尝试导入 GPIO（香橙派/树莓派常用 RPi.GPIO 或 orangepi.GPIO）
HAS_GPIO = False
GPIO = None
try:
    import RPi.GPIO as GPIO  # type: ignore

    GPIO.setmode(GPIO.BOARD)
    HAS_GPIO = True
except (ImportError, RuntimeError):
    try:
        import orangepi.GPIO as GPIO  # type: ignore

        GPIO.setmode(GPIO.BOARD)
        HAS_GPIO = True
    except (ImportError, RuntimeError):
        HAS_GPIO = False


class StepperGPIO:
    """
    单路步进电机 STEP/DIR/EN 驱动（软件脉冲）。

    - step_pin/dir_pin/en_pin 使用 BOARD 编号
    - dir_positive=True 表示 steps>0 时 DIR=HIGH
    """

    def __init__(
        self,
        step_pin: int,
        dir_pin: int,
        en_pin: Optional[int] = None,
        dir_positive: bool = True,
        step_high_time_s: float = 0.0004,
    ):
        if not HAS_GPIO or GPIO is None:
            raise RuntimeError("未检测到 GPIO，请在香橙派/树莓派上安装 RPi.GPIO 或 orangepi.GPIO")
        self.step_pin = step_pin
        self.dir_pin = dir_pin
        self.en_pin = en_pin
        self.dir_positive = dir_positive
        self.step_high_time_s = step_high_time_s

        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        if self.en_pin is not None:
            GPIO.setup(self.en_pin, GPIO.OUT)
            GPIO.output(self.en_pin, GPIO.LOW)  # 常见驱动 EN 低有效；若不符请改

        GPIO.output(self.step_pin, GPIO.LOW)

    def set_enabled(self, enabled: bool) -> None:
        if self.en_pin is None:
            return
        # 默认按 EN 低有效设计：enabled=True -> LOW
        GPIO.output(self.en_pin, GPIO.LOW if enabled else GPIO.HIGH)

    def set_direction_for_steps(self, steps: int) -> None:
        forward = steps >= 0
        level = GPIO.HIGH if (forward == self.dir_positive) else GPIO.LOW
        GPIO.output(self.dir_pin, level)

    def pulse(self, low_time_s: float) -> None:
        GPIO.output(self.step_pin, GPIO.HIGH)
        time.sleep(self.step_high_time_s)
        GPIO.output(self.step_pin, GPIO.LOW)
        time.sleep(max(0.0, low_time_s))


class MotorController:
    """双电机拉线控制：给定目标拉线长度 (L1, L2)，驱动左右电机收放线。"""

    def __init__(
        self,
        simulate: bool = True,
        steps_per_cm: float = 50.0,  # 每厘米线长对应的步数（与机械结构相关）
        max_speed_steps_per_sec: float = 200.0,
        # 真机引脚（BOARD 编号），不使用真机时可忽略
        left_step_pin: int = 31,
        left_dir_pin: int = 33,
        left_en_pin: Optional[int] = None,
        right_step_pin: int = 35,
        right_dir_pin: int = 37,
        right_en_pin: Optional[int] = None,
        left_dir_positive: bool = True,
        right_dir_positive: bool = True,
    ):
        self.simulate = simulate
        self.steps_per_cm = steps_per_cm
        self.max_speed = max_speed_steps_per_sec
        # 当前拉线长度 (cm)
        self._L1 = 0.0
        self._L2 = 0.0
        self._initialized = False
        self._left: Optional[StepperGPIO] = None
        self._right: Optional[StepperGPIO] = None

        if not self.simulate:
            self._left = StepperGPIO(
                step_pin=left_step_pin,
                dir_pin=left_dir_pin,
                en_pin=left_en_pin,
                dir_positive=left_dir_positive,
            )
            self._right = StepperGPIO(
                step_pin=right_step_pin,
                dir_pin=right_dir_pin,
                en_pin=right_en_pin,
                dir_positive=right_dir_positive,
            )
            self._left.set_enabled(True)
            self._right.set_enabled(True)

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
        if self._left is None or self._right is None:
            raise RuntimeError("真机模式未初始化步进驱动，请检查 GPIO 初始化是否成功")

        # 步数 = (目标长度 - 当前长度) * steps_per_cm
        steps1 = int(round((L1 - self._L1) * self.steps_per_cm))
        steps2 = int(round((L2 - self._L2) * self.steps_per_cm))
        if steps1 == 0 and steps2 == 0:
            self._L1 = L1
            self._L2 = L2
            return

        self._left.set_direction_for_steps(steps1)
        self._right.set_direction_for_steps(steps2)

        n1 = abs(steps1)
        n2 = abs(steps2)
        total = max(n1, n2)

        # 简单“同步步进”：用 Bresenham 思想按比例插步，尽量让两侧同时到位
        step_period = 1.0 / max(1.0, float(self.max_speed))
        low_time = max(0.0, step_period - self._left.step_high_time_s)

        err1 = 0
        err2 = 0
        for _ in range(total):
            err1 += n1
            err2 += n2
            if err1 >= total and n1 > 0:
                self._left.pulse(low_time_s=low_time)
                err1 -= total
            if err2 >= total and n2 > 0:
                self._right.pulse(low_time_s=low_time)
                err2 -= total

        # 到位后更新状态（以命令值为准）
        self._L1 = L1
        self._L2 = L2

    def close(self) -> None:
        """释放 GPIO 等资源。"""
        if not self.simulate and HAS_GPIO and GPIO is not None:
            try:
                GPIO.cleanup()
            except Exception:
                return


def create_motor_controller(simulate: bool = True, **kwargs) -> MotorController:
    """工厂：创建模拟或真实电机控制器。"""
    return MotorController(simulate=simulate, **kwargs)
