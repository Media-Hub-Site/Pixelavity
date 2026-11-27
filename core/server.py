# -*- coding: utf-8 -*-
"""
PixelAgents - Servidor HTTP / SSE Local
Sirve el frontend Pixel Art (HTML5 Canvas) y expone los endpoints en tiempo real
conectados al AntigravityBrainWatcher.
"""

import os
import json
import time
import threading
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional

from core.watcher import AntigravityBrainWatcher


class PixelAgentsRequestHandler(BaseHTTPRequestHandler):
    watcher: Optional[AntigravityBrainWatcher] = None
    web_dir: str = ""

    def log_message(self, format: str, *args):
        # Silenciar logs repetitivos de polling para mantener consola limpia
        pass

    def _send_json(self, data: dict, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/state":
            qs = parse_qs(parsed.query)
            since_str = qs.get("since", ["0"])[0]
            try:
                since_id = int(since_str)
            except ValueError:
                since_id = 0
            snap = self.watcher.get_snapshot(since_event_id=since_id)
            self._send_json(snap)
            return

        if route == "/api/usage":
            self._send_json(self.watcher.get_usage_summary())
            return

        if route == "/api/stream":
            # Server-Sent Events (SSE) para actualizaciones en vivo
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            last_id = 0
            try:
                while True:
                    snap = self.watcher.get_snapshot(since_event_id=last_id)
                    last_id = snap["latest_event_id"]
                    msg = f"data: {json.dumps(snap, ensure_ascii=False)}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(0.75)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                return

        # Servir archivos estáticos desde web_dir
        if route == "/" or route == "":
            route = "/index.html"

        safe_rel = os.path.normpath(route.lstrip("/"))
        if safe_rel.startswith(".."):
            self.send_error(403, "Forbidden")
            return

        file_path = os.path.join(self.web_dir, safe_rel)
        if not os.path.isfile(file_path):
            self.send_error(404, f"File not found: {route}")
            return

        ctype, _ = mimetypes.guess_type(file_path)
        if not ctype:
            ctype = "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except OSError as e:
            self.send_error(500, str(e))

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {}

        if route == "/api/simulate":
            action = body.get("action", "")
            res = self.watcher.trigger_simulation(action)
            self._send_json(res)
            return

        if route == "/api/command_agent":
            # Permite que el usuario haga clic en una zona del mapa para mandar a un agente allí
            agent_id = body.get("agent_id", "")
            station = body.get("station", "lounge")
            res = self._command_agent_to_station(agent_id, station)
            self._send_json(res)
            return

        self._send_json({"ok": False, "error": "Unknown endpoint"}, status=404)

    def _command_agent_to_station(self, agent_id: str, station: str) -> dict:
        station_info = {
            "library": ("reading", "📚 Investigando Librerías", "Enviado manualmente a la Biblioteca", "📚"),
            "coding_desk": ("coding", "💻 Programando en PC", "Enviado manualmente a la Estación de Código", "💻"),
            "server_lab": ("terminal", "⚡ Operando Servidores", "Enviado manualmente al Laboratorio Terminal", "⚡"),
            "web_station": ("browsing", "🌐 Explorando Red", "Enviado manualmente a la Cabina Web", "🌐"),
            "orchestrator_hub": ("orchestrating", "🎛️ Centro Orchestrator", "Enviado a la Mesa de Mando", "🎛️"),
            "art_studio": ("designing", "🎨 Diseñando UI/Sprites", "Enviado al Estudio Creativo", "🎨"),
            "strategy_board": ("thinking", "💭 Planificando en Pizarra", "Enviado a la Pizarra de Estrategia", "💭"),
            "lounge": ("idle", "☕ Descansando en Cafetería", "Enviado a la zona de descanso", "☕"),
        }
        act, badge, detail, icon = station_info.get(
            station, ("idle", f"📍 En {station}", "Movimiento manual", "📍")
        )
        with self.watcher.lock:
            target = self.watcher.simulated_agents.get(agent_id) or self.watcher.agents.get(agent_id)
            if not target and self.watcher.agents:
                target = list(self.watcher.agents.values())[0]
            if target:
                target["station"] = station
                target["activity"] = act
                target["badge"] = badge
                target["detail"] = detail
                target["icon"] = icon
                target["last_updated"] = time.time()
                self.watcher._emit_event(target["id"], station, act, badge, detail, icon, immediate=True)
                return {"ok": True, "agent_id": target["id"], "station": station}
        return {"ok": False, "error": "Agente no encontrado"}


class PixelAgentsServer:
    """Gestiona el ciclo de vida del servidor HTTP + BrainWatcher."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, brain_dir: Optional[str] = None, web_dir: Optional[str] = None):
        self.host = host
        self.port = port
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.web_dir = web_dir or os.path.join(base_dir, "web")
        self.watcher = AntigravityBrainWatcher(brain_dir=brain_dir)
        self.httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        self.watcher.start()
        PixelAgentsRequestHandler.watcher = self.watcher
        PixelAgentsRequestHandler.web_dir = self.web_dir

        # Buscar puerto libre a partir de self.port
        for candidate_port in range(self.port, self.port + 25):
            try:
                self.httpd = ThreadingHTTPServer((self.host, candidate_port), PixelAgentsRequestHandler)
                self.port = candidate_port
                break
            except OSError:
                continue

        if not self.httpd:
            raise RuntimeError("No se pudo abrir ningún puerto local para PixelAgents.")

        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name="PixelAgentsHTTP")
        self._thread.start()
        return f"http://{self.host}:{self.port}"

    def stop(self):
        self.watcher.stop()
        if self.httpd:
            self.httpd.shutdown()
