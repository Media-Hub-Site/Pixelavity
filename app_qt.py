# -*- coding: utf-8 -*-
"""
Pixelavity // Antigravity Live Visualizer — Native PyQt6 Desktop App
Incluye:
  1. Sprites Pixel Art Chibi esculpidos de alto detalle (12 peinados con flequillos y volumen,
     4 direcciones reales: Adelante, Atrás, Izquierda, Derecha)
  2. Creador de Personajes (3 por defecto + personalización completa y selección aleatoria sin repetir)
  3. Constructor de Oficina 100% basado en Cuadrículas (32x19 celdas de 32x32 px) con menú por categorías
     al estilo Pixel Agents (💻 Dispositivos, 🪑 Muebles, 🪴 Decoración, 🎨 Pisos, 🧱 Paredes)
  4. Pintado de pisos en dos modos: 🖌️ Modo 1x1 (uno por uno) y 🪣 Modo Rellenar (Flood-Fill)
  5. Pathfinding inteligente por cuadrículas (los agentes esquivan muros y muebles colocados)
  6. Colaboración automática ante demanda (Pair-Programming en celdas contiguas cuando hay más agentes
     que computadores o muebles).
"""

import os
import re
import sys
import math
import time
import random
from typing import Dict, List, Optional, Any, Tuple

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QSizePolicy, QSplitter, QMessageBox, QDialog, QFileDialog
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
    GRID_COLS,
    GRID_ROWS,
    TILE_SIZE,
    WORLD_W,
    WORLD_H,
    FLOOR_MATERIALS,
    WALL_MATERIALS,
    OBJECT_CATALOG,
    DEFAULT_CHARACTERS,
)
from core.sprites import SPRITE_ENGINE
from core.office_sprites import OFFICE_SPRITES
from core.dialogs_qt import CharacterCreatorDialog, OfficeBuilderDock, UsagePopupDialog


STATION_LABELS: Dict[str, Tuple[str, str]] = {
    "library":          ("📚", "BIBLIOTECA"),
    "strategy_board":   ("💭", "ESTRATEGIA"),
    "orchestrator_hub": ("🎛️", "ORCHESTRATOR"),
    "web_station":      ("🌐", "CABINA WEB"),
    "coding_desk":      ("💻", "COMPUTADORES"),
    "server_lab":       ("⚡", "TERMINAL LAB"),
    "art_studio":       ("🎨", "ESTUDIO UI"),
    "lounge":           ("☕", "CAFETERÍA & LOUNGE"),
}

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub("", str(text or "")).strip()


