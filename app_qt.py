# -*- coding: utf-8 -*-
"""
PixelAgents // Antigravity Live Visualizer - Native PyQt6 Desktop App
Aplicación de escritorio 100% nativa (sin navegador web) usando PyQt6 + QPainter a 60 FPS.
Se conecta directamente en memoria a AntigravityBrainWatcher para visualizar en tiempo real
los agentes de Gemini, chats paralelos y subagentes de Orchestrator.
"""

import os
import sys
import math
import time
import random
from typing import Dict, List, Optional, Any

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QSizePolicy, QSplitter
)

# Asegurar rutas de importación
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.watcher import AntigravityBrainWatcher


# =============================================================================
# DEFINICIÓN DE LAS 8 SALAS DEL ESCENARIO (Coordenadas lógicas 1024 x 600)
# =============================================================================
WORLD_W = 1024
WORLD_H = 600
HALLWAY_Y = 284

STATIONS: Dict[str, Dict[str, Any]] = {
    "library": {
        "id": "library",
        "title": "📚 BIBLIOTECA & LIBRERÍAS",
        "rect": (18, 42, 245, 214),
        "door": (140, 256),
        "floorA": "#3b281e",
        "floorB": "#332219",
        "border": "#d49a6a",
        "slots": [(68, 122, "up"), (142, 122, "up"), (212, 122, "up"), (105, 192, "down"), (175, 192, "down")],
    },
    "strategy_board": {
        "id": "strategy_board",
        "title": "💭 PIZARRA DE ESTRATEGIA",
        "rect": (277, 42, 225, 214),
        "door": (390, 256),
        "floorA": "#1a283b",
        "floorB": "#162233",
        "border": "#4fc3f7",
        "slots": [(335, 130, "up"), (395, 130, "up"), (452, 130, "up"), (365, 195, "up"), (425, 195, "up")],
    },
    "orchestrator_hub": {
        "id": "orchestrator_hub",
        "title": "🎛️ NÚCLEO ORCHESTRATOR",
        "rect": (516, 42, 235, 214),
        "door": (634, 256),
        "floorA": "#261e14",
        "floorB": "#1f1810",
        "border": "#ffd54f",
        "slots": [(595, 145, "down"), (672, 145, "down"), (560, 195, "right"), (705, 195, "left")],
    },
    "web_station": {
        "id": "web_station",
        "title": "🌐 CABINA WEB & RADAR",
        "rect": (765, 42, 241, 214),
        "door": (885, 256),
        "floorA": "#112833",
        "floorB": "#0e222b",
        "border": "#00e5ff",
        "slots": [(820, 132, "up"), (888, 132, "up"), (955, 132, "up"), (855, 198, "up"), (925, 198, "up")],
    },
    "coding_desk": {
        "id": "coding_desk",
        "title": "💻 SALA DE COMPUTADORES",
        "rect": (18, 312, 356, 268),
        "door": (196, 312),
        "floorA": "#162621",
        "floorB": "#12201c",
        "border": "#00e676",
        "slots": [(78, 402, "up"), (196, 402, "up"), (314, 402, "up"), (78, 506, "up"), (196, 506, "up"), (314, 506, "up")],
    },
    "server_lab": {
        "id": "server_lab",
        "title": "⚡ LABORATORIO TERMINAL",
        "rect": (388, 312, 224, 268),
        "door": (500, 312),
        "floorA": "#21242b",
        "floorB": "#1b1e24",
        "border": "#ffab40",
        "slots": [(445, 432, "up"), (505, 432, "up"), (562, 432, "up"), (472, 515, "up"), (535, 515, "up")],
    },
    "art_studio": {
        "id": "art_studio",
        "title": "🎨 ESTUDIO CREATIVO",
        "rect": (626, 312, 168, 268),
        "door": (710, 312),
        "floorA": "#291836",
        "floorB": "#22142d",
        "border": "#ea80fc",
        "slots": [(675, 428, "up"), (745, 428, "up"), (710, 512, "up")],
    },
    "lounge": {
        "id": "lounge",
        "title": "☕ CAFETERÍA & DESCANSO",
        "rect": (808, 312, 198, 268),
        "door": (907, 312),
        "floorA": "#2b1d24",
        "floorB": "#24181e",
        "border": "#ff8a80",
        "slots": [(855, 405, "up"), (952, 405, "up"), (862, 495, "right"), (912, 495, "up"), (958, 495, "left")],
    },
}


