"""
2025E 舵机控制（云台二自由度）：
- 有 GPIO 时用软件 PWM 驱动
- 无 GPIO 时用 DummyServo（PC 调试/不接真机）

引脚使用 BOARD 编号（与 2023E 保持一致）
"""

import config as cfg

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


def _angle_to_pulse_us(angle: float) -> int:
    angle = max(0.0, min(180.0, angle))
    return int(cfg.SERVO_MIN_US + (cfg.SERVO_MAX_US - cfg.SERVO_MIN_US) * angle / 180.0)


class DummyServo:
    def set_pan_tilt(self, pan_angle: float, tilt_angle: float) -> None:
        pan_angle = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan_angle))
        tilt_angle = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt_angle))
        print(f"[DummyServo] pan={pan_angle:.1f} tilt={tilt_angle:.1f}")

    def set_center(self) -> None:
        self.set_pan_tilt(cfg.PAN_CENTER, cfg.TILT_CENTER)

    def close(self) -> None:
        return


class SoftPWMServo:
    def __init__(self, pan_pin: int, tilt_pin: int, pwm_freq: int = 50):
        if not HAS_GPIO or GPIO is None:
            raise RuntimeError("未检测到 GPIO，请安装 RPi.GPIO 或 orangepi.GPIO")
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self.freq = pwm_freq
        GPIO.setup(pan_pin, GPIO.OUT)
        GPIO.setup(tilt_pin, GPIO.OUT)
        self._pwm_pan = GPIO.PWM(pan_pin, pwm_freq)
        self._pwm_tilt = GPIO.PWM(tilt_pin, pwm_freq)
        self._pwm_pan.start(0)
        self._pwm_tilt.start(0)

    def _duty_from_angle(self, angle: float) -> float:
        pulse_us = _angle_to_pulse_us(angle)
        period_us = 1_000_000 // self.freq
        return 100.0 * pulse_us / period_us

    def set_pan_tilt(self, pan_angle: float, tilt_angle: float) -> None:
        pan_angle = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan_angle))
        tilt_angle = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt_angle))
        self._pwm_pan.ChangeDutyCycle(self._duty_from_angle(pan_angle))
        self._pwm_tilt.ChangeDutyCycle(self._duty_from_angle(tilt_angle))

    def set_center(self) -> None:
        self.set_pan_tilt(cfg.PAN_CENTER, cfg.TILT_CENTER)

    def close(self) -> None:
        try:
            self._pwm_pan.stop()
            self._pwm_tilt.stop()
        finally:
            try:
                GPIO.cleanup()
            except Exception:
                return


def create_servo(use_dummy: bool = None, pan_pin: int = 7, tilt_pin: int = 11):
    if use_dummy is True or (use_dummy is None and not HAS_GPIO):
        return DummyServo()
    return SoftPWMServo(pan_pin=pan_pin, tilt_pin=tilt_pin, pwm_freq=50)

