# -*- coding: utf-8 -*-
"""舵机控制：香橙派 GPIO/PWM 接口（二自由度云台）"""

import time
import config as cfg

# 香橙派上可选用：OrangePi.GPIO / RPi.GPIO(部分镜像) / lgpio
# 无 GPIO 时用 DummyServo（PC 调试）
HAS_GPIO = False
GPIO = None
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    HAS_GPIO = True
except (ImportError, RuntimeError):
    try:
        import orangepi.GPIO as GPIO  # 香橙派官方
        GPIO.setmode(GPIO.BOARD)
        HAS_GPIO = True
    except (ImportError, RuntimeError):
        pass


def _angle_to_pulse_us(angle: float) -> int:
    """角度 [0,180] 转舵机脉宽 (us)。"""
    angle = max(0, min(180, angle))
    return int(cfg.SERVO_MIN_US + (cfg.SERVO_MAX_US - cfg.SERVO_MIN_US) * angle / 180.0)


class DummyServo:
    """无硬件时仅打印目标角度，便于在 PC 上跑通流程。"""

    def set_pan_tilt(self, pan_angle: float, tilt_angle: float) -> None:
        pan_angle = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan_angle))
        tilt_angle = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt_angle))
        print(f"[DummyServo] pan={pan_angle:.1f} tilt={tilt_angle:.1f}")

    def set_center(self) -> None:
        self.set_pan_tilt(cfg.PAN_CENTER, cfg.TILT_CENTER)


class SoftPWMServo:
    """用 GPIO 软件 PWM 驱动舵机（香橙派 + RPi.GPIO / OrangePi.GPIO）。"""

    def __init__(self, pan_pin: int, tilt_pin: int, pwm_freq: int = 50):
        """
        pan_pin, tilt_pin: BOARD 编号，参考香橙派引脚图。
        例如 Orange Pi Zero 2: 舵机信号接 7(GPIO4), 11(GPIO17)。
        """
        if not HAS_GPIO or GPIO is None:
            raise RuntimeError("未检测到 GPIO，请安装 RPi.GPIO 或 orangepi.GPIO")
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self.freq = pwm_freq
        self._pan_angle = cfg.PAN_CENTER
        self._tilt_angle = cfg.TILT_CENTER
        GPIO.setup(pan_pin, GPIO.OUT)
        GPIO.setup(tilt_pin, GPIO.OUT)
        self._pwm_pan = GPIO.PWM(pan_pin, pwm_freq)
        self._pwm_tilt = GPIO.PWM(tilt_pin, pwm_freq)
        self._pwm_pan.start(0)
        self._pwm_tilt.start(0)

    def _duty_from_angle(self, angle: float) -> float:
        """角度转占空比 (0~100)，50Hz 下约 2.5%~12.5% 对应 0.5ms~2.5ms。"""
        pulse_us = _angle_to_pulse_us(angle)
        period_us = 1_000_000 // self.freq
        return 100.0 * pulse_us / period_us

    def set_pan_tilt(self, pan_angle: float, tilt_angle: float) -> None:
        pan_angle = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan_angle))
        tilt_angle = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt_angle))
        self._pan_angle = pan_angle
        self._tilt_angle = tilt_angle
        self._pwm_pan.ChangeDutyCycle(self._duty_from_angle(pan_angle))
        self._pwm_tilt.ChangeDutyCycle(self._duty_from_angle(tilt_angle))

    def set_center(self) -> None:
        self.set_pan_tilt(cfg.PAN_CENTER, cfg.TILT_CENTER)


def create_servo(use_dummy: bool = None, pan_pin: int = 7, tilt_pin: int = 11):
    """工厂：无 GPIO 或 use_dummy=True 返回 DummyServo，否则返回 SoftPWMServo。"""
    if use_dummy is True or (use_dummy is None and not HAS_GPIO):
        return DummyServo()
    return SoftPWMServo(pan_pin=pan_pin, tilt_pin=tilt_pin, pwm_freq=50)
