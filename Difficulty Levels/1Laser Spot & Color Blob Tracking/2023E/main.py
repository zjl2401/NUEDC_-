# -*- coding: utf-8 -*-
"""激光追踪主程序：OpenCV + 香橙派，复位/定点/动态追踪/画圈"""

import cv2
import time
import argparse
import numpy as np
import config as cfg
from vision import VisionPipeline
from control import TrackerController, VelocityPredictor
from hardware import create_servo


def screen_to_angle(sx: float, sy: float, screen_w: float = None, screen_h: float = None) -> tuple:
    """屏幕坐标转舵机角度 (pan, tilt)。"""
    sw = screen_w or cfg.SCREEN_W
    sh = screen_h or cfg.SCREEN_H
    cx, cy = sw / 2, sh / 2
    pan = cfg.PAN_CENTER + (sx - cx) * cfg.SCREEN_TO_PAN
    tilt = cfg.TILT_CENTER + (sy - cy) * cfg.SCREEN_TO_TILT
    pan = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan))
    tilt = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt))
    return (pan, tilt)


def angle_from_delta(current_pan: float, current_tilt: float, delta_pan: float, delta_tilt: float) -> tuple:
    """当前角度 + PID 增量 -> 新角度。"""
    pan = current_pan + delta_pan
    tilt = current_tilt + delta_tilt
    pan = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan))
    tilt = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt))
    return (pan, tilt)


