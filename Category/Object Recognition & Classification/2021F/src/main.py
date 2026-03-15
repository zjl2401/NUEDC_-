"""
主循环与状态机（香橙派 + OpenCV）：协调视觉、路径规划、运动控制。
状态：IDLE -> 循线 -> 路口决策 -> 转向 -> 循线 -> ... -> 到达房号 -> 停靠 -> 送药 -> 返回
"""
from __future__ import annotations

import time
from enum import Enum
from typing import List, Optional

from src.config_loader import get_config, load_config
from src.vision.room_number import init_room_detector, recognize_room_number
from src.vision.marker import init_marker_detector, detect_stop_marker
from src.motion.line_follow import (
    compute_line_error,
    pid_line_follow,
    get_wheel_speeds as motion_wheel_speeds,
)
from src.motion.docking import (
    DockingState,
    should_start_docking,
    docking_speed,
    update_docking_state,
)
from src.path.recorder import TurnAction, record_turn, get_return_sequence
from src.path.return_path import consume_next_return_action
from src.hal.motor import set_wheel_speeds, stop_motors, get_encoder_ticks
from src.hal.sensor import read_line_sensors, is_junction
from src.hal.camera import init_camera, read_frame, release_camera

try:
    import cv2 as _cv2
except ImportError:
    _cv2 = None


class RobotState(Enum):
    IDLE = 0
    LINE_FOLLOW = 1
    JUNCTION_DECIDE = 2
    TURNING = 3
    DOCKING = 4
    DELIVER_MEDICINE = 5
    RETURNING = 6


