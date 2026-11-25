# -*- coding: utf-8 -*-
"""
Pixelavity // Antigravity Live Visualizer — Native PyQt6 Desktop App
Incluye:
  1. Sprites Chibi Pixel Art con contorno oscuro en 4 direcciones (Adelante, Atrás, Izquierda, Derecha)
  2. Creador de Personajes (3 por defecto + personalización completa y selección aleatoria sin repetir)
  3. Personalizador de Background / Oficina (pisos, paredes, dispositivos y decoración arrastrables)
  4. Validación de dispositivos mínimos (mín. 1 computador, 1 mueble de libros, etc.)
  5. Colaboración automática ante demanda (Pair-Programming: si hay 2 computadores y 3 agentes,
     1 usa un computador y los otros 2 comparten el otro programando y revisando juntos).
"""

import os
import re
import sys
import math
import time
import random
from typing import Dict, List, Optional, Any, Tuple

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QSizePolicy, QSplitter, QMessageBox
)

if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.watcher import AntigravityBrainWatcher
from core.customization import (
    CustomizationManager,
    FLOOR_MATERIALS,
    DEVICE_CATALOG,
    DECORATION_CATALOG,
    DEFAULT_CHARACTERS,
)
from core.sprites import SPRITE_ENGINE
from core.dialogs_qt import CharacterCreatorDialog, OfficeEditorBar


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
        "accent": "#d49a6a",
    },
    "strategy_board": {
        "id": "strategy_board",
        "icon": "💭",
        "title": "ESTRATEGIA",
        "rect": (278, 20, 232, 240),
        "door": (394, 260),
        "accent": "#38bdf8",
    },
    "orchestrator_hub": {
        "id": "orchestrator_hub",
        "icon": "🎛️",
        "title": "ORCHESTRATOR",
        "rect": (524, 20, 240, 240),
        "door": (644, 260),
        "accent": "#fbbf24",
    },
    "web_station": {
        "id": "web_station",
        "icon": "🌐",
        "title": "CABINA WEB",
        "rect": (778, 20, 242, 240),
        "door": (899, 260),
        "accent": "#22d3ee",
    },
    "coding_desk": {
        "id": "coding_desk",
        "icon": "💻",
        "title": "COMPUTADORES",
        "rect": (20, 328, 344, 272),
        "door": (192, 328),
        "accent": "#34d399",
    },
    "server_lab": {
        "id": "server_lab",
        "icon": "⚡",
        "title": "TERMINAL LAB",
        "rect": (378, 328, 218, 272),
        "door": (487, 328),
        "accent": "#fb923c",
    },
    "art_studio": {
        "id": "art_studio",
        "icon": "🎨",
        "title": "ESTUDIO UI",
        "rect": (610, 328, 154, 272),
        "door": (687, 328),
        "accent": "#e879f9",
    },
    "lounge": {
        "id": "lounge",
        "icon": "☕",
        "title": "CAFETERÍA & LOUNGE",
        "rect": (778, 328, 242, 272),
        "door": (899, 328),
        "accent": "#f87171",
    },
}


def find_room_at(wx: float, wy: float) -> str:
    for sid, st in STATIONS.items():
        rx, ry, rw, rh = st["rect"]
        if rx <= wx <= rx + rw and ry <= wy <= ry + rh:
            return sid
    return "hallway"


