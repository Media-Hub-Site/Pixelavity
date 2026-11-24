# -*- coding: utf-8 -*-
"""
PixelAgents // Antigravity Live Visualizer — Native PyQt6 Spectator App
Aplicación de escritorio 100% nativa en PyQt6 (modo espectador puro).
Se conecta directamente en memoria a AntigravityBrainWatcher para observar en tiempo real
a tus agentes de Gemini, chats paralelos y subagentes de Orchestrator.
"""

import os
import re
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.watcher import AntigravityBrainWatcher


# =============================================================================
# DEFINICIÓN DE LAS 8 SALAS DEL ESCENARIO (Coordenadas lógicas 1040 x 620)
# =============================================================================
WORLD_W = 1040
WORLD_H = 620
HALLWAY_Y = 294

STATIONS: Dict[str, Dict[str, Any]] = {
    "library": {
        "id": "library",
        "icon": "📚",
        "title": "BIBLIOTECA",
        "rect": (20, 20, 244, 240),
        "door": (142, 260),
        "floorA": "#271d18",
        "floorB": "#221915",
        "accent": "#d49a6a",
        "slots": [(68, 130, "up"), (142, 130, "up"), (216, 130, "up"), (100, 212, "down"), (184, 212, "down")],
    },
    "strategy_board": {
        "id": "strategy_board",
        "icon": "💭",
        "title": "ESTRATEGIA",
        "rect": (278, 20, 232, 240),
        "door": (394, 260),
        "floorA": "#141f2e",
        "floorB": "#111b28",
        "accent": "#38bdf8",
        "slots": [(332, 132, "up"), (394, 132, "up"), (456, 132, "up"), (360, 212, "up"), (428, 212, "up")],
    },
    "orchestrator_hub": {
        "id": "orchestrator_hub",
        "icon": "🎛️",
        "title": "ORCHESTRATOR",
        "rect": (524, 20, 240, 240),
        "door": (644, 260),
        "floorA": "#211a12",
        "floorB": "#1c160f",
        "accent": "#fbbf24",
        "slots": [(604, 162, "down"), (682, 162, "down"), (568, 216, "right"), (718, 216, "left")],
    },
    "web_station": {
        "id": "web_station",
        "icon": "🌐",
        "title": "CABINA WEB",
        "rect": (778, 20, 242, 240),
        "door": (899, 260),
        "floorA": "#10212b",
        "floorB": "#0d1c25",
        "accent": "#22d3ee",
        "slots": [(828, 132, "up"), (899, 132, "up"), (968, 132, "up"), (862, 214, "up"), (936, 214, "up")],
    },
    "coding_desk": {
        "id": "coding_desk",
        "icon": "💻",
        "title": "COMPUTADORES",
        "rect": (20, 328, 344, 272),
        "door": (192, 328),
        "floorA": "#12211c",
        "floorB": "#0f1c18",
        "accent": "#34d399",
        "slots": [(78, 422, "up"), (192, 422, "up"), (306, 422, "up"), (78, 530, "up"), (192, 530, "up"), (306, 530, "up")],
    },
    "server_lab": {
        "id": "server_lab",
        "icon": "⚡",
        "title": "TERMINAL LAB",
        "rect": (378, 328, 218, 272),
        "door": (487, 328),
        "floorA": "#1a1e26",
        "floorB": "#161920",
        "accent": "#fb923c",
        "slots": [(428, 446, "up"), (487, 446, "up"), (546, 446, "up"), (454, 536, "up"), (522, 536, "up")],
    },
    "art_studio": {
        "id": "art_studio",
        "icon": "🎨",
        "title": "ESTUDIO UI",
        "rect": (610, 328, 154, 272),
        "door": (687, 328),
        "floorA": "#21152c",
        "floorB": "#1c1225",
        "accent": "#e879f9",
        "slots": [(656, 446, "up"), (722, 446, "up"), (687, 536, "up")],
    },
    "lounge": {
        "id": "lounge",
        "icon": "☕",
        "title": "CAFETERÍA & LOUNGE",
        "rect": (778, 328, 242, 272),
        "door": (899, 328),
        "floorA": "#21171d",
        "floorB": "#1c1318",
        "accent": "#f87171",
        "slots": [(822, 426, "up"), (899, 426, "up"), (976, 426, "up"), (822, 536, "up"), (899, 536, "up"), (976, 536, "up")],
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
            self.x = 708.0
            self.y = 114.0
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
        self.compact_name = re.sub(r"\s*\[[^\]]+\]", "", self.name).strip() or self.name
        self.chat_title = data.get("chat_title", "Sesión Antigravity")
        self.model = data.get("model", "Gemini")
        self.is_subagent = bool(data.get("is_subagent", False))
        self.subagent_type = data.get("subagent_type", "main")
        self.parent_id = data.get("parent_id")
        self.children_ids = data.get("children_ids", [])
        self.palette = data.get("palette") or {"suit": "#38bdf8", "hair": "#1e293b", "accent": "#7dd3fc"}
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

    def enqueue_action(self, ev: Dict[str, Any]):
        st = ev.get("station")
        if st not in STATIONS:
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
                        "vy": -7.0,
                        "life": 0.32,
                        "max_life": 0.32,
                        "type": "dust",
                        "color": "#b4d2ff",
                    })
            return

        self.is_walking = False
        if self.hold_timer > 0:
            self.hold_timer = max(0.0, self.hold_timer - dt)

        rate = 0.35 if self.current_station == "lounge" else 1.7
        if random.random() < dt * rate:
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
            "coding_desk": (["</>", "{ }", "01"], "#34d399"),
            "library": (["📖", "doc", "🔍"], "#fbbf24"),
            "server_lab": (["⚡", "$>", "OK"], "#fb923c"),
            "strategy_board": (["💭", "💡"], "#38bdf8"),
            "orchestrator_hub": (["📡", "⚡"], "#fbbf24"),
            "web_station": (["🌐", "200"], "#22d3ee"),
            "art_studio": (["✨", "UI"], "#e879f9"),
            "lounge": (["~"], "#94a3b8"),
        }
        syms, color = table.get(self.current_station, (["✨"], "#38bdf8"))
        particles.append({
            "x": self.x + random.uniform(-7, 7),
            "y": self.y - 24,
            "vx": random.uniform(-4, 4),
            "vy": random.uniform(-24, -16),
            "life": 1.0,
            "max_life": 1.0,
            "type": "text",
            "text": random.choice(syms),
            "color": color,
        })


