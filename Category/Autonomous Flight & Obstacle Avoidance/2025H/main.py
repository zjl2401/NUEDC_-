# -*- coding: utf-8 -*-
"""
野生动物巡查系统 - 香橙派 / 纯软件模拟 主程序
运行：python main.py [--video 视频路径 | --simulate] ...
- 从“识别”到“感知”：运动目标检测 + 几何过滤，适应非固定形态与低信噪比
- 纯软件模拟：--simulate 合成场景，--video 用本地视频，无需摄像头
"""
from __future__ import annotations

import time
import argparse
import logging

import config as cfg
from perception import WildlifePerception
from simulate import synthetic_frame_generator, video_file_generator

logging.basicConfig(
    level=getattr(logging, getattr(cfg, "LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="野生动物巡查感知 - 香橙派 + OpenCV / 纯软件模拟")
    parser.add_argument("--cam", type=int, default=cfg.CAM_INDEX, help="摄像头设备号（默认 0）")
    parser.add_argument("--video", type=str, default=None, help="使用视频文件代替摄像头（纯软件）")
    parser.add_argument("--simulate", action="store_true", help="使用合成场景，无需摄像头与视频")
    parser.add_argument("--real", action="store_true", help="强制实时摄像头模式（忽略 --video/--simulate）")
    parser.add_argument("--width", type=int, default=cfg.PROC_WIDTH, help="处理宽度")
    parser.add_argument("--height", type=int, default=cfg.PROC_HEIGHT, help="处理高度")
    parser.add_argument("--no-show", action="store_true", help="不显示窗口（无屏/SSH 时省电）")
    parser.add_argument("--max-frames", type=int, default=None, help="最多处理帧数，默认无限")
    parser.add_argument("--delay", type=int, default=30, help="模拟时每帧延迟 ms（--simulate/--video）")
    args = parser.parse_args()
    if args.real:
        args.simulate = False
        args.video = None

    perception = WildlifePerception(
        cam_index=args.video if args.video else args.cam,
        width=args.width,
        height=args.height,
        target_fps=cfg.TARGET_FPS,
        process_every_n=cfg.PROCESS_EVERY_N_FRAMES,
        idle_sleep_frames=cfg.IDLE_SLEEP_FRAMES,
    )

    def on_detection(frame, fg_mask, targets):
        if targets:
            logger.info("检测到 %d 个目标 (小目标: %d)", len(targets), sum(1 for t in targets if t[2]))
        return True

    show = not args.no_show
    t0 = time.perf_counter()

    if args.simulate:
        logger.info("纯软件模拟：合成野外场景 + 运动目标 (分辨率 %dx%d)", args.width, args.height)
        gen = synthetic_frame_generator(args.width, args.height, max_frames=args.max_frames)
        perception.run_loop_with_generator(
            gen,
            callback=on_detection,
            show=show,
            max_frames=args.max_frames,
            delay_ms=args.delay,
        )
    elif args.video:
        logger.info("纯软件模拟：视频文件 %s (分辨率 %dx%d)", args.video, args.width, args.height)
        gen = video_file_generator(args.video, resize=(args.width, args.height), max_frames=args.max_frames)
        perception.run_loop_with_generator(
            gen,
            callback=on_detection,
            show=show,
            max_frames=args.max_frames,
            delay_ms=args.delay,
        )
    else:
        logger.info("实时摄像头 (设备 %s, 分辨率 %dx%d)", args.cam, args.width, args.height)
        perception.run_loop(
            callback=on_detection,
            show=show,
            max_frames=args.max_frames,
        )

    elapsed = time.perf_counter() - t0
    logger.info("运行结束, 耗时 %.1f s", elapsed)


if __name__ == "__main__":
    main()
