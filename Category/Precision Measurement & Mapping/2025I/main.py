# -*- coding: utf-8 -*-
"""
非接触式控制盘 (2025I) - 香橙派 OpenCV 纯软件模拟
运行：python main.py [--video 视频路径 | --simulate] ...
- 手势捕捉：平移、握拳/张开
- 非接触式映射：手部 2D 位置 → 虚拟控制盘上的控制量
- 实时反馈与抗干扰（肤色 YCrCb + 平滑 + 死区）
"""
from __future__ import annotations

import time
import argparse
import logging

import cv2
import config as cfg
from vision import HandDetector, HandState
from control_mapper import ControlMapper, draw_control_panel_overlay
from simulate import synthetic_frame_generator, video_file_generator
try:
    import serial
except ImportError:
    serial = None

logging.basicConfig(
    level=getattr(logging, getattr(cfg, "LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="非接触式控制盘 - 香橙派 + OpenCV / 纯软件模拟")
    parser.add_argument("--cam", type=int, default=cfg.CAM_INDEX, help="摄像头设备号（默认 0）")
    parser.add_argument("--video", type=str, default=None, help="使用视频文件代替摄像头（纯软件）")
    parser.add_argument("--simulate", action="store_true", help="使用合成场景（虚拟手运动），无需摄像头与视频")
    parser.add_argument("--width", type=int, default=cfg.PROC_WIDTH, help="处理宽度")
    parser.add_argument("--height", type=int, default=cfg.PROC_HEIGHT, help="处理高度")
    parser.add_argument("--no-show", action="store_true", help="不显示窗口（无屏/SSH 时）")
    parser.add_argument("--max-frames", type=int, default=None, help="最多处理帧数，默认无限")
    parser.add_argument("--delay", type=int, default=30, help="模拟时每帧延迟 ms（--simulate/--video）")
    parser.add_argument("--show-mask", action="store_true", help="显示肤色二值图")
    parser.add_argument("--serial", type=str, default=None, help="串口输出控制量，如 COM3 或 /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="串口波特率")
    args = parser.parse_args()

    detector = HandDetector()
    mapper = ControlMapper(width=args.width, height=args.height)
    show = not args.no_show
    show_mask = args.show_mask or getattr(cfg, "SHOW_SKIN_MASK", False)
    ser = None
    if args.serial:
        if serial is None:
            logger.error("未安装 pyserial，无法启用串口输出。请执行: pip install pyserial")
            return
        try:
            ser = serial.Serial(args.serial, args.baud, timeout=0.05)
            logger.info("串口输出已开启: %s @ %d", args.serial, args.baud)
        except Exception as e:
            logger.error("串口打开失败: %s", e)
            return

    def run_one_frame(frame, classify_gesture=True):
        center, state, contour, skin_mask = detector.process(frame, classify_gesture=classify_gesture)
        nx, ny = mapper.update(center, state)
        if ser is not None:
            # 输出格式：nx,ny,state\n，便于 MCU 解析
            line = f"{nx:.3f},{ny:.3f},{state.value}\n"
            try:
                ser.write(line.encode("utf-8"))
            except Exception:
                pass
        vis = draw_control_panel_overlay(frame, nx, ny, state)
        if contour is not None:
            cv2.drawContours(vis, [contour], -1, (0, 255, 255), 2)
        if center is not None:
            cx, cy = int(center[0]), int(center[1])
            cv2.circle(vis, (cx, cy), 6, (0, 255, 0), -1)
        return vis, skin_mask, (nx, ny), state

    t0 = time.perf_counter()
    n = 0

    if args.simulate:
        logger.info("纯软件模拟：合成虚拟手运动 (分辨率 %dx%d)", args.width, args.height)
        gen = synthetic_frame_generator(args.width, args.height, max_frames=args.max_frames)
        try:
            for frame, idx in gen:
                if args.max_frames is not None and n >= args.max_frames:
                    break
                n += 1
                vis, skin_mask, (nx, ny), state = run_one_frame(frame)
                if show:
                    cv2.imshow("control", vis)
                    if show_mask:
                        cv2.imshow("skin", skin_mask)
                    if cv2.waitKey(args.delay) & 0xFF == ord("q"):
                        break
        finally:
            if show:
                cv2.destroyAllWindows()

    elif args.video:
        logger.info("纯软件模拟：视频文件 %s (分辨率 %dx%d)", args.video, args.width, args.height)
        gen = video_file_generator(args.video, resize=(args.width, args.height), max_frames=args.max_frames)
        try:
            for frame, idx in gen:
                if args.max_frames is not None and n >= args.max_frames:
                    break
                n += 1
                vis, skin_mask, (nx, ny), state = run_one_frame(frame)
                if show:
                    cv2.imshow("control", vis)
                    if show_mask:
                        cv2.imshow("skin", skin_mask)
                    if cv2.waitKey(args.delay) & 0xFF == ord("q"):
                        break
        finally:
            if show:
                cv2.destroyAllWindows()

    else:
        cap = cv2.VideoCapture(args.cam)
        if not cap.isOpened():
            logger.error("无法打开摄像头: %s", args.cam)
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        logger.info("实时摄像头 (设备 %s, 分辨率 %dx%d)", args.cam, args.width, args.height)
        try:
            while True:
                if args.max_frames is not None and n >= args.max_frames:
                    break
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                frame = cv2.resize(frame, (args.width, args.height))
                vis, skin_mask, (nx, ny), state = run_one_frame(frame)
                if show:
                    cv2.imshow("control", vis)
                    if show_mask:
                        cv2.imshow("skin", skin_mask)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                n += 1
        finally:
            cap.release()
            if show:
                cv2.destroyAllWindows()

    elapsed = time.perf_counter() - t0
    if ser is not None:
        try:
            ser.close()
        except Exception:
            pass
    logger.info("运行结束, 耗时 %.1f s, 帧数 %d", elapsed, n)


if __name__ == "__main__":
    main()