# =============================================================================
# ENTIDAD VISUAL DE AGENTE (PATHFINDING + ANIMACIÓN)
# =============================================================================
class QtAgentEntity:
    def __init__(self, data: Dict[str, Any], entities_ref: Dict[str, "QtAgentEntity"]):
        self.id: str = data["id"]
        self.entities_ref = entities_ref
        self.is_walking = False
        self.walk_frame = 0
        self.walk_timer = 0.0
        self.waypoints: List[tuple] = []
        self.action_queue: List[Dict[str, Any]] = []
        self.hold_timer = 0.0

        init_st = data.get("station", "lounge")
        if init_st not in STATIONS:
            init_st = "lounge"
        self.current_station = init_st
        self.slot_index = 0

        self.sync_metadata(data)

        self.slot_index = self._compute_slot(init_st)
        sx, sy, sface = STATIONS[init_st]["slots"][self.slot_index]

        if self.is_subagent:
            self.x = 694.0
            self.y = 127.0
            self.spawn_timer = 1.4
        else:
            self.x = float(sx)
            self.y = float(sy)
            self.spawn_timer = 0.6

        self.face = sface
        if self.is_subagent and init_st != "orchestrator_hub":
            self.navigate_to(init_st)

    def sync_metadata(self, data: Dict[str, Any]):
        self.short_id = data.get("short_id", self.id[:8])
        self.name = data.get("name", self.short_id)
        self.chat_title = data.get("chat_title", "Sesión Antigravity")
        self.model = data.get("model", "Gemini")
        self.is_subagent = bool(data.get("is_subagent", False))
        self.subagent_type = data.get("subagent_type", "main")
        self.parent_id = data.get("parent_id")
        self.children_ids = data.get("children_ids", [])
        self.palette = data.get("palette") or {"suit": "#00e5ff", "hair": "#1a237e", "accent": "#80d8ff"}
        self.step_count = data.get("step_count", 0)
        self.is_live = bool(data.get("is_live", False))
        self.is_simulated = bool(data.get("is_simulated", False))

        if not self.is_walking and not self.action_queue:
            self.badge = data.get("badge", "☕ En espera")
            self.detail = data.get("detail", "")
            self.activity = data.get("activity", "idle")
            st = data.get("station", "lounge")
            if st in STATIONS and st != self.current_station:
                self.enqueue_action({
                    "station": st,
                    "activity": self.activity,
                    "badge": self.badge,
                    "detail": self.detail,
                })

    def _compute_slot(self, station_id: str) -> int:
        slots = STATIONS[station_id]["slots"]
        h = sum(ord(c) for c in self.id)
        taken = {
            other.slot_index
            for oid, other in self.entities_ref.items()
            if oid != self.id and other.current_station == station_id
        }
        for off in range(len(slots)):
            cand = (h + off) % len(slots)
            if cand not in taken:
                return cand
        return h % len(slots)

    def enqueue_action(self, ev: Dict[str, Any], immediate: bool = False):
        st = ev.get("station")
        if st not in STATIONS:
            return
        if immediate or ev.get("immediate"):
            self.action_queue.clear()
            self.hold_timer = 0.0
            self.badge = ev.get("badge", "Trabajando...")
            self.detail = ev.get("detail", "")
            self.activity = ev.get("activity", "coding")
            if st != self.current_station or self.is_walking:
                self.navigate_to(st)
            else:
                self.hold_timer = 2.0
            return

        if self.action_queue and self.action_queue[-1]["station"] == st and self.action_queue[-1]["badge"] == ev.get("badge"):
            return
        self.action_queue.append({
            "station": st,
            "activity": ev.get("activity", "coding"),
            "badge": ev.get("badge", "Trabajando..."),
            "detail": ev.get("detail", ""),
        })
        if len(self.action_queue) > 6:
            self.action_queue.pop(0)

    def navigate_to(self, target_st: str):
        if target_st not in STATIONS:
            return
        from_st = STATIONS[self.current_station]
        to_st = STATIONS[target_st]
        self.current_station = target_st
        self.slot_index = self._compute_slot(target_st)
        tx, ty, tface = to_st["slots"][self.slot_index]

        pts = []
        if from_st["id"] != to_st["id"]:
            pts.append((from_st["door"][0], from_st["door"][1], None))
            pts.append((from_st["door"][0], HALLWAY_Y, None))
            pts.append((to_st["door"][0], HALLWAY_Y, None))
            pts.append((to_st["door"][0], to_st["door"][1], None))
        pts.append((tx, ty, tface))
        self.waypoints = pts
        self.is_walking = True

    def update(self, dt: float, particles: List[Dict[str, Any]]):
        if self.spawn_timer > 0:
            self.spawn_timer = max(0.0, self.spawn_timer - dt)

        if self.waypoints:
            self.is_walking = True
            wx, wy, wface = self.waypoints[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = math.hypot(dx, dy)
            speed = 185.0 if len(self.action_queue) > 1 else 135.0

            if dist <= speed * dt:
                self.x = float(wx)
                self.y = float(wy)
                if wface:
                    self.face = wface
                self.waypoints.pop(0)
                if not self.waypoints:
                    self.is_walking = False
                    self.walk_frame = 0
                    self.hold_timer = 1.8 if len(self.action_queue) > 1 else 2.6
            else:
                self.x += (dx / dist) * speed * dt
                self.y += (dy / dist) * speed * dt
                if abs(dx) > abs(dy):
                    self.face = "right" if dx > 0 else "left"
                else:
                    self.face = "down" if dy > 0 else "up"

                self.walk_timer += dt
                if self.walk_timer >= 0.12:
                    self.walk_timer = 0.0
                    self.walk_frame = (self.walk_frame + 1) % 4
                    particles.append({
                        "x": self.x + random.uniform(-3, 3),
                        "y": self.y + 12,
                        "vx": 0.0,
                        "vy": -8.0,
                        "life": 0.35,
                        "max_life": 0.35,
                        "type": "dust",
                        "color": "#c8dcff",
                    })
            return

        self.is_walking = False
        if self.hold_timer > 0:
            self.hold_timer = max(0.0, self.hold_timer - dt)

        # Partículas de actividad en la estación
        if random.random() < dt * 2.1:
            self._emit_particle(particles)

        if self.hold_timer <= 0 and self.action_queue:
            nxt = self.action_queue.pop(0)
            self.badge = nxt["badge"]
            self.detail = nxt["detail"]
            self.activity = nxt["activity"]
            if nxt["station"] != self.current_station:
                self.navigate_to(nxt["station"])
            else:
                self.hold_timer = 2.0

    def _emit_particle(self, particles: List[Dict[str, Any]]):
        table = {
            "coding_desk": (["</>", "{ }", "01", "py"], "#00e676"),
            "library": (["📖", "📚", "doc", "🔍"], "#ffd54f"),
            "server_lab": (["⚡", "$>", "OK", "⚙️"], "#ffab40"),
            "strategy_board": (["💭", "💡", "✓"], "#4fc3f7"),
            "orchestrator_hub": (["🎛️", "📡", "⚡"], "#ffd54f"),
            "web_station": (["🌐", "HTTP", "200"], "#00e5ff"),
            "art_studio": (["🎨", "✨", "UI"], "#ea80fc"),
            "lounge": (["☕", "~", "zZ"], "#ff8a80"),
        }
        syms, color = table.get(self.current_station, (["✨"], "#00e5ff"))
        particles.append({
            "x": self.x + random.uniform(-9, 9),
            "y": self.y - 22,
            "vx": random.uniform(-5, 5),
            "vy": random.uniform(-26, -16),
            "life": 1.1,
            "max_life": 1.1,
            "type": "text",
            "text": random.choice(syms),
            "color": color,
        })


# =============================================================================
# WIDGET NATIVO DE RENDERIZADO PIXEL ART (QPainter 60 FPS)
# =============================================================================
class PixelOfficeWidget(QWidget):
    def __init__(self, on_select_agent, on_command_station, parent=None):
        super().__init__(parent)
        self.on_select_agent = on_select_agent
        self.on_command_station = on_command_station

        self.entities: Dict[str, QtAgentEntity] = {}
        self.particles: List[Dict[str, Any]] = []
        self.selected_agent_id: Optional[str] = None
        self.hovered_station_id: Optional[str] = None
        self.filter_mode: str = "all"

        self.setMouseTracking(True)
        self.setMinimumSize(720, 440)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._last_time = time.perf_counter()
        self._start_time = self._last_time

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)  # ~60 FPS

    def _compute_transform(self):
        w, h = self.width(), self.height()
        scale = min(w / WORLD_W, h / WORLD_H)
        ox = (w - WORLD_W * scale) / 2.0
        oy = (h - WORLD_H * scale) / 2.0
        return scale, ox, oy

    def _screen_to_world(self, sx: float, sy: float):
        scale, ox, oy = self._compute_transform()
        if scale <= 0:
            return 0.0, 0.0
        return (sx - ox) / scale, (sy - oy) / scale

    def _tick(self):
        now = time.perf_counter()
        dt = min(0.1, now - self._last_time)
        self._last_time = now

        for ent in self.entities.values():
            ent.update(dt, self.particles)

        for i in range(len(self.particles) - 1, -1, -1):
            p = self.particles[i]
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.pop(i)
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

        self.update()

    def mouseMoveEvent(self, event):
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())
        hovered = None
        for sid, st in STATIONS.items():
            rx, ry, rw, rh = st["rect"]
            if rx <= wx <= rx + rw and ry <= wy <= ry + rh:
                hovered = sid
                break
        self.hovered_station_id = hovered
        self.setCursor(Qt.CursorShape.PointingHandCursor if hovered else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())

        # 1. Clic sobre un personaje
        for ent in self.entities.values():
            if self.filter_mode == "live" and not (ent.is_live or ent.is_simulated):
                continue
            if math.hypot(wx - ent.x, wy - (ent.y - 6)) <= 24:
                self.selected_agent_id = ent.id
                self.on_select_agent(ent.id)
                return

        # 2. Clic sobre una sala -> mandar al agente seleccionado
        for sid, st in STATIONS.items():
            rx, ry, rw, rh = st["rect"]
            if rx <= wx <= rx + rw and ry <= wy <= ry + rh:
                if self.selected_agent_id:
                    self.on_command_station(self.selected_agent_id, sid)
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Fondo exterior
        painter.fillRect(self.rect(), QColor("#090c14"))

        scale, ox, oy = self._compute_transform()
        painter.translate(ox, oy)
        painter.scale(scale, scale)

        now_sec = time.perf_counter() - self._start_time

        self._draw_world(painter, now_sec)
        self._draw_orchestrator_links(painter, now_sec)

        visible = [
            e for e in self.entities.values()
            if self.filter_mode == "all" or e.is_live or e.is_simulated
        ]
        visible.sort(key=lambda e: e.y)

        for ent in visible:
            self._draw_agent(painter, ent, now_sec)

        self._draw_particles(painter)
        painter.end()

    def _rect(self, p: QPainter, x, y, w, h, fill: str, stroke: Optional[str] = None, sw: int = 2):
        p.fillRect(int(x), int(y), int(w), int(h), QColor(fill))
        if stroke:
            p.setPen(QPen(QColor(stroke), sw))
            p.drawRect(int(x), int(y), int(w), int(h))

    def _draw_world(self, p: QPainter, now_sec: float):
        # Fondo del complejo
        p.fillRect(0, 0, WORLD_W, WORLD_H, QColor("#0b0e17"))

        # Pasillo central
        self._rect(p, 18, 258, WORLD_W - 36, 52, "#151c2c", "#26324d", 2)
        pen_dash = QPen(QColor(0, 229, 255, 50), 2, Qt.PenStyle.DashLine)
        p.setPen(pen_dash)
        p.drawLine(35, HALLWAY_Y, WORLD_W - 35, HALLWAY_Y)

        p.setPen(QColor(139, 155, 180, 95))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(QRectF(0, HALLWAY_Y - 8, WORLD_W, 18), Qt.AlignmentFlag.AlignCenter,
                   "◄═══ CORREDOR CENTRAL ANTIGRAVITY HQ ═══►")

        # Dibujar las 8 salas
        for st in STATIONS.values():
            self._draw_station_base(p, st)

        self._draw_library_furniture(p, STATIONS["library"])
        self._draw_strategy_furniture(p, STATIONS["strategy_board"])
        self._draw_orchestrator_furniture(p, STATIONS["orchestrator_hub"], now_sec)
        self._draw_web_furniture(p, STATIONS["web_station"], now_sec)
        self._draw_coding_furniture(p, STATIONS["coding_desk"], now_sec)
        self._draw_server_furniture(p, STATIONS["server_lab"], now_sec)
        self._draw_art_furniture(p, STATIONS["art_studio"])
        self._draw_lounge_furniture(p, STATIONS["lounge"])

    def _draw_station_base(self, p: QPainter, st: Dict[str, Any]):
        x, y, w, h = st["rect"]
        hovered = (self.hovered_station_id == st["id"])

        # Baldosas pixeladas
        tile = 16
        cA, cB = QColor(st["floorA"]), QColor(st["floorB"])
        for ty in range(y, y + h, tile):
            for tx in range(x, x + w, tile):
                even = (((tx - x) // tile + (ty - y) // tile) % 2) == 0
                p.fillRect(tx, ty, min(tile, x + w - tx), min(tile, y + h - ty), cA if even else cB)

        p.setPen(QPen(QColor("#ffffff" if hovered else st["border"]), 3 if hovered else 2))
        p.drawRect(x, y, w, h)

        # Puerta abierta hacia el corredor
        dx, dy = st["door"]
        if dy <= 260:
            p.fillRect(dx - 18, y + h - 3, 36, 6, QColor("#151c2c"))
        else:
            p.fillRect(dx - 18, y - 3, 36, 6, QColor("#151c2c"))

        # Cartel superior
        self._rect(p, x + 6, y + 6, w - 12, 24, "#0d1220", st["border"], 1)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(x + 12, y + 22, st["title"])

    def _draw_library_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        colors = ["#ff5252", "#448aff", "#00e676", "#ffd740", "#e040fb", "#ff6e40"]
        for s in range(3):
            sx, sy = x + 18 + s * 74, y + 40
            self._rect(p, sx, sy, 62, 52, "#4e342e", "#8d6e63", 2)
            for row in range(3):
                ry = sy + 6 + row * 15
                p.fillRect(sx + 4, ry + 10, 54, 3, QColor("#3e2723"))
                for b in range(8):
                    p.fillRect(sx + 6 + b * 6, ry, 5, 10, QColor(colors[(s * 7 + row * 3 + b) % len(colors)]))

        for t in range(2):
            tx, ty = x + 38 + t * 96, y + 155
            self._rect(p, tx, ty, 70, 32, "#6d4c41", "#a1887f", 2)
            self._rect(p, tx + 16, ty + 8, 16, 12, "#fff8e1", "#bcaaa4", 1)
            self._rect(p, tx + 32, ty + 8, 16, 12, "#fff8e1", "#bcaaa4", 1)
            p.fillRect(tx + 54, ty + 10, 8, 8, QColor("#00e5ff"))

    def _draw_strategy_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        bx, by = x + 22, y + 40
        self._rect(p, bx, by, 180, 54, "#0d1b2a", "#4fc3f7", 2)
        p.fillRect(bx + 14, by + 12, 28, 14, QColor("#00e5ff"))
        p.fillRect(bx + 62, by + 12, 28, 14, QColor("#ffb300"))
        p.fillRect(bx + 110, by + 12, 28, 14, QColor("#00e676"))
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(bx + 42, by + 19, bx + 62, by + 19)
        p.drawLine(bx + 90, by + 19, bx + 110, by + 19)
        p.fillRect(bx + 150, by + 10, 10, 10, QColor("#ffeb3b"))
        p.fillRect(bx + 163, by + 10, 10, 10, QColor("#ff4081"))
        p.fillRect(bx + 150, by + 24, 10, 10, QColor("#00e676"))
        self._rect(p, x + 48, y + 155, 130, 28, "#1e2f48", "#4fc3f7", 1)

    def _draw_orchestrator_furniture(self, p: QPainter, st, now_sec: float):
        x, y, _, _ = st["rect"]
        cx, cy = x + 82, y + 105
        self._rect(p, cx - 42, cy - 26, 84, 52, "#1c160c", "#ffb300", 2)
        pulse = 18 + math.sin(now_sec * 4.0) * 4.0
        p.setPen(QPen(QColor("#ffd54f"), 2))
        p.drawEllipse(QPointF(cx, cy), pulse, pulse)
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 40, cy - 8, 80, 16), Qt.AlignmentFlag.AlignCenter, "ORCH-CORE")

        # Spawn Pad
        px, py = x + 178, y + 85
        self._rect(p, px - 26, py - 26, 52, 52, "#140f24", "#d500f9", 2)
        pr = 14 + math.cos(now_sec * 5.0) * 3.0
        p.setPen(QPen(QColor("#00e5ff"), 2))
        p.drawEllipse(QPointF(px, py), pr, pr)
        p.setPen(QColor("#ea80fc"))
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.drawText(QRectF(px - 35, py + 28, 70, 14), Qt.AlignmentFlag.AlignCenter, "SPAWN PAD")

    def _draw_web_furniture(self, p: QPainter, st, now_sec: float):
        x, y, _, _ = st["rect"]
        for m in range(3):
            mx, my = x + 24 + m * 68, y + 48
            self._rect(p, mx, my, 54, 34, "#0a1929", "#00e5ff", 2)
            bar_w = 14 + ((int(now_sec * 6) + m * 5) % 30)
            p.fillRect(mx + 6, my + 8, bar_w, 4, QColor(0, 229, 255, 110))
            p.fillRect(mx + 6, my + 16, 36, 4, QColor(0, 229, 255, 110))
            p.fillRect(mx + 6, my + 24, 24, 4, QColor(0, 229, 255, 110))

        gx, gy = x + 120, y + 165
        self._rect(p, gx - 35, gy - 20, 70, 40, "#0b1d28", "#00b0ff", 1)
        p.setPen(QPen(QColor("#00e5ff"), 1))
        p.drawEllipse(QPointF(gx, gy), 14, 14)
        p.drawLine(gx - 14, gy, gx + 14, gy)
        p.drawLine(gx, gy - 14, gx, gy + 14)

    def _draw_coding_furniture(self, p: QPainter, st, now_sec: float):
        active_desks = {
            e.slot_index for e in self.entities.values()
            if not e.is_walking and e.current_station == "coding_desk"
        }
        for idx, (sx, sy, _) in enumerate(st["slots"]):
            dx, dy = sx - 42, sy - 46
            occ = idx in active_desks
            self._rect(p, sx - 10, sy + 4, 20, 14, "#263238", "#455a64", 1)
            self._rect(p, dx, dy, 84, 34, "#2c384e", "#00e676" if occ else "#4a5d80", 2)
            for m in range(2):
                mx, my = dx + 8 + m * 36, dy + 4
                self._rect(p, mx, my, 28, 18, "#061f14" if occ else "#0f141d", "#00e676" if occ else "#37474f", 1)
                if occ:
                    sc = int(now_sec * 8 + idx + m) % 3
                    c = QColor("#00e676" if m == 0 else "#00e5ff")
                    p.fillRect(mx + 3, my + 4 + sc, 16, 2, c)
                    p.fillRect(mx + 3, my + 9, 20, 2, c)
                    p.fillRect(mx + 3, my + 14 - sc, 12, 2, c)
            self._rect(p, dx + 24, dy + 25, 28, 6, "#111722", "#546e7a", 1)
            self._rect(p, dx + 70, dy + 6, 10, 22, "#111722", "#00e5ff" if occ else "#37474f", 1)

    def _draw_server_furniture(self, p: QPainter, st, now_sec: float):
        x, y, _, _ = st["rect"]
        for r in range(4):
            rx, ry = x + 16 + r * 50, y + 42
            self._rect(p, rx, ry, 42, 62, "#12151c", "#546e7a", 2)
            for u in range(4):
                uy = ry + 6 + u * 14
                p.fillRect(rx + 4, uy, 34, 10, QColor("#1e2430"))
                blink = ((int(now_sec * 6) + r * 3 + u) % 3) == 0
                p.fillRect(rx + 7, uy + 3, 4, 4, QColor("#00e676" if blink else "#ff9100"))
                p.fillRect(rx + 14, uy + 3, 4, 4, QColor("#00e5ff"))
        self._rect(p, x + 35, y + 168, 154, 34, "#161b22", "#ff9100", 2)
        p.setPen(QColor("#00e676"))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(x + 44, y + 189, "$ antigravity --exec")

    def _draw_art_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        self._rect(p, x + 24, y + 48, 52, 42, "#fff8e1", "#ffb300", 2)
        p.fillRect(x + 32, y + 56, 16, 14, QColor("#ff4081"))
        p.fillRect(x + 48, y + 62, 18, 18, QColor("#00e5ff"))
        self._rect(p, x + 92, y + 52, 58, 38, "#311b92", "#ea80fc", 2)
        self._rect(p, x + 102, y + 60, 38, 22, "#1a0933", "#00e5ff", 1)

    def _draw_lounge_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        self._rect(p, x + 18, y + 44, 162, 34, "#4e342e", "#a1887f", 2)
        self._rect(p, x + 32, y + 48, 28, 24, "#b71c1c", "#ffcdd2", 1)
        self._rect(p, x + 140, y + 46, 22, 26, "#e1f5fe", "#29b6f6", 1)
        self._rect(p, x + 42, y + 150, 114, 42, "#880e4f", "#f48fb1", 2)
        p.fillRect(x + 50, y + 158, 98, 26, QColor("#ad1457"))

    def _draw_orchestrator_links(self, p: QPainter, now_sec: float):
        for ent in self.entities.values():
            if self.filter_mode == "live" and not (ent.is_live or ent.is_simulated):
                continue
            if ent.parent_id and ent.parent_id in self.entities:
                parent = self.entities[ent.parent_id]
                pen = QPen(QColor(255, 213, 79, 150), 2, Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.drawLine(int(parent.x), int(parent.y - 8), int(ent.x), int(ent.y - 8))
                t = (now_sec * 0.9) % 1.0
                px = parent.x + (ent.x - parent.x) * t
                py = (parent.y - 8) + ((ent.y - 8) - (parent.y - 8)) * t
                p.fillRect(int(px - 3), int(py - 3), 6, 6, QColor("#00e5ff"))

    def _draw_agent(self, p: QPainter, ent: QtAgentEntity, now_sec: float):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        walk_bob = (-3 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 4 + x))

        if ent.spawn_timer > 0:
            p.setPen(QPen(QColor("#00e5ff"), 2))
            r = 22 * ent.spawn_timer
            p.drawEllipse(QPointF(x, y - 6), r, r)

        if is_sel:
            p.setPen(QPen(QColor("#00e5ff"), 2))
            p.drawEllipse(QPointF(x, y + 12), 16, 7)

        # Sombra
        p.fillRect(x - 10, y + 10, 20, 5, QColor(0, 0, 0, 120))
        py = y + walk_bob

        # Piernas
        leg_l = (-3 if ent.walk_frame == 1 else 2 if ent.walk_frame == 3 else 0) if ent.is_walking else 0
        leg_r = (-3 if ent.walk_frame == 3 else 2 if ent.walk_frame == 1 else 0) if ent.is_walking else 0
        p.fillRect(x - 7, py + 3 + leg_l, 5, 8, QColor("#1e272e"))
        p.fillRect(x + 2, py + 3 + leg_r, 5, 8, QColor("#1e272e"))

        # Torso
        suit = ent.palette.get("suit", "#00e5ff")
        accent = ent.palette.get("accent", "#ffffff")
        hair = ent.palette.get("hair", "#263238")
        self._rect(p, x - 9, py - 9, 18, 13, suit, "#0b0e17", 1)
        p.fillRect(x - 3, py - 6, 6, 4, QColor(accent))

        # Brazos
        typing = (not ent.is_walking) and (ent.current_station in ("coding_desk", "server_lab"))
        jitter = int(math.sin(now_sec * 26) * 2) if typing else 0
        p.fillRect(x - 13, py - 8 + jitter, 4, 10, QColor(suit))
        p.fillRect(x + 9, py - 8 - jitter, 4, 10, QColor(suit))

        # Cabeza y cabello
        self._rect(p, x - 8, py - 23, 16, 14, "#ffccaa", "#0b0e17", 1)
        p.fillRect(x - 9, py - 25, 18, 5, QColor(hair))
        if ent.face == "left":
            p.fillRect(x + 5, py - 23, 4, 9, QColor(hair))
        elif ent.face == "right":
            p.fillRect(x - 9, py - 23, 4, 9, QColor(hair))

        # Ojos
        if ent.face == "left":
            p.fillRect(x - 6, py - 17, 3, 3, QColor("#111111"))
            p.fillRect(x - 1, py - 17, 3, 3, QColor("#111111"))
        elif ent.face == "right":
            p.fillRect(x - 2, py - 17, 3, 3, QColor("#111111"))
            p.fillRect(x + 3, py - 17, 3, 3, QColor("#111111"))
        elif ent.face == "down":
            p.fillRect(x - 5, py - 17, 3, 3, QColor("#111111"))
            p.fillRect(x + 2, py - 17, 3, 3, QColor("#111111"))

        # Antena de subagente o audífonos de agente principal
        if ent.is_subagent:
            p.fillRect(x - 1, py - 30, 2, 5, QColor("#ffd54f"))
            p.fillRect(x - 2, py - 32, 4, 3, QColor("#00e5ff"))
        else:
            p.fillRect(x - 10, py - 19, 2, 6, QColor(accent))
            p.fillRect(x + 8, py - 19, 2, 6, QColor(accent))

        # Objeto en mano
        if not ent.is_walking:
            if ent.current_station == "library":
                self._rect(p, x - 7, py - 5, 14, 9, "#fff8e1", "#d49a6a", 1)
                p.fillRect(x - 5, py - 4, 5, 7, QColor("#e65100"))
            elif ent.current_station == "lounge":
                self._rect(p, x + 6, py - 6, 7, 8, "#ffffff", "#ff5252", 1)

        # Nombre debajo de los pies
        name_tag = f"⚡ {ent.name}" if ent.is_subagent else ent.name
        font_name = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(font_name)
        nw = QFontMetrics(font_name).horizontalAdvance(name_tag) + 10
        self._rect(p, x - nw / 2, y + 15, nw, 15, "#0d1220", suit, 1)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(x - nw / 2, y + 15, nw, 15), Qt.AlignmentFlag.AlignCenter, name_tag)

        # Globo de diálogo sobre la cabeza
        bubble = f"🚶 → {STATIONS[ent.current_station]['title'].split()[1]}" if ent.is_walking else ent.badge
        if bubble:
            bubble = bubble[:26]
            font_b = QFont("Segoe UI", 8, QFont.Weight.Bold)
            p.setFont(font_b)
            bw = min(190, QFontMetrics(font_b).horizontalAdvance(bubble) + 14)
            bx = max(12, min(WORLD_W - bw - 12, x - bw / 2))
            by = py - 46
            self._rect(p, bx, by, bw, 17, "#131826", "#00e5ff" if is_sel else "#4a5d80", 1)
            p.setPen(QColor("#edf2ff"))
            p.drawText(QRectF(bx, by, bw, 17), Qt.AlignmentFlag.AlignCenter, bubble)

    def _draw_particles(self, p: QPainter):
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        for pt in self.particles:
            alpha = max(0, min(255, int(255 * (pt["life"] / pt["max_life"]))))
            c = QColor(pt["color"])
            c.setAlpha(alpha)
            if pt["type"] == "dust":
                p.fillRect(int(pt["x"]), int(pt["y"]), 4, 4, c)
            else:
                p.setPen(c)
                p.drawText(int(pt["x"]), int(pt["y"]), pt["text"])