def run_state_machine(
    target_room: int,
    path_stack: List[TurnAction],
    return_sequence: List[TurnAction],
    state: RobotState,
    integral: float,
    last_error: float,
    docking_state: DockingState,
    last_t: float,
    turn_end_t: float,
    current_return_action: Optional[TurnAction],
    cfg: dict,
) -> tuple:
    """
    单次状态机步进。返回 (next_state, path_stack, return_sequence, integral, last_error, docking_state, turn_end_t, current_return_action)。
    """
    t = time.monotonic()
    dt = min(0.1, max(0.001, t - last_t))

    frame = read_frame()
    sensor_values = read_line_sensors()
    junction = is_junction(
        sensor_values,
        cfg.get("junction", {}).get("black_threshold", 3),
    )

    lf = cfg.get("line_follow", {})
    kp = lf.get("kp", 0.5)
    ki = lf.get("ki", 0.0)
    kd = lf.get("kd", 0.1)
    base_speed = lf.get("base_speed", 0.5)
    max_diff = lf.get("max_diff", 0.4)

    dock_cfg = cfg.get("docking", {})

    # 视觉：房号 + 停止线（仅在有效帧时）
    current_room, room_conf = 0, 0.0
    stop_detected, stop_score = False, 0.0
    if frame is not None:
        roi_ratio = cfg.get("room_number", {}).get("roi")
        if roi_ratio:
            current_room, room_conf = recognize_room_number(frame, roi=None)
        else:
            current_room, room_conf = recognize_room_number(frame, roi=None)
        stop_detected, stop_score = detect_stop_marker(frame, roi=None)

    room_reached = current_room == target_room and room_conf > 0.3
    try_docking = should_start_docking(
        room_reached, stop_detected, target_room, current_room
    )

    # ---------- 状态分支 ----------
    if state == RobotState.IDLE:
        return (
            RobotState.LINE_FOLLOW,
            path_stack,
            return_sequence,
            integral,
            last_error,
            docking_state,
            turn_end_t,
            None,
        )

    if state == RobotState.DELIVER_MEDICINE:
        # 送药动作完成：生成返回序列并进入 RETURNING
        return_sequence.clear()
        return_sequence.extend(get_return_sequence(path_stack))
        set_wheel_speeds(0.0, 0.0)
        return (
            RobotState.RETURNING,
            path_stack,
            return_sequence,
            integral,
            last_error,
            DockingState.NOT_DOCKING,
            t,
            None,
        )

    if state == RobotState.DOCKING:
        left_enc, right_enc = get_encoder_ticks()
        encoder_dist = abs(left_enc) + abs(right_enc)
        encoder_dist = encoder_dist / 1e6 if encoder_dist else 0.0
        speed = docking_speed(
            docking_state,
            None,
            base_speed,
            dock_cfg.get("slow_speed", 0.2),
            dock_cfg.get("min_speed", 0.05),
        )
        if docking_state == DockingState.STOPPED:
            set_wheel_speeds(0.0, 0.0)
            return (
                RobotState.DELIVER_MEDICINE,
                path_stack,
                return_sequence,
                integral,
                last_error,
                docking_state,
                turn_end_t,
                None,
            )
        err = compute_line_error(sensor_values)
        pid_out, integral, last_error = pid_line_follow(
            err, kp, ki, kd, integral, last_error, dt
        )
        left_s, right_s = motion_wheel_speeds(speed, pid_out, max_diff)
        set_wheel_speeds(left_s, right_s)
        new_dock = update_docking_state(
            docking_state,
            stop_detected,
            speed,
            encoder_dist,
            dock_cfg.get("stop_threshold_cm", 2.0) / 100.0,
        )
        return (
            RobotState.DOCKING,
            path_stack,
            return_sequence,
            integral,
            last_error,
            new_dock,
            turn_end_t,
            None,
        )

    if state == RobotState.RETURNING:
        if t >= turn_end_t:
            action = consume_next_return_action(return_sequence)
            current_return_action = action
            turn_end_t = t + 0.8
            if action is None:
                set_wheel_speeds(0.0, 0.0)
                return (
                    RobotState.IDLE,
                    path_stack,
                    return_sequence,
                    integral,
                    last_error,
                    docking_state,
                    turn_end_t,
                    None,
                )
        else:
            action = current_return_action
        if action is not None and t < turn_end_t:
            if action == TurnAction.LEFT:
                set_wheel_speeds(-base_speed * 0.5, base_speed * 0.5)
            elif action == TurnAction.RIGHT:
                set_wheel_speeds(base_speed * 0.5, -base_speed * 0.5)
            else:
                err = compute_line_error(sensor_values)
                pid_out, integral, last_error = pid_line_follow(
                    err, kp, ki, kd, integral, last_error, dt
                )
                left_s, right_s = motion_wheel_speeds(base_speed, pid_out, max_diff)
                set_wheel_speeds(left_s, right_s)
        next_return_action = action
        return (
            RobotState.RETURNING,
            path_stack,
            return_sequence,
            integral,
            last_error,
            docking_state,
            turn_end_t,
            next_return_action,
        )

    if state == RobotState.TURNING:
        if t < turn_end_t:
            return (
                state,
                path_stack,
                return_sequence,
                integral,
                last_error,
                docking_state,
                turn_end_t,
                None,
            )
        return (
            RobotState.LINE_FOLLOW,
            path_stack,
            return_sequence,
            integral,
            last_error,
            docking_state,
            turn_end_t,
            None,
        )

    if state == RobotState.JUNCTION_DECIDE:
        # 简化：根据目标房号与当前路径选择左/右/直（此处仅示例：左转）
        action = TurnAction.LEFT
        record_turn(path_stack, action)
        turn_end_t = t + 0.8
        return (
            RobotState.TURNING,
            path_stack,
            return_sequence,
            integral,
            last_error,
            docking_state,
            turn_end_t,
            None,
        )

    # LINE_FOLLOW
    if try_docking:
        set_wheel_speeds(base_speed * 0.3, base_speed * 0.3)
        return (
            RobotState.DOCKING,
            path_stack,
            return_sequence,
            integral,
            last_error,
            DockingState.SLOW_DOWN,
            turn_end_t,
            None,
        )

    if junction:
        return (
            RobotState.JUNCTION_DECIDE,
            path_stack,
            return_sequence,
            integral,
            last_error,
            docking_state,
            turn_end_t,
            None,
        )

    error = compute_line_error(sensor_values)
    pid_out, integral, last_error = pid_line_follow(
        error, kp, ki, kd, integral, last_error, dt
    )
    left_s, right_s = motion_wheel_speeds(base_speed, pid_out, max_diff)
    set_wheel_speeds(left_s, right_s)

    return (
        RobotState.LINE_FOLLOW,
        path_stack,
        return_sequence,
        integral,
        last_error,
        docking_state,
        turn_end_t,
        None,
    )


