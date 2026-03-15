# -*- coding: utf-8 -*-
"""纯软件模拟：无摄像头、无飞控。"""
import cv2
import numpy as np
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg

W, H = cfg.FRAME_WIDTH, cfg.FRAME_HEIGHT
CENTER_X, CENTER_Y = W/2, H/2
RED_BGR = (0, 0, 255)
TARGET_RADIUS = 35
TRACK_RADIUS, TRACK_OMEGA = 120, 0.8


def make_blank():
    return np.full((H, W, 3), (80, 80, 80), dtype=np.uint8)


def draw_red_circle(frame, cx, cy, r=None):
    r = r or TARGET_RADIUS
    cv2.circle(frame, (int(cx), int(cy)), r, RED_BGR, -1)
    cv2.circle(frame, (int(cx), int(cy)), r, (0, 0, 200), 2)


def get_simulated_frame_search(t):
    frame = make_blank()
    mx, my = CENTER_X + 20, CENTER_Y - 30
    draw_red_circle(frame, mx, my)
    cv2.putText(frame, "Sim: SEARCH", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
    return frame


def get_simulated_frame_track(t):
    frame = make_blank()
    tx = CENTER_X + TRACK_RADIUS * np.cos(t * TRACK_OMEGA)
    ty = CENTER_Y + TRACK_RADIUS * np.sin(t * TRACK_OMEGA)
    draw_red_circle(frame, tx, ty)
    cv2.putText(frame, "Sim: TRACK", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
    cv2.circle(frame, (int(CENTER_X), int(CENTER_Y)), 6, (255,255,0), 2)
    return frame


def get_simulated_frame_track_figure8(t):
    frame = make_blank()
    scale = 100
    tx = CENTER_X + scale * np.sin(t * 0.6)
    ty = CENTER_Y + scale * np.sin(t * 1.2) * 0.6
    draw_red_circle(frame, tx, ty)
    cv2.putText(frame, "Sim: TRACK (8)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
    cv2.circle(frame, (int(CENTER_X), int(CENTER_Y)), 6, (255,255,0), 2)
    return frame


class _SimState:
    IDLE, TAKEOFF, SEARCH, TRACK, LAND, DONE = "idle", "takeoff", "search", "track", "land", "done"


def run_simulate_full_mission(track_trajectory="circle", show_window=True):
    from vision import detect_ground_markers, MovingTargetTracker
    from control import TrackPIDController
    from flight import create_flight_interface
    flight = create_flight_interface(use_simulate=True)
    state = _SimState.IDLE
    track_pid = TrackPIDController()
    moving_tracker = MovingTargetTracker()
    search_start = None
    center_x, center_y = CENTER_X, CENTER_Y
    get_track = get_simulated_frame_track_figure8 if track_trajectory == "figure8" else get_simulated_frame_track
    t0 = time.time()
    print("纯软件模拟：按 Q 退出")
    while True:
        t = time.time() - t0
        if state == _SimState.SEARCH:
            frame = get_simulated_frame_search(t)
        elif state == _SimState.TRACK:
            frame = get_track(t)
        else:
            frame = get_simulated_frame_search(0)
        if state == _SimState.IDLE:
            state = _SimState.TAKEOFF
            search_start = None
        elif state == _SimState.TAKEOFF:
            flight.arm_and_takeoff(cfg.TARGET_ALTITUDE_M)
            flight.set_altitude_hold(cfg.TARGET_ALTITUDE_M)
            state = _SimState.SEARCH
            search_start = time.time()
        elif state == _SimState.SEARCH:
            markers = detect_ground_markers(frame)
            if markers:
                m = markers[0]
                print(f"[模拟] 发现标志 {m.color_type} @ ({m.cx:.0f},{m.cy:.0f})")
                state = _SimState.TRACK
                track_pid.reset()
                moving_tracker.reset()
            if search_start and (time.time() - search_start) > 3.0:
                print("[模拟] 超时，进入跟踪")
                state = _SimState.TRACK
                track_pid.reset()
                moving_tracker.reset()
            flight.hover()
        elif state == _SimState.TRACK:
            result = moving_tracker.update(frame)
            if result.found or result.lost_frames <= cfg.LOST_FRAME_KEEP:
                fb, lr = track_pid.update(result.pred_cx, result.pred_cy, center_x, center_y, dt=1.0/25.0)
                flight.set_velocity_body(fb, lr, 0.0)
                if show_window:
                    cv2.circle(frame, (int(result.pred_cx), int(result.pred_cy)), 18, (0,255,0), 2)
            else:
                flight.hover()
            if show_window:
                cv2.circle(frame, (int(center_x), int(center_y)), 5, (255,255,0), 1)
        elif state == _SimState.LAND:
            flight.land()
            state = _SimState.DONE
        elif state == _SimState.DONE:
            break
        if show_window:
            cv2.putText(frame, f"State: {state}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.imshow("2017C Simulate", frame)
        if cv2.waitKey(25) & 0xFF == ord("q"):
            state = _SimState.LAND
    if state != _SimState.DONE:
        flight.land()
    cv2.destroyAllWindows()
    print("模拟结束")


def run_simulate_track_only(show_window=True):
    from vision import MovingTargetTracker
    from control import TrackPIDController
    track_pid = TrackPIDController()
    moving_tracker = MovingTargetTracker()
    center_x, center_y = CENTER_X, CENTER_Y
    t0 = time.time()
    print("模拟跟踪：按 Q 退出")
    while True:
        t = time.time() - t0
        frame = get_simulated_frame_track(t)
        result = moving_tracker.update(frame)
        fb, lr = track_pid.update(result.pred_cx, result.pred_cy, center_x, center_y, dt=1.0/25.0)
        if show_window:
            cv2.circle(frame, (int(result.pred_cx), int(result.pred_cy)), 18, (0,255,0), 2)
            cv2.putText(frame, f"FB={fb:.2f} LR={lr:.2f}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1)
            cv2.imshow("2017C Sim Track", frame)
        if cv2.waitKey(25) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()
