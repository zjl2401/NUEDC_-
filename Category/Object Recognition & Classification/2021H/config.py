# -*- coding: utf-8 -*-
"""用电器辨识装置 - 配置与电器定义"""

# 采样参数（模拟 ADC）
SAMPLE_RATE = 4000   # 采样率 Hz（满足 Nyquist，可分析谐波）
LINE_FREQ = 50       # 工频 50Hz
VOLTAGE_RMS = 220    # 额定电压 V

# 电器编号与名称（符合题目：≥7种，1~5 小电流≤50mA，7号>8A）
APPLIANCE_NAMES = {
    1: "1号-自制电器(阻容二极管)",
    2: "2号-LED灯泡",
    3: "3号-节能灯管",
    4: "4号-USB充电器",
    5: "5号-无线路由器",
    6: "6号-电风扇",
    7: "7号-电磁炉/热水壶",
}

# 每种电器模拟参数：电流有效值(mA)、功率因数、谐波成分等
# 题目：1号与2号电流相同但相位不同且含谐波，电流差<1mA
APPLIANCE_PARAMS = {
    1: {"i_rms_ma": 25, "pf": 0.55, "phase_deg": 45, "harmonics": [0.3, 0.15, 0.08]},   # 自制，谐波丰富
    2: {"i_rms_ma": 25, "pf": 0.95, "phase_deg": 18, "harmonics": [0.02, 0.01, 0.005]}, # LED，接近正弦
    3: {"i_rms_ma": 120, "pf": 0.6, "phase_deg": 53, "harmonics": [0.25, 0.12, 0.06]},   # 节能灯
    4: {"i_rms_ma": 80, "pf": 0.7, "phase_deg": 45, "harmonics": [0.2, 0.1, 0.05]},     # USB充电器
    5: {"i_rms_ma": 35, "pf": 0.65, "phase_deg": 50, "harmonics": [0.15, 0.08, 0.04]},  # 路由器
    6: {"i_rms_ma": 350, "pf": 0.85, "phase_deg": 32, "harmonics": [0.05, 0.02, 0.01]},  # 电风扇
    7: {"i_rms_ma": 8500, "pf": 0.92, "phase_deg": 23, "harmonics": [0.03, 0.02, 0.01]}, # 大电流>8A
}

# 识别窗口：每段分析时长（秒）
ANALYSIS_WINDOW = 0.2
# 响应时间要求 ≤2s
MAX_RESPONSE_TIME_S = 2.0
