# -*- coding: utf-8 -*-
"""
2021 电赛 D 题 - 基于互联网的摄像机入侵检测系统（纯软件模拟）
主入口：摄像头/视频 → 入侵检测 → 本地与网络告警。
"""

import argparse
import yaml
import cv2
from pathlib import Path

from camera import open_source, read_frame
from detector import IntrusionDetector
from alert import AlertManager


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main():
    parser = argparse.ArgumentParser(description="基于互联网的摄像机入侵检测系统（纯软件模拟）")
    parser.add_argument("--source", default="0", help="摄像头索引(0/1)或视频文件路径")
    parser.add_argument("--real", action="store_true", help="强制摄像头模式（source 视为摄像头索引）")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--no-display", action="store_true", help="不显示窗口（无头运行）")
    parser.add_argument("--save-video", default=None, help="保存检测结果视频路径（可选）")
    args = parser.parse_args()

    source = args.source
    if args.real and not str(source).isdigit():
        source = "0"
    if str(source).isdigit():
        source = int(source)

    cfg = load_config(args.config)
    det_cfg = cfg.get("detection", {})
    alert_cfg = cfg.get("alert", {})
    net_cfg = cfg.get("network", {})

    roi = cfg.get("roi")
    detector = IntrusionDetector(
        min_area=det_cfg.get("min_area", 500),
        threshold=det_cfg.get("threshold", 25),
        blur_ksize=det_cfg.get("blur_ksize", 5),
        history=det_cfg.get("history", 500),
        var_threshold=det_cfg.get("var_threshold", 16),
        roi=tuple(roi) if roi else None,
    )

    alert_mgr = AlertManager(
        trigger_frames=alert_cfg.get("trigger_frames", 3),
        cooldown_seconds=alert_cfg.get("cooldown_seconds", 10.0),
        network_enabled=net_cfg.get("enabled", False),
        network_url=net_cfg.get("url", "http://localhost:8080/alert"),
        network_timeout=net_cfg.get("timeout", 5),
    )

    cap = open_source(source)
    display = not args.no_display
    writer = None

    print("启动入侵检测，按 'q' 退出。")
    try:
        while True:
            result = read_frame(cap)
            if result is None:
                break
            _, frame = result

            is_intrusion, frame_out, _ = detector.process(frame)
            triggered = alert_mgr.update(is_intrusion)

            if triggered:
                cv2.putText(
                    frame_out, "ALERT!", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2,
                )

            if display:
                cv2.imshow("2021D Intrusion Detection", frame_out)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if args.save_video:
                if writer is None:
                    h, w = frame_out.shape[:2]
                    writer = cv2.VideoWriter(
                        args.save_video,
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        20.0,
                        (w, h),
                    )
                writer.write(frame_out)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if display:
            cv2.destroyAllWindows()
    print("已退出。")


if __name__ == "__main__":
    main()