# =============================================================================
# WIDGET NATIVO DE RENDERIZADO PIXEL ART (MODO ESPECTADOR PURO A 60 FPS)
# =============================================================================
class PixelOfficeWidget(QWidget):
    def __init__(self, on_select_agent, parent=None):
        super().__init__(parent)
        self.on_select_agent = on_select_agent

        self.entities: Dict[str, QtAgentEntity] = {}
        self.particles: List[Dict[str, Any]] = []
        self.selected_agent_id: Optional[str] = None
        self.hovered_agent_id: Optional[str] = None
        self.filter_mode: str = "all"

        self.setMouseTracking(True)
        self.setMinimumSize(720, 440)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._last_time = time.perf_counter()
        self._start_time = self._last_time

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

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

    def _visible_entities(self) -> List[QtAgentEntity]:
        return [
            e for e in self.entities.values()
            if (not e.is_simulated) and (self.filter_mode == "all" or e.is_live)
        ]

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
        found = None
        for ent in self._visible_entities():
            if math.hypot(wx - ent.x, wy - (ent.y - 6)) <= 24:
                found = ent.id
                break
        self.hovered_agent_id = found
        self.setCursor(Qt.CursorShape.PointingHandCursor if found else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())
        for ent in self._visible_entities():
            if math.hypot(wx - ent.x, wy - (ent.y - 6)) <= 24:
                self.selected_agent_id = ent.id
                self.on_select_agent(ent.id)
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(self.rect(), QColor("#080b13"))

        scale, ox, oy = self._compute_transform()
        painter.translate(ox, oy)
        painter.scale(scale, scale)

        now_sec = time.perf_counter() - self._start_time
        visible = self._visible_entities()
        visible.sort(key=lambda e: e.y)

        self._draw_world(painter, now_sec, visible)
        self._draw_orchestrator_links(painter, now_sec, visible)

        # Capa 1: Cuerpos de agentes
        for ent in visible:
            self._draw_agent_body(painter, ent, now_sec)

        # Capa 2: Etiquetas de fondo
        priority = None
        for ent in visible:
            if ent.id in (self.hovered_agent_id, self.selected_agent_id):
                priority = ent
                continue
            self._draw_agent_overlay(painter, ent, now_sec, force_full=False)

        # Capa 3: Agente seleccionado o bajo cursor siempre encima
        if priority:
            self._draw_agent_overlay(painter, priority, now_sec, force_full=True)

        self._draw_particles(painter)
        painter.end()

    def _rect(self, p: QPainter, x, y, w, h, fill: str, stroke: Optional[str] = None, sw: int = 1):
        p.fillRect(int(x), int(y), int(w), int(h), QColor(fill))
        if stroke:
            p.setPen(QPen(QColor(stroke), sw))
            p.drawRect(int(x), int(y), int(w), int(h))

    def _round_pill(self, p: QPainter, x, y, w, h, radius: float, fill: QColor, stroke: Optional[QColor] = None):
        p.setBrush(fill)
        p.setPen(QPen(stroke, 1) if stroke else Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_world(self, p: QPainter, now_sec: float, visible: List[QtAgentEntity]):
        occupied: Dict[str, int] = {}
        for e in visible:
            occupied[e.current_station] = occupied.get(e.current_station, 0) + 1

        p.fillRect(0, 0, WORLD_W, WORLD_H, QColor("#080b13"))

        # Corredor central
        self._rect(p, 20, 264, WORLD_W - 40, 60, "#101624", "#1d283f", 1)
        p.setPen(QPen(QColor(56, 189, 248, 35), 1, Qt.PenStyle.DashLine))
        p.drawLine(40, HALLWAY_Y, WORLD_W - 40, HALLWAY_Y)

        p.setPen(QColor(148, 163, 184, 65))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(QRectF(0, HALLWAY_Y - 8, WORLD_W, 16), Qt.AlignmentFlag.AlignCenter,
                   "ANTIGRAVITY HQ  ·  CORREDOR CENTRAL")

        for st in STATIONS.values():
            cnt = occupied.get(st["id"], 0)
            is_working = cnt > 0 and st["id"] != "lounge"
            self._draw_station_base(p, st, cnt, is_working)

        self._draw_library_furniture(p, STATIONS["library"])
        self._draw_strategy_furniture(p, STATIONS["strategy_board"])
        self._draw_orchestrator_furniture(p, STATIONS["orchestrator_hub"], now_sec, occupied.get("orchestrator_hub", 0) > 0)
        self._draw_web_furniture(p, STATIONS["web_station"], now_sec, occupied.get("web_station", 0) > 0)
        self._draw_coding_furniture(p, STATIONS["coding_desk"], now_sec, visible)
        self._draw_server_furniture(p, STATIONS["server_lab"], now_sec, occupied.get("server_lab", 0) > 0)
        self._draw_art_furniture(p, STATIONS["art_studio"])
        self._draw_lounge_furniture(p, STATIONS["lounge"], now_sec)

    def _draw_station_base(self, p: QPainter, st: Dict[str, Any], count: int, is_working: bool):
        x, y, w, h = st["rect"]
        tile = 16
        cA, cB = QColor(st["floorA"]), QColor(st["floorB"])
        for ty in range(y, y + h, tile):
            for tx in range(x, x + w, tile):
                even = (((tx - x) // tile + (ty - y) // tile) % 2) == 0
                p.fillRect(tx, ty, min(tile, x + w - tx), min(tile, y + h - ty), cA if even else cB)

        p.setPen(QPen(QColor(st["accent"] if is_working else "#23304a"), 2 if is_working else 1))
        p.drawRect(x, y, w, h)

        # Puerta al pasillo
        dx, dy = st["door"]
        if dy <= 270:
            p.fillRect(dx - 18, y + h - 3, 36, 6, QColor("#101624"))
        else:
            p.fillRect(dx - 18, y - 3, 36, 6, QColor("#101624"))

        # Cabecera limpia de la sala
        p.fillRect(x + 1, y + 1, w - 2, 26, QColor(10, 14, 24, 200))
        p.setPen(QColor(st["accent"] if is_working else "#94a3b8"))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(x + 10, y + 18, f"{st['icon']} {st['title']}")

        if count > 0:
            self._round_pill(p, x + w - 28, y + 6, 20, 15, 7, QColor(56, 189, 248, 40))
            p.setPen(QColor(st["accent"] if is_working else "#cbd5e1"))
            p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            p.drawText(QRectF(x + w - 28, y + 6, 20, 15), Qt.AlignmentFlag.AlignCenter, str(count))

    def _draw_library_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        books = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ec4899"]
        for s in range(3):
            sx, sy = x + 18 + s * 72, y + 38
            self._rect(p, sx, sy, 62, 52, "#3e2723", "#6d4c41", 1)
            for row in range(3):
                ry = sy + 6 + row * 15
                p.fillRect(sx + 4, ry + 10, 54, 3, QColor("#2b1b17"))
                for b in range(8):
                    p.fillRect(sx + 6 + b * 6, ry, 5, 10, QColor(books[(s * 7 + row * 3 + b) % len(books)]))
        for t in range(2):
            tx, ty = x + 36 + t * 98, y + 162
            self._rect(p, tx, ty, 70, 30, "#4e342e", "#795548", 1)
            self._rect(p, tx + 14, ty + 7, 16, 12, "#fef3c7", "#a1887f", 1)
            self._rect(p, tx + 30, ty + 7, 16, 12, "#fef3c7", "#a1887f", 1)

    def _draw_strategy_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        bx, by = x + 22, y + 40
        self._rect(p, bx, by, 188, 54, "#0d1726", "#2a4365", 1)
        p.fillRect(bx + 14, by + 13, 28, 14, QColor("#38bdf8"))
        p.fillRect(bx + 62, by + 13, 28, 14, QColor("#fbbf24"))
        p.fillRect(bx + 110, by + 13, 28, 14, QColor("#34d399"))
        p.setPen(QPen(QColor("#94a3b8"), 2))
        p.drawLine(bx + 42, by + 20, bx + 62, by + 20)
        p.drawLine(bx + 90, by + 20, bx + 110, by + 20)
        p.fillRect(bx + 152, by + 11, 10, 10, QColor("#fde047"))
        p.fillRect(bx + 166, by + 11, 10, 10, QColor("#f472b6"))
        p.fillRect(bx + 152, by + 25, 10, 10, QColor("#34d399"))
        self._rect(p, x + 48, y + 162, 136, 26, "#162235", "#2a4365", 1)

    def _draw_orchestrator_furniture(self, p: QPainter, st, now_sec: float, active: bool):
        x, y, _, _ = st["rect"]
        cx, cy = x + 80, y + 98
        self._rect(p, cx - 42, cy - 26, 84, 52, "#19130b", "#fbbf24" if active else "#5c4620", 1)
        pulse = 17 + math.sin(now_sec * 3.5) * 3.0
        p.setPen(QPen(QColor(251, 191, 36, 215 if active else 90), 2))
        p.drawEllipse(QPointF(cx, cy), pulse, pulse)
        p.setPen(QColor("#fcd34d"))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 40, cy - 8, 80, 16), Qt.AlignmentFlag.AlignCenter, "ORCH-CORE")

        px, py = x + 184, y + 92
        self._rect(p, px - 26, py - 26, 52, 52, "#140f24", "#7e22ce", 1)
        pr = 13 + math.cos(now_sec * 4.0) * 2.5
        p.setPen(QPen(QColor(56, 189, 248, 165), 2))
        p.drawEllipse(QPointF(px, py), pr, pr)
        p.setPen(QColor("#c084fc"))
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.drawText(QRectF(px - 35, py + 29, 70, 14), Qt.AlignmentFlag.AlignCenter, "SPAWN PAD")

    def _draw_web_furniture(self, p: QPainter, st, now_sec: float, active: bool):
        x, y, _, _ = st["rect"]
        for m in range(3):
            mx, my = x + 22 + m * 68, y + 46
            self._rect(p, mx, my, 56, 34, "#0a1724", "#22d3ee" if active else "#1e3a52", 1)
            bw = (14 + ((int(now_sec * 6) + m * 5) % 30)) if active else 26
            bar_col = QColor(34, 211, 238, 115 if active else 42)
            p.fillRect(mx + 6, my + 8, bw, 4, bar_col)
            p.fillRect(mx + 6, my + 16, 36, 4, bar_col)
            p.fillRect(mx + 6, my + 24, 22, 4, bar_col)
        gx, gy = x + 121, y + 164
        self._rect(p, gx - 34, gy - 20, 68, 40, "#0b1a24", "#1e3a52", 1)
        p.setPen(QPen(QColor(34, 211, 238, 220 if active else 100), 1))
        p.drawEllipse(QPointF(gx, gy), 13, 13)
        p.drawLine(gx - 13, gy, gx + 13, gy)
        p.drawLine(gx, gy - 13, gx, gy + 13)

    def _draw_coding_furniture(self, p: QPainter, st, now_sec: float, visible: List[QtAgentEntity]):
        active_desks = {e.slot_index for e in visible if not e.is_walking and e.current_station == "coding_desk"}
        for idx, (sx, sy, _) in enumerate(st["slots"]):
            dx, dy = sx - 42, sy - 46
            occ = idx in active_desks
            self._rect(p, sx - 10, sy + 4, 20, 14, "#1e293b", "#334155", 1)
            self._rect(p, dx, dy, 84, 34, "#1e293b", "#34d399" if occ else "#334155", 1)
            for m in range(2):
                mx, my = dx + 8 + m * 36, dy + 4
                self._rect(p, mx, my, 28, 18, "#062116" if occ else "#0c121d", "#34d399" if occ else "#263245", 1)
                if occ:
                    sc = int(now_sec * 8 + idx + m) % 3
                    c = QColor("#34d399" if m == 0 else "#38bdf8")
                    p.fillRect(mx + 3, my + 4 + sc, 16, 2, c)
                    p.fillRect(mx + 3, my + 9, 20, 2, c)
                    p.fillRect(mx + 3, my + 14 - sc, 12, 2, c)
            self._rect(p, dx + 24, dy + 25, 28, 5, "#0f172a", "#334155", 1)
            self._rect(p, dx + 70, dy + 6, 10, 22, "#0f172a", "#38bdf8" if occ else "#263245", 1)

    def _draw_server_furniture(self, p: QPainter, st, now_sec: float, active: bool):
        x, y, _, _ = st["rect"]
        for r in range(4):
            rx, ry = x + 15 + r * 49, y + 40
            self._rect(p, rx, ry, 40, 62, "#0f131a", "#2d3748", 1)
            for u in range(4):
                uy = ry + 6 + u * 14
                p.fillRect(rx + 4, uy, 32, 10, QColor("#1a202c"))
                spd = 8 if active else 2
                blink = ((int(now_sec * spd) + r * 3 + u) % 3) == 0
                p.fillRect(rx + 7, uy + 3, 4, 4, QColor("#34d399" if blink else "#fb923c"))
                p.fillRect(rx + 14, uy + 3, 4, 4, QColor("#38bdf8"))
        self._rect(p, x + 32, y + 174, 154, 32, "#111620", "#fb923c" if active else "#334155", 1)
        p.setPen(QColor("#34d399" if active else "#64748b"))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(x + 43, y + 194, "$ antigravity --exec")

    def _draw_art_furniture(self, p: QPainter, st):
        x, y, _, _ = st["rect"]
        self._rect(p, x + 18, y + 46, 48, 40, "#fef3c7", "#d97706", 1)
        p.fillRect(x + 25, y + 53, 15, 13, QColor("#f43f5e"))
        p.fillRect(x + 40, y + 59, 17, 17, QColor("#38bdf8"))
        self._rect(p, x + 80, y + 50, 56, 36, "#2e1065", "#a855f7", 1)
        self._rect(p, x + 90, y + 58, 36, 20, "#13072e", "#38bdf8", 1)

    def _draw_lounge_furniture(self, p: QPainter, st, now_sec: float):
        x, y, _, _ = st["rect"]
        self._rect(p, x + 20, y + 42, 202, 30, "#3b231e", "#6d4c41", 1)
        self._rect(p, x + 34, y + 46, 26, 22, "#991b1b", "#f87171", 1)
        steam_y = int(y + 40 - ((now_sec * 12) % 8))
        p.fillRect(x + 44, steam_y, 3, 4, QColor(255, 255, 255, 55))
        self._rect(p, x + 186, y + 44, 22, 24, "#bae6fd", "#38bdf8", 1)
        self._rect(p, x + 46, y + 148, 150, 34, "#6b153b", "#be185d", 1)
        p.fillRect(x + 54, y + 155, 134, 20, QColor("#831843"))

    def _draw_orchestrator_links(self, p: QPainter, now_sec: float, visible: List[QtAgentEntity]):
        vis_ids = {e.id for e in visible}
        for ent in visible:
            if ent.parent_id and ent.parent_id in vis_ids:
                parent = self.entities[ent.parent_id]
                p.setPen(QPen(QColor(251, 191, 36, 130), 2, Qt.PenStyle.DashLine))
                p.drawLine(int(parent.x), int(parent.y - 8), int(ent.x), int(ent.y - 8))
                t = (now_sec * 0.85) % 1.0
                px = parent.x + (ent.x - parent.x) * t
                py = (parent.y - 8) + ((ent.y - 8) - (parent.y - 8)) * t
                p.fillRect(int(px - 2.5), int(py - 2.5), 5, 5, QColor("#38bdf8"))

    def _draw_agent_body(self, p: QPainter, ent: QtAgentEntity, now_sec: float):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        is_hov = (ent.id == self.hovered_agent_id)
        walk_bob = (-3 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 3.5 + x))

        if ent.spawn_timer > 0:
            p.setPen(QPen(QColor("#38bdf8"), 2))
            r = 20 * ent.spawn_timer
            p.drawEllipse(QPointF(x, y - 6), r, r)

        if is_sel or is_hov:
            p.setPen(QPen(QColor("#38bdf8" if is_sel else "#cbd5e1"), 2 if is_sel else 1))
            p.drawEllipse(QPointF(x, y + 12), 15, 6)

        p.fillRect(x - 9, y + 10, 18, 4, QColor(0, 0, 0, 110))
        py = y + walk_bob

        leg_l = (-3 if ent.walk_frame == 1 else 2 if ent.walk_frame == 3 else 0) if ent.is_walking else 0
        leg_r = (-3 if ent.walk_frame == 3 else 2 if ent.walk_frame == 1 else 0) if ent.is_walking else 0
        p.fillRect(x - 6, py + 3 + leg_l, 4, 8, QColor("#1e293b"))
        p.fillRect(x + 2, py + 3 + leg_r, 4, 8, QColor("#1e293b"))

        suit = ent.palette.get("suit", "#38bdf8")
        accent = ent.palette.get("accent", "#ffffff")
        hair = ent.palette.get("hair", "#1e293b")
        self._rect(p, x - 8, py - 9, 16, 13, suit, "#090d16", 1)
        p.fillRect(x - 2, py - 6, 4, 4, QColor(accent))

        typing = (not ent.is_walking) and (ent.current_station in ("coding_desk", "server_lab"))
        jitter = int(math.sin(now_sec * 24) * 2) if typing else 0
        p.fillRect(x - 12, py - 8 + jitter, 4, 9, QColor(suit))
        p.fillRect(x + 8, py - 8 - jitter, 4, 9, QColor(suit))

        self._rect(p, x - 7, py - 22, 14, 13, "#fed7aa", "#090d16", 1)
        p.fillRect(x - 8, py - 24, 16, 5, QColor(hair))
        if ent.face == "left":
            p.fillRect(x + 4, py - 22, 4, 8, QColor(hair))
        elif ent.face == "right":
            p.fillRect(x - 8, py - 22, 4, 8, QColor(hair))

        if ent.face == "left":
            p.fillRect(x - 5, py - 16, 2, 3, QColor("#0f172a"))
            p.fillRect(x - 1, py - 16, 2, 3, QColor("#0f172a"))
        elif ent.face == "right":
            p.fillRect(x - 1, py - 16, 2, 3, QColor("#0f172a"))
            p.fillRect(x + 3, py - 16, 2, 3, QColor("#0f172a"))
        elif ent.face == "down":
            p.fillRect(x - 4, py - 16, 2, 3, QColor("#0f172a"))
            p.fillRect(x + 2, py - 16, 2, 3, QColor("#0f172a"))

        if ent.is_subagent:
            p.fillRect(x - 1, py - 29, 2, 5, QColor("#fbbf24"))
            p.fillRect(x - 2, py - 31, 4, 2, QColor("#38bdf8"))
        else:
            p.fillRect(x - 9, py - 18, 2, 5, QColor(accent))
            p.fillRect(x + 7, py - 18, 2, 5, QColor(accent))

        if not ent.is_walking:
            if ent.current_station == "library":
                self._rect(p, x - 6, py - 5, 12, 8, "#fef3c7", "#d97706", 1)
            elif ent.current_station == "lounge":
                self._rect(p, x + 5, py - 6, 6, 7, "#f8fafc", "#f87171", 1)

    def _draw_agent_overlay(self, p: QPainter, ent: QtAgentEntity, now_sec: float, force_full: bool):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        is_hov = (ent.id == self.hovered_agent_id)
        is_idle_lounge = (not ent.is_walking) and (ent.current_station == "lounge")
        walk_bob = (-3 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 3.5 + x))
        py = y + walk_bob

        # Etiqueta compacta debajo de los pies
        label = f"⚡ {ent.compact_name}" if ent.is_subagent else ent.compact_name
        if len(label) > 13:
            label = label[:12] + "…"
        font_name = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(font_name)
        nw = QFontMetrics(font_name).horizontalAdvance(label) + 10
        self._round_pill(
            p, x - nw / 2, y + 15, nw, 14, 4,
            QColor(15, 23, 42, 240 if is_sel else 205),
            QColor("#38bdf8") if is_sel else QColor(148, 163, 184, 65),
        )
        p.setPen(QColor("#ffffff" if is_sel else "#cbd5e1"))
        p.drawText(QRectF(x - nw / 2, y + 15, nw, 14), Qt.AlignmentFlag.AlignCenter, label)

        # Globo inteligente anti-solapamiento
        if is_idle_lounge and not force_full:
            self._round_pill(p, x - 10, py - 42, 20, 15, 7, QColor(15, 23, 42, 210), QColor(248, 113, 113, 90))
            p.setPen(QColor("#fca5a5"))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRectF(x - 10, py - 42, 20, 15), Qt.AlignmentFlag.AlignCenter, "☕")
        else:
            bubble = f"→ {STATIONS[ent.current_station]['title']}" if ent.is_walking else ent.badge
            if bubble:
                if len(bubble) > 26:
                    bubble = bubble[:25] + "…"
                font_b = QFont("Segoe UI", 8, QFont.Weight.Bold)
                p.setFont(font_b)
                bw = QFontMetrics(font_b).horizontalAdvance(bubble) + 14
                bx = max(10.0, min(WORLD_W - bw - 10.0, x - bw / 2))
                by = py - 46
                self._round_pill(
                    p, bx, by, bw, 18, 6,
                    QColor(15, 23, 42, 242),
                    QColor("#38bdf8") if (is_sel or is_hov) else QColor(148, 163, 184, 90),
                )
                p.setPen(QColor("#f1f5f9"))
                p.drawText(QRectF(bx, by, bw, 18), Qt.AlignmentFlag.AlignCenter, bubble)

    def _draw_particles(self, p: QPainter):
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        for pt in self.particles:
            alpha = max(0, min(255, int(255 * (pt["life"] / pt["max_life"]))))
            c = QColor(pt["color"])
            c.setAlpha(alpha)
            if pt["type"] == "dust":
                p.fillRect(int(pt["x"]), int(pt["y"]), 3, 3, c)
            else:
                p.setPen(c)
                p.drawText(int(pt["x"]), int(pt["y"]), pt["text"])


