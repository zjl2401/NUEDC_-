# -*- coding: utf-8 -*-
"""
2005 E题 - 悬挂运动控制系统 纯软件模拟与 OpenCV 可视化
"""
import math
import time
from typing import List, Tuple, Optional, Callable

import cv2
import numpy as np

from kinematics import (
    BOARD_WIDTH,
    BOARD_HEIGHT,
    LEFT_MOTOR,
    RIGHT_MOTOR,
    forward_kinematics,
    inverse_kinematics,
    check_workspace,
)
from trajectory import (
    trajectory_line,
    trajectory_circle,
    trajectory_square,
    trajectory_arbitrary,
    points_to_string_lengths,
    validate_trajectory,
)
from motor_control import MotorController

# 显示尺寸 (像素)，板面 80x100 cm 按比例缩放
DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 800
SCALE_X = DISPLAY_WIDTH / BOARD_WIDTH
SCALE_Y = DISPLAY_HEIGHT / BOARD_HEIGHT


def cm_to_pixel(x_cm: float, y_cm: float) -> Tuple[int, int]:
    """板面坐标 (cm) 转图像坐标 (像素)。原点左下，y 向上；图像 y 向下。"""
    px = int(x_cm * SCALE_X)
    py = int(DISPLAY_HEIGHT - y_cm * SCALE_Y)
    return (px, py)


def pixel_to_cm(px: int, py: int) -> Tuple[float, float]:
    """图像坐标转板面坐标 (cm)。"""
    x_cm = px / SCALE_X
    y_cm = (DISPLAY_HEIGHT - py) / SCALE_Y
    return (x_cm, y_cm)


