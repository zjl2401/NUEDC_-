#!/usr/bin/env python3
"""
香橙派 + OpenCV 智能送药车 — 运行入口。
在项目根目录 2021F 下执行：
  python run.py
或指定目标房号：
  python run.py --room 2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证从项目根目录可导入 src
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.main import main_loop


def main():
    parser = argparse.ArgumentParser(description="智能送药车主程序（香橙派 + OpenCV）")
    parser.add_argument("--room", type=int, default=1, help="目标房号 (1-9)")
    parser.add_argument("--no-camera", action="store_true", help="不启用摄像头（仅循线/传感器）")
    parser.add_argument("--sim", action="store_true", help="纯软件仿真模式（无需硬件，带可视化）")
    parser.add_argument("--no-sim-window", action="store_true", help="仿真时不弹出可视化窗口")
    parser.add_argument("--hz", type=float, default=50, help="主循环频率")
    args = parser.parse_args()
    use_sim = args.sim
    main_loop(
        target_room=args.room,
        use_camera=not args.no_camera if not use_sim else False,
        loop_hz=args.hz,
        use_sim=use_sim,
        show_sim_window=use_sim and not args.no_sim_window,
    )


if __name__ == "__main__":
    main()
