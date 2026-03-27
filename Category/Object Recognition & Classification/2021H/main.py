# -*- coding: utf-8 -*-
"""
2021年电赛H题 - 用电器辨识装置（纯软件模拟）
香橙派 + OpenCV：学习模式 / 分析识别模式，实时显示电器类别与特征参量
"""

import cv2
import numpy as np
import time
import argparse

from config import (
    SAMPLE_RATE,
    APPLIANCE_NAMES,
    ANALYSIS_WINDOW,
    MAX_RESPONSE_TIME_S,
)
from appliance_simulator import generate_appliance_current, generate_voltage_reference
from feature_extractor import extract_features
from classifier import ApplianceClassifier, get_appliance_name


# 显示窗口
WIN_W, WIN_H = 900, 640
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.55
THICKNESS = 1


def put_text_cn(img, text: str, x: int, y: int, color=(255, 255, 255)):
    """OpenCV 不支持中文，用英文/数字占位；实际部署可换 cv2 + PIL 绘中文。"""
    cv2.putText(img, text, (x, y), FONT, FONT_SCALE, color, THICKNESS, cv2.LINE_AA)


def draw_wave(img, data: np.ndarray, x0: int, y0: int, w: int, h: int, color=(0, 255, 0)):
    """在 img 上绘制波形 (x0,y0) 为左上角，w*h 为区域。"""
    if len(data) < 2:
        return
    n = len(data)
    pts = np.column_stack([
        x0 + np.linspace(0, w, n).astype(int),
        y0 + h // 2 - (data - np.mean(data)) / (np.std(data) + 1e-9) * (h * 0.4),
    ]).astype(np.int32)
    pts[:, 1] = np.clip(pts[:, 1], y0, y0 + h - 1)
    cv2.polylines(img, [pts], False, color, 1, cv2.LINE_AA)


def run_learning_mode(clf: ApplianceClassifier, duration_per_appliance: float = 3.0):
    """学习模式：依次对 1~7 号电器采样并存储特征。"""
    for aid in sorted(APPLIANCE_NAMES.keys()):
        print(f"Learning appliance {aid}: {get_appliance_name(aid)} ...")
        samples = 5  # 每个电器采 5 段取平均
        for _ in range(samples):
            i_ma = generate_appliance_current(aid, ANALYSIS_WINDOW)
            v = generate_voltage_reference(ANALYSIS_WINDOW)
            feats = extract_features(i_ma, v)
            clf.add_sample(aid, feats)
        time.sleep(0.2)
    clf.fit()
    clf.save()
    print("Learning done. Model saved.")


def run_recognition_loop(clf: ApplianceClassifier, active_ids: list):
    """
    分析识别模式：根据当前“在用电器”列表 active_ids 模拟电流，
    提取特征并识别，返回识别结果与特征参量。
    """
    duration = ANALYSIS_WINDOW
    if active_ids:
        from appliance_simulator import generate_combined_current
        i_ma = generate_combined_current(active_ids, duration)
    else:
        i_ma = generate_appliance_current(0, duration)  # 无电器时近似为 0
        i_ma = np.zeros_like(i_ma)
    v = generate_voltage_reference(duration)
    feats = extract_features(i_ma, v)
    pred_id = clf.predict_single(feats)
    pred_multi = clf.predict_multi(feats, threshold=2.5)
    return feats, pred_id, pred_multi