# =============================================================================
# ESTILO MODERNO LIMPIO PARA PyQt6 (CON SCROLLBARS OSCUROS)
# =============================================================================
CLEAN_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #090d16;
    color: #eef3ff;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#TopBar, QFrame#SidePanel {
    background-color: #101624;
    border: 1px solid #1f2b42;
    border-radius: 10px;
}
QLabel#BrandTitle {
    font-family: 'Consolas';
    font-size: 14px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#BrandSub {
    font-size: 11px;
    color: #6e7f9c;
}
QLabel#LivePill {
    background-color: rgba(52, 211, 153, 28);
    border: 1px solid rgba(52, 211, 153, 95);
    border-radius: 11px;
    padding: 3px 10px;
    color: #34d399;
    font-family: 'Consolas';
    font-size: 10px;
    font-weight: bold;
}
QLabel#StatsPill {
    background-color: #151d2e;
    border: 1px solid #1f2b42;
    border-radius: 8px;
    padding: 4px 10px;
    color: #a8b7d0;
    font-family: 'Consolas';
    font-size: 11px;
}
QLabel#PanelTitle {
    background-color: #151d2e;
    color: #a8b7d0;
    font-family: 'Consolas';
    font-size: 10px;
    font-weight: bold;
    padding: 7px 12px;
    border-bottom: 1px solid #1f2b42;
}
QPushButton {
    background-color: #151d2e;
    color: #a8b7d0;
    border: 1px solid #1f2b42;
    border-radius: 7px;
    padding: 5px 11px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1b253b;
    color: #ffffff;
    border-color: #2e4266;
}
QPushButton:checked {
    background-color: rgba(56, 189, 248, 45);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 120);
}
QListWidget {
    background-color: #101624;
    border: none;
    outline: none;
    padding: 4px;
    font-family: 'Consolas';
    font-size: 11px;
}
QListWidget::item {
    background-color: #151d2e;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 7px 8px;
    margin: 2px 3px;
    color: #e2e8f0;
}
QListWidget::item:hover {
    background-color: #1b253b;
}
QListWidget::item:selected {
    background-color: rgba(56, 189, 248, 28);
    border: 1px solid rgba(56, 189, 248, 110);
    color: #ffffff;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #24324d;
    border-radius: 3px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #354a73;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class PixelAgentsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PixelAgents // Antigravity")
        self.resize(1340, 800)
        self.setMinimumSize(1020, 640)
        self.setStyleSheet(CLEAN_STYLESHEET)

        self.watcher = AntigravityBrainWatcher()
        self.watcher.start()
        self.last_event_id = 0
        self.is_first_sync = True
        self._recent_logs: List[Dict[str, Any]] = []

        self._build_ui()

        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._sync_from_watcher)
        self.sync_timer.start(750)
        self._sync_from_watcher()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. BARRA SUPERIOR MINIMALISTA
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(14, 8, 14, 8)
        top_layout.setSpacing(10)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        title_lbl = QLabel("👾 PIXEL AGENTS  ·  ANTIGRAVITY")
        title_lbl.setObjectName("BrandTitle")
        sub_lbl = QLabel("Modo Espectador en Tiempo Real")
        sub_lbl.setObjectName("BrandSub")
        brand_col.addWidget(title_lbl)
        brand_col.addWidget(sub_lbl)
        top_layout.addLayout(brand_col)

        top_layout.addStretch()

        self.lbl_live = QLabel("● EN VIVO")
        self.lbl_live.setObjectName("LivePill")
        top_layout.addWidget(self.lbl_live)

        self.lbl_stats = QLabel("0 chats · 0 subagentes")
        self.lbl_stats.setObjectName("StatsPill")
        top_layout.addWidget(self.lbl_stats)

        self.btn_filter_live = QPushButton("Solo Activos")
        self.btn_filter_live.setCheckable(True)
        self.btn_filter_live.toggled.connect(self._toggle_filter_live)
        top_layout.addWidget(self.btn_filter_live)

        self.btn_pin = QPushButton("📌 Fijar Encima")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Mantiene PixelAgents flotando encima de Antigravity / VS Code")
        self.btn_pin.toggled.connect(self._toggle_always_on_top)
        top_layout.addWidget(self.btn_pin)

        main_layout.addWidget(topbar)

        # 2. CUERPO PRINCIPAL (LIENZO 100% LIMPIO + PANEL LATERAL)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter, stretch=1)

        self.office_widget = PixelOfficeWidget(on_select_agent=self._on_agent_selected)
        splitter.addWidget(self.office_widget)

        # Panel derecho limpio
        side_panel = QFrame()
        side_panel.setObjectName("SidePanel")
        side_panel.setMinimumWidth(290)
        side_panel.setMaximumWidth(370)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        lbl_insp = QLabel("INSPECTOR")
        lbl_insp.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_insp)

        self.lbl_inspector = QLabel("Haz clic sobre un personaje para ver sus detalles.")
        self.lbl_inspector.setWordWrap(True)
        self.lbl_inspector.setStyleSheet("padding: 12px; font-size: 12px; color: #cbd5e1;")
        side_layout.addWidget(self.lbl_inspector)

        lbl_agents = QLabel("AGENTES")
        lbl_agents.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_agents)

        self.list_agents = QListWidget()
        self.list_agents.itemClicked.connect(self._on_list_agent_clicked)
        side_layout.addWidget(self.list_agents, stretch=5)

        lbl_feed = QLabel("ACTIVIDAD RECIENTE")
        lbl_feed.setObjectName("PanelTitle")
        side_layout.addWidget(lbl_feed)

        self.list_feed = QListWidget()
        side_layout.addWidget(self.list_feed, stretch=4)

        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

    def _toggle_always_on_top(self, checked: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _toggle_filter_live(self, checked: bool):
        self.office_widget.filter_mode = "live" if checked else "all"
        self._refresh_sidebar()

    def _on_agent_selected(self, agent_id: str):
        self.office_widget.selected_agent_id = agent_id
        self._refresh_sidebar()

    def _on_list_agent_clicked(self, item: QListWidgetItem):
        aid = item.data(Qt.ItemDataRole.UserRole)
        if aid:
            self.office_widget.selected_agent_id = aid
            self._refresh_sidebar()

    def _sync_from_watcher(self):
        snap = self.watcher.get_snapshot(since_event_id=self.last_event_id)
        ents = self.office_widget.entities
        current_ids = set()

        for ag in snap.get("agents", []):
            if ag.get("is_simulated"):
                continue
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
                    target.enqueue_action(ev)
            if snap.get("latest_event_id", 0) > self.last_event_id:
                self.last_event_id = snap["latest_event_id"]

        if not self.office_widget.selected_agent_id and ents:
            self.office_widget.selected_agent_id = next(iter(ents.keys()))

        self._recent_logs = [
            l for l in snap.get("recent_log", [])
            if not str(l.get("agent_id", "")).startswith(("sim-", "sub-"))
        ]
        self._refresh_sidebar()

    def _refresh_sidebar(self):
        visible = self.office_widget._visible_entities()
        chats = sum(1 for e in visible if not e.is_subagent)
        subs = sum(1 for e in visible if e.is_subagent)
        self.lbl_stats.setText(f"{chats} chats · {subs} subagentes")

        sel = self.office_widget.entities.get(self.office_widget.selected_agent_id or "")
        if sel:
            st = STATIONS.get(sel.current_station, {})
            st_label = f"{st.get('icon', '')} {st.get('title', sel.current_station)}"
            role = f"SUB · {sel.subagent_type.upper()}" if sel.is_subagent else "PRINCIPAL"
            self.lbl_inspector.setText(
                f"<b style='font-size:13px;color:#ffffff'>{sel.name}</b> "
                f"<span style='color:#38bdf8;font-size:10px'>[{role}]</span><br>"
                f"<span style='color:#fbbf24'>{sel.model}</span><br><br>"
                f"<b>Sala:</b> {st_label}<br>"
                f"<b>Estado:</b> {sel.badge}<br>"
                f"<span style='color:#6e7f9c;font-size:11px'>{sel.chat_title}</span>"
            )
        else:
            self.lbl_inspector.setText("Haz clic sobre un personaje para ver sus detalles.")

        self.list_agents.clear()
        for e in visible:
            prefix = "↳ " if e.is_subagent else ""
            item = QListWidgetItem(f"{prefix}{e.name}\n{e.badge}")
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            self.list_agents.addItem(item)
            if e.id == self.office_widget.selected_agent_id:
                item.setSelected(True)

        self.list_feed.clear()
        for log in self._recent_logs[:12]:
            txt = f"{log.get('time_str', '')} · {log.get('agent_name', '')}\n{log.get('badge', '')}"
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