# =============================================================================
# ENTIDAD DE AGENTE CON SOPORTE 4 DIRECCIONES Y MODO COLABORACIÓN
# =============================================================================
class QtAgentEntity:
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.is_walking = False
        self.walk_frame = 0
        self.walk_timer = 0.0
        self.waypoints: List[Tuple[float, float, Optional[str]]] = []
        self.action_queue: List[Dict[str, Any]] = []
        self.hold_timer = 0.0

        init_st = data.get("station", "lounge")
        if init_st not in STATIONS:
            init_st = "lounge"
        self.current_station = init_st

        # Datos de colaboración / dispositivo asignado
        self.assigned_device_id: Optional[str] = None
        self.target_x: float = 880.0
        self.target_y: float = 440.0
        self.target_face: str = "down"
        self.role: str = "primary"
        self.is_collaborating: bool = False
        self.partner_name: Optional[str] = None

        # Personaje visual asignado del pool del usuario
        self.character: Dict[str, Any] = DEFAULT_CHARACTERS[0]

        self.sync_metadata(data)

        if self.is_subagent:
            self.x = 708.0
            self.y = 114.0
            self.spawn_timer = 1.4
        else:
            self.x = self.target_x
            self.y = self.target_y
            self.spawn_timer = 0.6

        self.face = "down"

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

    def apply_slot_allocation(self, alloc: Dict[str, Any], show_walls: bool = True):
        """
        Actualiza el destino físico del agente según el dispositivo que le tocó
        (y si está en modo colaboración / pair-programming al lado de otro compañero).
        """
        new_tx = float(alloc["x"])
        new_ty = float(alloc["y"])
        new_face = alloc.get("face", "up")
        self.assigned_device_id = alloc.get("device_id")
        self.role = alloc.get("role", "primary")
        self.is_collaborating = bool(alloc.get("is_collaborating", False))
        self.partner_name = alloc.get("partner_name")

        # Si el destino cambió significativamente y no está ya caminando hacia él, trazar ruta
        if math.hypot(new_tx - self.target_x, new_ty - self.target_y) > 6.0:
            self.target_x = new_tx
            self.target_y = new_ty
            self.target_face = new_face
            if not self.is_walking:
                self._build_path_to(new_tx, new_ty, new_face, show_walls)
            elif self.waypoints:
                self.waypoints[-1] = (new_tx, new_ty, new_face)
        else:
            self.target_face = new_face
            if not self.is_walking:
                self.face = new_face

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

    def _build_path_to(self, tx: float, ty: float, tface: str, show_walls: bool = True):
        pts: List[Tuple[float, float, Optional[str]]] = []
        from_room = find_room_at(self.x, self.y)
        to_room = find_room_at(tx, ty)

        if show_walls and from_room != to_room:
            if from_room in STATIONS:
                fdx, fdy = STATIONS[from_room]["door"]
                pts.append((float(fdx), float(fdy), None))
                pts.append((float(fdx), float(HALLWAY_Y), None))
            else:
                pts.append((self.x, float(HALLWAY_Y), None))

            if to_room in STATIONS:
                tdx, tdy = STATIONS[to_room]["door"]
                pts.append((float(tdx), float(HALLWAY_Y), None))
                pts.append((float(tdx), float(tdy), None))
            else:
                pts.append((tx, float(HALLWAY_Y), None))

        pts.append((tx, ty, tface))
        self.waypoints = pts
        self.is_walking = True

    def update(self, dt: float, particles: List[Dict[str, Any]], show_walls: bool = True):
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
                    self.face = self.target_face
                    self.hold_timer = 1.8 if len(self.action_queue) > 1 else 2.6
            else:
                self.x += (dx / dist) * speed * dt
                self.y += (dy / dist) * speed * dt
                # Actualizar dirección de sprite (4 direcciones: adelante, atrás, izquierda, derecha)
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
                        "y": self.y + 13,
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

        rate = 0.4 if self.current_station == "lounge" else (2.2 if self.is_collaborating else 1.6)
        if random.random() < dt * rate:
            self._emit_particle(particles)

        if self.hold_timer <= 0 and self.action_queue:
            nxt = self.action_queue.pop(0)
            self.badge = nxt["badge"]
            self.detail = nxt["detail"]
            self.activity = nxt["activity"]
            if nxt["station"] != self.current_station:
                self.current_station = nxt["station"]
            self.hold_timer = 2.0

    def _emit_particle(self, particles: List[Dict[str, Any]]):
        if self.is_collaborating and self.current_station != "lounge":
            syms = ["💬", "💡", "👀", "</>", "🤝"]
            color = "#fbbf24" if self.role == "collaborator" else "#38bdf8"
        else:
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
            "x": self.x + random.uniform(-8, 8),
            "y": self.y - 26,
            "vx": random.uniform(-4, 4),
            "vy": random.uniform(-24, -16),
            "life": 1.0,
            "max_life": 1.0,
            "type": "text",
            "text": random.choice(syms),
            "color": color,
        })


