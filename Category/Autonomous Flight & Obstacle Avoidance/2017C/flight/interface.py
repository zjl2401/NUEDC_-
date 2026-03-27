# -*- coding: utf-8 -*-
"""飞控接口抽象。"""
from abc import ABC, abstractmethod
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


class FlightInterface(ABC):
    @abstractmethod
    def arm_and_takeoff(self, height_m: float): pass
    @abstractmethod
    def land(self): pass
    @abstractmethod
    def set_velocity_body(self, forward: float, right: float, yaw_rate: float = 0.0): pass
    @abstractmethod
    def set_altitude_hold(self, alt_m: float): pass
    @abstractmethod
    def hover(self): pass
    @abstractmethod
    def is_armed(self): pass


class SimulateFlightInterface(FlightInterface):
    def __init__(self):
        self._armed = False
    def arm_and_takeoff(self, height_m):
        print(f"[SIM] 起飞 -> {height_m}m")
        self._armed = True
        return True
    def land(self):
        print("[SIM] 降落")
        self._armed = False
        return True
    def set_velocity_body(self, forward, right, yaw_rate=0.0):
        print(f"[SIM] 速度 body: F={forward:.3f} R={right:.3f}")
    def set_altitude_hold(self, alt_m):
        print(f"[SIM] 定高 {alt_m}m")
    def hover(self):
        print("[SIM] 悬停")
    def is_armed(self):
        return self._armed


def create_flight_interface(use_simulate=None, connection_string=None, baud=None):
    """
    use_simulate=True：仅打印指令，不接飞控。
    use_simulate=False：通过 MAVLink 连接实机（需 pymavlink），见 config 与 README。
    """
    sim = use_simulate if use_simulate is not None else getattr(cfg, "FLIGHT_SIMULATE", True)
    if sim:
        return SimulateFlightInterface()
    from flight.mavlink_real import MavlinkFlightInterface

    return MavlinkFlightInterface(connection_string=connection_string, baud=baud)
