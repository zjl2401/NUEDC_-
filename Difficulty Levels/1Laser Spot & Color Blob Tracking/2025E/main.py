# -*- coding: utf-8 -*-
"""
2025E 视觉闭环控制 - 纯软件模拟
模式：多目标切换、利萨如轨迹跟随、动态环境抗干扰
"""

import cv2
import numpy as np
import time
import argparse
import config as cfg
from vision_2025 import detect_multi_targets, select_target_by_id, select_target_by_color_name
from control_2025 import TrackerController, KalmanPredictor, lissajous_xy
from sim_env import SimEnv, create_multi_target_scene, COLOR_BGR


def clamp_xy(x: float, y: float, w: int, h: int, margin: int = 15) -> tuple:
    x = max(margin, min(w - margin, x))
    y = max(margin, min(h - margin, y))
    return (x, y)


# ---------- 1. 多目标协同/切换 ----------
def run_multi_target_switch(use_kalman: bool = True):
    """
    多目标场景：红/绿/蓝/黄多个运动 blob，通过按键或自动周期切换锁定目标，
    绿色十字（云台/小车）用 PID 追踪当前选中目标。
    """
    print("模式: 多目标协同/切换 [1-4] 切换目标(红/绿/蓝/黄) [Q] 退出")
    env = SimEnv(enable_flicker=False, enable_occlusion=False, enable_light_sine=False)
    create_multi_target_scene(env)
    ctrl = TrackerController()
    kalman = KalmanPredictor() if use_kalman else None
    # 当前锁定的目标编号 0=红 1=绿 2=蓝 3=黄
    target_id = 0
    follower_x, follower_y = env.w / 2, env.h / 2
    trail = []
    dt = 1.0 / cfg.SIM_FPS
    t_last = time.time()
    while True:
        frame = env.step()
        t_now = time.time()
        dt = min(0.1, t_now - t_last)
        t_last = t_now
        detections = detect_multi_targets(frame, normalize_light=True)
        target_xy = select_target_by_id(detections, target_id)
        if target_xy is None and kalman is not None:
            # 遮挡或丢失时用 Kalman 预测
            pred_x, pred_y = kalman.predict_only()
            if pred_x != 0 or pred_y != 0:
                target_xy = (pred_x, pred_y, "?")
        if target_xy is not None:
            tx, ty, _ = target_xy
            if kalman is not None:
                tx, ty = kalman.update(tx, ty)
            dx, dy = ctrl.update(tx, ty, follower_x, follower_y, dt=dt)
            follower_x += dx
            follower_y += dy
            follower_x, follower_y = clamp_xy(follower_x, follower_y, env.w, env.h)
        trail.append((int(follower_x), int(follower_y)))
        if len(trail) > 60:
            trail.pop(0)
        for i, pt in enumerate(trail):
            alpha = (i + 1) / len(trail)
            cv2.circle(frame, pt, 2, (0, int(200 * alpha), 0), -1)
        cv2.drawMarker(frame, (int(follower_x), int(follower_y)), (0, 255, 0),
                       cv2.MARKER_CROSS, 20, 2)
        if target_xy:
            cv2.circle(frame, (int(target_xy[0]), int(target_xy[1])), 8, (255, 255, 255), 2)
        cv2.putText(frame, f"Lock: {['Red','Green','Blue','Yellow'][target_id]} (1-4)", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow("2025E Multi-Target", frame)
        key = cv2.waitKey(max(1, int(1000 / cfg.SIM_FPS))) & 0xFF
        if key == ord("q"):
            break
        if ord("1") <= key <= ord("4"):
            target_id = key - ord("1")
            if kalman:
                kalman.reset()
    cv2.destroyAllWindows()


# ---------- 2. 非线性轨迹跟随（利萨如） ----------
def run_lissajous_follow(use_kalman: bool = True):
    """
    目标点沿利萨如图形运动，绿色十字（云台）用 PID 跟随该轨迹。
    纯软件：轨迹由公式生成，不经过视觉检测，用于验证控制性能。
    """
    print("模式: 利萨如图形轨迹跟随 [Q] 退出")
    w, h = cfg.CANVAS_W, cfg.CANVAS_H
    ctrl = TrackerController()
    kalman = KalmanPredictor() if use_kalman else None
    follower_x, follower_y = w / 2, h / 2
    t0 = time.time()
    trail = []
    dt = 1.0 / cfg.SIM_FPS
    while True:
        t = time.time() - t0
        target_x, target_y = lissajous_xy(t * cfg.LISSAJOUS_SPEED)
        if kalman is not None:
            target_x, target_y = kalman.update(target_x, target_y)
        dx, dy = ctrl.update(target_x, target_y, follower_x, follower_y, dt=dt)
        follower_x += dx
        follower_y += dy
        follower_x, follower_y = clamp_xy(follower_x, follower_y, w, h)
        trail.append((int(follower_x), int(follower_y)))
        if len(trail) > 200:
            trail.pop(0)
        frame = np.full((h, w, 3), (40, 40, 40), dtype=np.uint8)
        for i, pt in enumerate(trail):
            alpha = (i + 1) / len(trail)
            cv2.circle(frame, pt, 2, (0, int(180 * alpha), 0), -1)
        cv2.circle(frame, (int(target_x), int(target_y)), 10, (0, 0, 255), -1)
        cv2.drawMarker(frame, (int(follower_x), int(follower_y)), (0, 255, 0),
                       cv2.MARKER_CROSS, 18, 2)
        cv2.putText(frame, "Lissajous follow", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow("2025E Lissajous", frame)
        if cv2.waitKey(max(1, int(1000 / cfg.SIM_FPS))) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


# ---------- 3. 动态环境适应 ----------
def run_dynamic_env(use_kalman: bool = True):
    """
    多目标 + 利萨如红色目标；开启闪烁、遮挡、光照周期变化。
    绿色十字始终锁定红色（利萨如），在干扰下保持追踪。
    """
    print("模式: 动态环境适应（闪烁/遮挡/光照） [Q] 退出")
    env = SimEnv(enable_flicker=True, enable_occlusion=True, enable_light_sine=True)
    create_multi_target_scene(env)
    ctrl = TrackerController()
    kalman = KalmanPredictor() if use_kalman else None
    follower_x, follower_y = env.w / 2, env.h / 2
    trail = []
    dt = 1.0 / cfg.SIM_FPS
    t_last = time.time()
    lost_frames = 0
    while True:
        frame = env.step()
        t_now = time.time()
        dt = min(0.1, t_now - t_last)
        t_last = t_now
        detections = detect_multi_targets(frame, normalize_light=True)
        target_xy = select_target_by_color_name(detections, "red")
        if target_xy is not None:
            tx, ty, _ = target_xy
            if kalman is not None:
                tx, ty = kalman.update(tx, ty)
            lost_frames = 0
        else:
            lost_frames += 1
            if kalman is not None and lost_frames <= 30:
                tx, ty = kalman.predict_only()
            else:
                tx, ty = follower_x, follower_y
        dx, dy = ctrl.update(tx, ty, follower_x, follower_y, dt=dt)
        follower_x += dx
        follower_y += dy
        follower_x, follower_y = clamp_xy(follower_x, follower_y, env.w, env.h)
        trail.append((int(follower_x), int(follower_y)))
        if len(trail) > 80:
            trail.pop(0)
        for i, pt in enumerate(trail):
            alpha = (i + 1) / len(trail)
            cv2.circle(frame, pt, 2, (0, int(200 * alpha), 0), -1)
        cv2.drawMarker(frame, (int(follower_x), int(follower_y)), (0, 255, 0),
                       cv2.MARKER_CROSS, 20, 2)
        status = "TRACK" if target_xy else f"LOST ({lost_frames})"
        cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.imshow("2025E Dynamic Env", frame)
        if cv2.waitKey(max(1, int(1000 / cfg.SIM_FPS))) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="2025E 视觉闭环控制 - 纯软件模拟")
    parser.add_argument(
        "--mode",
        choices=["multi", "lissajous", "dynamic"],
        default="multi",
        help="multi=多目标切换, lissajous=利萨如跟随, dynamic=动态环境抗干扰",
    )
    parser.add_argument("--no-kalman", action="store_true", help="关闭 Kalman 预测")
    args = parser.parse_args()
    use_kalman = not args.no_kalman
    if args.mode == "multi":
        run_multi_target_switch(use_kalman=use_kalman)
    elif args.mode == "lissajous":
        run_lissajous_follow(use_kalman=use_kalman)
    elif args.mode == "dynamic":
        run_dynamic_env(use_kalman=use_kalman)
    print("退出。")


if __name__ == "__main__":
    main()
