# -*- coding: utf-8 -*-
"""
2017 电赛 C 题 - 四旋翼自主飞行器探测跟踪系统
香橙派 + OpenCV，飞控为抽象接口。
"""

import os
import sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import cv2
import time
import argparse
from enum import Enum

import config as cfg
from camera import open_camera, read_frame
from vision import detect_ground_markers, MovingTargetTracker, detect_air_target
from control import TrackPIDController
from flight import create_flight_interface


class State(Enum):
    IDLE = "idle"
    TAKEOFF = "takeoff"
    SEARCH = "search"
    TRACK = "track"
    AIR_TRACK = "air_track"
    LAND = "land"
    DONE = "done"


def run_full_mission(use_simulate_flight=True, skip_takeoff_land=False, show_window=True):
    flight = create_flight_interface(use_simulate=use_simulate_flight)
    cap = open_camera()
    if not cap.isOpened():
        print("摄像头打开失败")
        return
    state = State.IDLE
    track_pid = TrackPIDController()
    moving_tracker = MovingTargetTracker()
    search_start = None
    h, w = cfg.FRAME_HEIGHT, cfg.FRAME_WIDTH
    center_x, center_y = w / 2, h / 2
    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret or frame is None:
                continue
            t = time.time()
            if state == State.IDLE:
                state = State.TAKEOFF
                search_start = None
            elif state == State.TAKEOFF:
                if not skip_takeoff_land:
                    flight.arm_and_takeoff(cfg.TARGET_ALTITUDE_M)
                    flight.set_altitude_hold(cfg.TARGET_ALTITUDE_M)
                state = State.SEARCH
                search_start = t
            elif state == State.SEARCH:
                markers = detect_ground_markers(frame)
                if markers:
                    m = markers[0]
                    print(f"[搜索] 发现地面标志 {m.color_type} @ ({m.cx:.0f},{m.cy:.0f})")
                    state = State.TRACK
                    track_pid.reset()
                    moving_tracker.reset()
                if search_start and (t - search_start) > getattr(cfg, "SEARCH_TIMEOUT_S", 60):
                    print("[搜索] 超时，进入跟踪")
                    state = State.TRACK
                flight.hover()
            elif state == State.TRACK:
                result = moving_tracker.update(frame)
                if result.found or result.lost_frames <= cfg.LOST_FRAME_KEEP:
                    forward_back, left_right = track_pid.update(
                        result.pred_cx, result.pred_cy, center_x, center_y, dt=1.0/25.0)
                    flight.set_velocity_body(forward_back, left_right, 0.0)
                    if show_window:
                        cv2.circle(frame, (int(result.pred_cx), int(result.pred_cy)), 15, (0,255,0), 2)
                else:
                    flight.hover()
                if show_window:
                    cv2.circle(frame, (int(center_x), int(center_y)), 5, (255,255,0), 1)
            elif state == State.AIR_TRACK:
                air = detect_air_target(frame)
                if air.found:
                    fb, lr = track_pid.update(air.cx, air.cy, center_x, center_y, dt=1.0/25.0)
                    flight.set_velocity_body(fb, lr, 0.0)
                else:
                    flight.hover()
                if show_window:
                    cv2.circle(frame, (int(air.cx), int(air.cy)), 12, (0,165,255), 2)
            elif state == State.LAND:
                if not skip_takeoff_land:
                    flight.land()
                state = State.DONE
            elif state == State.DONE:
                break
            if show_window:
                cv2.putText(frame, f"State: {state.value}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                cv2.imshow("2017C", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                state = State.LAND
        if state != State.DONE:
            flight.land()
    finally:
        cap.release()
        cv2.destroyAllWindows()
    print("任务结束")


def run_vision_only(mode="search"):
    cap = open_camera()
    if not cap.isOpened():
        print("摄像头打开失败")
        return
    tracker = MovingTargetTracker()
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            continue
        if mode == "search":
            for m in detect_ground_markers(frame):
                cv2.rectangle(frame, (m.bbox[0], m.bbox[1]), (m.bbox[0]+m.bbox[2], m.bbox[1]+m.bbox[3]), (0,255,0), 2)
        elif mode == "track":
            r = tracker.update(frame)
            cv2.circle(frame, (int(r.pred_cx), int(r.pred_cy)), 20, (0,255,0), 2)
        else:
            air = detect_air_target(frame)
            if air.found:
                cv2.circle(frame, (int(air.cx), int(air.cy)), 15, (0,165,255), 2)
        cv2.imshow("vision", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="2017C 四旋翼探测跟踪")
    parser.add_argument("--mode", choices=["full", "vision", "simulate"], default="vision")
    parser.add_argument("--vision-mode", choices=["search", "track", "air"], default="track")
    parser.add_argument("--simulate", action="store_true", default=True)
    parser.add_argument("--no-simulate", action="store_false", dest="simulate")
    parser.add_argument("--skip-flight", action="store_true")
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--sim-track", choices=["circle", "figure8"], default="circle")
    parser.add_argument("--sim-track-only", action="store_true")
    args = parser.parse_args()

    if args.mode == "simulate":
        from simulate import run_simulate_full_mission, run_simulate_track_only
        if args.sim_track_only:
            run_simulate_track_only(show_window=not args.no_window)
        else:
            run_simulate_full_mission(track_trajectory=args.sim_track, show_window=not args.no_window)
        return
    if args.mode == "vision":
        run_vision_only(args.vision_mode)
        return
    run_full_mission(use_simulate_flight=args.simulate, skip_takeoff_land=args.skip_flight, show_window=not args.no_window)


if __name__ == "__main__":
    main()