# =============================================================================
# VENTANA PRINCIPAL NATIVA PyQt6
# =============================================================================
DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0b0e17;
    color: #edf2ff;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#TopBar, QFrame#ControlDeck, QFrame#SidePanel {
    background-color: #131826;
    border: 2px solid #2b3754;
    border-radius: 8px;
}
QLabel#BrandTitle {
    font-family: 'Consolas';
    font-size: 16px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#LivePill {
    background-color: rgba(0, 230, 118, 35);
    border: 1px solid #00e676;
    border-radius: 10px;
    padding: 4px 10px;
    color: #00e676;
    font-family: 'Consolas';
    font-size: 11px;
    font-weight: bold;
}
QLabel#PanelTitle {
    background-color: #192136;
    color: #00e5ff;
    font-family: 'Consolas';
    font-size: 11px;
    font-weight: bold;
    padding: 6px 10px;
    border-bottom: 1px solid #2b3754;
}
QPushButton {
    background-color: #1a2133;
    color: #edf2ff;
    border: 1px solid #354569;
    border-radius: 5px;
    padding: 5px 10px;
    font-family: 'Consolas';
    font-size: 11px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #232d45;
    border-color: #00e5ff;
}
QPushButton:checked {
    background-color: #00e5ff;
    color: #071018;
    border-color: #00e5ff;
}
QPushButton#BtnCyan {
    border-color: #00e5ff;
    color: #80f0ff;
}
QPushButton#BtnAmber {
    border-color: #ffb300;
    color: #ffe082;
}
QPushButton#BtnDanger {
    border-color: #ff1744;
    color: #ff8a80;
}
QListWidget {
    background-color: #131826;
    border: none;
    outline: none;
    font-family: 'Consolas';
    font-size: 11px;
}
QListWidget::item {
    background-color: #1a2133;
    border: 1px solid #2b3754;
    border-radius: 5px;
    padding: 6px;
    margin: 3px 4px;
}
QListWidget::item:selected {
    background-color: rgba(0, 229, 255, 40);
    border: 1px solid #00e5ff;
    color: #ffffff;
}
"""


class PixelAgentsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixelAgents // Antigravity Live Desktop Visualizer")
        self.resize(1380, 820)
        self.setMinimumSize(1080, 680)
        self.setStyleSheet(DARK_STYLESHEET)

        # Iniciar watcher directamente en memoria
        self.watcher = AntigravityBrainWatcher()
        self.watcher.start()
        self.last_event_id = 0
        self.is_first_sync = True

        self._build_ui()

        # Sincronizar estado cada 750ms
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._sync_from_watcher)
        self.sync_timer.start(750)
        self._sync_from_watcher()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. BARRA SUPERIOR
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(12, 8, 12, 8)

        title_lbl = QLabel("👾 PIXEL AGENTS  //  ANTIGRAVITY DESKTOP")
        title_lbl.setObjectName("BrandTitle")
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()

        self.lbl_live = QLabel("● ANTIGRAVITY BRAIN LIVE")
        self.lbl_live.setObjectName("LivePill")
        top_layout.addWidget(self.lbl_live)

        self.lbl_stats = QLabel("Chats: 0  |  Subagentes: 0")
        self.lbl_stats.setStyleSheet("font-family: Consolas; font-weight: bold; color: #00e5ff; padding: 0 8px;")
        top_layout.addWidget(self.lbl_stats)

        self.btn_pin = QPushButton("📌 Fijar Encima")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Mantiene PixelAgents flotando encima de Antigravity / VS Code")
        self.btn_pin.toggled.connect(self._toggle_always_on_top)
        top_layout.addWidget(self.btn_pin)

        self.btn_filter_live = QPushButton("Solo En Vivo")
        self.btn_filter_live.setCheckable(True)
        self.btn_filter_live.toggled.connect(self._toggle_filter_live)
        top_layout.addWidget(self.btn_filter_live)

        main_layout.addWidget(topbar)

        # 2. CUERPO PRINCIPAL (LIENZO PIXEL ART + PANEL LATERAL)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # Columna izquierda: Canvas + Barra de control inferior
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.office_widget = PixelOfficeWidget(
            on_select_agent=self._on_agent_selected,
            on_command_station=self._on_command_station,
        )
        left_layout.addWidget(self.office_widget, stretch=1)

        # Barra inferior de simulación y movimiento
        deck = QFrame()
        deck.setObjectName("ControlDeck")
        deck_layout = QHBoxLayout(deck)
        deck_layout.setContentsMargins(10, 6, 10, 6)

        btn_chat = QPushButton("➕ Nuevo Chat")
        btn_chat.setObjectName("BtnCyan")
        btn_chat.clicked.connect(lambda: self._sim("spawn_chat"))
        deck_layout.addWidget(btn_chat)

        btn_orch = QPushButton("🎛️ Orchestrator (3 Subs)")
        btn_orch.setObjectName("BtnAmber")
        btn_orch.clicked.connect(lambda: self._sim("spawn_orchestrator"))
        deck_layout.addWidget(btn_orch)

        btn_clear = QPushButton("🧹 Limpiar Demo")
        btn_clear.setObjectName("BtnDanger")
        btn_clear.clicked.connect(lambda: self._sim("clear_sim"))
        deck_layout.addWidget(btn_clear)

        deck_layout.addStretch()

        quick_moves = [
            ("📚 Biblioteca", "library"),
            ("💻 Computador", "coding_desk"),
            ("⚡ Terminal", "server_lab"),
            ("💭 Pizarra", "strategy_board"),
            ("☕ Cafetería", "lounge"),
        ]
        for label, st_id in quick_moves:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, s=st_id: self._move_selected_to(s))
            deck_layout.addWidget(b)

        left_layout.addWidget(deck)
        splitter.addWidget(left_container)

        # Columna derecha: Inspector + Lista de Agentes + Telemetría
        side_panel = QFrame()
        side_panel.setObjectName("SidePanel")
        side_panel.setMinimumWidth(310)
        side_panel.setMaximumWidth(400)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        lbl_insp = QLabel("🔍 INSPECTOR DE AGENTE")
        lbl_insp.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_insp)

        self.lbl_inspector = QLabel("Haz clic en un personaje para ver su modelo y tarea.")
        self.lbl_inspector.setWordWrap(True)
        self.lbl_inspector.setStyleSheet("padding: 10px; font-size: 12px; color: #d1e3ff;")
        side_layout.addWidget(self.lbl_inspector)

        lbl_agents = QLabel("🤖 AGENTES EN LA OFICINA")
        lbl_agents.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_agents)

        self.list_agents = QListWidget()
        self.list_agents.itemClicked.connect(self._on_list_agent_clicked)
        side_layout.addWidget(self.list_agents, stretch=1)

        lbl_feed = QLabel("📡 TELEMETRÍA ANTIGRAVITY (LIVE)")
        lbl_feed.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_feed)

        self.list_feed = QListWidget()
        side_layout.addWidget(self.list_feed, stretch=1)

        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

    def _toggle_always_on_top(self, checked: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _toggle_filter_live(self, checked: bool):
        self.office_widget.filter_mode = "live" if checked else "all"
        self._refresh_sidebar()

    def _sim(self, action: str):
        res = self.watcher.trigger_simulation(action)
        if res.get("agent_id"):
            self.office_widget.selected_agent_id = res["agent_id"]
        elif res.get("orchestrator_id"):
            self.office_widget.selected_agent_id = res["orchestrator_id"]
        self._sync_from_watcher()

    def _move_selected_to(self, station_id: str):
        aid = self.office_widget.selected_agent_id
        if aid:
            self._on_command_station(aid, station_id)

    def _on_agent_selected(self, agent_id: str):
        self.office_widget.selected_agent_id = agent_id
        self._refresh_sidebar()

    def _on_list_agent_clicked(self, item: QListWidgetItem):
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.office_widget.selected_agent_id = aid
            self._refresh_sidebar()

    def _on_command_station(self, agent_id: str, station_id: str):
        ent = self.office_widget.entities.get(agent_id)
        if ent:
            st_title = STATIONS.get(station_id, {}).get("title", station_id)
            ent.enqueue_action({
                "station": station_id,
                "activity": "coding",
                "badge": f"📍 {st_title}",
                "detail": f"Enviado a {st_title}",
                "immediate": True,
            }, immediate=True)
            self._refresh_sidebar()

    def _sync_from_watcher(self):
        snap = self.watcher.get_snapshot(since_event_id=self.last_event_id)
        ents = self.office_widget.entities
        current_ids = set()

        for ag in snap.get("agents", []):
            aid = ag["id"]
            current_ids.add(aid)
            if aid not in ents:
                ents[aid] = QtAgentEntity(ag, ents)
            else:
                ents[aid].sync_metadata(ag)

        for old_id in list(ents.keys()):
            if old_id not in current_ids:
                del ents[old_id]
                if self.office_widget.selected_agent_id == old_id:
                    self.office_widget.selected_agent_id = None

        if self.is_first_sync:
            self.is_first_sync = False
            self.last_event_id = snap.get("latest_event_id", 0)
        else:
            for ev in snap.get("events", []):
                if ev["id"] > self.last_event_id:
                    self.last_event_id = ev["id"]
                target = ents.get(ev["agent_id"])
                if target:
                    target.enqueue_action(ev, immediate=bool(ev.get("immediate", False)))
            if snap.get("latest_event_id", 0) > self.last_event_id:
                self.last_event_id = snap["latest_event_id"]

        if not self.office_widget.selected_agent_id and ents:
            self.office_widget.selected_agent_id = next(iter(ents.keys()))

        self._recent_logs = snap.get("recent_log", [])
        self._refresh_sidebar()

    def _refresh_sidebar(self):
        ents = list(self.office_widget.entities.values())
        visible = [
            e for e in ents
            if self.office_widget.filter_mode == "all" or e.is_live or e.is_simulated
        ]
        chats = sum(1 for e in visible if not e.is_subagent)
        subs = sum(1 for e in visible if e.is_subagent)
        self.lbl_stats.setText(f"Chats: {chats}  |  Subagentes: {subs}")

        # Actualizar inspector
        sel = self.office_widget.entities.get(self.office_widget.selected_agent_id or "")
        if sel:
            st_title = STATIONS.get(sel.current_station, {}).get("title", sel.current_station)
            role = f"SUBAGENTE ({sel.subagent_type.upper()})" if sel.is_subagent else "AGENTE PRINCIPAL"
            self.lbl_inspector.setText(
                f"<b>{sel.name}</b>  <span style='color:#ffb300'>[{role}]</span><br>"
                f"<span style='color:#ffd54f'>Modelo:</span> {sel.model}<br>"
                f"<span style='color:#00e5ff'>Sala:</span> {st_title}<br>"
                f"<span style='color:#00e676'>Estado:</span> {sel.badge}<br>"
                f"<span style='color:#8b9bb4'>{sel.chat_title}</span>"
            )
        else:
            self.lbl_inspector.setText("Haz clic en un personaje para inspeccionarlo.")

        # Actualizar lista de agentes
        self.list_agents.clear()
        for e in visible:
            prefix = "↳ [SUB] " if e.is_subagent else "💬 "
            item = QListWidgetItem(f"{prefix}{e.name}  ({e.model})\n   {e.badge}")
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            self.list_agents.addItem(item)
            if e.id == self.office_widget.selected_agent_id:
                item.setSelected(True)

        # Actualizar feed de telemetría
        self.list_feed.clear()
        for log in getattr(self, "_recent_logs", [])[:12]:
            txt = f"[{log.get('time_str', '')}] {log.get('agent_name', '')}\n  {log.get('badge', '')}"
            self.list_feed.addItem(txt)

    def closeEvent(self, event):
        self.watcher.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = PixelAgentsWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
