# -*- coding: utf-8 -*-
"""
2023 电赛 G 题 - 空地协同智能消防系统
香橙派 + OpenCV，纯软件模拟：无人机上帝视角搜火源，小车接收坐标避障灭火。
"""
import os
import sys
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import cv2
import time
import argparse

import config as cfg
from scene import World
from vision import detect_fire_sources
from comm import CommChannel, FireReport
from uav import UAVAgent
from ground import GroundVehicle


def run_simulate(seed: int = None, show_window: bool = True):
    world = World(
        width=cfg.WORLD_WIDTH,
        height=cfg.WORLD_HEIGHT,
        seed=seed,
    )
    # 固定一个火源（也可 world.add_fire_random() 随机）
    fire = world.add_fire(world.w * 0.65, world.h * 0.55, radius=28)
    # 可选：再放一个火源
    # world.add_fire_random(margin=100)

    channel = CommChannel(latency_frames=getattr(cfg, "COMM_LATENCY_FRAMES", 0))
    uav = UAVAgent(channel, (world.w, world.h))
    vehicle = GroundVehicle(channel, world.obstacles, (world.w, world.h))

    def on_fire_extinguished(fx: float, fy: float):
        for f in world.fires:
            if not f.extinguished and abs(f.x - fx) < 50 and abs(f.y - fy) < 50:
                f.extinguished = True
                print(f"[灭火] 火源已扑灭 @ ({f.x:.0f}, {f.y:.0f})")
                break

    frame_id = 0
    t0 = time.time()
    print("2023G 空地协同消防模拟 - 按 Q 退出")
    print("无人机俯视搜火 → 坐标下发 → 小车避障前往 → 灭火")

    while True:
        frame_id += 1
        channel.tick()
        vx, vy = vehicle.position
        uav_view = world.get_uav_view(vehicle_xy=(vx, vy), uav_xy=None)
        detections = uav.update(uav_view)
        vehicle.update(world_fires_extinguish_callback=on_fire_extinguished)

        # 绘制
        frame = world.render(vehicle_xy=(vx, vy), uav_xy=None)
        if detections:
            for d in detections[:1]:
                cv2.circle(frame, (int(d.x), int(d.y)), 8, (0, 255, 255), 2)
                cv2.putText(frame, "UAV see", (int(d.x) + 10, int(d.y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        if vehicle.state.path:
            for i, (gx, gy) in enumerate(vehicle.state.path):
                wx, wy = world.obstacles.grid_to_world(gx, gy)
                cv2.circle(frame, (wx, wy), 2, (200, 200, 0), -1)
        if vehicle.is_extinguishing:
            cv2.putText(frame, "EXTINGUISHING...", (int(vx) - 50, int(vy) - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        elapsed = time.time() - t0
        cv2.putText(frame, f"F{frame_id} | t={elapsed:.1f}s", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        active = world.get_active_fires()
        cv2.putText(frame, f"Fires left: {len(active)}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        if show_window:
            cv2.imshow("2023G Air-Ground Firefighting", frame)
        key = cv2.waitKey(1000 // getattr(cfg, "FPS", 30)) & 0xFF
        if key == ord("q"):
            break
        if len(world.get_active_fires()) == 0:
            cv2.putText(frame, "Mission Complete!", (world.w // 2 - 80, world.h // 2 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)
            if show_window:
                cv2.imshow("2023G Air-Ground Firefighting", frame)
            cv2.waitKey(2000)
            break

    cv2.destroyAllWindows()
    print("任务结束")


def main():
    parser = argparse.ArgumentParser(description="2023G 空地协同智能消防系统（纯软件模拟）")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-window", action="store_true", help="不显示窗口")
    args = parser.parse_args()
    run_simulate(seed=args.seed, show_window=not args.no_window)


if __name__ == "__main__":
    main()
