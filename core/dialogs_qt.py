# -*- coding: utf-8 -*-
"""
Pixelavity - Creador de Personajes por Secciones Visuales y Constructor de Oficina con Cuadrados de Diseño
  - Todos los atributos del personaje (Peinado, Cara, Ropa, Zapatos, Accesorios) están organizados por
    secciones y muestran cuadrados visuales con SOLO esa pieza pixel-art aislada (sin adivinar por nombre).
  - Todos los objetos de la oficina (Dispositivos, Muebles, Decoración, Pisos y Paredes) se muestran como
    cuadrados visuales con el diseño pixel-art real de cada elemento.
"""

import copy
import random
from typing import Dict, Any, Optional, Callable, List

from PyQt6.QtCore import Qt, QTimer, QRectF, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QColorDialog, QMessageBox, QCheckBox, QButtonGroup,
    QScrollArea, QStackedWidget
)

from core.customization import (
    CustomizationManager,
    SKIN_TONES,
    FACE_STYLES,
    HAIR_STYLES,
    HAIR_COLORS,
    OUTFIT_STYLES,
    SHOE_STYLES,
    ACCESSORY_STYLES,
    FLOOR_MATERIALS,
    WALL_MATERIALS,
    OBJECT_CATALOG,
)
from core.sprites import SPRITE_ENGINE


CLOTHING_COLOR_PRESETS = [
    "#334155", "#1e293b", "#38bdf8", "#0284c7", "#10b981",
    "#059669", "#f43f5e", "#e11d48", "#f472b6", "#a855f7",
    "#eab308", "#f97316", "#78350f", "#f8fafc",
]

SHOE_COLOR_PRESETS = [
    "#451a03", "#1e293b", "#0f172a", "#be185d", "#0284c7",
    "#15803d", "#b45309", "#7c2d12", "#6b21a8", "#dc2626",
]