def run_reset(servo, vision: VisionPipeline) -> None:
    """复位：绿点对准屏幕中心。"""
    print("模式: 复位对齐（绿点 -> 屏幕中心）")
    ctrl = TrackerController()
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    if hasattr(cv2, "CAP_PROP_EXPOSURE"):
        cap.set(cv2.CAP_PROP_EXPOSURE, cfg.EXPOSURE)
    last_angle = (cfg.PAN_CENTER, cfg.TILT_CENTER)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        red_xy, green_xy, work = vision.process_frame(frame, calibrate_if_needed=True)
        h, w = work.shape[:2]
        center = (w / 2, h / 2)
        current = green_xy if green_xy else center
        delta_pan, delta_tilt = ctrl.update(center[0], center[1], current[0], current[1], dt=1.0)
        pan, tilt = angle_from_delta(last_angle[0], last_angle[1], delta_pan, delta_tilt)
        last_angle = (pan, tilt)
        servo.set_pan_tilt(pan, tilt)
        cv2.circle(work, (int(center[0]), int(center[1])), 5, (255, 255, 0), 1)
        if green_xy:
            cv2.circle(work, (int(green_xy[0]), int(green_xy[1])), 5, (0, 255, 0), 2)
        cv2.imshow("reset", work)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def run_track(servo, vision: VisionPipeline, use_predict: bool) -> None:
    """定点/动态追踪：绿点追红点。"""
    print("模式: 动态追踪" if use_predict else "模式: 定点追踪")
    ctrl = TrackerController()
    predictor = VelocityPredictor() if use_predict else None
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    if hasattr(cv2, "CAP_PROP_EXPOSURE"):
        cap.set(cv2.CAP_PROP_EXPOSURE, cfg.EXPOSURE)
    last_angle = (cfg.PAN_CENTER, cfg.TILT_CENTER)
    target_xy = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        red_xy, green_xy, work = vision.process_frame(frame, calibrate_if_needed=True)
        h, w = work.shape[:2]
        fallback = (w / 2, h / 2)
        current = green_xy if green_xy else fallback
        if target_xy is None:
            target_xy = fallback
        if red_xy:
            target_xy = predictor.update(red_xy[0], red_xy[1]) if predictor else red_xy
        delta_pan, delta_tilt = ctrl.update(target_xy[0], target_xy[1], current[0], current[1], dt=1.0)
        pan, tilt = angle_from_delta(last_angle[0], last_angle[1], delta_pan, delta_tilt)
        last_angle = (pan, tilt)
        servo.set_pan_tilt(pan, tilt)
        if red_xy:
            cv2.circle(work, (int(red_xy[0]), int(red_xy[1])), 6, (0, 0, 255), 2)
        if green_xy:
            cv2.circle(work, (int(green_xy[0]), int(green_xy[1])), 5, (0, 255, 0), 2)
        cv2.imshow("track", work)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def run_simulate_track(use_predict: bool) -> None:
    """纯软件模拟：红点自动运动，绿点用 PID 追踪，无需摄像头和舵机。"""
    print("模式: 模拟追踪（红点自动画圆，绿点 PID 追赶）")
    W, H = 640, 480
    ctrl = TrackerController()
    predictor = VelocityPredictor() if use_predict else None
    green_x, green_y = W / 2, H / 2
    t0 = time.time()
    trail = []
    while True:
        t = time.time() - t0
        # 红点沿圆周运动
        red_x = W / 2 + 180 * np.cos(t * 0.6)
        red_y = H / 2 + 180 * np.sin(t * 0.6)
        target_x, target_y = (red_x, red_y)
        if predictor:
            target_x, target_y = predictor.update(red_x, red_y)
        delta_pan, delta_tilt = ctrl.update(target_x, target_y, green_x, green_y, dt=1.0)
        # 角度增量转像素增量（与 screen_to_angle 对应）
        green_x += delta_pan / cfg.SCREEN_TO_PAN
        green_y += delta_tilt / cfg.SCREEN_TO_TILT
        green_x = max(20, min(W - 20, green_x))
        green_y = max(20, min(H - 20, green_y))
        trail.append((int(green_x), int(green_y)))
        if len(trail) > 80:
            trail.pop(0)
        # 绘制
        frame = np.full((H, W, 3), (35, 35, 35), dtype=np.uint8)
        for i, pt in enumerate(trail):
            alpha = (i + 1) / len(trail)
            cv2.circle(frame, pt, 3, (0, int(180 * alpha), 0), -1)
        cv2.circle(frame, (int(red_x), int(red_y)), 12, (0, 0, 255), -1)
        cv2.circle(frame, (int(red_x), int(red_y)), 14, (0, 0, 200), 2)
        cv2.circle(frame, (int(green_x), int(green_y)), 10, (0, 255, 0), -1)
        cv2.circle(frame, (int(green_x), int(green_y)), 12, (0, 200, 0), 2)
        cv2.putText(frame, "Red=target  Green=laser (PID)  [Q]uit", (10, H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("sim_track", frame)
        if cv2.waitKey(25) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def run_simulate_reset() -> None:
    """模拟复位：绿点从随机位置回到中心。"""
    print("模式: 模拟复位（绿点回到中心）")
    W, H = 640, 480
    ctrl = TrackerController()
    green_x, green_y = W / 2 + 150, H / 2 - 80
    center = (W / 2, H / 2)
    while True:
        delta_pan, delta_tilt = ctrl.update(center[0], center[1], green_x, green_y, dt=1.0)
        green_x += delta_pan / cfg.SCREEN_TO_PAN
        green_y += delta_tilt / cfg.SCREEN_TO_TILT
        green_x = max(0, min(W, green_x))
        green_y = max(0, min(H, green_y))
        frame = np.full((H, W, 3), (35, 35, 35), dtype=np.uint8)
        cv2.circle(frame, (int(center[0]), int(center[1])), 8, (255, 255, 0), 2)
        cv2.circle(frame, (int(green_x), int(green_y)), 10, (0, 255, 0), -1)
        cv2.putText(frame, "Green -> Center  [Q]uit", (10, H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("sim_reset", frame)
        if cv2.waitKey(25) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def run_simulate_circle(radius: float = 120, speed: float = 0.12) -> None:
    """模拟画圈：绿点沿圆周运动。"""
    print("模式: 模拟画圈")
    W, H = 640, 480
    cx, cy = W / 2, H / 2
    t0 = time.time()
    while True:
        t = time.time() - t0
        green_x = cx + radius * np.cos(t * speed)
        green_y = cy + radius * np.sin(t * speed)
        frame = np.full((H, W, 3), (35, 35, 35), dtype=np.uint8)
        cv2.circle(frame, (int(cx), int(cy)), 5, (255, 255, 0), 1)
        cv2.circle(frame, (int(green_x), int(green_y)), 10, (0, 255, 0), -1)
        cv2.putText(frame, "Circle scan  [Q]uit", (10, H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("sim_circle", frame)
        if cv2.waitKey(25) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def run_scan_circle(servo, vision: VisionPipeline, radius: float = 80, speed: float = 0.15) -> None:
    """自主画圈：沿黑框内切圆轨迹运动。"""
    print("模式: 自主画圈")
    cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    if hasattr(cv2, "CAP_PROP_EXPOSURE"):
        cap.set(cv2.CAP_PROP_EXPOSURE, cfg.EXPOSURE)
    cx, cy = cfg.SCREEN_W / 2, cfg.SCREEN_H / 2
    t0 = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, _, work = vision.process_frame(frame, calibrate_if_needed=True)
        t = time.time() - t0
        sx = cx + radius * np.cos(t * speed)
        sy = cy + radius * np.sin(t * speed)
        pan, tilt = screen_to_angle(sx, sy)
        servo.set_pan_tilt(pan, tilt)
        cv2.circle(work, (int(sx), int(sy)), 4, (255, 255, 0), 2)
        cv2.imshow("scan", work)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="激光追踪：复位/定点/动态/画圈")
    parser.add_argument("--mode", choices=["reset", "track", "dynamic", "circle"], default="track")
    parser.add_argument("--no-perspective", action="store_true", help="不做透视校正")
    parser.add_argument("--dummy", action="store_true", help="不接舵机，仅打印角度")
    parser.add_argument("--simulate", action="store_true",
                        help="纯软件模拟：无需摄像头和舵机，红/绿点用程序绘制看效果")
    args = parser.parse_args()

    if args.simulate:
        if args.mode == "reset":
            run_simulate_reset()
        elif args.mode == "track":
            run_simulate_track(use_predict=False)
        elif args.mode == "dynamic":
            run_simulate_track(use_predict=True)
        elif args.mode == "circle":
            run_simulate_circle()
        print("退出。")
        return

    servo = create_servo(use_dummy=args.dummy)
    vision = VisionPipeline(use_perspective=not args.no_perspective)

    if args.mode == "reset":
        run_reset(servo, vision)
    elif args.mode == "track":
        run_track(servo, vision, use_predict=False)
    elif args.mode == "dynamic":
        run_track(servo, vision, use_predict=True)
    elif args.mode == "circle":
        run_scan_circle(servo, vision)

    servo.set_center()
    print("退出。")


if __name__ == "__main__":
    main()
