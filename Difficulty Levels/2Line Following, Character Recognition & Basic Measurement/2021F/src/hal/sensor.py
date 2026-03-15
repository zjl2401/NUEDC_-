"""
巡线传感器、距离传感器（香橙派 GPIO 读取）。
多路红外巡线：黑线为低/高依硬件，此处约定 1=检测到黑线。
支持仿真注入：set_simulator(sim) 后由仿真器提供数据。
"""
from __future__ import annotations

from typing import List, Any

# 未接硬件时使用 mock：返回中间为黑，模拟直线
_use_mock = True
_mock_values = [0.0, 0.0, 1.0, 0.0, 0.0]
_simulator: Any = None


def set_simulator(sim: Any) -> None:
    """注入仿真器后，read_line_sensors 从仿真器读取。"""
    global _simulator
    _simulator = sim


def set_mock_mode(mock: bool, mock_values: List[float] | None = None) -> None:
    """True=不读 GPIO，返回 mock_values（默认中间为黑）。"""
    global _use_mock, _mock_values
    _use_mock = mock
    if mock_values is not None:
        _mock_values = list(mock_values)


def read_line_sensors() -> List[float]:
    """
    读取多路巡线传感器，从左到右。
    返回值：0=白/未检测到线，1 或较大值=黑线。香橙派上从 config 的 gpio.line_sensor_pins 读取。
    """
    if _simulator is not None:
        return _simulator.read_line_sensors()
    if _use_mock:
        return list(_mock_values)
    return list(_mock_values)


def read_distance_cm() -> float:
    """超声波/红外测距，单位 cm。无传感器时返回 999。"""
    if _use_mock:
        return 999.0
    return 999.0


def is_junction(sensor_values: List[float], threshold: int = 3) -> bool:
    """至少 threshold 路为黑视为路口（T 字等）。"""
    black_count = sum(1 for v in sensor_values if v > 0.5)
    return black_count >= threshold
