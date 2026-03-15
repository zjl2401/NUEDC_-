"""
加载 config/default.yaml，供主程序与各模块使用。
香橙派上可将配置放在 /home/.../2021F/config/ 或当前工作目录。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

# 项目根目录（2021F）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"

_config: dict[str, Any] = {}


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    global _config
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        _config = _default_config()
        return _config
    if yaml is None:
        _config = _default_config()
        return _config
    with open(p, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f) or {}
    return _config


def get_config() -> dict[str, Any]:
    if not _config:
        load_config()
    return _config


def _default_config() -> dict[str, Any]:
    return {
        "line_follow": {"kp": 0.5, "ki": 0.0, "kd": 0.1, "base_speed": 0.5, "max_diff": 0.4},
        "docking": {"slow_speed": 0.2, "min_speed": 0.05, "stop_threshold_cm": 2.0},
        "marker": {
            "red_hsv_low1": [0, 100, 100],
            "red_hsv_high1": [10, 255, 255],
            "red_hsv_low2": [170, 100, 100],
            "red_hsv_high2": [180, 255, 255],
            "min_area": 500,
        },
        "room_number": {"roi": [0.3, 0.2, 0.4, 0.3]},
        "junction": {"black_threshold": 3},
        "camera": {"device": 0, "width": 640, "height": 480},
        "gpio": {
            "line_sensor_pins": [7, 11, 13, 15, 19],
            "motor_left_pwm": 12,
            "motor_left_dir": 16,
            "motor_right_pwm": 18,
            "motor_right_dir": 22,
        },
    }