class SuspendedPenSimulator:
    """悬挂画笔仿真器：维护当前拉线长度，用正解得到笔位置并绘制。"""

    def __init__(self, motor: Optional[MotorController] = None):
        self.motor = motor or MotorController(simulate=True)
        # 轨迹绘制缓存（已画过的轨迹）
        self.trajectory_canvas = None
        self.reset_canvas()
        # 当前笔位置 (cm)，由 motor 的 L1,L2 正解得到
        self._update_pen_position()

    def reset_canvas(self) -> None:
        self.trajectory_canvas = np.ones((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8) * 255

    def _update_pen_position(self) -> Tuple[float, float]:
        L1, L2 = self.motor.get_current_lengths()
        x, y = forward_kinematics(L1, L2)
        return (x, y)

    @property
    def pen_position_cm(self) -> Tuple[float, float]:
        return self._update_pen_position()

    def set_pen_position_cm(self, x: float, y: float) -> None:
        """直接设置笔位置（通过逆解更新拉线长度）。"""
        L1, L2 = inverse_kinematics(x, y)
        self.motor.set_initial_lengths(L1, L2)

    def run_trajectory(
        self,
        points_cm: List[Tuple[float, float]],
        speed_cm_s: float = 3.0,
        draw: bool = True,
        dt: float = 0.03,
        on_step: Optional[Callable[["SuspendedPenSimulator"], None]] = None,
    ) -> None:
        """
        沿给定轨迹点序列运动，每段匀速。
        draw: 是否在画布上绘制轨迹（模拟画笔）。
        on_step: 每步执行后的回调，用于动画刷新窗口，签名为 (self) -> None。
        """
        if not points_cm:
            return
        ok, errs = validate_trajectory(points_cm)
        if not ok:
            print("轨迹越界:", errs)
            return
        lengths_seq = points_to_string_lengths(points_cm)
        seg_len = 0.0
        for i in range(1, len(points_cm)):
            seg_len += math.sqrt(
                (points_cm[i][0] - points_cm[i - 1][0]) ** 2
                + (points_cm[i][1] - points_cm[i - 1][1]) ** 2
            )
        total_time = seg_len / speed_cm_s if speed_cm_s > 0 else 0.1
        step_time = total_time / max(1, len(points_cm) - 1)

        for i, (x, y) in enumerate(points_cm):
            L1, L2 = lengths_seq[i]
            self.motor.move_to_lengths(L1, L2, block=True, duration_sec=step_time if i > 0 else 0)
            if draw and i > 0:
                pt0 = cm_to_pixel(points_cm[i - 1][0], points_cm[i - 1][1])
                pt1 = cm_to_pixel(x, y)
                cv2.line(self.trajectory_canvas, pt0, pt1, (0, 0, 0), 2)
            if on_step:
                on_step(self)
        return

    def draw_frame(self, frame: np.ndarray) -> None:
        """在 frame 上绘制：板面边框、电机、拉线、笔、已画轨迹。"""
        # 板面白底 + 已画轨迹
        board = self.trajectory_canvas.copy()
        # 边框
        cv2.rectangle(board, (0, 0), (DISPLAY_WIDTH - 1, DISPLAY_HEIGHT - 1), (100, 100, 100), 2)
        # 电机位置（小圆）
        ml = cm_to_pixel(LEFT_MOTOR[0], LEFT_MOTOR[1])
        mr = cm_to_pixel(RIGHT_MOTOR[0], RIGHT_MOTOR[1])
        cv2.circle(board, ml, 8, (0, 0, 200), -1)
        cv2.circle(board, mr, 8, (0, 0, 200), -1)
        cv2.putText(board, "L", (ml[0] - 6, ml[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255))
        cv2.putText(board, "R", (mr[0] - 6, mr[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255))
        # 拉线
        x, y = self.pen_position_cm
        pen_px = cm_to_pixel(x, y)
        cv2.line(board, ml, pen_px, (180, 180, 180), 1)
        cv2.line(board, mr, pen_px, (180, 180, 180), 1)
        # 画笔（圆点）
        cv2.circle(board, pen_px, 6, (200, 0, 0), -1)
        cv2.putText(
            board,
            f"({x:.1f},{y:.1f})",
            (pen_px[0] + 8, pen_px[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 100, 0),
        )
        # 叠加到输出
        frame[:] = board

    def get_frame(self) -> np.ndarray:
        out = np.zeros((DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype=np.uint8)
        self.draw_frame(out)
        return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="2005 E题 悬挂运动控制系统 - 模拟与演示")
    parser.add_argument("--sim", action="store_true", default=True, help="纯软件模拟（默认）")
    parser.add_argument("--no-sim", action="store_false", dest="sim", help="接真实电机（香橙派）")
    parser.add_argument("--demo", action="store_true", help="自动演示：起点→点→直线→圆→正方形")
    parser.add_argument("--animate", action="store_true", help="演示时逐步动画显示（与 --demo 同用）")
    parser.add_argument("--steps-per-cm", type=float, default=50.0, help="每厘米对应步数（机械标定）")
    parser.add_argument("--max-speed", type=float, default=200.0, help="最大步频（steps/s）")
    parser.add_argument("--left-step-pin", type=int, default=31, help="左电机 STEP（BOARD）")
    parser.add_argument("--left-dir-pin", type=int, default=33, help="左电机 DIR（BOARD）")
    parser.add_argument("--left-en-pin", type=int, default=None, help="左电机 EN（BOARD，可选）")
    parser.add_argument("--right-step-pin", type=int, default=35, help="右电机 STEP（BOARD）")
    parser.add_argument("--right-dir-pin", type=int, default=37, help="右电机 DIR（BOARD）")
    parser.add_argument("--right-en-pin", type=int, default=None, help="右电机 EN（BOARD，可选）")
    parser.add_argument("--invert-left-dir", action="store_true", help="反转左电机方向逻辑")
    parser.add_argument("--invert-right-dir", action="store_true", help="反转右电机方向逻辑")
    args = parser.parse_args()

    motor = MotorController(
        simulate=args.sim,
        steps_per_cm=args.steps_per_cm,
        max_speed_steps_per_sec=args.max_speed,
        left_step_pin=args.left_step_pin,
        left_dir_pin=args.left_dir_pin,
        left_en_pin=args.left_en_pin,
        right_step_pin=args.right_step_pin,
        right_dir_pin=args.right_dir_pin,
        right_en_pin=args.right_en_pin,
        left_dir_positive=not args.invert_left_dir,
        right_dir_positive=not args.invert_right_dir,
    )
    if not args.sim:
        print("[Real Mode] STEP/DIR config loaded:")
        print(
            f" L: STEP={args.left_step_pin} DIR={args.left_dir_pin} EN={args.left_en_pin} "
            f"dir_positive={not args.invert_left_dir}"
        )
        print(
            f" R: STEP={args.right_step_pin} DIR={args.right_dir_pin} EN={args.right_en_pin} "
            f"dir_positive={not args.invert_right_dir}"
        )
        print(f" steps_per_cm={args.steps_per_cm}, max_speed={args.max_speed} steps/s")
    sim = SuspendedPenSimulator(motor)

    # 起始点：题目常规定为左下角附近，如 (10, 10) cm
    start_cm = (10.0, 10.0)
    if not check_workspace(start_cm[0], start_cm[1]):
        start_cm = (10.0, 10.0)
    sim.set_pen_position_cm(start_cm[0], start_cm[1])

    if args.demo:
        win_demo = "2005 E - Suspended Motion (Demo)"
        cv2.namedWindow(win_demo)
        def show_step(s: "SuspendedPenSimulator") -> None:
            if args.animate:
                cv2.imshow(win_demo, s.get_frame())
                cv2.waitKey(1)
        on_step = show_step if args.animate else None
        # 演示轨迹
        pts_line = trajectory_line(start_cm, (50.0, 50.0), speed_cm_s=4.0)
        sim.run_trajectory(pts_line, speed_cm_s=4.0, draw=True, on_step=on_step)
        pts_circle = trajectory_circle((40.0, 50.0), 20.0, speed_cm_s=5.0)
        sim.run_trajectory(pts_circle, speed_cm_s=5.0, draw=True, on_step=on_step)
        pts_sq = trajectory_square((65.0, 50.0), 25.0, speed_cm_s=3.0)
        sim.run_trajectory(pts_sq, speed_cm_s=3.0, draw=True, on_step=on_step)
        cv2.imshow(win_demo, sim.get_frame())
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # 交互：实时显示，按键执行动作
    win = "2005 E - Suspended Motion (Sim)" if args.sim else "2005 E - Suspended Motion"
    cv2.namedWindow(win)

    while True:
        frame = sim.get_frame()
        cv2.putText(
            frame,
            "Keys: 1=Go(40,60) 2=Line 3=Circle 4=Square C=Clear Q=Quit",
            (10, DISPLAY_HEIGHT - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (0, 0, 0),
        )
        cv2.imshow(win, frame)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q") or key == 27:
            break
        if key == ord("c"):
            sim.reset_canvas()
            continue
        if key == ord("1"):
            pts = trajectory_line(sim.pen_position_cm, (40.0, 60.0), speed_cm_s=3.0)
            sim.run_trajectory(pts, speed_cm_s=3.0, draw=True)
        if key == ord("2"):
            pts = trajectory_line(sim.pen_position_cm, (70.0, 80.0), speed_cm_s=3.0)
            sim.run_trajectory(pts, speed_cm_s=3.0, draw=True)
        if key == ord("3"):
            pts = trajectory_circle((40.0, 50.0), 18.0, speed_cm_s=4.0)
            sim.run_trajectory(pts, speed_cm_s=4.0, draw=True)
        if key == ord("4"):
            pts = trajectory_square((40.0, 50.0), 20.0, speed_cm_s=3.0)
            sim.run_trajectory(pts, speed_cm_s=3.0, draw=True)

    cv2.destroyAllWindows()
    motor.close()


if __name__ == "__main__":
    main()
