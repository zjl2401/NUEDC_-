"""
精准停靠：到达目标房号且检测到停止线/色块后，在规定区域内平稳停车，误差厘米级。
"""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class DockingState(Enum):
    NOT_DOCKING = 0
    SLOW_DOWN = 1
    FINAL_APPROACH = 2
    STOPPED = 3


def should_start_docking(
    room_reached: bool,
    stop_marker_detected: bool,
    target_room: int,
    current_room: int,
) -> bool:
    """
    判断是否应进入停靠流程。
    :param room_reached: 当前识别房号是否等于目标
    :param stop_marker_detected: 是否检测到红线/色块
    :param target_room: 目标房号
    :param current_room: 当前识别房号
    """
    return room_reached and stop_marker_detected and (current_room == target_room)


def docking_speed(
    state: DockingState,
    distance_to_stop: float | None,
    base_speed: float,
    slow_speed: float = 0.2,
    min_speed: float = 0.05,
) -> float:
    """
    停靠阶段速度曲线：减速 → 缓行 → 停止。
    :param distance_to_stop: 距停止线/目标位置距离（若无可用传感器则为 None，按时间/编码器估算）
    """
    if state == DockingState.NOT_DOCKING:
        return base_speed
    if state == DockingState.SLOW_DOWN:
        return slow_speed
    if state == DockingState.FINAL_APPROACH:
        if distance_to_stop is not None and distance_to_stop < 0.05:
            return 0.0
        return min_speed
    return 0.0


def update_docking_state(
    state: DockingState,
    stop_marker_detected: bool,
    speed: float,
    encoder_dist: float,
    stop_threshold: float = 0.02,
) -> DockingState:
    """
    根据传感器与编码器更新停靠状态机。
    """
    if state == DockingState.STOPPED:
        return state
    if not stop_marker_detected and state == DockingState.NOT_DOCKING:
        return state
    if state == DockingState.NOT_DOCKING:
        return DockingState.SLOW_DOWN
    if state == DockingState.SLOW_DOWN:
        return DockingState.FINAL_APPROACH
    if state == DockingState.FINAL_APPROACH and speed <= 0 and encoder_dist < stop_threshold:
        return DockingState.STOPPED
    return state
