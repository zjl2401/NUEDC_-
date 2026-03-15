# -*- coding: utf-8 -*-
"""
2021 国赛 G 题 - 植保飞行器 (Plant Protection UAV)
香橙派 + OpenCV，纯软件模拟：视觉识别与自主巡航。
"""

import os
import sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import cv2
import time
import argparse
import random

import config as cfg
from scene.world import build_map, get_uav_view, get_cell_center
from vision import detector
from uav.uav_agent import UAVAgent, UAVState


def main():
    parser = argparse.ArgumentParser(
        description="2021G 植保飞行器 - 香橙派 + OpenCV 纯软件模拟（视觉识别与自主巡航）"
    )
    parser.add_argument("--mode", default="simulate", choices=["simulate"],
                        help="运行模式，当前仅支持 simulate")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，固定 A/绿色区块布局")
    parser.add_argument("--no-window", action="store_true", help="无界面运行")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 固定布局：A 在 (1,1)，绿色区块为除 A 外的部分格子
    a_block = (1, 1)
    green_cells = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)]
    if args.seed is not None:
        # 可改为随机选 A 和绿色
        pass

    world_img = build_map(a_block, green_cells, seed=args.seed)
    uav = UAVAgent()
    uav.set_mission(a_block, green_cells)

    t0 = time.time()
    frame_count = 0
    while True:
        frame_count += 1
        uav.update(world_img, detector)
        display = world_img.copy()
        # 绘制 UAV 位置
        cx, cy = int(uav.x), int(uav.y)
        cv2.circle(display, (cx, cy), 10, (0, 255, 255), 2)
        cv2.putText(display, uav.state, (cx + 14, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        # 已播撒区块半透明覆盖
        for (r, c) in uav.sprayed_cells:
            gx, gy = get_cell_center(r, c)
            cv2.circle(display, (gx, gy), 8, (0, 255, 0), -1)

        if not args.no_window:
            cv2.imshow("2021G Plant Protection UAV (Simulate)", display)
            key = cv2.waitKey(1000 // cfg.FPS) & 0xFF
            if key == ord("q") or key == ord("Q"):
                break

        if uav.state == UAVState.DONE:
            elapsed = time.time() - t0
            print(f"[完成] 状态: {uav.state}, 降落精度: {'OK' if uav.landing_ok else 'NG'}, 用时: {elapsed:.1f}s")
            if not args.no_window:
                cv2.waitKey(2000)
            break

        if time.time() - t0 > cfg.MISSION_TIMEOUT_S:
            print("[超时] 360s 未完成作业")
            break

    if not args.no_window:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