# =============================================================================
# LIENZO 2D PIXEL ART (MODO ESPECTADOR + MODO EDICIÓN DE BACKGROUND)
# =============================================================================
class PixelOfficeWidget(QWidget):
    def __init__(self, manager: CustomizationManager, on_select_agent, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_select_agent = on_select_agent

        self.entities: Dict[str, QtAgentEntity] = {}
        self.particles: List[Dict[str, Any]] = []
        self.selected_agent_id: Optional[str] = None
        self.hovered_agent_id: Optional[str] = None
        self.filter_mode: str = "all"

        # Estado del Modo Edición de Oficina / Background
        self.edit_mode: bool = False
        self.editor_bar: Optional[OfficeEditorBar] = None
        self.dragging_item_id: Optional[str] = None
        self.hovered_item_id: Optional[str] = None

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

    def _screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        scale, ox, oy = self._compute_transform()
        if scale <= 0:
            return 0.0, 0.0
        return (sx - ox) / scale, (sy - oy) / scale

    def _visible_entities(self) -> List[QtAgentEntity]:
        return [
            e for e in self.entities.values()
            if (not e.is_simulated) and (self.filter_mode == "all" or e.is_live)
        ]

    def refresh_allocations(self):
        """
        Recalcula los personajes asignados a cada agente y sus posiciones frente a los
        dispositivos del mapa (activando Pair-Programming cuando hay más agentes que dispositivos).
        """
        office = self.manager.get_office_layout()
        show_walls = bool(office.get("show_room_walls", True))
        all_ids = list(self.entities.keys())
        char_map = self.manager.assign_characters_to_agents(all_ids)
        for aid, ent in self.entities.items():
            if aid in char_map:
                ent.character = char_map[aid]

        agents_payload = [
            {"id": e.id, "name": e.character.get("name", e.compact_name), "station": e.current_station}
            for e in self._visible_entities()
        ]
        allocs = self.manager.allocate_station_positions(agents_payload)
        for aid, alloc in allocs.items():
            if aid in self.entities:
                self.entities[aid].apply_slot_allocation(alloc, show_walls=show_walls)

    def _tick(self):
        now = time.perf_counter()
        dt = min(0.1, now - self._last_time)
        self._last_time = now

        office = self.manager.get_office_layout()
        show_walls = bool(office.get("show_room_walls", True))

        for ent in self.entities.values():
            ent.update(dt, self.particles, show_walls=show_walls)

        for i in range(len(self.particles) - 1, -1, -1):
            p = self.particles[i]
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.pop(i)
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

        self.update()

    def _find_item_at(self, wx: float, wy: float) -> Optional[Dict[str, Any]]:
        office = self.manager.get_office_layout()
        # Buscar primero en dispositivos y decoraciones (de arriba hacia abajo)
        for d in reversed(office.get("devices", [])):
            spec = DEVICE_CATALOG.get(d["type"], {"w": 64, "h": 44})
            w, h = spec["w"], spec["h"]
            if (d["x"] - w / 2) <= wx <= (d["x"] + w / 2) and (d["y"] - h / 2) <= wy <= (d["y"] + h / 2):
                return {"kind": "device", "item": d, "spec": spec}
        for dec in reversed(office.get("decorations", [])):
            spec = DECORATION_CATALOG.get(dec["type"], {"w": 32, "h": 32})
            w, h = spec["w"], spec["h"]
            if (dec["x"] - w / 2) <= wx <= (dec["x"] + w / 2) and (dec["y"] - h / 2) <= wy <= (dec["y"] + h / 2):
                return {"kind": "decoration", "item": dec, "spec": spec}
        return None

    def mouseMoveEvent(self, event):
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())

        if self.edit_mode:
            if self.dragging_item_id:
                self.manager.move_item(self.dragging_item_id, int(wx), int(wy))
                self.refresh_allocations()
                self.update()
                return
            hit = self._find_item_at(wx, wy)
            self.hovered_item_id = hit["item"]["id"] if hit else None
            self.setCursor(Qt.CursorShape.OpenHandCursor if hit else Qt.CursorShape.CrossCursor)
            return

        found = None
        for ent in self._visible_entities():
            if math.hypot(wx - ent.x, wy - (ent.y - 8)) <= 24:
                found = ent.id
                break
        self.hovered_agent_id = found
        self.setCursor(Qt.CursorShape.PointingHandCursor if found else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())

        if self.edit_mode:
            hit = self._find_item_at(wx, wy)
            if event.button() == Qt.MouseButton.LeftButton:
                if hit:
                    self.dragging_item_id = hit["item"]["id"]
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                elif self.editor_bar:
                    # Pintar el piso de la sala o corredor clicado
                    room_id = find_room_at(wx, wy)
                    mat_id = self.editor_bar.selected_floor_material()
                    self.manager.set_room_floor(room_id, mat_id)
                    self.update()
            elif event.button() == Qt.MouseButton.RightButton and hit:
                item_id = hit["item"]["id"]
                if hit["kind"] == "device":
                    ok, msg = self.manager.remove_device(item_id)
                    if not ok:
                        QMessageBox.warning(self, "Regla Mínima de Dispositivos", msg)
                    else:
                        self.refresh_allocations()
                else:
                    self.manager.remove_decoration(item_id)
                self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            for ent in self._visible_entities():
                if math.hypot(wx - ent.x, wy - (ent.y - 8)) <= 24:
                    self.selected_agent_id = ent.id
                    self.on_select_agent(ent.id)
                    return

    def mouseReleaseEvent(self, event):
        if self.dragging_item_id:
            self.dragging_item_id = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.refresh_allocations()

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

        # Capa 1: Sprites Chibi en 4 direcciones
        for ent in visible:
            self._draw_agent_body(painter, ent, now_sec)

        # Capa 2: Etiquetas de fondo
        priority = None
        for ent in visible:
            if ent.id in (self.hovered_agent_id, self.selected_agent_id):
                priority = ent
                continue
            self._draw_agent_overlay(painter, ent, now_sec, force_full=False)

        # Capa 3: Agente seleccionado o bajo cursor siempre al frente
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

    def _draw_floor_area(self, p: QPainter, x: int, y: int, w: int, h: int, mat_id: str):
        mat = FLOOR_MATERIALS.get(mat_id, FLOOR_MATERIALS["walnut_wood"])
        cA, cB = QColor(mat["colorA"]), QColor(mat["colorB"])
        pat = mat.get("pattern", "tiles")
        tile = 16

        for ty in range(y, y + h, tile):
            for tx in range(x, x + w, tile):
                tw = min(tile, x + w - tx)
                th = min(tile, y + h - ty)
                if pat == "planks":
                    row_even = (((ty - y) // 8) % 2) == 0
                    p.fillRect(tx, ty, tw, th, cA if row_even else cB)
                    p.fillRect(tx, ty, tw, 1, cB)
                elif pat == "grate":
                    p.fillRect(tx, ty, tw, th, cA)
                    p.fillRect(tx + 2, ty + 2, max(1, tw - 4), max(1, th - 4), cB)
                else:
                    even = (((tx - x) // tile + (ty - y) // tile) % 2) == 0
                    p.fillRect(tx, ty, tw, th, cA if even else cB)

    def _draw_world(self, p: QPainter, now_sec: float, visible: List[QtAgentEntity]):
        office = self.manager.get_office_layout()
        room_floors = office.get("room_floors", {})
        hallway_mat = office.get("hallway_floor", "marble_slate")
        show_walls = bool(office.get("show_room_walls", True))

        occupied: Dict[str, int] = {}
        active_device_ids = set()
        for e in visible:
            occupied[e.current_station] = occupied.get(e.current_station, 0) + 1
            if not e.is_walking and e.assigned_device_id:
                active_device_ids.add(e.assigned_device_id)

        p.fillRect(0, 0, WORLD_W, WORLD_H, QColor("#080b13"))

        # Piso del corredor central (o piso base si las paredes están desactivadas)
        if show_walls:
            self._draw_floor_area(p, 20, 264, WORLD_W - 40, 60, hallway_mat)
            p.setPen(QPen(QColor("#1d283f"), 1))
            p.drawRect(20, 264, WORLD_W - 40, 60)
        else:
            self._draw_floor_area(p, 20, 20, WORLD_W - 40, WORLD_H - 40, hallway_mat)

        # Salas
        for sid, st in STATIONS.items():
            x, y, w, h = st["rect"]
            cnt = occupied.get(sid, 0)
            is_working = cnt > 0 and sid != "lounge"
            mat_id = room_floors.get(sid, "walnut_wood")
            self._draw_floor_area(p, x, y, w, h, mat_id)

            if show_walls:
                p.setPen(QPen(QColor(st["accent"] if is_working else "#23304a"), 2 if is_working else 1))
                p.drawRect(x, y, w, h)
                dx, dy = st["door"]
                if dy <= 270:
                    p.fillRect(dx - 18, y + h - 3, 36, 6, QColor("#151d2e"))
                else:
                    p.fillRect(dx - 18, y - 3, 36, 6, QColor("#151d2e"))

            # Cabecera de la zona
            p.fillRect(x + 1, y + 1, w - 2, 24, QColor(10, 14, 24, 195))
            p.setPen(QColor(st["accent"] if is_working else "#94a3b8"))
            p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            p.drawText(x + 10, y + 16, f"{st['icon']} {st['title']}")

            if cnt > 0:
                self._round_pill(p, x + w - 28, y + 5, 20, 14, 7, QColor(56, 189, 248, 40))
                p.setPen(QColor(st["accent"] if is_working else "#cbd5e1"))
                p.drawText(QRectF(x + w - 28, y + 5, 20, 14), Qt.AlignmentFlag.AlignCenter, str(cnt))

        # Dibujar Decoraciones colocadas por el usuario
        for dec in office.get("decorations", []):
            self._draw_decoration(p, dec, now_sec)

        # Dibujar Dispositivos Interactivos colocados por el usuario
        for dev in office.get("devices", []):
            is_active = dev.get("id") in active_device_ids
            self._draw_device(p, dev, is_active, now_sec)

        if self.edit_mode:
            p.setPen(QPen(QColor(56, 189, 248, 180), 2, Qt.PenStyle.DashLine))
            p.drawRect(4, 4, WORLD_W - 8, WORLD_H - 8)

    def _draw_device(self, p: QPainter, dev: Dict[str, Any], is_active: bool, now_sec: float):
        dtype = dev.get("type", "computer_desk")
        spec = DEVICE_CATALOG.get(dtype, DEVICE_CATALOG["computer_desk"])
        cx, cy = int(dev["x"]), int(dev["y"])
        w, h = spec["w"], spec["h"]
        x, y = cx - w // 2, cy - h // 2
        is_hov = self.edit_mode and (dev.get("id") == self.hovered_item_id)

        if dtype == "computer_desk":
            # Silla + Mesa con doble monitor que se enciende cuando programan
            self._rect(p, cx - 10, cy + 16, 20, 12, "#1e293b", "#334155", 1)
            self._rect(p, x, y, w, 32, "#1e293b", "#34d399" if is_active else "#334155", 1)
            for m in range(2):
                mx, my = x + 8 + m * 34, y + 4
                self._rect(p, mx, my, 26, 17, "#062116" if is_active else "#0c121d", "#34d399" if is_active else "#263245", 1)
                if is_active:
                    sc = int(now_sec * 8 + m) % 3
                    c = QColor("#34d399" if m == 0 else "#38bdf8")
                    p.fillRect(mx + 3, my + 4 + sc, 15, 2, c)
                    p.fillRect(mx + 3, my + 9, 18, 2, c)
                    p.fillRect(mx + 3, my + 13 - sc, 11, 2, c)
            self._rect(p, x + 22, y + 24, 26, 5, "#0f172a", "#334155", 1)
            self._rect(p, x + 66, y + 6, 9, 20, "#0f172a", "#38bdf8" if is_active else "#263245", 1)

        elif dtype == "bookshelf":
            books = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ec4899"]
            self._rect(p, x, y, w, h, "#3e2723", "#d49a6a" if is_active else "#6d4c41", 1)
            for row in range(3):
                ry = y + 6 + row * 14
                p.fillRect(x + 4, ry + 10, w - 8, 3, QColor("#2b1b17"))
                for b in range(8):
                    p.fillRect(x + 6 + b * 6, ry, 5, 10, QColor(books[(row * 3 + b) % len(books)]))

        elif dtype == "server_terminal":
            self._rect(p, x, y, w, h - 14, "#0f131a", "#fb923c" if is_active else "#2d3748", 1)
            for u in range(3):
                uy = y + 5 + u * 11
                p.fillRect(x + 5, uy, w - 10, 8, QColor("#1a202c"))
                blink = ((int(now_sec * (8 if is_active else 2)) + u) % 2) == 0
                p.fillRect(x + 8, uy + 2, 4, 4, QColor("#34d399" if blink else "#fb923c"))
                p.fillRect(x + 15, uy + 2, 4, 4, QColor("#38bdf8"))
            self._rect(p, x + 4, y + h - 12, w - 8, 12, "#111620", "#fb923c" if is_active else "#334155", 1)

        elif dtype == "whiteboard":
            self._rect(p, x, y, w, h, "#0d1726", "#38bdf8" if is_active else "#2a4365", 1)
            p.fillRect(x + 10, y + 10, 22, 12, QColor("#38bdf8"))
            p.fillRect(x + 44, y + 10, 22, 12, QColor("#fbbf24"))
            p.fillRect(x + 78, y + 10, 22, 12, QColor("#34d399"))
            p.setPen(QPen(QColor("#94a3b8"), 2))
            p.drawLine(x + 32, y + 16, x + 44, y + 16)
            p.drawLine(x + 66, y + 16, x + 78, y + 16)
            p.fillRect(x + 12, y + 28, 8, 8, QColor("#fde047"))
            p.fillRect(x + 24, y + 28, 8, 8, QColor("#f472b6"))

        elif dtype == "orchestrator_core":
            self._rect(p, x, y, w, h, "#19130b", "#fbbf24" if is_active else "#5c4620", 1)
            pulse = 14 + math.sin(now_sec * 3.5) * 2.5
            p.setPen(QPen(QColor(251, 191, 36, 220 if is_active else 100), 2))
            p.drawEllipse(QPointF(cx, cy), pulse, pulse)
            p.setPen(QColor("#fcd34d"))
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(QRectF(x, cy - 7, w, 14), Qt.AlignmentFlag.AlignCenter, "ORCH-HUB")

        elif dtype == "web_radar":
            self._rect(p, x, y, w, h, "#0a1724", "#22d3ee" if is_active else "#1e3a52", 1)
            p.setPen(QPen(QColor(34, 211, 238, 220 if is_active else 110), 1))
            p.drawEllipse(QPointF(cx, cy), 12, 12)
            p.drawLine(cx - 12, cy, cx + 12, cy)
            p.drawLine(cx, cy - 12, cx, cy + 12)

        elif dtype == "art_easel":
            self._rect(p, x, y, w, h, "#2e1065", "#e879f9" if is_active else "#6b21a8", 1)
            self._rect(p, x + 8, y + 7, w - 16, h - 14, "#fef3c7", "#d97706", 1)
            p.fillRect(x + 14, y + 12, 14, 12, QColor("#f43f5e"))
            p.fillRect(x + 28, y + 16, 16, 12, QColor("#38bdf8"))

        elif dtype == "coffee_sofa":
            self._rect(p, x, y, w, h, "#6b153b", "#f87171" if is_active else "#9d174d", 1)
            p.fillRect(x + 7, y + 7, w - 14, h - 14, QColor("#831843"))

        if self.edit_mode:
            p.setPen(QPen(QColor("#38bdf8" if is_hov else "#facc15"), 2 if is_hov else 1, Qt.PenStyle.DotLine))
            p.drawRect(x - 2, y - 2, w + 4, h + 4)

    def _draw_decoration(self, p: QPainter, dec: Dict[str, Any], now_sec: float):
        dtype = dec.get("type", "plant_monstera")
        spec = DECORATION_CATALOG.get(dtype, DECORATION_CATALOG["plant_monstera"])
        cx, cy = int(dec["x"]), int(dec["y"])
        w, h = spec["w"], spec["h"]
        x, y = cx - w // 2, cy - h // 2
        is_hov = self.edit_mode and (dec.get("id") == self.hovered_item_id)

        if dtype in ("plant_monstera", "plant_cactus"):
            self._rect(p, cx - 7, cy + 4, 14, 10, "#9a3412", "#23110d", 1)
            leaf_c = "#10b981" if dtype == "plant_monstera" else "#22c55e"
            self._rect(p, cx - 10, cy - 10, 20, 14, leaf_c, "#064e3b", 1)
            p.fillRect(cx - 4, cy - 14, 8, 6, QColor("#34d399"))
        elif dtype == "arcade_machine":
            self._rect(p, x, y, w, h, "#311042", "#e879f9", 1)
            self._rect(p, x + 5, y + 7, w - 10, 16, "#090d16", "#38bdf8", 1)
            p.fillRect(x + 9, y + 12, 6, 6, QColor("#f43f5e"))
            p.fillRect(x + 17, y + 14, 6, 4, QColor("#facc15"))
        elif dtype == "water_cooler":
            self._rect(p, x + 3, cy - 2, w - 6, 20, "#e2e8f0", "#64748b", 1)
            self._rect(p, x + 4, y + 2, w - 8, 15, "#bae6fd", "#38bdf8", 1)
        elif dtype == "coffee_bar":
            self._rect(p, x, y, w, h, "#3b231e", "#78350f", 1)
            self._rect(p, x + 8, y + 4, 18, 18, "#991b1b", "#f87171", 1)
            steam_y = int(y - 2 - ((now_sec * 10) % 6))
            p.fillRect(x + 15, steam_y, 3, 4, QColor(255, 255, 255, 70))
        elif dtype in ("rug_persian", "rug_cyber"):
            c1 = "#7f1d1d" if dtype == "rug_persian" else "#0f2942"
            c2 = "#f59e0b" if dtype == "rug_persian" else "#38bdf8"
            self._rect(p, x, y, w, h, c1, c2, 1)
            self._rect(p, x + 6, y + 6, w - 12, h - 12, c1, c2, 1)
        elif dtype == "floor_lamp":
            p.fillRect(cx - 1, cy - 8, 3, 22, QColor("#94a3b8"))
            self._rect(p, cx - 8, cy - 18, 16, 10, "#fef08a", "#ca8a04", 1)
        elif dtype == "trophy":
            self._rect(p, cx - 6, cy + 4, 12, 8, "#451a03", "#23110d", 1)
            self._rect(p, cx - 7, cy - 10, 14, 14, "#facc15", "#ca8a04", 1)

        if self.edit_mode:
            p.setPen(QPen(QColor("#38bdf8" if is_hov else "#a855f7"), 2 if is_hov else 1, Qt.PenStyle.DotLine))
            p.drawRect(x - 2, y - 2, w + 4, h + 4)

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
        walk_bob = (-2 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 3.5 + x))

        if ent.spawn_timer > 0:
            p.setPen(QPen(QColor("#38bdf8"), 2))
            r = 22 * ent.spawn_timer
            p.drawEllipse(QPointF(x, y - 8), r, r)

        if is_sel or is_hov:
            p.setPen(QPen(QColor("#38bdf8" if is_sel else "#cbd5e1"), 2 if is_sel else 1))
            p.drawEllipse(QPointF(x, y + 14), 16, 6)

        # Sombra en el piso
        p.setBrush(QColor(0, 0, 0, 115))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(x - 12, y + 10, 24, 7))

        # Renderizar el Sprite Chibi personalizado en la dirección actual (down, up, left, right)
        is_typing = (not ent.is_walking) and (ent.current_station in ("coding_desk", "server_lab"))
        pix = SPRITE_ENGINE.get_pixmap(
            ent.character,
            direction=ent.face,
            walk_frame=ent.walk_frame if ent.is_walking else 0,
            scale=2,
            is_typing=is_typing,
        )
        p.drawPixmap(int(x - pix.width() / 2), int(y - pix.height() + 15 + walk_bob), pix)

    def _draw_agent_overlay(self, p: QPainter, ent: QtAgentEntity, now_sec: float, force_full: bool):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        is_hov = (ent.id == self.hovered_agent_id)
        is_idle_lounge = (not ent.is_walking) and (ent.current_station == "lounge")
        walk_bob = (-2 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 3.5 + x))
        py = y + walk_bob

        # Nombre del personaje + modelo compacto debajo de los pies
        char_name = ent.character.get("name", "Agente")
        label = f"⚡ {char_name}" if ent.is_subagent else f"{char_name} · {ent.compact_name}"
        if len(label) > 16:
            label = label[:15] + "…"

        font_name = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(font_name)
        nw = QFontMetrics(font_name).horizontalAdvance(label) + 10
        self._round_pill(
            p, x - nw / 2, y + 16, nw, 14, 4,
            QColor(15, 23, 42, 240 if is_sel else 205),
            QColor("#38bdf8") if is_sel else QColor(148, 163, 184, 65),
        )
        p.setPen(QColor("#ffffff" if is_sel else "#cbd5e1"))
        p.drawText(QRectF(x - nw / 2, y + 16, nw, 14), Qt.AlignmentFlag.AlignCenter, label)

        # Globo de actividad o de colaboración (Pair-Programming)
        if is_idle_lounge and not force_full:
            self._round_pill(p, x - 10, py - 46, 20, 15, 7, QColor(15, 23, 42, 210), QColor(248, 113, 113, 90))
            p.setPen(QColor("#fca5a5"))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRectF(x - 10, py - 46, 20, 15), Qt.AlignmentFlag.AlignCenter, "☕")
        else:
            if ent.is_walking:
                bubble = f"→ {STATIONS[ent.current_station]['title']}"
            elif ent.is_collaborating and ent.current_station != "lounge":
                if ent.role == "collaborator":
                    bubble = f"🤝 Revisando con {ent.partner_name or 'compañero'}"
                else:
                    bubble = f"{ent.badge[:18]} + {ent.partner_name or 'equipo'}"
            else:
                bubble = ent.badge

            if bubble:
                if len(bubble) > 27:
                    bubble = bubble[:26] + "…"
                font_b = QFont("Segoe UI", 8, QFont.Weight.Bold)
                p.setFont(font_b)
                bw = QFontMetrics(font_b).horizontalAdvance(bubble) + 14
                bx = max(10.0, min(WORLD_W - bw - 10.0, x - bw / 2))
                by = py - 50
                border_c = QColor("#fbbf24") if (ent.is_collaborating and ent.current_station != "lounge") else (
                    QColor("#38bdf8") if (is_sel or is_hov) else QColor(148, 163, 184, 90)
                )
                self._round_pill(p, bx, by, bw, 18, 6, QColor(15, 23, 42, 242), border_c)
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
# ESTILO MODERNO LIMPIO PARA PyQt6
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
    border-color: #38bdf8;
}
QPushButton:checked {
    background-color: rgba(56, 189, 248, 45);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 130);
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
    def __init__(self, brain_dir: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Pixelavity // Antigravity Live Visualizer")
        self.resize(1360, 820)
        self.setMinimumSize(1040, 650)
        self.setStyleSheet(CLEAN_STYLESHEET)

        icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.customization = CustomizationManager()
        self.watcher = AntigravityBrainWatcher(brain_dir=brain_dir)
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
        main_layout.setSpacing(10)

        # 1. BARRA SUPERIOR
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(14, 8, 14, 8)
        top_layout.setSpacing(10)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        title_lbl = QLabel("👾 PIXELAVITY  ·  ANTIGRAVITY")
        title_lbl.setObjectName("BrandTitle")
        sub_lbl = QLabel("MediaHub Conglomerate · Visualizador Personalizable en Tiempo Real")
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

        # Botón para abrir el Creador de Personajes (4 direcciones)
        self.btn_chars = QPushButton("👤 Personajes")
        self.btn_chars.setToolTip("Crear y personalizar personajes (pelo, cara, ropa, zapatos, accesorios)")
        self.btn_chars.clicked.connect(self._open_character_creator)
        top_layout.addWidget(self.btn_chars)

        # Botón para activar/desactivar el Editor de Background / Oficina
        self.btn_edit_office = QPushButton("🏗️ Personalizar Oficina")
        self.btn_edit_office.setCheckable(True)
        self.btn_edit_office.setToolTip("Modificar pisos, paredes, muebles, computadores y decoración")
        self.btn_edit_office.toggled.connect(self._toggle_office_editor)
        top_layout.addWidget(self.btn_edit_office)

        self.btn_filter_live = QPushButton("Solo Activos")
        self.btn_filter_live.setCheckable(True)
        self.btn_filter_live.toggled.connect(self._toggle_filter_live)
        top_layout.addWidget(self.btn_filter_live)

        self.btn_pin = QPushButton("📌 Fijar Encima")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Mantiene Pixelavity flotando encima de Antigravity / VS Code")
        self.btn_pin.toggled.connect(self._toggle_always_on_top)
        top_layout.addWidget(self.btn_pin)

        main_layout.addWidget(topbar)

        # 2. BARRA DESPLEGABLE DE EDICIÓN DE OFICINA (Oculta por defecto en Modo Espectador)
        self.office_widget = PixelOfficeWidget(
            manager=self.customization,
            on_select_agent=self._on_agent_selected,
        )
        self.editor_bar = OfficeEditorBar(
            manager=self.customization,
            on_layout_changed=self._on_office_layout_changed,
        )
        self.editor_bar.setVisible(False)
        self.office_widget.editor_bar = self.editor_bar
        main_layout.addWidget(self.editor_bar)

        # 3. CUERPO PRINCIPAL (MAPA + PANEL LATERAL)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter, stretch=1)

        splitter.addWidget(self.office_widget)

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

        lbl_agents = QLabel("AGENTES EN LA OFICINA")
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

    def _open_character_creator(self):
        dlg = CharacterCreatorDialog(
            manager=self.customization,
            on_changed=self._on_characters_updated,
            parent=self,
        )
        dlg.exec()
        self._on_characters_updated()

    def _on_characters_updated(self):
        SPRITE_ENGINE.clear_cache()
        self.office_widget.refresh_allocations()
        self._refresh_sidebar()

    def _toggle_office_editor(self, checked: bool):
        self.editor_bar.setVisible(checked)
        self.office_widget.edit_mode = checked
        self.office_widget.update()

    def _on_office_layout_changed(self):
        self.office_widget.refresh_allocations()
        self.office_widget.update()
        self._refresh_sidebar()

    def _toggle_always_on_top(self, checked: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _toggle_filter_live(self, checked: bool):
        self.office_widget.filter_mode = "live" if checked else "all"
        self.office_widget.refresh_allocations()
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
                ents[aid] = QtAgentEntity(ag)
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

        self.office_widget.refresh_allocations()

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
            char_name = sel.character.get("name", "Personaje")
            collab_txt = ""
            if sel.is_collaborating and sel.current_station != "lounge":
                mode_lbl = "Revisando en equipo con" if sel.role == "collaborator" else "Compartiendo estación con"
                collab_txt = f"<br><span style='color:#fbbf24'>🤝 {mode_lbl} <b>{sel.partner_name}</b></span>"

            self.lbl_inspector.setText(
                f"<b style='font-size:13px;color:#ffffff'>{char_name}</b> "
                f"<span style='color:#94a3b8'>({sel.name})</span> "
                f"<span style='color:#38bdf8;font-size:10px'>[{role}]</span><br>"
                f"<span style='color:#fbbf24'>{sel.model}</span><br><br>"
                f"<b>Sala:</b> {st_label}<br>"
                f"<b>Estado:</b> {sel.badge}"
                f"{collab_txt}<br>"
                f"<span style='color:#6e7f9c;font-size:11px'>{sel.chat_title}</span>"
            )
        else:
            self.lbl_inspector.setText("Haz clic sobre un personaje para ver sus detalles.")

        self.list_agents.clear()
        for e in visible:
            prefix = "↳ " if e.is_subagent else ""
            char_name = e.character.get("name", "Agente")
            collab_tag = f" [🤝 con {e.partner_name}]" if (e.is_collaborating and e.current_station != "lounge") else ""
            pix = SPRITE_ENGINE.get_pixmap(e.character, direction="down", walk_frame=0, scale=2)
            item = QListWidgetItem(QIcon(pix), f"{prefix}{char_name} ({e.compact_name}){collab_tag}\n{e.badge}")
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


def run_desktop_app(brain_dir: Optional[str] = None):
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MediaHub.Pixelavity.App")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Pixelavity")
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = PixelAgentsWindow(brain_dir=brain_dir)
    win.show()
    sys.exit(app.exec())


def main():
    run_desktop_app()


if __name__ == "__main__":
    main()
