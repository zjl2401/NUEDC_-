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
from hardware import create_servo
from vision_real import RealVisionPipeline
from target_lock import TargetLock
from scoring import ScoreState


def clamp_xy(x: float, y: float, w: int, h: int, margin: int = 15) -> tuple:
    x = max(margin, min(w - margin, x))
    y = max(margin, min(h - margin, y))
    return (x, y)


def _clamp_angle(pan: float, tilt: float) -> tuple:
    pan = max(cfg.PAN_MIN, min(cfg.PAN_MAX, pan))
    tilt = max(cfg.TILT_MIN, min(cfg.TILT_MAX, tilt))
    return (pan, tilt)


def _pixel_error_to_angle_delta(err_x: float, err_y: float) -> tuple:
    # 像素误差 -> 角度增量（符号方向按你的云台安装方向可能需要取反）
    d_pan = err_x * cfg.PIXEL_TO_PAN
    d_tilt = err_y * cfg.PIXEL_TO_TILT
    return (d_pan, d_tilt)


def _open_camera(camera_index: int = None):
    idx = cfg.CAMERA_INDEX if camera_index is None else camera_index
    cap = cv2.VideoCapture(idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.FRAME_HEIGHT)
    if hasattr(cv2, "CAP_PROP_EXPOSURE"):
        try:
            cap.set(cv2.CAP_PROP_EXPOSURE, cfg.EXPOSURE)
        except Exception:
            pass
    return cap


