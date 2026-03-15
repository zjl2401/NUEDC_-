# -*- coding: utf-8 -*-
"""
告警模块：本地打印 + 可选的 HTTP 上报，模拟“基于互联网”的入侵告警。
"""

import time
import json
from typing import Optional

try:
    import requests
except ImportError:
    requests = None


class AlertManager:
    """入侵告警管理：防抖、冷却、本地与网络上报。"""

    def __init__(
        self,
        trigger_frames: int = 3,
        cooldown_seconds: float = 10.0,
        network_enabled: bool = False,
        network_url: str = "http://localhost:8080/alert",
        network_timeout: int = 5,
    ):
        self.trigger_frames = trigger_frames
        self.cooldown_seconds = cooldown_seconds
        self.network_enabled = network_enabled and requests is not None
        self.network_url = network_url
        self.network_timeout = network_timeout

        self._intrusion_count = 0
        self._last_alert_time: Optional[float] = None

    def update(self, is_intrusion: bool) -> bool:
        """
        每帧调用。若连续 trigger_frames 帧检测到入侵且在冷却时间外，则触发告警。

        Returns:
            本次是否触发了告警
        """
        if is_intrusion:
            self._intrusion_count += 1
        else:
            self._intrusion_count = 0

        if self._intrusion_count < self.trigger_frames:
            return False

        now = time.time()
        if self._last_alert_time is not None and (now - self._last_alert_time) < self.cooldown_seconds:
            return False

        self._last_alert_time = now
        self._intrusion_count = 0
        self._fire_alert()
        return True

    def _fire_alert(self) -> None:
        """执行本地告警与网络上报。"""
        msg = "[INTRUSION] 检测到入侵"
        print(msg)

        if self.network_enabled:
            self._send_network_alert()

    def _send_network_alert(self) -> None:
        """通过 HTTP POST 上报告警（模拟基于互联网）。"""
        if not requests:
            return
        payload = {
            "event": "intrusion",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "message": "摄像机入侵检测告警",
        }
        try:
            r = requests.post(
                self.network_url,
                json=payload,
                timeout=self.network_timeout,
                headers={"Content-Type": "application/json"},
            )
            print(f"[NET] 告警已上报: {self.network_url} -> {r.status_code}")
        except Exception as e:
            print(f"[NET] 上报失败: {e}")
