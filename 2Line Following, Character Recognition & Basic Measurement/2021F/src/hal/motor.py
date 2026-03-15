"""
电机控制（香橙派）：双轮差速。支持 GPIO 软件 PWM 或外接电机驱动板（串口/I2C）。
支持仿真注入：set_simulator(sim) 后速度写入仿真器。
"""
from __future__ import annotations

from typing import Tuple, Any

_use_mock = True
_left = 0.0
_right = 0.0
_simulator: Any = None


def set_simulator(sim: Any) -> None:
    """注入仿真器后，set_wheel_speeds 会写入仿真器。"""
    global _simulator
    _simulator = sim


def set_mock_mode(mock: bool) -> None:
    """True=不驱动真实电机，仅更新内部速度（便于在 PC 上调试）。"""
    global _use_mock
    _use_mock = mock


def set_wheel_speeds(left: float, right: float) -> None:
    """
    设置左右轮目标速度，范围建议 [-1, 1]。
    香橙派实现示例（需根据实际驱动板改）：
      - 使用 GPIO PWM 脚：左轮 PWM 占空比 = f(left)，方向脚 = sign(left)
      - 或通过串口发送指令到 L298N/DRV8833 等驱动板
    """
    global _left, _right
    _left = max(-1.0, min(1.0, left))
    _right = max(-1.0, min(1.0, right))
    if _simulator is not None:
        _simulator.set_wheel_speeds(_left, _right)
        return
    if _use_mock:
        return
    # 实际硬件：例如
    # import OPi.GPIO as GPIO
    # pwm_left.ChangeDutyCycle(int((left + 1) * 50))
    # ...
    pass


def get_wheel_speeds() -> Tuple[float, float]:
    """返回当前设置的速度（mock 或从编码器反推）。"""
    return _left, _right


def get_encoder_ticks() -> Tuple[int, int]:
    """若接有编码器，从硬件读取 (左轮计数, 右轮计数)。"""
    return 0, 0


def reset_encoders() -> None:
    """清零编码器。"""
    pass


def stop_motors() -> None:
    """紧急停止：两轮速度置 0 并下发。"""
    set_wheel_speeds(0.0, 0.0)
