# -*- coding: utf-8 -*-
"""
2025电赛C题 - 单目视觉目标物测量 - 主程序（纯软件仿真）
Orange Pi RK3588 + OpenCV：物像建模 + 边缘提取 + 单目测距/测尺寸
"""

import os
import sys
import cv2
import numpy as np
import argparse
import config
from camera_calibration import get_camera_matrix_and_distortion
from edge_detection import (
    detect_circles,
    detect_rectangles,
    detect_edges_canny,
    find_contours,
)
from measurement import (
    measure_circle,
    measure_rectangle,
    distance_from_reference_size,
    real_size_from_distance,
)


def draw_measurements(image: np.ndarray, results: dict, K: np.ndarray) -> np.ndarray:
    """在图像上绘制检测结果与测量文字。"""
    out = image.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    color_circle = (0, 255, 0)
    color_rect = (255, 165, 0)

    for r in results.get("circles", []):
        cx, cy = int(r["center_px"][0]), int(r["center_px"][1])
        r_px = int(r["radius_px"])
        cv2.circle(out, (cx, cy), r_px, color_circle, 2)
        cv2.circle(out, (cx, cy), 2, color_circle, -1)
        text = f"d={r['diameter_m']*100:.1f}cm" if r.get("diameter_m") else f"r={r_px}px"
        if r.get("distance_m") is not None:
            text += f" dist={r['distance_m']*100:.0f}cm"
        cv2.putText(out, text, (cx - 40, cy - r_px - 5), font, scale, color_circle, 1)

    for r in results.get("rectangles", []):
        pts = r["box_points"]
        cv2.drawContours(out, [pts], 0, color_rect, 2)
        cx, cy = int(r["center_px"][0]), int(r["center_px"][1])
        cv2.circle(out, (cx, cy), 3, color_rect, -1)
        w_m = r.get("width_m")
        h_m = r.get("height_m")
        if w_m is not None and h_m is not None:
            text = f"{w_m*100:.1f}x{h_m*100:.1f}cm"
        else:
            text = f"{r['width_px']:.0f}x{r['height_px']:.0f}px"
        if r.get("distance_m") is not None:
            text += f" d={r['distance_m']*100:.0f}cm"
        cv2.putText(out, text, (cx - 30, cy - 15), font, scale, color_rect, 1)

    return out


def run_measurement(
    image: np.ndarray,
    reference_real_size_m: float = None,
    plane_distance_m: float = None,
    use_plane_for_scale: bool = True,
) -> tuple:
    """
    对单张图像执行：标定加载 -> 圆/矩形检测 -> 尺寸与距离估计。
    reference_real_size_m: 已知参考物尺寸(米)，用于反推距离；若为 None 且给 plane_distance_m 则用平面距离推算尺寸。
    plane_distance_m: 假设目标所在平面与相机的距离(米)。
    use_plane_for_scale: 若 True 且给 plane_distance_m，用该距离换算像素到世界尺寸。
    """
    h, w = image.shape[:2]
    K, dist = get_camera_matrix_and_distortion(image_size=(h, w))

    # 若图像有畸变可先去畸变（这里简化不处理）
    # image_undist = cv2.undistort(image, K, dist)

    circles_px = detect_circles(image)
    rects = detect_rectangles(image)

    # 测量：优先用参考尺寸反推距离，否则用平面距离推算尺寸
    ref_m = reference_real_size_m if reference_real_size_m is not None else config.REFERENCE_OBJECT_REAL_HEIGHT_M
    plane_z = plane_distance_m if plane_distance_m is not None else config.DEFAULT_CAMERA_HEIGHT_M
    fx = (K[0, 0] + K[1, 1]) / 2.0

    circle_results = []
    for (cx, cy, r) in circles_px:
        if use_plane_for_scale and plane_z > 0:
            circle_results.append(measure_circle(
                (cx, cy), r, K, distance_m=plane_z,
            ))
        else:
            circle_results.append(measure_circle(
                (cx, cy), r, K,
                real_diameter_m=ref_m,
            ))
    # 统一用 ref 反推距离时
    if not use_plane_for_scale and ref_m > 0 and circle_results:
        for cr in circle_results:
            if cr.get("distance_m") is None:
                cr["distance_m"] = distance_from_reference_size(
                    fx, ref_m, cr["diameter_px"]
                )
                cr["diameter_m"] = ref_m

    rect_results = []
    for rect in rects:
        c = rect["center"]
        wp, hp = rect["width_px"], rect["height_px"]
        if use_plane_for_scale and plane_z > 0:
            rr = measure_rectangle(c, wp, hp, K, distance_m=plane_z)
        else:
            rr = measure_rectangle(
                c, wp, hp, K,
                real_width_m=ref_m,
                real_height_m=ref_m,
            )
        rr["center_px"] = c
        rr["width_px"] = wp
        rr["height_px"] = hp
        rr["box_points"] = rect["box_points"]
        rect_results.append(rr)

    results = {"circles": circle_results, "rectangles": rect_results}
    vis = draw_measurements(image, results, K)
    return results, vis, K