def main():
    parser = argparse.ArgumentParser(description="2021H 用电器辨识（模拟/CSV 实采样）")
    parser.add_argument("--csv", type=str, default=None, help="CSV 文件路径（单列电流 mA，或两列: 电流mA,电压V）")
    parser.add_argument("--window-s", type=float, default=ANALYSIS_WINDOW, help="每次识别窗口时长（秒）")
    parser.add_argument("--step-s", type=float, default=ANALYSIS_WINDOW, help="滑窗步长（秒）")
    parser.add_argument("--no-window", action="store_true", help="CSV 模式不显示窗口，仅打印结果")
    args = parser.parse_args()

    clf = ApplianceClassifier()
    try:
        clf.load()
    except Exception:
        pass
    if not getattr(clf, "is_fitted", False):
        print("No model found. Running learning mode first...")
        run_learning_mode(clf)

    if args.csv:
        data = np.loadtxt(args.csv, delimiter=",")
        if data.ndim == 1:
            i_ma_all = data.astype(np.float32)
            v_all = generate_voltage_reference(len(i_ma_all) / SAMPLE_RATE)
        else:
            i_ma_all = data[:, 0].astype(np.float32)
            if data.shape[1] >= 2:
                v_all = data[:, 1].astype(np.float32)
            else:
                v_all = generate_voltage_reference(len(i_ma_all) / SAMPLE_RATE)
        win_n = max(1, int(args.window_s * SAMPLE_RATE))
        step_n = max(1, int(args.step_s * SAMPLE_RATE))
        idx = 0
        print("CSV 实采样识别开始，按 Ctrl+C 可中断。")
        while idx + win_n <= len(i_ma_all):
            i_ma = i_ma_all[idx: idx + win_n]
            v = v_all[idx: idx + win_n]
            feats = extract_features(i_ma, v)
            pred_id = clf.predict_single(feats)
            pred_multi = clf.predict_multi(feats, threshold=2.5)
            print(
                f"[{idx/SAMPLE_RATE:7.2f}s] pred={get_appliance_name(pred_id)} "
                f"multi={[get_appliance_name(a) for a in pred_multi]} "
                f"Irms={feats['rms_ma']:.1f}mA PF={feats['pf']:.3f}"
            )
            idx += step_n
            if not args.no_window:
                # CSV 模式仅用于快速核验，窗口显示简化为一帧文本图
                img = np.zeros((220, 760, 3), dtype=np.uint8)
                img[:] = (35, 35, 40)
                put_text_cn(img, "2021H CSV Real-Sample Recognition", 20, 35, (180, 220, 255))
                put_text_cn(img, f"Time: {idx/SAMPLE_RATE:.2f}s", 20, 68, (200, 200, 200))
                put_text_cn(img, f"Pred: {get_appliance_name(pred_id)}", 20, 104, (200, 255, 200))
                put_text_cn(img, f"Irms={feats['rms_ma']:.1f}mA PF={feats['pf']:.3f}", 20, 138, (220, 220, 220))
                put_text_cn(img, "Q: quit", 20, 178, (200, 180, 180))
                cv2.imshow("H-Appliance Recognition", img)
                k = cv2.waitKey(1) & 0xFF
                if k in (ord("q"), ord("Q"), 27):
                    break
        cv2.destroyAllWindows()
        return

    # 模拟“当前在用电器”（可改为键盘/按钮切换）
    active_ids = [2]  # 默认 2 号 LED 灯
    last_switch = time.time()
    response_start = None

    cv2.namedWindow("H-Appliance Recognition", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("H-Appliance Recognition", WIN_W, WIN_H)

    while True:
        t0 = time.time()
        feats, pred_id, pred_multi = run_recognition_loop(clf, active_ids)
        if response_start is None:
            response_start = t0
        response_time = time.time() - response_start

        # 绘制界面
        img = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
        img[:] = (40, 42, 46)

        y = 28
        put_text_cn(img, "2021 NUEDC H - Appliance Recognition (Simulation)", 20, y, (200, 220, 255))
        y += 28
        mode_text = "Mode: Recognition | Response time: %.2fs (<=2s)" % min(response_time, MAX_RESPONSE_TIME_S)
        put_text_cn(img, mode_text, 20, y, (180, 255, 180))
        y += 26

        # 当前模拟的在用电器
        active_str = ", ".join([get_appliance_name(a) for a in active_ids]) if active_ids else "None"
        put_text_cn(img, "Simulated ON: " + active_str, 20, y, (255, 255, 200))
        y += 24
        put_text_cn(img, "Recognized: " + get_appliance_name(pred_id), 20, y, (200, 255, 200))
        put_text_cn(img, "Multi-match: " + ", ".join([get_appliance_name(a) for a in pred_multi]), 380, y, (200, 255, 200))
        y += 32

        # 特征参量
        cv2.putText(img, "Features: I_rms=%.1f mA  Phase=%.1f deg  PF=%.3f" % (
            feats["rms_ma"], feats["phase_deg"], feats["pf"]), (20, y), FONT, FONT_SCALE, (220, 220, 220), THICKNESS, cv2.LINE_AA)
        y += 22
        cv2.putText(img, "H3=%.3f  H5=%.3f  H7=%.3f" % (
            feats["h3_ratio"], feats["h5_ratio"], feats["h7_ratio"]), (20, y), FONT, FONT_SCALE, (220, 220, 220), THICKNESS, cv2.LINE_AA)
        y += 36

        # 波形区：当前电流
        from appliance_simulator import generate_combined_current
        if active_ids:
            i_ma = generate_combined_current(active_ids, ANALYSIS_WINDOW)
        else:
            i_ma = np.zeros(int(SAMPLE_RATE * ANALYSIS_WINDOW), dtype=np.float32)
        draw_wave(img, i_ma, 20, y, WIN_W - 40, 180, (0, 255, 150))
        put_text_cn(img, "Current waveform (simulated)", 20, y - 4, (200, 200, 200))
        y += 200

        # 按键说明
        put_text_cn(img, "Keys: 1-7 toggle appliance, L=re-learn, Q=quit", 20, y, (180, 180, 200))
        cv2.imshow("H-Appliance Recognition", img)

        key = cv2.waitKey(80) & 0xFF
        if key == ord("q") or key == ord("Q") or key == 27:
            break
        if key == ord("l") or key == ord("L"):
            clf.clear()
            run_learning_mode(clf)
            response_start = None
        if ord("1") <= key <= ord("7"):
            aid = key - ord("0")
            if aid in active_ids:
                active_ids.remove(aid)
            else:
                active_ids.append(aid)
                active_ids.sort()
            response_start = time.time()

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