# ---------- 真机：摄像头输入 + 云台输出 ----------
def run_real_track(
    mode: str,
    use_kalman: bool,
    use_dummy_servo: bool,
    use_perspective: bool,
    roi: bool,
    serial_port: str = None,
    serial_baud: int = 115200,
    camera_index: int = None,
    pan_pin: int = None,
    tilt_pin: int = None,
    show_window: bool = True,
    max_frames: int = None,
    save_preview: str = None,
):
    """
    真机运行：
      - 从摄像头取帧
      - vision_2025 做多颜色检测
      - 选择目标（multi:按键切换 / dynamic:追 red / lissajous:忽略，建议用 simulate）
      - PID/Kalman 输出 -> 转换为舵机角度增量 -> set_pan_tilt
      - 无显示器时用 show_window=False（SSH 无头），Ctrl+C 或 --max-frames 退出
    """
    if mode == "lissajous":
        raise SystemExit("真机模式不建议用 lissajous（该模式本意是纯公式轨迹控制验证），请用 --mode multi 或 dynamic")

    servo = create_servo(use_dummy=use_dummy_servo, pan_pin=pan_pin, tilt_pin=tilt_pin)
    cap = _open_camera(camera_index)
    if not cap.isOpened():
        raise SystemExit("无法打开摄像头，请检查 CAMERA_INDEX 或驱动")

    ctrl = TrackerController()
    kalman = KalmanPredictor() if use_kalman else None
    pipeline = RealVisionPipeline(
        use_perspective=use_perspective,
        roi_enabled=roi,
        roi_size=cfg.ROI_SIZE,
    )
    lock = TargetLock()
    score = ScoreState()

    sender = None
    if serial_port:
        from comm import SerialSender

        sender = SerialSender(serial_port, baud=serial_baud)

    target_id = 0
    pan, tilt = (cfg.PAN_CENTER, cfg.TILT_CENTER)
    servo.set_pan_tilt(pan, tilt)

    t_last = time.time()
    lost_frames = 0
    frame_idx = 0

    if show_window:
        print("真机模式: [C]透视标定  [1-4]切目标(仅 multi)  [Q]退出")
    else:
        print("真机无头模式: 终端打印状态；Ctrl+C 退出；可用 --max-frames / --save-preview")

    try:
        while True:
            if max_frames is not None and frame_idx >= max_frames:
                break
            ok, frame = cap.read()
            if not ok or frame is None:
                print("读帧失败，退出。")
                break
            frame_idx += 1

            t_now = time.time()
            dt = min(0.1, t_now - t_last)
            t_last = t_now

            # 透视标定（首次/手动触发）；无头时建议 --no-perspective
            if use_perspective and pipeline.transformer is not None and pipeline.transformer.M is None:
                pipeline.calibrate_if_needed(frame)

            detections, work = pipeline.process(frame, normalize_light=True)
            if mode == "multi":
                color_name = ["red", "green", "blue", "yellow"][target_id]
            else:
                color_name = "red"

            h, w = work.shape[:2]
            center_x, center_y = (w / 2.0, h / 2.0)

            prior_xy = None
            if kalman is not None:
                px, py = kalman.predict_only()
                if px != 0 or py != 0:
                    prior_xy = (px, py)
            lock_res = lock.update_by_color_name(detections, color_name=color_name, prior_xy=prior_xy)

            if lock_res.target_xy is not None:
                tx, ty = lock_res.target_xy
                if kalman is not None:
                    tx, ty = kalman.update(tx, ty)
                lost_frames = 0
                pipeline.update_roi_center((tx, ty))
            else:
                lost_frames += 1
                if kalman is not None and lost_frames <= 30:
                    tx, ty = kalman.predict_only()
                else:
                    tx, ty = center_x, center_y
                pipeline.update_roi_center(None)

            dx, dy = ctrl.update(tx, ty, center_x, center_y, dt=dt)
            d_pan, d_tilt = _pixel_error_to_angle_delta(dx, dy)
            pan, tilt = _clamp_angle(pan + d_pan, tilt + d_tilt)
            servo.set_pan_tilt(pan, tilt)

            target_for_draw = lock_res.target_xy
            if target_for_draw:
                cv2.circle(work, (int(target_for_draw[0]), int(target_for_draw[1])), 10, (255, 255, 255), 2)
            cv2.circle(work, (int(center_x), int(center_y)), 5, (255, 255, 0), 1)
            cv2.circle(work, (int(center_x), int(center_y)), cfg.HIT_RADIUS_PX, (80, 80, 255), 1)
            cv2.putText(work, f"pan={pan:.1f} tilt={tilt:.1f}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            status = lock_res.status if lock_res.status != "TRACK" else ("TRACK" if lock_res.stable else "ACQUIRE")
            cv2.putText(work, status, (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(work, f"hits={score.hits} score={score.score}", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

            new_hit = score.update(target_xy=target_for_draw, aim_xy=(center_x, center_y))
            if new_hit:
                cv2.putText(work, "HIT!", (w - 90, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

            if show_window:
                cv2.imshow("2025E Real", work)

            if not show_window and frame_idx % 15 == 0:
                print(
                    f"[{frame_idx}] color={color_name} status={status} "
                    f"pan={pan:.1f} tilt={tilt:.1f} hits={score.hits}"
                )
            if save_preview and frame_idx % 30 == 0:
                cv2.imwrite(save_preview, work)

            if sender is not None:
                ex = tx - center_x
                ey = ty - center_y
                sender.send_line(
                    f"pan={pan:.2f} tilt={tilt:.2f} ex={ex:.2f} ey={ey:.2f} s={status} hits={score.hits} score={score.score}"
                )

            if show_window:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("c") and use_perspective:
                    pipeline.transformer.M = None if pipeline.transformer is not None else None
                    pipeline.calibrate_if_needed(frame)
                if mode == "multi" and ord("1") <= key <= ord("4"):
                    target_id = key - ord("1")
                    if kalman:
                        kalman.reset()
                    lock.reset()
            else:
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，退出。")
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
        if sender is not None:
            sender.close()
        try:
            servo.set_center()
            servo.close()
        except Exception:
            pass


def run_real_reset(
    use_dummy_servo: bool,
    use_perspective: bool,
    camera_index: int = None,
    pan_pin: int = None,
    tilt_pin: int = None,
    show_window: bool = True,
    max_frames: int = None,
    save_preview: str = None,
):
    """真机复位：云台回中；无显示器时 show_window=False。"""
    servo = create_servo(use_dummy=use_dummy_servo, pan_pin=pan_pin, tilt_pin=tilt_pin)
    servo.set_center()
    cap = _open_camera(camera_index)
    if not cap.isOpened():
        raise SystemExit("无法打开摄像头，请检查 CAMERA_INDEX 或驱动")

    pipeline = RealVisionPipeline(use_perspective=use_perspective, roi_enabled=False, roi_size=cfg.ROI_SIZE)
    if show_window:
        print("真机复位: 云台已回中  [C]透视标定  [Q]退出")
    else:
        print("真机复位(无头): Ctrl+C 退出；可用 --max-frames / --save-preview")
    frame_idx = 0
    try:
        while True:
            if max_frames is not None and frame_idx >= max_frames:
                break
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            frame_idx += 1
            if use_perspective:
                pipeline.calibrate_if_needed(frame)
            _, work = pipeline.process(frame, normalize_light=True)
            h, w = work.shape[:2]
            cv2.circle(work, (int(w / 2), int(h / 2)), 6, (255, 255, 0), 2)
            if show_window:
                cv2.imshow("2025E Reset", work)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("c") and use_perspective:
                    if pipeline.transformer is not None:
                        pipeline.transformer.M = None
                    pipeline.calibrate_if_needed(frame)
            else:
                if frame_idx % 15 == 0:
                    print(f"[{frame_idx}] reset ok, frame={w}x{h}")
                if save_preview and frame_idx % 30 == 0:
                    cv2.imwrite(save_preview, work)
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，退出。")
    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
        try:
            servo.close()
        except Exception:
            pass


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
    lock = TargetLock()
    score = ScoreState()
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
        color_name = ["red", "green", "blue", "yellow"][target_id]
        lock_res = lock.update_by_color_name(detections, color_name=color_name)
        if lock_res.target_xy is not None:
            tx, ty = lock_res.target_xy
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
        if lock_res.target_xy:
            cv2.circle(frame, (int(lock_res.target_xy[0]), int(lock_res.target_xy[1])), 8, (255, 255, 255), 2)
        cv2.circle(frame, (int(follower_x), int(follower_y)), cfg.HIT_RADIUS_PX, (80, 80, 255), 1)
        new_hit = score.update(
            target_xy=lock_res.target_xy,
            aim_xy=(follower_x, follower_y),
        )
        if new_hit:
            cv2.putText(frame, "HIT!", (env.w - 90, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"Lock: {['Red','Green','Blue','Yellow'][target_id]} (1-4)", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, f"hits={score.hits} score={score.score}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.imshow("2025E Multi-Target", frame)
        key = cv2.waitKey(max(1, int(1000 / cfg.SIM_FPS))) & 0xFF
        if key == ord("q"):
            break
        if ord("1") <= key <= ord("4"):
            target_id = key - ord("1")
            if kalman:
                kalman.reset()
            lock.reset()
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
    lock = TargetLock()
    score = ScoreState()
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
        lock_res = lock.update_by_color_name(detections, color_name="red")
        if lock_res.target_xy is not None:
            tx, ty = lock_res.target_xy
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
        status = lock_res.status if lock_res.status != "TRACK" else ("TRACK" if lock_res.stable else "ACQUIRE")
        cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        if lock_res.target_xy:
            cv2.circle(frame, (int(lock_res.target_xy[0]), int(lock_res.target_xy[1])), 8, (255, 255, 255), 2)
        cv2.circle(frame, (int(follower_x), int(follower_y)), cfg.HIT_RADIUS_PX, (80, 80, 255), 1)
        new_hit = score.update(target_xy=lock_res.target_xy, aim_xy=(follower_x, follower_y))
        if new_hit:
            cv2.putText(frame, "HIT!", (env.w - 90, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"hits={score.hits} score={score.score}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        cv2.imshow("2025E Dynamic Env", frame)
        if cv2.waitKey(max(1, int(1000 / cfg.SIM_FPS))) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="2025E 视觉闭环控制 - 仿真/真机")
    parser.add_argument(
        "--mode",
        choices=["multi", "lissajous", "dynamic", "reset"],
        default="multi",
        help="multi=多目标切换, lissajous=利萨如跟随(仿真), dynamic=动态环境抗干扰, reset=真机回中/标定",
    )
    parser.add_argument("--no-kalman", action="store_true", help="关闭 Kalman 预测")
    parser.add_argument("--real", action="store_true", help="真机模式：摄像头输入 + 云台/舵机输出")
    parser.add_argument("--dummy", action="store_true", help="真机模式下不接舵机，仅打印角度（或无 GPIO 时自动 dummy）")
    parser.add_argument("--no-perspective", action="store_true", help="真机模式关闭透视矫正")
    parser.add_argument("--no-roi", action="store_true", help="真机模式关闭 ROI（默认开启）")
    parser.add_argument("--serial", type=str, default=None, help="可选：串口端口，例如 COM3 或 /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="可选：串口波特率")
    parser.add_argument("--camera-index", type=int, default=None, help="摄像头索引（默认 config.CAMERA_INDEX）")
    parser.add_argument("--pan-pin", type=int, default=None, help="云台水平舵机 BOARD 脚（默认 config.PAN_PIN_BOARD）")
    parser.add_argument("--tilt-pin", type=int, default=None, help="云台俯仰舵机 BOARD 脚（默认 config.TILT_PIN_BOARD）")
    parser.add_argument("--no-show", action="store_true", help="无显示器/SSH 无头：不弹窗，终端打印状态")
    parser.add_argument("--max-frames", type=int, default=None, help="最多处理帧数（无头调试用）")
    parser.add_argument("--save-preview", type=str, default=None, help="无头时周期性保存预览图路径，如 /tmp/preview.jpg")
    args = parser.parse_args()
    use_kalman = not args.no_kalman

    if args.real:
        use_perspective = cfg.USE_PERSPECTIVE and (not args.no_perspective)
        use_roi = cfg.ROI_ENABLED and (not args.no_roi)
        # 无头时默认关掉透视（无法按 C 标定）
        if args.no_show and not args.no_perspective and use_perspective:
            print("提示: --no-show 下建议加 --no-perspective（已可用参数关闭）")
        if args.mode == "reset":
            run_real_reset(
                use_dummy_servo=args.dummy,
                use_perspective=use_perspective,
                camera_index=args.camera_index,
                pan_pin=args.pan_pin,
                tilt_pin=args.tilt_pin,
                show_window=not args.no_show,
                max_frames=args.max_frames,
                save_preview=args.save_preview,
            )
            print("退出。")
            return
        run_real_track(
            mode=args.mode,
            use_kalman=use_kalman,
            use_dummy_servo=args.dummy,
            use_perspective=use_perspective,
            roi=use_roi,
            serial_port=args.serial,
            serial_baud=args.baud,
            camera_index=args.camera_index,
            pan_pin=args.pan_pin,
            tilt_pin=args.tilt_pin,
            show_window=not args.no_show,
            max_frames=args.max_frames,
            save_preview=args.save_preview,
        )
        print("退出。")
        return

    if args.mode == "multi":
        run_multi_target_switch(use_kalman=use_kalman)
    elif args.mode == "lissajous":
        run_lissajous_follow(use_kalman=use_kalman)
    elif args.mode == "dynamic":
        run_dynamic_env(use_kalman=use_kalman)
    elif args.mode == "reset":
        raise SystemExit("reset 模式仅用于真机，请加 --real")
    print("退出。")


if __name__ == "__main__":
    main()
