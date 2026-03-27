"""
2025E 可选串口通信（给单片机/飞控下发瞄准误差或云台角度）

依赖:
    pip install pyserial

使用:
    from comm import SerialSender
    sender = SerialSender("COM3", 115200)
    sender.send_line("pan=90 tilt=90 ex=12 ey=-8")
"""

from typing import Optional


class SerialSender:
    def __init__(self, port: str, baud: int = 115200, newline: str = "\n"):
        self.port = port
        self.baud = baud
        self.newline = newline
        self._ser: Optional[object] = None

        try:
            import serial  # type: ignore
        except ImportError as e:
            raise RuntimeError("未安装 pyserial，请先 pip install pyserial") from e

        self._ser = serial.Serial(port=self.port, baudrate=self.baud, timeout=0.01)

    def send_line(self, line: str) -> None:
        if self._ser is None:
            return
        data = (line + self.newline).encode("utf-8", errors="ignore")
        try:
            self._ser.write(data)
        except Exception:
            return

    def close(self) -> None:
        try:
            if self._ser is not None:
                self._ser.close()
        finally:
            self._ser = None

