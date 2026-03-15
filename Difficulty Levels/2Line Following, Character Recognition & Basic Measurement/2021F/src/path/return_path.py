"""
原路返回：送药完成后按反向序列执行转向。
"""
from __future__ import annotations

from typing import List

from .recorder import TurnAction, get_return_sequence


def consume_next_return_action(
    return_sequence: List[TurnAction],
) -> TurnAction | None:
    """
    按顺序取下一个“返回动作”。
    :return: 下一个转向动作，若已全部执行完则返回 None
    """
    if not return_sequence:
        return None
    return return_sequence.pop(0)
