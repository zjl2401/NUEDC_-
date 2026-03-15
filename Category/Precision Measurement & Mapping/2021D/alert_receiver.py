# -*- coding: utf-8 -*-
"""
简易告警接收服务：用于模拟“基于互联网”的告警接收端。
运行后可在 config.yaml 中开启 network.enabled 并设置 url 为本机地址进行联调。
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/alert" or self.path == "/":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            try:
                data = json.loads(body.decode("utf-8"))
                print(f"[RECV] 收到告警: {data}")
            except Exception as e:
                print(f"[RECV] 解析失败: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}")


def main():
    port = 8080
    server = HTTPServer(("0.0.0.0", port), AlertHandler)
    print(f"告警接收服务已启动: http://0.0.0.0:{port}/alert ，按 Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("已退出。")


if __name__ == "__main__":
    main()
