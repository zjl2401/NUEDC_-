# -*- coding: utf-8 -*-
"""从电流（及电压）采样中提取特征参量：RMS、功率因数、谐波含量等"""

import numpy as np
from scipy import signal
from config import SAMPLE_RATE, LINE_FREQ, VOLTAGE_RMS


def compute_rms(x: np.ndarray) -> float:
    """电流有效值 (mA)。"""
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def compute_phase_deg(current_ma: np.ndarray, voltage_v: np.ndarray) -> float:
    """
    通过互相关估计电流相对电压的相位差（度）。
    电流、电压长度需一致，单位：mA、V。
    """
    if len(current_ma) != len(voltage_v) or len(current_ma) < 10:
        return 0.0
    c = current_ma.astype(np.float64) / (np.max(np.abs(current_ma)) + 1e-9)
    v = voltage_v.astype(np.float64) / (np.max(np.abs(voltage_v)) + 1e-9)
    corr = signal.correlate(c, v, mode="same")
    n = len(c)
    mid = n // 2
    # 找峰值位置偏移
    win = corr[mid - n // 4 : mid + n // 4]
    if len(win) < 2:
        return 0.0
    peak_idx = np.argmax(win) - len(win) // 2
    # 采样点数 -> 相位（一个周期 = SAMPLE_RATE/LINE_FREQ 点）
    samples_per_cycle = SAMPLE_RATE / LINE_FREQ
    phase_rad = 2 * np.pi * peak_idx / samples_per_cycle
    return float(np.rad2deg(phase_rad))


def compute_power_factor(phase_deg: float) -> float:
    """功率因数 ≈ cos(电流相对电压的相位差)。"""
    return float(np.cos(np.deg2rad(phase_deg)))


def compute_harmonic_ratio(i_ma: np.ndarray, fundamental_hz: float = LINE_FREQ) -> list:
    """
    返回 3、5、7 次谐波与基波幅值比 [H3, H5, H7]。
    """
    n = len(i_ma)
    if n < 64:
        return [0.0, 0.0, 0.0]
    fft = np.fft.rfft(i_ma.astype(np.float64))
    freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
    idx_f1 = int(round(fundamental_hz / df))
    if idx_f1 >= len(fft):
        return [0.0, 0.0, 0.0]
    a1 = np.abs(fft[idx_f1])
    if a1 < 1e-9:
        a1 = 1e-9
    ratios = []
    for k in [3, 5, 7]:
        idx = int(round(k * fundamental_hz / df))
        if idx < len(fft):
            ratios.append(float(np.abs(fft[idx]) / a1))
        else:
            ratios.append(0.0)
    return ratios


def extract_features(current_ma: np.ndarray, voltage_v: np.ndarray = None) -> dict:
    """
    提取一组特征参量，用于识别电器。
    返回：rms_ma, phase_deg, pf, h3_ratio, h5_ratio, h7_ratio
    """
    rms_ma = compute_rms(current_ma)
    phase_deg = 0.0
    if voltage_v is not None and len(voltage_v) == len(current_ma):
        phase_deg = compute_phase_deg(current_ma, voltage_v)
    pf = compute_power_factor(phase_deg)
    h3, h5, h7 = compute_harmonic_ratio(current_ma)
    return {
        "rms_ma": rms_ma,
        "phase_deg": phase_deg,
        "pf": pf,
        "h3_ratio": h3,
        "h5_ratio": h5,
        "h7_ratio": h7,
    }


if __name__ == "__main__":
    from appliance_simulator import generate_appliance_current, generate_voltage_reference
    for aid in [1, 2, 7]:
        dur = 0.2
        i = generate_appliance_current(aid, dur)
        v = generate_voltage_reference(dur)
        f = extract_features(i, v)
        print(f"Appliance {aid}: {f}")
