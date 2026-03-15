# -*- coding: utf-8 -*-
"""电器电流波形模拟器：根据电器类型生成带谐波、相位的电流采样序列"""

import numpy as np
from config import SAMPLE_RATE, LINE_FREQ, APPLIANCE_PARAMS


def generate_appliance_current(appliance_id: int, duration_s: float, noise_std: float = 0.5) -> np.ndarray:
    """
    生成指定电器的电流波形（基波 + 谐波 + 相位 + 噪声）。
    电流单位：mA（毫安）。
    """
    if appliance_id not in APPLIANCE_PARAMS:
        return np.zeros(int(SAMPLE_RATE * duration_s))
    p = APPLIANCE_PARAMS[appliance_id]
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    omega = 2 * np.pi * LINE_FREQ
    # 基波：I*sin(ωt - φ)，幅值 = I_rms * sqrt(2)
    i_rms = p["i_rms_ma"] / 1000.0  # 转为 A 便于计算幅值
    phase_rad = np.deg2rad(p["phase_deg"])
    current = (i_rms * np.sqrt(2)) * np.sin(omega * t - phase_rad)
    # 3、5、7 次谐波
    for k, h_ratio in enumerate(p["harmonics"], start=3):
        if k % 2 == 0:
            continue
        current += (i_rms * np.sqrt(2) * h_ratio) * np.sin(k * omega * t - phase_rad * 1.2)
    # 转回 mA
    current_ma = current * 1000.0
    if noise_std > 0:
        current_ma += np.random.normal(0, noise_std, n)
    return current_ma.astype(np.float32)


def generate_voltage_reference(duration_s: float) -> np.ndarray:
    """生成参考电压波形 (V)，用于计算功率因数/相位。"""
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    from config import VOLTAGE_RMS
    v = VOLTAGE_RMS * np.sqrt(2) * np.sin(2 * np.pi * LINE_FREQ * t)
    return v.astype(np.float32)


def generate_combined_current(active_ids: list, duration_s: float, noise_std: float = 0.5) -> np.ndarray:
    """多电器同时用电时，电流为各电器电流之和。"""
    n = int(SAMPLE_RATE * duration_s)
    total = np.zeros(n, dtype=np.float32)
    for aid in active_ids:
        total += generate_appliance_current(aid, duration_s, noise_std=0)
    if noise_std > 0:
        total += np.random.normal(0, noise_std, n).astype(np.float32)
    return total


if __name__ == "__main__":
    # 简单测试
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for aid in [1, 2, 7]:
        y = generate_appliance_current(aid, 0.1)
        plt.figure()
        plt.plot(np.arange(len(y)) / SAMPLE_RATE * 1000, y)
        plt.title(f"Appliance {aid}")
        plt.xlabel("t (ms)")
        plt.ylabel("I (mA)")
        plt.savefig(f"test_current_{aid}.png")
        plt.close()
    print("Generated test_current_1.png, test_current_2.png, test_current_7.png")