def main():
    """入口：文件测量 / 实时摄像头测量 / 仿真图测量。"""
    parser = argparse.ArgumentParser(description="2025C 单目视觉目标测量")
    parser.add_argument("image", nargs="?", default=None, help="输入图像路径（可选）")
    parser.add_argument("--real", action="store_true", help="实时摄像头模式")
    parser.add_argument("--cam", type=int, default=0, help="摄像头索引（实时模式）")
    parser.add_argument("--width", type=int, default=640, help="实时模式采集宽度")
    parser.add_argument("--height", type=int, default=480, help="实时模式采集高度")
    parser.add_argument("--max-frames", type=int, default=None, help="实时模式最多处理帧数")
    parser.add_argument("--plane-distance", type=float, default=config.DEFAULT_CAMERA_HEIGHT_M, help="测量平面距离（米）")
    parser.add_argument("--save-dir", type=str, default=config.PROJECT_ROOT, help="结果保存目录")
    args = parser.parse_args()

    os.makedirs(config.SAMPLE_IMAGES_DIR, exist_ok=True)
    os.makedirs(config.CALIBRATION_DIR, exist_ok=True)
    os.makedirs(args.save_dir, exist_ok=True)

    # 1) 若命令行给图像路径，则对该图测量
    if args.image:
        path = args.image
        if not os.path.isfile(path):
            print(f"文件不存在: {path}")
            return
        image = cv2.imread(path)
        if image is None:
            print("无法读取图像")
            return
        results, vis, _ = run_measurement(
            image,
            plane_distance_m=args.plane_distance,
            use_plane_for_scale=True,
        )
        out_path = os.path.join(args.save_dir, "output_measurement.png")
        cv2.imwrite(out_path, vis)
        print(f"结果已保存: {out_path}")
        print("圆数量:", len(results["circles"]))
        print("矩形数量:", len(results["rectangles"]))
        for i, c in enumerate(results["circles"]):
            print(f"  圆{i+1}: 直径={c.get('diameter_m')} m, 距离={c.get('distance_m')} m")
        for i, r in enumerate(results["rectangles"]):
            print(f"  矩形{i+1}: 宽={r.get('width_m')} m 高={r.get('height_m')} m 距离={r.get('distance_m')} m")
        cv2.imshow("Measurement", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    # 2) 实时摄像头模式
    if args.real:
        cap = cv2.VideoCapture(args.cam)
        if not cap.isOpened():
            print(f"无法打开摄像头: {args.cam}")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        print("实时测量已启动，按 Q 退出。")
        frame_idx = 0
        try:
            while True:
                if args.max_frames is not None and frame_idx >= args.max_frames:
                    break
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                frame = cv2.resize(frame, (args.width, args.height))
                results, vis, _ = run_measurement(
                    frame,
                    plane_distance_m=args.plane_distance,
                    use_plane_for_scale=True,
                )
                cv2.putText(
                    vis,
                    f"circles={len(results['circles'])} rects={len(results['rectangles'])}",
                    (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow("2025C Real Measurement", vis)
                frame_idx += 1
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
        return

    # 3) 无参数：生成仿真图并测量
    w, h = 640, 480
    img = np.ones((h, w, 3), dtype=np.uint8) * 240
    cv2.circle(img, (320, 240), 80, (80, 80, 80), -1)
    cv2.circle(img, (320, 240), 80, (0, 0, 0), 2)
    cv2.rectangle(img, (100, 100), (220, 200), (100, 100, 100), -1)
    cv2.rectangle(img, (100, 100), (220, 200), (0, 0, 0), 2)
    # 加少量噪声模拟真实
    noise = np.random.randint(-10, 10, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    sim_path = os.path.join(config.SAMPLE_IMAGES_DIR, "sim_targets.png")
    cv2.imwrite(sim_path, img)
    print("已生成仿真图:", sim_path)

    results, vis, _ = run_measurement(
        img,
        plane_distance_m=args.plane_distance if args.plane_distance else 0.5,
        use_plane_for_scale=True,
    )
    out_path = os.path.join(args.save_dir, "output_sim.png")
    cv2.imwrite(out_path, vis)
    print("仿真测量结果已保存:", out_path)
    print("圆:", len(results["circles"]), "矩形:", len(results["rectangles"]))
    cv2.imshow("Simulation", vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
