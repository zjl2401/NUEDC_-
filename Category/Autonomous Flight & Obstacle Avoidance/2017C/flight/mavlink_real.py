# -*- coding: utf-8 -*-
"""
MAVLink 实机飞控（最小可用）：ArduPilot Copter GUIDED 下发送机体系速度指令。

依赖：pip install pymavlink

说明：
- 速度指令使用 SET_POSITION_TARGET_LOCAL_NED + MAV_FRAME_BODY_NED（前 x、右 y）。
- 起飞/降落使用 COMMAND_LONG（不同飞控固件参数可能略有差异，务必在安全环境调试）。
- PX4 需 OFFBOARD 模式，本实现以 ArduPilot 为主；若用 PX4 请自行改模式与消息序列。
"""
from __future__ import annotations

import sys
import os
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg

try:
    from pymavlink import mavutil
except ImportError as _e:  # pragma: no cover
    mavutil = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

from flight.interface import FlightInterface


def _require_pymavlink():
    if mavutil is None:
        raise RuntimeError(
            "实机模式需要安装 pymavlink：pip install pymavlink"
        ) from _IMPORT_ERR


def _velocity_type_mask() -> int:
    """仅使用 vx,vy,vz；忽略位置、加速度、偏航（不含 VX/VY/VZ ignore）。"""
    m = mavutil.mavlink
    bits = (
        "POSITION_TARGET_TYPEMASK_X_IGNORE",
        "POSITION_TARGET_TYPEMASK_Y_IGNORE",
        "POSITION_TARGET_TYPEMASK_Z_IGNORE",
        "POSITION_TARGET_TYPEMASK_AX_IGNORE",
        "POSITION_TARGET_TYPEMASK_AY_IGNORE",
        "POSITION_TARGET_TYPEMASK_AZ_IGNORE",
        "POSITION_TARGET_TYPEMASK_FORCE_SET",
        "POSITION_TARGET_TYPEMASK_YAW_IGNORE",
        "POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE",
    )
    mask = 0
    for n in bits:
        if hasattr(m, n):
            mask |= getattr(m, n)
    if mask == 0:
        return 3575
    return mask


class MavlinkFlightInterface(FlightInterface):
    """通过 MAVLink 连接飞控（串口或 UDP）。"""

    def __init__(self, connection_string: Optional[str] = None, baud: Optional[int] = None):
        _require_pymavlink()
        conn = (connection_string or "").strip()
        if not conn:
            conn = getattr(cfg, "FLIGHT_CONNECTION_STRING", "") or ""
        if not conn:
            conn = getattr(cfg, "FLIGHT_SERIAL_PORT", "/dev/ttyUSB0")
        baud = int(baud if baud is not None else getattr(cfg, "FLIGHT_BAUD", 57600))

        if conn.startswith("udp:") or conn.startswith("tcp:") or conn.startswith("udpin:") or conn.startswith("udpout:"):
            self.master = mavutil.mavlink_connection(conn)
        else:
            self.master = mavutil.mavlink_connection(conn, baud=baud)

        self.master.wait_heartbeat()
        self._armed = False
        self._type_mask = _velocity_type_mask()
        self._vmax = float(getattr(cfg, "FLIGHT_VEL_MAX_MS", 0.5))
        self._yaw_rate_scale = float(getattr(cfg, "FLIGHT_YAW_RATE_RADS", 0.3))

    def _ts_ms(self) -> int:
        return int(time.time() * 1000) % (2**32)

    def _set_mode_guided(self) -> None:
        """尝试切到 GUIDED（ArduPilot Copter）。"""
        mapping = self.master.mode_mapping()
        if not mapping or "GUIDED" not in mapping:
            print("[MAVLink] 未找到 GUIDED 模式映射，请手动切 GUIDED/OFFBOARD 后再运行。")
            return
        mode_id = mapping["GUIDED"]
        self.master.set_mode(mode_id)

    def arm_and_takeoff(self, height_m: float):
        self._set_mode_guided()
        time.sleep(0.2)
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1.0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        time.sleep(0.5)
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            float(height_m),
        )
        self._armed = True
        print(f"[MAVLink] 已发送解锁与起飞指令，目标高度约 {height_m:.2f} m（请目视确认）")

    def land(self):
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        time.sleep(0.5)
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0.0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        self._armed = False
        print("[MAVLink] 已发送降落/上锁指令")

    def set_velocity_body(self, forward: float, right: float, yaw_rate: float = 0.0):
        """forward/right 为归一化大致 [-1,1]，内部乘 FLIGHT_VEL_MAX_MS。"""
        vx = float(forward) * self._vmax
        vy = float(right) * self._vmax
        vz = 0.0
        yr = float(yaw_rate) * self._yaw_rate_scale
        self.master.mav.set_position_target_local_ned_send(
            self._ts_ms(),
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            self._type_mask,
            0.0,
            0.0,
            0.0,
            vx,
            vy,
            vz,
            0.0,
            0.0,
            0.0,
            0.0,
            yr,
        )

    def set_altitude_hold(self, alt_m: float):
        # 定高由飞控高度环完成；此处仅打印提示
        print(f"[MAVLink] 定高目标 {alt_m:.2f} m（请确认已起飞并在 ALT_HOLD/GUIDED）")

    def hover(self):
        self.set_velocity_body(0.0, 0.0, 0.0)

    def is_armed(self):
        return self._armed

    def close(self):
        try:
            self.master.close()
        except Exception:
            pass