def main_loop(
    target_room: int = 1,
    use_camera: bool = True,
    loop_hz: float = 50,
    use_sim: bool = False,
    show_sim_window: bool = True,
) -> None:
    """主循环：加载配置、初始化摄像头与视觉（或仿真）、运行状态机。"""
    load_config()
    cfg = get_config()

    sim = None
    if use_sim:
        from src.simulator import Simulator
        sim = Simulator()
        from src.hal import sensor as hal_sensor
        from src.hal import motor as hal_motor
        from src.hal import camera as hal_camera
        hal_sensor.set_simulator(sim)
        hal_motor.set_simulator(sim)
        hal_camera.set_simulator(sim)
    else:
        cam_cfg = cfg.get("camera", {})
        if use_camera:
            ok = init_camera(
                device=cam_cfg.get("device", 0),
                width=cam_cfg.get("width", 640),
                height=cam_cfg.get("height", 480),
            )
            if not ok:
                print("摄像头初始化失败，继续运行（无视觉）。")

    roi = cfg.get("room_number", {}).get("roi")
    if roi:
        init_room_detector(roi=tuple(roi))
    else:
        init_room_detector()

    m = cfg.get("marker", {})
    init_marker_detector(
        hsv_low1=tuple(m.get("red_hsv_low1", [0, 100, 100])),
        hsv_high1=tuple(m.get("red_hsv_high1", [10, 255, 255])),
        hsv_low2=tuple(m.get("red_hsv_low2", [170, 100, 100])),
        hsv_high2=tuple(m.get("red_hsv_high2", [180, 255, 255])),
        min_area=m.get("min_area", 500),
    )

    state = RobotState.LINE_FOLLOW
    path_stack: List[TurnAction] = []
    return_sequence: List[TurnAction] = []
    integral, last_error = 0.0, 0.0
    docking_state = DockingState.NOT_DOCKING
    last_t = time.monotonic()
    turn_end_t = 0.0
    current_return_action: Optional[TurnAction] = None
    period = 1.0 / loop_hz

    try:
        while True:
            (
                state,
                path_stack,
                return_sequence,
                integral,
                last_error,
                docking_state,
                turn_end_t,
                current_return_action,
            ) = run_state_machine(
                target_room,
                path_stack,
                return_sequence,
                state,
                integral,
                last_error,
                docking_state,
                last_t,
                turn_end_t,
                current_return_action,
                cfg,
            )
            now = time.monotonic()
            dt = now - last_t
            if sim is not None:
                sim.step(dt)
                if show_sim_window and _cv2 is not None:
                    frame = read_frame()
                    top = None
                    try:
                        from src.simulator import draw_track_top_down
                        top = draw_track_top_down(sim.track, sim.get_pose()[:2], sim.theta)
                    except Exception:
                        pass
                    if frame is not None:
                        _cv2.imshow("Sim Camera", frame)
                    if top is not None:
                        _cv2.imshow("Sim Track", top)
                    _cv2.waitKey(1)
            last_t = now
            time.sleep(max(0, period - (time.monotonic() - last_t)))
    except KeyboardInterrupt:
        pass
    finally:
        stop_motors()
        if not use_sim:
            release_camera()
        if use_sim and show_sim_window and _cv2 is not None:
            try:
                _cv2.destroyAllWindows()
            except Exception:
                pass


if __name__ == "__main__":
    main_loop(target_room=1, use_camera=True, loop_hz=50)
