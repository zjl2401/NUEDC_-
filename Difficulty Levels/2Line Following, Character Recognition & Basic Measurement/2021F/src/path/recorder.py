"""
路径记录：记录去程的转向序列，供原路返回使用。
"""
from __future__ import annotations

from enum import Enum
from typing import List


class TurnAction(Enum):
    STRAIGHT = 0
    LEFT = 1
    RIGHT = 2


# 返回时：左 <-> 右 对调，直行不变
RETURN_ACTION_MAP = {
    TurnAction.STRAIGHT: TurnAction.STRAIGHT,
    TurnAction.LEFT: TurnAction.RIGHT,
    TurnAction.RIGHT: TurnAction.LEFT,
}


def record_turn(path_stack: List[TurnAction], action: TurnAction) -> None:
    """在路口执行转向时，将动作压入 path_stack。"""
    path_stack.append(action)


def get_return_sequence(path_stack: List[TurnAction]) -> List[TurnAction]:
    """
    得到原路返回的转向序列：顺序反转，且左/右对调。
    """
    return [RETURN_ACTION_MAP[a] for a in reversed(path_stack)]


def clear_path(path_stack: List[TurnAction]) -> None:
    """清空路径记录（新一轮任务）。"""
    path_stack.clear()