class FourDirPreviewWidget(QWidget):
    """
    Muestra el personaje editado en las 4 direcciones simultáneamente:
    Adelante (down), Atrás (up), Izquierda (left) y Derecha (right).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character: Dict[str, Any] = {}
        self.walk_frame = 0
        self.animate_walk = True
        self.setMinimumSize(300, 290)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(180)

    def set_character(self, char_data: Dict[str, Any]):
        self.character = copy.deepcopy(char_data)
        self.update()

    def _tick(self):
        if self.animate_walk:
            self.walk_frame = (self.walk_frame + 1) % 4
        else:
            self.walk_frame = 0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#0b101d"))

        p.setPen(QPen(QColor("#1f2b42"), 1))
        p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 10, 10)

        if not self.character:
            p.end()
            return

        directions = [
            ("down",  "ADELANTE"),
            ("up",    "ATRÁS"),
            ("left",  "IZQUIERDA"),
            ("right", "DERECHA"),
        ]

        cols = 2
        cell_w = self.width() / cols
        cell_h = (self.height() - 16) / 2
        scale = 3

        for idx, (dir_id, label) in enumerate(directions):
            r = idx // cols
            c = idx % cols
            cx = c * cell_w + cell_w / 2
            cy = 8 + r * cell_h + cell_h / 2

            card_rect = QRectF(c * cell_w + 10, 8 + r * cell_h + 5, cell_w - 20, cell_h - 10)
            p.setBrush(QColor("#131b2e"))
            p.setPen(QPen(QColor("#24334f"), 1))
            p.drawRoundedRect(card_rect, 8, 8)

            p.setBrush(QColor(0, 0, 0, 115))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - 22, cy + 28, 44, 11))

            pix = SPRITE_ENGINE.get_pixmap(self.character, direction=dir_id, walk_frame=self.walk_frame, scale=scale)
            bob = -3 if (self.animate_walk and self.walk_frame % 2 == 1) else 0
            p.drawPixmap(int(cx - pix.width() / 2), int(cy - pix.height() / 2 - 4 + bob), pix)

            p.setPen(QColor("#94a3b8"))
            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            p.drawText(
                QRectF(card_rect.left(), card_rect.bottom() - 20, card_rect.width(), 16),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        p.end()


# =============================================================================
# CREADOR DE PERSONAJES CON SECCIONES Y CUADRADOS VISUALES DE DISEÑO AISLADO
# =============================================================================
class CharacterCreatorDialog(QDialog):
    """
    Editor visual de personajes organizado por secciones (Peinado, Cara, Ropa, Zapatos, Accesorio).
    Cada opción se muestra como un cuadrado de diseño pixel-art con SOLO esa parte renderizada.
    """

    def __init__(self, manager: CustomizationManager, on_changed: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_changed = on_changed
        self.setWindowTitle("Pixelavity · Creador Visual de Personajes")
        self.resize(1040, 660)
        self.setMinimumSize(960, 600)

        self.current_char: Dict[str, Any] = {}
        self._updating_ui = False

        # Mapas de botones cuadrados de diseño por sección: (part_kind, style_id) -> QPushButton
        self._design_squares: Dict[str, Dict[str, QPushButton]] = {
            "hair": {},
            "face": {},
            "outfit": {},
            "shoes": {},
            "accessory": {},
        }

        self._build_ui()
        self._reload_list(select_index=0)

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #090d16;
                color: #eef3ff;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#Card {
                background-color: #101624;
                border: 1px solid #1f2b42;
                border-radius: 10px;
            }
            QLabel#SectionTitle {
                color: #38bdf8;
                font-family: 'Consolas';
                font-size: 11px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #151d2e;
                color: #ffffff;
                border: 1px solid #283754;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #151d2e;
                color: #dce7ff;
                border: 1px solid #283754;
                border-radius: 6px;
                padding: 6px 11px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d2840;
                border-color: #38bdf8;
            }
            QPushButton#SectionTab {
                background-color: #141c2e;
                color: #94a3b8;
                border: 1px solid #22304a;
                border-radius: 7px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#SectionTab:checked {
                background-color: rgba(56, 189, 248, 45);
                color: #38bdf8;
                border: 1px solid #38bdf8;
            }
            QPushButton#DesignSquare {
                background-color: #141d2f;
                border: 2px solid #24334f;
                border-radius: 9px;
                padding: 2px;
            }
            QPushButton#DesignSquare:hover {
                background-color: #1b2740;
                border-color: #64748b;
            }
            QPushButton#DesignSquare:checked {
                background-color: rgba(56, 189, 248, 35);
                border: 2px solid #38bdf8;
            }
            QPushButton#PrimaryBtn {
                background-color: rgba(56, 189, 248, 45);
                color: #38bdf8;
                border-color: #38bdf8;
            }
            QPushButton#DangerBtn {
                background-color: rgba(248, 113, 113, 30);
                color: #fca5a5;
                border-color: #ef4444;
            }
            QListWidget {
                background-color: #131b2e;
                border: 1px solid #1f2b42;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 7px 9px;
                border-radius: 6px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: rgba(56, 189, 248, 40);
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        # 1. COLUMNA IZQUIERDA: LISTA DE PERSONAJES
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_card.setFixedWidth(230)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        lbl_pool = QLabel("👥 TUS PERSONAJES")
        lbl_pool.setObjectName("SectionTitle")
        left_layout.addWidget(lbl_pool)

        self.list_chars = QListWidget()
        self.list_chars.setIconSize(QSize(38, 46))
        self.list_chars.currentRowChanged.connect(self._on_row_selected)
        left_layout.addWidget(self.list_chars, stretch=1)

        btn_new = QPushButton("➕ Crear Nuevo Personaje")
        btn_new.setObjectName("PrimaryBtn")
        btn_new.clicked.connect(self._create_new_character)
        left_layout.addWidget(btn_new)

        btn_rand = QPushButton("🎲 Aspecto Aleatorio")
        btn_rand.clicked.connect(self._randomize_current)
        left_layout.addWidget(btn_rand)

        btn_del = QPushButton("🗑️ Eliminar Personaje")
        btn_del.setObjectName("DangerBtn")
        btn_del.clicked.connect(self._delete_current)
        left_layout.addWidget(btn_del)

        btn_reset = QPushButton("↺ Restaurar 3 por Defecto")
        btn_reset.clicked.connect(self._reset_defaults)
        left_layout.addWidget(btn_reset)

        root.addWidget(left_card)

        # 2. COLUMNA CENTRAL: VISTA PREVIA EN 4 DIRECCIONES + NOMBRE
        center_card = QFrame()
        center_card.setObjectName("Card")
        center_layout = QVBoxLayout(center_card)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(10)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Nombre:"))
        self.inp_name = QLineEdit()
        self.inp_name.textEdited.connect(self._on_name_edited)
        name_row.addWidget(self.inp_name, stretch=1)

        self.chk_anim = QCheckBox("Caminar")
        self.chk_anim.setChecked(True)
        self.chk_anim.toggled.connect(self._toggle_walk_anim)
        name_row.addWidget(self.chk_anim)
        center_layout.addLayout(name_row)

        self.preview_widget = FourDirPreviewWidget()
        center_layout.addWidget(self.preview_widget, stretch=1)

        hint_lbl = QLabel(
            "💡 Selecciona una sección a la derecha (Peinado, Cara, Ropa, Zapatos o Accesorio) "
            "y haz clic sobre cualquier cuadrado visual para aplicar ese diseño al instante."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #8b9bb4; font-size: 11px; padding: 7px; background: #131b2e; border-radius: 6px;")
        center_layout.addWidget(hint_lbl)

        root.addWidget(center_card, stretch=1)

        # 3. COLUMNA DERECHA: SECCIONES DE ATRIBUTOS CON CUADRADOS VISUALES
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_card.setFixedWidth(415)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        lbl_sec = QLabel("🎨 SECCIONES DE DISEÑO")
        lbl_sec.setObjectName("SectionTitle")
        right_layout.addWidget(lbl_sec)

        # Barra de pestañas de sección
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(5)
        self.sec_group = QButtonGroup(self)
        self.sec_group.setExclusive(True)

        sections = [
            (0, "💇 Peinado"),
            (1, "🙂 Cara"),
            (2, "👕 Ropa"),
            (3, "👟 Zapatos"),
            (4, "🎩 Accesorio"),
        ]
        for idx, title in sections:
            b = QPushButton(title)
            b.setObjectName("SectionTab")
            b.setCheckable(True)
            if idx == 0:
                b.setChecked(True)
            b.clicked.connect(lambda checked=False, i=idx: self.stack.setCurrentIndex(i))
            self.sec_group.addButton(b, idx)
            tabs_row.addWidget(b)
        right_layout.addLayout(tabs_row)

        # Contenedor por páginas para cada sección
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_hair_page())
        self.stack.addWidget(self._build_face_page())
        self.stack.addWidget(self._build_outfit_page())
        self.stack.addWidget(self._build_shoes_page())
        self.stack.addWidget(self._build_accessory_page())
        right_layout.addWidget(self.stack, stretch=1)

        btn_close = QPushButton("✓ Guardar y Volver a la Oficina")
        btn_close.setObjectName("PrimaryBtn")
        btn_close.setMinimumHeight(38)
        btn_close.clicked.connect(self.accept)
        right_layout.addWidget(btn_close)

        root.addWidget(right_card)

    def _create_design_grid(
        self,
        part_kind: str,
        styles_list: List[Dict[str, str]],
        char_field: str,
        cols: int = 4,
    ) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 6px; margin: 2px; }
            QScrollBar::handle:vertical { background: #24324d; border-radius: 3px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(2, 2, 6, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        for idx, item in enumerate(styles_list):
            sid = item["id"]
            sname = item["name"]
            btn = QPushButton()
            btn.setObjectName("DesignSquare")
            btn.setCheckable(True)
            btn.setFixedSize(78, 78)
            btn.setIconSize(QSize(64, 64))
            btn.setToolTip(sname)
            btn.clicked.connect(lambda checked=False, f=char_field, v=sid: self._select_style(f, v))
            self._design_squares[part_kind][sid] = btn
            grid.addWidget(btn, idx // cols, idx % cols)

        grid.setRowStretch((len(styles_list) + cols - 1) // cols, 1)
        scroll.setWidget(container)
        return scroll

    def _create_color_swatches_row(self, title: str, color_key: str, hex_list: List[str]) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(6)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        v.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(6)
        for hx in hex_list[:9]:
            sw = QPushButton()
            sw.setFixedSize(28, 28)
            sw.setToolTip(hx)
            sw.setStyleSheet(
                f"background-color: {hx}; border: 2px solid #2b3a55; border-radius: 6px;"
            )
            sw.clicked.connect(lambda checked=False, k=color_key, c=hx: self._set_color(k, c))
            row.addWidget(sw)

        btn_custom = QPushButton("🎨")
        btn_custom.setFixedSize(32, 28)
        btn_custom.setToolTip("Elegir color personalizado...")
        btn_custom.clicked.connect(lambda checked=False, k=color_key: self._pick_custom_color(k))
        row.addWidget(btn_custom)
        row.addStretch()

        v.addLayout(row)
        return w

    def _build_hair_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona el diseño del pelo ({len(HAIR_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("hair", HAIR_STYLES, "hair_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color del Pelo:",
            "hair_color",
            [c["color"] for c in HAIR_COLORS],
        ))
        return page

    def _build_face_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona la expresión de la cara ({len(FACE_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("face", FACE_STYLES, "face_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Tono de Piel:",
            "skin_color",
            [s["color"] for s in SKIN_TONES],
        ))
        return page

    def _build_outfit_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(8)

        lbl = QLabel(f"Selecciona el diseño de la ropa ({len(OUTFIT_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("outfit", OUTFIT_STYLES, "outfit_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color Superior (Camisa / Chaqueta / Capa):",
            "top_color",
            CLOTHING_COLOR_PRESETS[:9],
        ))
        layout.addWidget(self._create_color_swatches_row(
            "Color Inferior (Pantalón / Falda / Overol):",
            "bottom_color",
            CLOTHING_COLOR_PRESETS[3:12],
        ))
        return page

    def _build_shoes_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona el diseño de los zapatos ({len(SHOE_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("shoes", SHOE_STYLES, "shoe_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color del Calzado:",
            "shoe_color",
            SHOE_COLOR_PRESETS,
        ))
        return page

    def _build_accessory_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona el sombrero o accesorio ({len(ACCESSORY_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("accessory", ACCESSORY_STYLES, "accessory", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color del Accesorio / Cinta / Detalle:",
            "accessory_color",
            CLOTHING_COLOR_PRESETS[2:11],
        ))
        return page

    def _refresh_design_squares(self):
        """Actualiza los íconos de todos los cuadrados visuales con los colores del personaje actual."""
        if not self.current_char:
            return
        ch = self.current_char
        field_by_kind = {
            "hair": "hair_style",
            "face": "face_style",
            "outfit": "outfit_style",
            "shoes": "shoe_style",
            "accessory": "accessory",
        }
        for kind, btn_map in self._design_squares.items():
            active_val = ch.get(field_by_kind[kind])
            for sid, btn in btn_map.items():
                pix = SPRITE_ENGINE.get_part_preview_pixmap(kind, sid, ch, box_size=62)
                btn.setIcon(QIcon(pix))
                btn.setChecked(sid == active_val)

    def _select_style(self, field: str, style_id: str):
        if self._updating_ui or not self.current_char:
            return
        self.current_char[field] = style_id
        self._persist_current()

    def _set_color(self, color_key: str, hex_color: str):
        if self._updating_ui or not self.current_char:
            return
        self.current_char[color_key] = hex_color
        self._persist_current()

    def _pick_custom_color(self, color_key: str):
        initial = QColor(self.current_char.get(color_key, "#38bdf8"))
        chosen = QColorDialog.getColor(initial, self, "Seleccionar Color")
        if chosen.isValid():
            self.current_char[color_key] = chosen.name()
            self._persist_current()

    def _on_name_edited(self):
        if self._updating_ui or not self.current_char:
            return
        self.current_char["name"] = self.inp_name.text().strip() or "Personaje"
        self._persist_current()

    def _toggle_walk_anim(self, checked: bool):
        self.preview_widget.animate_walk = checked

    def _reload_list(self, select_index: int = 0):
        self._updating_ui = True
        self.list_chars.clear()
        chars = self.manager.get_characters()
        for ch in chars:
            pix = SPRITE_ENGINE.get_pixmap(ch, direction="down", walk_frame=0, scale=2)
            item = QListWidgetItem(QIcon(pix), f"  {ch.get('name', 'Agente')}")
            item.setData(Qt.ItemDataRole.UserRole, ch["id"])
            self.list_chars.addItem(item)
        self._updating_ui = False

        if chars:
            idx = max(0, min(select_index, len(chars) - 1))
            self.list_chars.setCurrentRow(idx)

    def _on_row_selected(self, row: int):
        if self._updating_ui or row < 0:
            return
        chars = self.manager.get_characters()
        if row >= len(chars):
            return
        self.current_char = copy.deepcopy(chars[row])
        self._updating_ui = True
        self.inp_name.setText(self.current_char.get("name", "Personaje"))
        self.preview_widget.set_character(self.current_char)
        self._refresh_design_squares()
        self._updating_ui = False

    def _persist_current(self):
        saved = self.manager.save_character(self.current_char)
        self.current_char = saved
        self.preview_widget.set_character(saved)
        self._refresh_design_squares()
        row = self.list_chars.currentRow()
        if row >= 0:
            item = self.list_chars.item(row)
            if item:
                pix = SPRITE_ENGINE.get_pixmap(saved, direction="down", walk_frame=0, scale=2)
                item.setIcon(QIcon(pix))
                item.setText(f"  {saved.get('name', 'Personaje')}")
        if self.on_changed:
            self.on_changed()

    def _create_new_character(self):
        palette = ["#38bdf8", "#10b981", "#f43f5e", "#a855f7", "#f59e0b", "#3b82f6", "#ec4899"]
        new_ch = {
            "name": f"Agente #{len(self.manager.get_characters()) + 1}",
            "skin_color": random.choice(SKIN_TONES)["color"],
            "face_style": random.choice(FACE_STYLES)["id"],
            "hair_style": random.choice(HAIR_STYLES)["id"],
            "hair_color": random.choice(HAIR_COLORS)["color"],
            "outfit_style": random.choice(OUTFIT_STYLES)["id"],
            "top_color": random.choice(palette),
            "bottom_color": random.choice(["#1e293b", "#334155", "#1e3a8a", "#3f2e21", "#4c1d95"]),
            "shoe_style": random.choice(SHOE_STYLES)["id"],
            "shoe_color": random.choice(SHOE_COLOR_PRESETS),
            "accessory": random.choice(ACCESSORY_STYLES)["id"],
            "accessory_color": random.choice(palette),
        }
        self.manager.save_character(new_ch)
        self._reload_list(select_index=len(self.manager.get_characters()) - 1)
        if self.on_changed:
            self.on_changed()

    def _randomize_current(self):
        if not self.current_char:
            return
        palette = ["#38bdf8", "#10b981", "#f43f5e", "#a855f7", "#f59e0b", "#3b82f6", "#ec4899", "#eab308"]
        self.current_char.update({
            "skin_color": random.choice(SKIN_TONES)["color"],
            "face_style": random.choice(FACE_STYLES)["id"],
            "hair_style": random.choice(HAIR_STYLES)["id"],
            "hair_color": random.choice(HAIR_COLORS)["color"],
            "outfit_style": random.choice(OUTFIT_STYLES)["id"],
            "top_color": random.choice(palette),
            "bottom_color": random.choice(["#1e293b", "#334155", "#1e3a8a", "#3f2e21", "#581c87"]),
            "shoe_style": random.choice(SHOE_STYLES)["id"],
            "shoe_color": random.choice(SHOE_COLOR_PRESETS),
            "accessory": random.choice(ACCESSORY_STYLES)["id"],
            "accessory_color": random.choice(palette),
        })
        self._persist_current()

    def _delete_current(self):
        if not self.current_char:
            return
        ok, msg = self.manager.delete_character(self.current_char["id"])
        if not ok:
            QMessageBox.warning(self, "Regla de Personajes", msg)
            return
        self._reload_list(select_index=0)
        if self.on_changed:
            self.on_changed()

    def _reset_defaults(self):
        self.manager.reset_characters_to_default()
        self._reload_list(select_index=0)
        if self.on_changed:
            self.on_changed()


# =============================================================================
# MENÚ CONSTRUCTOR DE OFICINA CON CUADRADOS VISUALES PIXEL-ART POR CATEGORÍA
# =============================================================================
class OfficeBuilderDock(QFrame):
    """
    Panel constructor de oficina por cuadrículas (32x19 celdas).
    Muestra cada dispositivo, mueble, decoración, piso o pared como un CUADRADO VISUAL
    con el diseño pixel-art real del elemento (sin listas de texto).
    """

    def __init__(self, manager: CustomizationManager, on_state_changed: Callable, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_state_changed = on_state_changed
        self.setObjectName("BuilderDock")

        self.active_category: str = "devices"
        self.tool_mode: str = "place_object"
        self.selected_object_type: str = "computer_desk"
        self.selected_floor_material: str = "walnut_wood"
        self.selected_wall_material: str = "dark_tech"
        self.floor_paint_submode: str = "floor_1x1"

        self._item_buttons: Dict[str, QPushButton] = {}
        self._build_ui()
        self._populate_category("devices")

    def _build_ui(self):
        self.setStyleSheet("""
            QFrame#BuilderDock {
                background-color: #101726;
                border: 1px solid #38bdf8;
                border-radius: 10px;
            }
            QPushButton#CatTab {
                background-color: #151e30;
                color: #94a3b8;
                border: 1px solid #23324d;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#CatTab:checked {
                background-color: rgba(56, 189, 248, 45);
                color: #38bdf8;
                border-color: #38bdf8;
            }
            QPushButton#ToolBtn {
                background-color: #151e30;
                color: #cbd5e1;
                border: 1px solid #283754;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#ToolBtn:checked {
                background-color: rgba(251, 191, 36, 45);
                color: #fcd34d;
                border-color: #fbbf24;
            }
            QPushButton#TileSquare {
                background-color: #141d2f;
                border: 2px solid #24334f;
                border-radius: 8px;
                padding: 2px;
            }
            QPushButton#TileSquare:hover {
                background-color: #1c2842;
                border-color: #64748b;
            }
            QPushButton#TileSquare:checked {
                background-color: rgba(52, 211, 153, 35);
                border: 2px solid #34d399;
            }
        """)

        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(10, 8, 10, 8)
        main_v.setSpacing(6)

        # FILA 1: PESTAÑAS DE CATEGORÍAS + MODOS DE CUADRÍCULA
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)

        categories = [
            ("devices",     "💻 Dispositivos"),
            ("furniture",   "🪑 Muebles"),
            ("decorations", "🪴 Decoración"),
            ("floors",      "🎨 Pisos"),
            ("walls",       "🧱 Paredes"),
        ]
        for cid, clabel in categories:
            btn = QPushButton(clabel)
            btn.setObjectName("CatTab")
            btn.setCheckable(True)
            if cid == "devices":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked=False, c=cid: self._populate_category(c))
            self.cat_group.addButton(btn)
            top_row.addWidget(btn)

        top_row.addSpacing(10)

        self.btn_floor_1x1 = QPushButton("🖌️ Piso 1x1 (Uno por uno)")
        self.btn_floor_1x1.setObjectName("ToolBtn")
        self.btn_floor_1x1.setCheckable(True)
        self.btn_floor_1x1.setChecked(True)
        self.btn_floor_1x1.clicked.connect(lambda: self._set_floor_submode("floor_1x1"))
        top_row.addWidget(self.btn_floor_1x1)

        self.btn_floor_fill = QPushButton("🪣 Piso Rellenar")
        self.btn_floor_fill.setObjectName("ToolBtn")
        self.btn_floor_fill.setCheckable(True)
        self.btn_floor_fill.clicked.connect(lambda: self._set_floor_submode("floor_fill"))
        top_row.addWidget(self.btn_floor_fill)

        top_row.addStretch()

        self.lbl_selected_info = QLabel("")
        self.lbl_selected_info.setStyleSheet("color: #38bdf8; font-family: Consolas; font-size: 11px; font-weight: bold;")
        top_row.addWidget(self.lbl_selected_info)

        top_row.addSpacing(8)

        self.btn_tool_move = QPushButton("🖐️ Mover")
        self.btn_tool_move.setObjectName("ToolBtn")
        self.btn_tool_move.setCheckable(True)
        self.btn_tool_move.setToolTip("Mover cualquier objeto existente de una cuadrícula a otra")
        self.btn_tool_move.clicked.connect(lambda: self._set_explicit_tool("move"))
        top_row.addWidget(self.btn_tool_move)

        self.btn_tool_del = QPushButton("🗑️ Borrar")
        self.btn_tool_del.setObjectName("ToolBtn")
        self.btn_tool_del.setCheckable(True)
        self.btn_tool_del.setToolTip("Eliminar objeto o pared de la cuadrícula clicada")
        self.btn_tool_del.clicked.connect(lambda: self._set_explicit_tool("delete"))
        top_row.addWidget(self.btn_tool_del)

        btn_reset = QPushButton("↺ Restaurar")
        btn_reset.setObjectName("ToolBtn")
        btn_reset.setToolTip("Restaurar el mapa de la oficina por defecto")
        btn_reset.clicked.connect(self._reset_map)
        top_row.addWidget(btn_reset)

        main_v.addLayout(top_row)

        # FILA 2: CUADRADOS VISUALES DE DISEÑO PIXEL-ART
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(74)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.items_container = QWidget()
        self.items_layout = QHBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(2, 2, 2, 2)
        self.items_layout.setSpacing(8)
        scroll.setWidget(self.items_container)
        main_v.addWidget(scroll)

    def _make_square_button(self, pix: QPixmap, tooltip: str, badge_text: str = "") -> QPushButton:
        # Si hay etiqueta de tamaño en cuadrículas (ej. "2x1"), dibujarla discretamente en la esquina del ícono
        if badge_text:
            composed = QPixmap(pix.size())
            composed.fill(Qt.GlobalColor.transparent)
            p = QPainter(composed)
            p.drawPixmap(0, 0, pix)
            p.fillRect(composed.width() - 22, composed.height() - 13, 21, 12, QColor(9, 13, 22, 215))
            p.setPen(QColor("#94a3b8"))
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(QRectF(composed.width() - 22, composed.height() - 13, 21, 12), Qt.AlignmentFlag.AlignCenter, badge_text)
            p.end()
            pix = composed

        btn = QPushButton()
        btn.setObjectName("TileSquare")
        btn.setCheckable(True)
        btn.setFixedSize(64, 64)
        btn.setIconSize(QSize(54, 54))
        btn.setIcon(QIcon(pix))
        btn.setToolTip(tooltip)
        return btn

    def _sync_tool_buttons(self):
        self.btn_tool_move.setChecked(self.tool_mode == "move")
        self.btn_tool_del.setChecked(self.tool_mode == "delete")
        is_floor_cat = (self.active_category == "floors")
        self.btn_floor_1x1.setVisible(is_floor_cat)
        self.btn_floor_fill.setVisible(is_floor_cat)
        self.btn_floor_1x1.setChecked(self.floor_paint_submode == "floor_1x1" and self.tool_mode == "floor_1x1")
        self.btn_floor_fill.setChecked(self.floor_paint_submode == "floor_fill" and self.tool_mode == "floor_fill")

    def _set_floor_submode(self, submode: str):
        self.floor_paint_submode = submode
        self.tool_mode = submode
        self._sync_tool_buttons()
        self.on_state_changed()

    def _set_explicit_tool(self, tmode: str):
        self.tool_mode = tmode
        for b in self._item_buttons.values():
            b.setChecked(False)
        self.lbl_selected_info.setText("🖐️ Mover en Cuadrícula" if tmode == "move" else "🗑️ Borrar de Cuadrícula")
        self._sync_tool_buttons()
        self.on_state_changed()

    def _populate_category(self, category_id: str):
        self.active_category = category_id
        while self.items_layout.count():
            child = self.items_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._item_buttons.clear()

        if category_id in ("devices", "furniture", "decorations"):
            first_key = None
            for okey, spec in OBJECT_CATALOG.items():
                if spec["category"] != category_id:
                    continue
                if first_key is None:
                    first_key = okey
                size_tag = f"{spec['tile_w']}x{spec['tile_h']}"
                pix = SPRITE_ENGINE.get_office_preview_pixmap(category_id, okey, spec, box_size=54)
                btn = self._make_square_button(pix, f"{spec['name']} ({size_tag} cuadrículas)", badge_text=size_tag)
                btn.clicked.connect(lambda checked=False, k=okey: self._select_object_item(k))
                self.items_layout.addWidget(btn)
                self._item_buttons[okey] = btn

            self.items_layout.addStretch()
            if first_key:
                self._select_object_item(first_key)

        elif category_id == "floors":
            first_mat = None
            for fkey, fspec in FLOOR_MATERIALS.items():
                if first_mat is None:
                    first_mat = fkey
                pix = SPRITE_ENGINE.get_office_preview_pixmap("floors", fkey, fspec, box_size=54)
                btn = self._make_square_button(pix, f"Piso: {fspec['name']}")
                btn.clicked.connect(lambda checked=False, k=fkey: self._select_floor_item(k))
                self.items_layout.addWidget(btn)
                self._item_buttons[fkey] = btn

            self.items_layout.addStretch()
            if first_mat:
                self._select_floor_item(self.selected_floor_material or first_mat)

        elif category_id == "walls":
            for wkey, wspec in WALL_MATERIALS.items():
                pix = SPRITE_ENGINE.get_office_preview_pixmap("walls", wkey, wspec, box_size=54)
                btn = self._make_square_button(pix, f"Pared: {wspec['name']} (1x1)", badge_text="1x1")
                btn.clicked.connect(lambda checked=False, k=wkey: self._select_wall_item(k))
                self.items_layout.addWidget(btn)
                self._item_buttons[wkey] = btn

            pix_erase = SPRITE_ENGINE.get_office_preview_pixmap("walls", "__erase_wall__", {}, box_size=54)
            btn_erase_wall = self._make_square_button(pix_erase, "Abrir Puerta / Borrar Pared (1x1)", badge_text="DEL")
            btn_erase_wall.clicked.connect(self._select_wall_eraser)
            self.items_layout.addWidget(btn_erase_wall)
            self._item_buttons["__erase_wall__"] = btn_erase_wall

            self.items_layout.addStretch()
            self._select_wall_item(self.selected_wall_material)

    def _select_object_item(self, obj_key: str):
        self.selected_object_type = obj_key
        self.tool_mode = "place_object"
        for k, b in self._item_buttons.items():
            b.setChecked(k == obj_key)
        spec = OBJECT_CATALOG.get(obj_key, {})
        self.lbl_selected_info.setText(f"{spec.get('name', obj_key)} [{spec.get('tile_w', 1)}x{spec.get('tile_h', 1)}]")
        self._sync_tool_buttons()
        self.on_state_changed()

    def _select_floor_item(self, mat_key: str):
        self.selected_floor_material = mat_key
        self.tool_mode = self.floor_paint_submode
        for k, b in self._item_buttons.items():
            b.setChecked(k == mat_key)
        fspec = FLOOR_MATERIALS.get(mat_key, {})
        self.lbl_selected_info.setText(f"Piso: {fspec.get('name', mat_key)}")
        self._sync_tool_buttons()
        self.on_state_changed()

    def _select_wall_item(self, wall_key: str):
        self.selected_wall_material = wall_key
        self.tool_mode = "wall_place"
        for k, b in self._item_buttons.items():
            b.setChecked(k == wall_key)
        wspec = WALL_MATERIALS.get(wall_key, {})
        self.lbl_selected_info.setText(f"Pared: {wspec.get('name', wall_key)}")
        self._sync_tool_buttons()
        self.on_state_changed()

    def _select_wall_eraser(self):
        self.tool_mode = "wall_erase"
        for k, b in self._item_buttons.items():
            b.setChecked(k == "__erase_wall__")
        self.lbl_selected_info.setText("Abrir Puerta / Borrar Pared [1x1]")
        self._sync_tool_buttons()
        self.on_state_changed()

    def _reset_map(self):
        self.manager.reset_office_to_default()
        self.on_state_changed()