# =============================================================================
# ENTIDAD DE AGENTE CON PATHFINDING POR CUADRÍCULA Y 4 DIRECCIONES
# =============================================================================
class QtAgentEntity:
    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.is_walking = False
        self.walk_frame = 0
        self.walk_timer = 0.0
        self.anim_frame = random.randint(0, 3)
        self.anim_timer = 0.0
        self.waypoints: List[Tuple[float, float, Optional[str]]] = []
        self.action_queue: List[Dict[str, Any]] = []
        self.hold_timer = 0.0

        init_st = data.get("station", "lounge")
        if init_st not in STATION_LABELS:
            init_st = "lounge"
        self.current_station = init_st

        self.assigned_device_id: Optional[str] = None
        self.assigned_device_type: Optional[str] = None
        self.target_col: int = 25
        self.target_row: int = 15
        self.target_x: float = 25 * TILE_SIZE + TILE_SIZE / 2
        self.target_y: float = 15 * TILE_SIZE + TILE_SIZE / 2
        self.target_face: str = "down"
        self.role: str = "primary"
        self.is_collaborating: bool = False
        self.partner_name: Optional[str] = None

        self.character: Dict[str, Any] = DEFAULT_CHARACTERS[0]
        self.sync_metadata(data)

        if self.is_subagent:
            self.x = 19 * TILE_SIZE + TILE_SIZE / 2
            self.y = 4 * TILE_SIZE + TILE_SIZE / 2
            self.spawn_timer = 1.4
        else:
            self.x = self.target_x
            self.y = self.target_y
            self.spawn_timer = 0.6

        self.face = "down"

    def current_cell(self) -> Tuple[int, int]:
        return (
            max(0, min(GRID_COLS - 1, int(self.x // TILE_SIZE))),
            max(0, min(GRID_ROWS - 1, int(self.y // TILE_SIZE))),
        )

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
        self.input_tokens = int(data.get("input_tokens", 0) or 0)
        self.output_tokens = int(data.get("output_tokens", 0) or 0)
        self.cache_read_tokens = int(data.get("cache_read_tokens", 0) or 0)
        self.is_live = bool(data.get("is_live", False))
        self.is_simulated = bool(data.get("is_simulated", False))

        if not self.is_walking and not self.action_queue:
            self.badge = data.get("badge", "☕ En espera")
            self.detail = data.get("detail", "")
            self.activity = data.get("activity", "idle")
            st = data.get("station", "lounge")
            if st in STATION_LABELS and st != self.current_station:
                self.enqueue_action({
                    "station": st,
                    "activity": self.activity,
                    "badge": self.badge,
                    "detail": self.detail,
                })

    def apply_slot_allocation(self, alloc: Dict[str, Any], manager: CustomizationManager):
        new_col = int(alloc["col"])
        new_row = int(alloc["row"])
        new_tx = float(alloc["x"])
        new_ty = float(alloc["y"])
        new_face = alloc.get("face", "up")

        self.assigned_device_id = alloc.get("device_id")
        self.assigned_device_type = alloc.get("device_type")
        self.role = alloc.get("role", "primary")
        self.is_collaborating = bool(alloc.get("is_collaborating", False))
        self.partner_name = alloc.get("partner_name")

        if (new_col, new_row) != (self.target_col, self.target_row) or math.hypot(new_tx - self.target_x, new_ty - self.target_y) > 8.0:
            self.target_col = new_col
            self.target_row = new_row
            self.target_x = new_tx
            self.target_y = new_ty
            self.target_face = new_face
            self._build_grid_path(manager, (new_col, new_row), new_face)
        else:
            self.target_face = new_face
            if not self.is_walking:
                self.face = new_face

    def _build_grid_path(self, manager: CustomizationManager, goal_cell: Tuple[int, int], final_face: str):
        start_cell = self.current_cell()
        cells = manager.find_grid_path(start_cell, goal_cell)
        if not cells:
            self.waypoints = [(
                goal_cell[0] * TILE_SIZE + TILE_SIZE / 2,
                goal_cell[1] * TILE_SIZE + TILE_SIZE / 2,
                final_face,
            )]
        else:
            pts: List[Tuple[float, float, Optional[str]]] = []
            for idx, (c, r) in enumerate(cells):
                f = final_face if idx == len(cells) - 1 else None
                pts.append((c * TILE_SIZE + TILE_SIZE / 2, r * TILE_SIZE + TILE_SIZE / 2, f))
            self.waypoints = pts
        self.is_walking = True

    def enqueue_action(self, ev: Dict[str, Any]):
        st = ev.get("station")
        if st not in STATION_LABELS:
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

    def get_current_action(self) -> Tuple[str, float]:
        """Devuelve (nombre_animación, segundos_por_frame) según la estación y rol del agente."""
        if self.is_walking:
            return ("walk", 0.12)
        if self.role == "collaborator" and self.current_station != "lounge":
            if self.current_station == "library":
                return ("reading", 0.38)
            return ("thinking", 0.40)

        if self.current_station == "lounge":
            if self.assigned_device_type == "coffee_bar":
                return ("coffee_standing", 0.55)
            return ("relaxing", 0.55)

        mapping = {
            "coding_desk":      ("typing_seated", 0.14),
            "library":          ("reading",       0.40),
            "strategy_board":   ("thinking",      0.42),
            "server_lab":       ("terminal",      0.16),
            "web_station":      ("browsing",      0.26),
            "art_studio":       ("painting",      0.26),
            "orchestrator_hub": ("orchestrating", 0.28),
        }
        return mapping.get(self.current_station, ("idle", 0.55))

    def update(self, dt: float, particles: List[Dict[str, Any]]) -> bool:
        """Devuelve True si cambió de estación y requiere recalcular posiciones."""
        station_changed = False
        if self.spawn_timer > 0:
            self.spawn_timer = max(0.0, self.spawn_timer - dt)

        if self.waypoints:
            self.is_walking = True
            wx, wy, wface = self.waypoints[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = math.hypot(dx, dy)
            speed = 180.0 if len(self.action_queue) > 1 else 130.0

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
                        "life": 0.30,
                        "max_life": 0.30,
                        "type": "dust",
                        "color": "#b4d2ff",
                    })
            return False

        self.is_walking = False
        _, frame_dur = self.get_current_action()
        self.anim_timer += dt
        if self.anim_timer >= frame_dur:
            self.anim_timer = 0.0
            self.anim_frame = (self.anim_frame + 1) % 4

        if self.hold_timer > 0:
            self.hold_timer = max(0.0, self.hold_timer - dt)

        rate = 0.35 if self.current_station == "lounge" else (2.2 if self.is_collaborating else 1.5)
        if random.random() < dt * rate:
            self._emit_particle(particles)

        if self.hold_timer <= 0 and self.action_queue:
            nxt = self.action_queue.pop(0)
            self.badge = nxt["badge"]
            self.detail = nxt["detail"]
            self.activity = nxt["activity"]
            if nxt["station"] != self.current_station:
                self.current_station = nxt["station"]
                station_changed = True
            self.hold_timer = 2.0

        return station_changed

    def _emit_particle(self, particles: List[Dict[str, Any]]):
        if self.is_collaborating and self.current_station != "lounge":
            syms = ["...", "?!", "</>", "+1", "OK"]
            color = "#fbbf24" if self.role == "collaborator" else "#38bdf8"
        else:
            table = {
                "coding_desk":      (["</>", "{ }", "01"], "#34d399"),
                "library":          (["doc", "lib", "pkg"], "#fbbf24"),
                "server_lab":       (["$>", "OK", "run"], "#fb923c"),
                "strategy_board":   (["...", "?", "!"], "#38bdf8"),
                "orchestrator_hub": (["SYNC", "HUB"], "#fbbf24"),
                "web_station":      (["GET", "200"], "#22d3ee"),
                "art_studio":       (["CSS", "UI"], "#e879f9"),
                "lounge":           (["~", "zZ"], "#94a3b8"),
            }
            syms, color = table.get(self.current_station, (["."], "#38bdf8"))

        particles.append({
            "x": self.x + random.uniform(-8, 8),
            "y": self.y - 32,
            "vx": random.uniform(-4, 4),
            "vy": random.uniform(-24, -16),
            "life": 1.0,
            "max_life": 1.0,
            "type": "text",
            "text": random.choice(syms),
            "color": color,
        })


# =============================================================================
# LIENZO 2D BASADO EN CUADRÍCULAS 32x19 (ESPECTADOR + CONSTRUCTOR PIXEL AGENTS)
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
        self.show_demo: bool = False

        # Modo Constructor por Cuadrículas
        self.edit_mode: bool = False
        self.builder_dock: Optional[OfficeBuilderDock] = None
        self.hover_col: int = -1
        self.hover_row: int = -1
        self.moving_item_id: Optional[str] = None
        self.moving_item_type: Optional[str] = None
        self._mouse_painting: bool = False

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

    def _world_to_cell(self, wx: float, wy: float) -> Tuple[int, int]:
        return (
            max(0, min(GRID_COLS - 1, int(wx // TILE_SIZE))),
            max(0, min(GRID_ROWS - 1, int(wy // TILE_SIZE))),
        )

    def _visible_entities(self) -> List[QtAgentEntity]:
        return [
            e for e in self.entities.values()
            if (self.show_demo or not e.is_simulated) and (self.filter_mode == "all" or e.is_live)
        ]

    def refresh_allocations(self):
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
                self.entities[aid].apply_slot_allocation(alloc, self.manager)

    def _tick(self):
        now = time.perf_counter()
        dt = min(0.1, now - self._last_time)
        self._last_time = now

        need_realloc = False
        for ent in self.entities.values():
            if ent.update(dt, self.particles):
                need_realloc = True

        if need_realloc:
            self.refresh_allocations()

        for i in range(len(self.particles) - 1, -1, -1):
            p = self.particles[i]
            p["life"] -= dt
            if p["life"] <= 0:
                self.particles.pop(i)
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt

        self.update()

    # -------------------------------------------------------------------------
    # INTERACCIÓN CON EL MOUSE POR CUADRÍCULAS (32x19)
    # -------------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())
        col, row = self._world_to_cell(wx, wy)
        self.hover_col, self.hover_row = col, row

        if self.edit_mode and self.builder_dock:
            tmode = self.builder_dock.tool_mode
            if self._mouse_painting:
                if tmode == "floor_1x1":
                    self.manager.paint_floor_tile(col, row, self.builder_dock.selected_floor_material)
                elif tmode == "wall_place":
                    self.manager.set_wall_tile(col, row, self.builder_dock.selected_wall_material)
                elif tmode == "wall_erase":
                    self.manager.set_wall_tile(col, row, None)
                elif tmode == "move" and self.moving_item_id:
                    if self.manager.move_object_to_cell(self.moving_item_id, col, row):
                        self.refresh_allocations()
            self.update()
            return

        found = None
        for ent in self._visible_entities():
            if math.hypot(wx - ent.x, wy - (ent.y - 16)) <= 24:
                found = ent.id
                break
        self.hovered_agent_id = found
        self.setCursor(Qt.CursorShape.PointingHandCursor if found else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        wx, wy = self._screen_to_world(event.position().x(), event.position().y())
        col, row = self._world_to_cell(wx, wy)
        self.hover_col, self.hover_row = col, row

        if self.edit_mode and self.builder_dock:
            tmode = self.builder_dock.tool_mode

            # Clic derecho siempre elimina el objeto o pared en la cuadrícula clicada
            if event.button() == Qt.MouseButton.RightButton or (
                event.button() == Qt.MouseButton.LeftButton and tmode == "delete"
            ):
                hit_obj = self.manager.find_object_at_cell(col, row)
                if hit_obj:
                    ok, msg = self.manager.remove_object(hit_obj["id"])
                    if not ok:
                        QMessageBox.warning(self, "Regla de Dispositivos Mínimos", msg)
                    else:
                        self.refresh_allocations()
                else:
                    self.manager.set_wall_tile(col, row, None)
                self.update()
                return

            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_painting = True
                if tmode == "floor_1x1":
                    self.manager.paint_floor_tile(col, row, self.builder_dock.selected_floor_material)
                elif tmode == "floor_fill":
                    self.manager.flood_fill_floor(col, row, self.builder_dock.selected_floor_material)
                elif tmode == "wall_place":
                    self.manager.set_wall_tile(col, row, self.builder_dock.selected_wall_material)
                    self.refresh_allocations()
                elif tmode == "wall_erase":
                    self.manager.set_wall_tile(col, row, None)
                    self.refresh_allocations()
                elif tmode == "place_object":
                    obj_type = self.builder_dock.selected_object_type
                    # Si hace clic sobre un objeto existente con el mismo tipo o quiere moverlo:
                    ok, _ = self.manager.place_new_object(obj_type, col, row)
                    if ok:
                        self.refresh_allocations()
                    else:
                        # Si hizo clic sobre un objeto ya existente, permitir arrastrarlo por la cuadrícula
                        hit_obj = self.manager.find_object_at_cell(col, row)
                        if hit_obj:
                            self.moving_item_id = hit_obj["id"]
                            self.moving_item_type = hit_obj["type"]
                elif tmode == "move":
                    hit_obj = self.manager.find_object_at_cell(col, row)
                    if hit_obj:
                        self.moving_item_id = hit_obj["id"]
                        self.moving_item_type = hit_obj["type"]
                self.update()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            for ent in self._visible_entities():
                if math.hypot(wx - ent.x, wy - (ent.y - 16)) <= 24:
                    self.selected_agent_id = ent.id
                    self.on_select_agent(ent.id)
                    return

    def mouseReleaseEvent(self, event):
        self._mouse_painting = False
        if self.moving_item_id:
            if 0 <= self.hover_col < GRID_COLS and 0 <= self.hover_row < GRID_ROWS:
                self.manager.move_object_to_cell(self.moving_item_id, self.hover_col, self.hover_row)
            self.moving_item_id = None
            self.moving_item_type = None
            self.refresh_allocations()
            self.update()

    # -------------------------------------------------------------------------
    # RENDERIZADO DEL MUNDO PIXEL AGENTS EN CUADRÍCULAS 32x19 (16px NATIVO x2)
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.fillRect(self.rect(), QColor("#1c1e2a"))

        scale, ox, oy = self._compute_transform()
        painter.translate(ox, oy)
        painter.scale(scale, scale)

        now_sec = time.perf_counter() - self._start_time
        visible = self._visible_entities()

        self._draw_tile_world(painter, now_sec, visible)
        self._draw_orchestrator_links(painter, now_sec, visible)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        priority = None
        for ent in sorted(visible, key=lambda e: e.y):
            if ent.id in (self.hovered_agent_id, self.selected_agent_id):
                priority = ent
                continue
            self._draw_agent_overlay(painter, ent, now_sec, force_full=False)

        if priority:
            self._draw_agent_overlay(painter, priority, now_sec, force_full=True)

        if self.edit_mode:
            self._draw_grid_editor_overlay(painter)

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

    def _draw_tile_world(self, p: QPainter, now_sec: float, visible: List[QtAgentEntity]):
        office = self.manager.get_office_layout()
        fgrid = office.get("floor_grid", [])
        wgrid = office.get("wall_grid", [])
        items = office.get("items", [])

        active_device_ids = {
            e.assigned_device_id for e in visible
            if not e.is_walking and e.assigned_device_id
        }
        anim_tick = int(now_sec * 4)

        # 1. PISOS 32x19 (16x16 nativo a 2x)
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                mat_id = fgrid[r][c] if (r < len(fgrid) and c < len(fgrid[r])) else "cream_tile"
                pix_floor = OFFICE_SPRITES.get_floor_pixmap(mat_id, scale=2)
                p.drawPixmap(c * TILE_SIZE, r * TILE_SIZE, pix_floor)

        # 2. ALFOMBRAS NO BLOQUEANTES (debajo de muebles y sillas)
        for it in items:
            otype = it.get("type", "")
            spec = OBJECT_CATALOG.get(otype)
            if not spec or bool(spec.get("blocking", True)):
                continue
            if otype in ("office_chair", "gaming_chair", "wall_clock"):
                continue
            pix_it, oh = OFFICE_SPRITES.get_item_sprite(otype, False, anim_tick, scale=2)
            p.drawPixmap(int(it["col"]) * TILE_SIZE, int(it["row"]) * TILE_SIZE - oh, pix_it)

        # 3. PAREDES AUTO-TILEADAS + RELOJES DE PARED
        def _has_wall(rr: int, cc: int) -> bool:
            return 0 <= rr < GRID_ROWS and 0 <= cc < GRID_COLS and rr < len(wgrid) and cc < len(wgrid[rr]) and (wgrid[rr][cc] is not None)

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                w_id = wgrid[r][c] if (r < len(wgrid) and c < len(wgrid[r])) else None
                if not w_id:
                    continue
                pix_wall = OFFICE_SPRITES.get_wall_pixmap(
                    w_id,
                    has_north=_has_wall(r - 1, c),
                    has_south=_has_wall(r + 1, c),
                    has_west=_has_wall(r, c - 1),
                    has_east=_has_wall(r, c + 1),
                    scale=2,
                )
                p.drawPixmap(c * TILE_SIZE, r * TILE_SIZE, pix_wall)

        for it in items:
            if it.get("type") == "wall_clock":
                pix_clk, oh = OFFICE_SPRITES.get_item_sprite("wall_clock", False, anim_tick, scale=2)
                p.drawPixmap(int(it["col"]) * TILE_SIZE, int(it["row"]) * TILE_SIZE - oh, pix_clk)

        # 4. SILLAS DE OFICINA (colocadas explícitamente y en seat_cell de escritorios/terminales)
        chair_cells_drawn = set()
        for it in items:
            otype = it.get("type", "")
            if otype in ("office_chair", "gaming_chair"):
                cc, rr = int(it["col"]), int(it["row"])
                chair_cells_drawn.add((cc, rr))
                pix_ch, oh = OFFICE_SPRITES.get_item_sprite(otype, False, anim_tick, scale=2)
                p.drawPixmap(cc * TILE_SIZE, rr * TILE_SIZE - oh, pix_ch)

        for it in items:
            otype = it.get("type", "")
            if otype in ("computer_desk", "laptop_desk", "server_terminal", "web_radar"):
                spec = OBJECT_CATALOG.get(otype, {})
                dx, dy, _ = spec.get("seat_cell", (0, 1, "up"))
                sc = int(it["col"]) + dx
                sr = int(it["row"]) + dy
                if 0 <= sc < GRID_COLS and 0 <= sr < GRID_ROWS and (sc, sr) not in chair_cells_drawn:
                    chair_cells_drawn.add((sc, sr))
                    ckind = "gaming" if otype == "server_terminal" else "wood"
                    pix_ch, oh = OFFICE_SPRITES.get_chair_sprite(ckind, scale=2)
                    p.drawPixmap(sc * TILE_SIZE, sr * TILE_SIZE - oh, pix_ch)

        # 5. CAPA Y-SORTED 2.5D: MUEBLES BLOQUEANTES + AGENTES
        draw_queue: List[Tuple[float, int, Any]] = []
        for it in items:
            otype = it.get("type", "")
            spec = OBJECT_CATALOG.get(otype)
            if not spec or not bool(spec.get("blocking", True)):
                continue
            ic, ir = int(it["col"]), int(it["row"])
            th = int(spec["tile_h"])
            if otype in ("coffee_sofa", "lounge_armchair"):
                # Permite que el agente sentado en la misma celda del sofá se dibuje encima
                sort_y = ir * TILE_SIZE + 8.0
            else:
                sort_y = (ir + th) * TILE_SIZE - 4.0
            draw_queue.append((sort_y, 0, it))

        for ent in visible:
            draw_queue.append((ent.y, 1, ent))

        draw_queue.sort(key=lambda entry: (entry[0], entry[1]))

        for _, kind, obj in draw_queue:
            if kind == 0:
                otype = obj["type"]
                is_act = obj.get("id") in active_device_ids
                pix_it, oh = OFFICE_SPRITES.get_item_sprite(otype, is_act, anim_tick, scale=2)
                p.drawPixmap(int(obj["col"]) * TILE_SIZE, int(obj["row"]) * TILE_SIZE - oh, pix_it)
            else:
                self._draw_agent_body(p, obj, now_sec)

    def _draw_grid_editor_overlay(self, p: QPainter):
        """Dibuja las líneas de la cuadrícula 32x19 y la previsualización verde/roja por celda."""
        p.setPen(QPen(QColor(148, 163, 184, 38), 1))
        for c in range(GRID_COLS + 1):
            p.drawLine(c * TILE_SIZE, 0, c * TILE_SIZE, WORLD_H)
        for r in range(GRID_ROWS + 1):
            p.drawLine(0, r * TILE_SIZE, WORLD_W, r * TILE_SIZE)

        if not (0 <= self.hover_col < GRID_COLS and 0 <= self.hover_row < GRID_ROWS) or not self.builder_dock:
            return

        tmode = self.builder_dock.tool_mode
        hc, hr = self.hover_col, self.hover_row

        if tmode in ("place_object", "move"):
            otype = self.moving_item_type if (tmode == "move" and self.moving_item_type) else self.builder_dock.selected_object_type
            spec = OBJECT_CATALOG.get(otype)
            if spec:
                tw, th = int(spec["tile_w"]), int(spec["tile_h"])
                valid = self.manager.can_place_object(otype, hc, hr, ignore_item_id=self.moving_item_id)
                fill_c = QColor(52, 211, 153, 75) if valid else QColor(248, 113, 113, 85)
                border_c = QColor("#34d399" if valid else "#f87171")
                p.fillRect(hc * TILE_SIZE, hr * TILE_SIZE, tw * TILE_SIZE, th * TILE_SIZE, fill_c)
                p.setPen(QPen(border_c, 2))
                p.drawRect(hc * TILE_SIZE, hr * TILE_SIZE, tw * TILE_SIZE, th * TILE_SIZE)
        else:
            # Celda 1x1 resaltada para Pisos, Paredes o Borrador
            p.fillRect(hc * TILE_SIZE, hr * TILE_SIZE, TILE_SIZE, TILE_SIZE, QColor(56, 189, 248, 65))
            p.setPen(QPen(QColor("#38bdf8"), 2))
            p.drawRect(hc * TILE_SIZE, hr * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        # Indicador de coordenada de cuadrícula en la esquina superior izquierda
        self._round_pill(p, 10, 10, 145, 22, 6, QColor(15, 23, 42, 230), QColor("#38bdf8"))
        p.setPen(QColor("#38bdf8"))
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.drawText(QRectF(10, 10, 145, 22), Qt.AlignmentFlag.AlignCenter, f"Cuadrícula [{hc}, {hr}]")

    def _draw_orchestrator_links(self, p: QPainter, now_sec: float, visible: List[QtAgentEntity]):
        vis_ids = {e.id for e in visible}
        for ent in visible:
            if ent.parent_id and ent.parent_id in vis_ids:
                parent = self.entities[ent.parent_id]
                p.setPen(QPen(QColor(251, 191, 36, 130), 2, Qt.PenStyle.DashLine))
                p.drawLine(int(parent.x), int(parent.y - 10), int(ent.x), int(ent.y - 10))
                t = (now_sec * 0.85) % 1.0
                px = parent.x + (ent.x - parent.x) * t
                py = (parent.y - 10) + ((ent.y - 10) - (parent.y - 10)) * t
                p.fillRect(int(px - 2.5), int(py - 2.5), 5, 5, QColor("#38bdf8"))

    def _draw_agent_body(self, p: QPainter, ent: QtAgentEntity, now_sec: float):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        is_hov = (ent.id == self.hovered_agent_id)
        action, _ = ent.get_current_action()
        is_seated = action in ("typing_seated", "browsing", "terminal", "relaxing")
        walk_bob = (-2 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else (0 if is_seated else int(math.sin(now_sec * 3.0 + x) * 0.6))

        if ent.spawn_timer > 0:
            p.setPen(QPen(QColor("#38bdf8"), 2))
            r = 18 * ent.spawn_timer
            p.drawEllipse(QPointF(x, y - 8), r, r)

        if is_sel or is_hov:
            p.setPen(QPen(QColor("#38bdf8" if is_sel else "#f8fafc"), 2 if is_sel else 1))
            p.drawEllipse(QPointF(x, y + 11), 13, 5)

        if not is_seated:
            p.setBrush(QColor(0, 0, 0, 95))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(x - 10, y + 8, 20, 6))

        pix = SPRITE_ENGINE.get_pixmap(
            ent.character,
            direction=ent.face,
            walk_frame=ent.walk_frame if ent.is_walking else 0,
            scale=2,
            action=action,
            anim_frame=ent.walk_frame if ent.is_walking else ent.anim_frame,
        )
        # Sprite 16x32 a escala 2 = 32x64; pies en y=29*2 = 58 -> anclado a +12 px bajo el centro de celda
        y_nudge = 14 if is_seated else 12
        p.drawPixmap(int(x - pix.width() / 2), int(y - 58 + y_nudge + walk_bob), pix)

    def _draw_agent_overlay(self, p: QPainter, ent: QtAgentEntity, now_sec: float, force_full: bool):
        x, y = int(ent.x), int(ent.y)
        is_sel = (ent.id == self.selected_agent_id)
        is_hov = (ent.id == self.hovered_agent_id)
        is_idle_lounge = (not ent.is_walking) and (ent.current_station == "lounge")
        walk_bob = (-2 if ent.walk_frame % 2 == 1 else 0) if ent.is_walking else int(math.sin(now_sec * 3.5 + x) * 0.6)
        py = y + walk_bob

        char_name = ent.character.get("name", "Agente")
        label = f"[SUB] {char_name}" if ent.is_subagent else f"{char_name} · {ent.compact_name}"
        if len(label) > 16:
            label = label[:15] + "…"

        font_name = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(font_name)
        nw = QFontMetrics(font_name).horizontalAdvance(label) + 10
        self._round_pill(
            p, x - nw / 2, y + 14, nw, 14, 4,
            QColor(15, 23, 42, 240 if is_sel else 210),
            QColor("#38bdf8") if is_sel else QColor(148, 163, 184, 75),
        )
        p.setPen(QColor("#ffffff" if is_sel else "#cbd5e1"))
        p.drawText(QRectF(x - nw / 2, y + 14, nw, 14), Qt.AlignmentFlag.AlignCenter, label)

        if is_idle_lounge and not force_full:
            self._round_pill(p, x - 11, py - 56, 22, 15, 7, QColor(15, 23, 42, 215), QColor(248, 113, 113, 95))
            p.setPen(QColor("#fca5a5"))
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(QRectF(x - 11, py - 56, 22, 15), Qt.AlignmentFlag.AlignCenter, "zZ")
        else:
            st_title = STATION_LABELS.get(ent.current_station, ("", ent.current_station))[1]
            clean_badge = strip_emojis(ent.badge)
            if ent.is_walking:
                bubble = f"-> {st_title}"
            elif ent.is_collaborating and ent.current_station != "lounge":
                if ent.role == "collaborator":
                    bubble = f"Revisando con {ent.partner_name or 'compañero'}"
                else:
                    bubble = f"{clean_badge[:18]} + {ent.partner_name or 'equipo'}"
            else:
                bubble = clean_badge

            if bubble:
                if len(bubble) > 27:
                    bubble = bubble[:26] + "…"
                font_b = QFont("Segoe UI", 8, QFont.Weight.Bold)
                p.setFont(font_b)
                bw = QFontMetrics(font_b).horizontalAdvance(bubble) + 14
                bx = max(10.0, min(WORLD_W - bw - 10.0, x - bw / 2))
                by = max(4.0, py - 60)
                border_c = QColor("#fbbf24") if (ent.is_collaborating and ent.current_station != "lounge") else (
                    QColor("#38bdf8") if (is_sel or is_hov) else QColor(148, 163, 184, 95)
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
QScrollBar:vertical, QScrollBar:horizontal {
    background: transparent;
    width: 6px;
    height: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #24324d;
    border-radius: 3px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #354a73;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}
"""


class PixelAgentsWindow(QMainWindow):
    def __init__(self, brain_dir: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Pixelavity v2.0.0 // Pixel Agents Edition")
        self.setMinimumSize(880, 560)
        self._apply_responsive_window_size()
        self.setStyleSheet(CLEAN_STYLESHEET)

        icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.customization = CustomizationManager()
        resolved_brain = brain_dir or self.customization.get_custom_brain_dir()
        self.watcher = AntigravityBrainWatcher(brain_dir=resolved_brain)
        self.watcher.start()
        self.last_event_id = 0
        self.is_first_sync = True
        self._last_snapshot: Dict[str, Any] = {}
        self._recent_logs: List[Dict[str, Any]] = []

        self._build_ui()

        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._sync_from_watcher)
        self.sync_timer.start(750)
        self._sync_from_watcher()

    def _apply_responsive_window_size(self):
        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        if screen:
            avail = screen.availableGeometry()
            w = min(1380, max(880, int(avail.width() * 0.92)))
            h = min(840, max(560, int(avail.height() * 0.92)))
            self.resize(w, h)
        else:
            self.resize(1200, 740)

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
        title_lbl = QLabel("PIXELAVITY  ·  ANTIGRAVITY")
        title_lbl.setObjectName("BrandTitle")
        sub_lbl = QLabel("MediaHub Conglomerate · Oficina en Cuadrícula 32x19")
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

        self.btn_chars = QPushButton("Personajes")
        self.btn_chars.setToolTip("Crear y personalizar personajes (peinados, cara, ropa, zapatos, accesorios)")
        self.btn_chars.clicked.connect(self._open_character_creator)
        top_layout.addWidget(self.btn_chars)

        self.btn_edit_office = QPushButton("Constructor de Oficina")
        self.btn_edit_office.setCheckable(True)
        self.btn_edit_office.setToolTip("Abrir menú por categorías (Dispositivos, Muebles, Decoración, Pisos, Paredes)")
        self.btn_edit_office.toggled.connect(self._toggle_office_editor)
        top_layout.addWidget(self.btn_edit_office)

        self.btn_usage = QPushButton("Usage")
        self.btn_usage.setToolTip("Ver consumo de tokens en 5h / 7 días (Gemini vs Claude/GPT) y cuota CLI")
        self.btn_usage.clicked.connect(self._open_usage_dialog)
        top_layout.addWidget(self.btn_usage)

        self.btn_conn = QPushButton("Conexión")
        self.btn_conn.setToolTip("Diagnóstico de Antigravity, elegir carpeta manualmente o probar Modo Demo")
        self.btn_conn.clicked.connect(self._open_connection_dialog)
        top_layout.addWidget(self.btn_conn)

        self.btn_filter_live = QPushButton("Solo Activos")
        self.btn_filter_live.setCheckable(True)
        self.btn_filter_live.toggled.connect(self._toggle_filter_live)
        top_layout.addWidget(self.btn_filter_live)

        self.btn_pin = QPushButton("Fijar Encima")
        self.btn_pin.setCheckable(True)
        self.btn_pin.toggled.connect(self._toggle_always_on_top)
        top_layout.addWidget(self.btn_pin)

        main_layout.addWidget(topbar)

        # 2. MENÚ CONSTRUCTOR POR CATEGORÍAS Y CUADRÍCULAS (Oculto por defecto)
        self.office_widget = PixelOfficeWidget(
            manager=self.customization,
            on_select_agent=self._on_agent_selected,
        )
        self.builder_dock = OfficeBuilderDock(
            manager=self.customization,
            on_state_changed=self._on_office_layout_changed,
        )
        self.builder_dock.setVisible(False)
        self.office_widget.builder_dock = self.builder_dock
        main_layout.addWidget(self.builder_dock)

        # 3. CUERPO PRINCIPAL
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
        self.list_agents.setIconSize(QSize(32, 48))
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

    def _open_usage_dialog(self):
        dlg = UsagePopupDialog(self.watcher, parent=self)
        dlg.exec()

    def _on_characters_updated(self):
        SPRITE_ENGINE.clear_cache()
        self.office_widget.refresh_allocations()
        self._refresh_sidebar()

    def _toggle_office_editor(self, checked: bool):
        self.builder_dock.setVisible(checked)
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

    def _open_connection_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Conexión y Diagnóstico · Pixelavity")
        dlg.setMinimumWidth(560)
        dlg.setStyleSheet(CLEAN_STYLESHEET)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        snap = self.watcher.get_snapshot()
        mode = snap.get("detection_mode", "waiting")
        bdir = snap.get("brain_dir", "")
        exists = bool(snap.get("brain_dir_exists", False))

        mode_labels = {
            "transcript":    "Conectado en tiempo real (transcript.jsonl)",
            "artifacts":     "Conectado en modo artefactos (.md / planes)",
            "conversations": "Conectado en modo sesiones (.pb)",
            "waiting":       "Carpeta detectada, esperando conversaciones activas",
            "not_found":     "No se encontró la carpeta 'brain' de Antigravity",
        }
        status_color = "#34d399" if mode in ("transcript", "artifacts", "conversations") else ("#fbbf24" if exists else "#f87171")

        lbl_info = QLabel(
            f"<b>Estado:</b> <span style='color:{status_color}'>{mode_labels.get(mode, mode)}</span><br>"
            f"<b>Carpeta actual:</b> <span style='color:#94a3b8'>{bdir}</span><br>"
            f"<b>Agentes detectados:</b> {len([a for a in snap.get('agents', []) if not a.get('is_simulated')])}<br>"
            f"<b>Configuración guardada:</b> <span style='color:#64748b'>{self.customization.storage_path}</span>"
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("background:#101624; border:1px solid #1f2b42; border-radius:8px; padding:12px; font-size:12px;")
        lay.addWidget(lbl_info)

        lbl_help = QLabel(
            "Si en este computador Antigravity guarda sus datos en otra ubicación, selecciona la carpeta "
            "<b>brain</b> (o la carpeta <b>.gemini/antigravity</b>). También puedes activar el Modo Demo para "
            "probar la oficina con agentes de ejemplo."
        )
        lbl_help.setWordWrap(True)
        lbl_help.setStyleSheet("color:#94a3b8; font-size:11px;")
        lay.addWidget(lbl_help)

        row_btns = QHBoxLayout()
        btn_pick = QPushButton("Elegir Carpeta...")
        btn_auto = QPushButton("Auto-detectar")
        btn_demo = QPushButton("Quitar Demo" if self.office_widget.show_demo else "Activar Modo Demo")
        btn_log = QPushButton("Abrir Carpeta de Logs")

        def pick_folder():
            chosen = QFileDialog.getExistingDirectory(dlg, "Selecciona la carpeta 'brain' o '.gemini/antigravity'", bdir or os.path.expanduser("~"))
            if chosen:
                self.customization.set_custom_brain_dir(chosen)
                self.watcher.set_brain_dir(chosen)
                self._sync_from_watcher()
                dlg.accept()

        def auto_detect():
            self.customization.set_custom_brain_dir(None)
            self.watcher.set_brain_dir(None)
            self._sync_from_watcher()
            dlg.accept()

        def toggle_demo():
            self.office_widget.show_demo = not self.office_widget.show_demo
            if self.office_widget.show_demo:
                self.watcher.trigger_simulation("spawn_orchestrator")
            else:
                self.watcher.trigger_simulation("clear_sim")
            self._sync_from_watcher()
            dlg.accept()

        def open_logs():
            log_dir = os.path.dirname(self.customization.storage_path)
            try:
                if sys.platform == "win32":
                    os.startfile(log_dir)
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", log_dir])
            except Exception as ex:
                QMessageBox.information(dlg, "Carpeta de Logs", f"Ruta de logs y configuración:\n{log_dir}\n({ex})")

        btn_pick.clicked.connect(pick_folder)
        btn_auto.clicked.connect(auto_detect)
        btn_demo.clicked.connect(toggle_demo)
        btn_log.clicked.connect(open_logs)

        row_btns.addWidget(btn_pick)
        row_btns.addWidget(btn_auto)
        row_btns.addWidget(btn_demo)
        row_btns.addWidget(btn_log)
        lay.addLayout(row_btns)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dlg.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        dlg.exec()

    def _sync_from_watcher(self):
        snap = self.watcher.get_snapshot(since_event_id=self.last_event_id)
        self._last_snapshot = snap
        ents = self.office_widget.entities
        current_ids = set()

        for ag in snap.get("agents", []):
            if ag.get("is_simulated") and not self.office_widget.show_demo:
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
            if self.office_widget.show_demo or not str(l.get("agent_id", "")).startswith(("sim-", "sub-"))
        ]
        self._update_connection_pill(snap)
        self._refresh_sidebar()

    def _update_connection_pill(self, snap: Dict[str, Any]):
        if not hasattr(self, "lbl_live"):
            return
        real_agents = [a for a in snap.get("agents", []) if not a.get("is_simulated")]
        exists = bool(snap.get("brain_dir_exists", False))
        bdir = snap.get("brain_dir", "")

        if self.office_widget.show_demo:
            self.lbl_live.setText("● MODO DEMO")
            self.lbl_live.setStyleSheet("color:#c084fc; background:rgba(192,132,252,0.14); border:1px solid rgba(192,132,252,0.45); border-radius:6px; padding:4px 9px; font-family:'Consolas'; font-size:11px; font-weight:bold;")
            self.lbl_live.setToolTip(f"Modo Demo activo · Carpeta: {bdir}")
        elif real_agents:
            self.lbl_live.setText("● EN VIVO")
            self.lbl_live.setStyleSheet("")
            self.lbl_live.setToolTip(f"Conectado a Antigravity ({snap.get('detection_mode')}) en:\n{bdir}")
        elif exists:
            self.lbl_live.setText("● ESPERANDO CHATS")
            self.lbl_live.setStyleSheet("color:#fbbf24; background:rgba(251,191,36,0.14); border:1px solid rgba(251,191,36,0.45); border-radius:6px; padding:4px 9px; font-family:'Consolas'; font-size:11px; font-weight:bold;")
            self.lbl_live.setToolTip(f"Carpeta detectada, sin sesiones aún:\n{bdir}")
        else:
            self.lbl_live.setText("● SIN ANTIGRAVITY")
            self.lbl_live.setStyleSheet("color:#fca5a5; background:rgba(248,113,113,0.14); border:1px solid rgba(248,113,113,0.45); border-radius:6px; padding:4px 9px; font-family:'Consolas'; font-size:11px; font-weight:bold;")
            self.lbl_live.setToolTip("No se encontró ~/.gemini/antigravity/brain. Haz clic en 'Conexión' para elegir carpeta o probar Demo.")

    def _refresh_sidebar(self):
        if not hasattr(self, "lbl_inspector") or not hasattr(self, "list_agents"):
            return
        visible = self.office_widget._visible_entities()
        chats = sum(1 for e in visible if not e.is_subagent)
        subs = sum(1 for e in visible if e.is_subagent)
        self.lbl_stats.setText(f"{chats} chats · {subs} subagentes")

        sel = self.office_widget.entities.get(self.office_widget.selected_agent_id or "")
        if sel:
            st_icon, st_title = STATION_LABELS.get(sel.current_station, ("📍", sel.current_station))
            role = f"SUB · {sel.subagent_type.upper()}" if sel.is_subagent else "PRINCIPAL"
            char_name = sel.character.get("name", "Personaje")
            collab_txt = ""
            if sel.is_collaborating and sel.current_station != "lounge":
                mode_lbl = "Revisando en equipo con" if sel.role == "collaborator" else "Compartiendo estación con"
                collab_txt = f"<br><span style='color:#fbbf24'>🤝 {mode_lbl} <b>{sel.partner_name}</b></span>"

            tot_tok = sel.input_tokens + sel.output_tokens
            tok_txt = ""
            if tot_tok > 0:
                tok_txt = (
                    f"<br><b>Tokens:</b> {tot_tok:,} "
                    f"<span style='color:#64748b'>(caché {sel.cache_read_tokens:,})</span>"
                )

            self.lbl_inspector.setText(
                f"<b style='font-size:13px;color:#ffffff'>{char_name}</b> "
                f"<span style='color:#94a3b8'>({sel.name})</span> "
                f"<span style='color:#38bdf8;font-size:10px'>[{role}]</span><br>"
                f"<span style='color:#fbbf24'>{sel.model}</span><br><br>"
                f"<b>Estación:</b> {st_icon} {st_title} <span style='color:#64748b'>[{sel.target_col}, {sel.target_row}]</span><br>"
                f"<b>Estado:</b> {sel.badge}"
                f"{tok_txt}"
                f"{collab_txt}<br>"
                f"<span style='color:#6e7f9c;font-size:11px'>{sel.chat_title}</span>"
            )
        else:
            self.lbl_inspector.setText("Haz clic sobre un personaje para ver sus detalles.")

        self.list_agents.clear()
        for e in visible:
            prefix = "> " if e.is_subagent else ""
            char_name = e.character.get("name", "Agente")
            collab_tag = f" [con {e.partner_name}]" if (e.is_collaborating and e.current_station != "lounge") else ""
            pix = SPRITE_ENGINE.get_pixmap(e.character, direction="down", walk_frame=0, scale=2)
            item = QListWidgetItem(QIcon(pix), f"{prefix}{char_name} ({e.compact_name}){collab_tag}\n{strip_emojis(e.badge)}")
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            self.list_agents.addItem(item)
            if e.id == self.office_widget.selected_agent_id:
                item.setSelected(True)

        self.list_feed.clear()
        for log in self._recent_logs[:12]:
            txt = f"{log.get('time_str', '')} · {log.get('agent_name', '')}\n{strip_emojis(log.get('badge', ''))}"
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
