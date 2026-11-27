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
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QColorDialog, QMessageBox, QCheckBox, QButtonGroup,
    QScrollArea, QStackedWidget, QComboBox
)

from core.customization import (
    CustomizationManager,
    SKIN_TONES,
    EYE_COLORS,
    FACE_STYLES,
    HAIR_STYLES,
    HAIR_COLORS,
    TORSO_STYLES,
    PANTS_STYLES,
    SHOE_STYLES,
    ACCESSORY_STYLES,
    BACK_GEAR_STYLES,
    FLOOR_MATERIALS,
    WALL_MATERIALS,
    OBJECT_CATALOG,
)
from core.sprites import SPRITE_ENGINE


CLOTHING_COLOR_PRESETS = [
    "#1f6199", "#1d4e78", "#2a7a64", "#942c4f", "#3d4a6b",
    "#0e7490", "#78350f", "#585358", "#334155", "#d97706",
    "#10b981", "#f43f5e", "#7e22ce", "#e2e8f0",
]

SHOE_COLOR_PRESETS = [
    "#1a1e26", "#3d261f", "#1e293b", "#7c1d2e", "#78350f",
    "#b45309", "#15803d", "#0284c7", "#6b21a8", "#e2e8f0",
]


PREVIEW_ANIMATIONS = [
    ("walk",          "Caminar (walk1-3)"),
    ("typing_seated", "Sentado · Programar (type1-2)"),
    ("reading",       "Leer con Lentes (read1-2)"),
    ("thinking",      "Pizarra · Pensar"),
    ("terminal",      "Terminal · Servidor"),
    ("browsing",      "Web · Navegar"),
    ("painting",      "Estudio Diseño · Pintar"),
    ("orchestrating", "Orchestrator · Tablet"),
    ("relaxing",      "Lounge · Café"),
    ("idle",          "Quieto · Parpadear"),
]


class FourDirPreviewWidget(QWidget):
    """
    Muestra el personaje editado en las 4 direcciones simultáneamente:
    Adelante (down), Atrás (up), Izquierda 3/4 (left) y Derecha 3/4 (right).
    Soporta previsualización de todas las animaciones interactivas por estación.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character: Dict[str, Any] = {}
        self.walk_frame = 0
        self.preview_action = "walk"
        self.setMinimumSize(340, 380)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(220)

    def set_character(self, char_data: Dict[str, Any]):
        self.character = copy.deepcopy(char_data)
        self.update()

    def set_preview_action(self, action: str):
        self.preview_action = action
        self.walk_frame = 0
        speed_ms = {
            "walk": 180,
            "typing_seated": 160,
            "terminal": 180,
            "browsing": 240,
            "painting": 260,
            "orchestrating": 280,
            "reading": 400,
            "thinking": 420,
            "relaxing": 500,
            "idle": 520,
        }.get(action, 240)
        self.timer.setInterval(speed_ms)
        self.update()

    def _tick(self):
        self.walk_frame = (self.walk_frame + 1) % 4
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
            ("down",  "DOWN (ADELANTE)"),
            ("right", "RIGHT (DERECHA)"),
            ("up",    "UP (ATRÁS)"),
            ("left",  "LEFT (IZQUIERDA)"),
        ]

        cols = 2
        cell_w = self.width() / cols
        cell_h = (self.height() - 16) / 2
        scale = 4 if cell_h >= 165 else 3

        for idx, (dir_id, label) in enumerate(directions):
            r = idx // cols
            c = idx % cols
            cx = c * cell_w + cell_w / 2
            cy = 8 + r * cell_h + cell_h / 2

            card_rect = QRectF(c * cell_w + 10, 8 + r * cell_h + 5, cell_w - 20, cell_h - 10)
            p.setBrush(QColor("#131b2e"))
            p.setPen(QPen(QColor("#24334f"), 1))
            p.drawRoundedRect(card_rect, 8, 8)

            pix = SPRITE_ENGINE.get_pixmap(
                self.character,
                direction=dir_id,
                walk_frame=self.walk_frame if self.preview_action == "walk" else 0,
                scale=scale,
                action=self.preview_action,
                anim_frame=self.walk_frame,
            )
            bob = -2 if (self.preview_action == "walk" and self.walk_frame % 2 == 1) else 0
            draw_y = int(cy - pix.height() / 2 - 8 + bob)
            foot_y = draw_y + pix.height() - (2 * scale)

            p.setBrush(QColor(0, 0, 0, 110))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - 22, foot_y - 4, 44, 10))

            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            p.drawPixmap(int(cx - pix.width() / 2), draw_y, pix)

            p.setPen(QColor("#94a3b8"))
            p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            p.drawText(
                QRectF(card_rect.left(), card_rect.bottom() - 20, card_rect.width(), 16),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        p.end()


# =============================================================================
# CREADOR DE PERSONAJES CON 7 SECCIONES MODULARES Y CUADRADOS VISUALES
# =============================================================================
class CharacterCreatorDialog(QDialog):
    """
    Editor visual de personajes organizado por 7 secciones independientes:
    Peinado, Cara, Torso, Pantalón, Botas, Cabeza y Espalda/Armas.
    Cada opción se muestra como un cuadrado de diseño pixel-art con SOLO esa pieza renderizada.
    """

    def __init__(self, manager: CustomizationManager, on_changed: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_changed = on_changed
        self.setWindowTitle("Pixelavity · Creador Visual de Personajes (Pixel Agents)")
        self.resize(1160, 720)
        self.setMinimumSize(1040, 650)

        self.current_char: Dict[str, Any] = {}
        self._updating_ui = False

        # Mapas de botones cuadrados de diseño por sección: (part_kind, style_id) -> QPushButton
        self._design_squares: Dict[str, Dict[str, QPushButton]] = {
            "hair": {},
            "face": {},
            "torso": {},
            "pants": {},
            "shoes": {},
            "accessory": {},
            "back_gear": {},
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

        lbl_pool = QLabel("TUS PERSONAJES")
        lbl_pool.setObjectName("SectionTitle")
        left_layout.addWidget(lbl_pool)

        self.list_chars = QListWidget()
        self.list_chars.setIconSize(QSize(32, 56))
        self.list_chars.currentRowChanged.connect(self._on_row_selected)
        left_layout.addWidget(self.list_chars, stretch=1)

        btn_new = QPushButton("+ Crear Nuevo Personaje")
        btn_new.setObjectName("PrimaryBtn")
        btn_new.clicked.connect(self._create_new_character)
        left_layout.addWidget(btn_new)

        btn_rand = QPushButton("Aspecto Aleatorio")
        btn_rand.clicked.connect(self._randomize_current)
        left_layout.addWidget(btn_rand)

        btn_del = QPushButton("Eliminar Personaje")
        btn_del.setObjectName("DangerBtn")
        btn_del.clicked.connect(self._delete_current)
        left_layout.addWidget(btn_del)

        btn_reset = QPushButton("Restaurar por Defecto")
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

        self.cmb_anim = QComboBox()
        self.cmb_anim.setStyleSheet("""
            QComboBox {
                background-color: #151d2e; color: #38bdf8;
                border: 1px solid #283754; border-radius: 6px;
                padding: 5px 8px; font-size: 11px; font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #101624; color: #eef3ff;
                selection-background-color: #1e3a5f;
            }
        """)
        for act_id, act_label in PREVIEW_ANIMATIONS:
            self.cmb_anim.addItem(act_label, act_id)
        self.cmb_anim.currentIndexChanged.connect(self._on_anim_changed)
        name_row.addWidget(self.cmb_anim)
        center_layout.addLayout(name_row)

        self.preview_widget = FourDirPreviewWidget()
        center_layout.addWidget(self.preview_widget, stretch=1)

        hint_lbl = QLabel(
            "Combina libremente Peinado, Cara, Torso, Pantalón, Botas, Accesorios de Cabeza "
            "y Equipo de Espalda/Armas. Haz clic en cualquier diseño para verlo en vivo."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #8b9bb4; font-size: 11px; padding: 7px; background: #131b2e; border-radius: 6px;")
        center_layout.addWidget(hint_lbl)

        root.addWidget(center_card, stretch=1)

        # 3. COLUMNA DERECHA: 7 SECCIONES DE ATRIBUTOS CON CUADRADOS VISUALES
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_card.setFixedWidth(445)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        lbl_sec = QLabel("SECCIONES DE DISEÑO")
        lbl_sec.setObjectName("SectionTitle")
        right_layout.addWidget(lbl_sec)

        # Cuadrícula limpia de 2 filas para las 7 secciones modulares
        tabs_grid = QGridLayout()
        tabs_grid.setSpacing(5)
        self.sec_group = QButtonGroup(self)
        self.sec_group.setExclusive(True)

        sections = [
            (0, "Peinado"),
            (1, "Cara"),
            (2, "Torso"),
            (3, "Pantalón"),
            (4, "Botas"),
            (5, "Cabeza"),
            (6, "Espalda"),
        ]
        for idx, title in sections:
            b = QPushButton(title)
            b.setObjectName("SectionTab")
            b.setCheckable(True)
            if idx == 0:
                b.setChecked(True)
            b.clicked.connect(lambda checked=False, i=idx: self.stack.setCurrentIndex(i))
            self.sec_group.addButton(b, idx)
            tabs_grid.addWidget(b, idx // 4, idx % 4)
        right_layout.addLayout(tabs_grid)

        # Contenedor por páginas para cada sección
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_hair_page())
        self.stack.addWidget(self._build_face_page())
        self.stack.addWidget(self._build_torso_page())
        self.stack.addWidget(self._build_pants_page())
        self.stack.addWidget(self._build_shoes_page())
        self.stack.addWidget(self._build_accessory_page())
        self.stack.addWidget(self._build_back_gear_page())
        right_layout.addWidget(self.stack, stretch=1)

        btn_close = QPushButton("Guardar y Volver a la Oficina")
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

        btn_custom = QPushButton("+")
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
        layout.setSpacing(8)

        lbl = QLabel(f"Selecciona la expresión de la cara ({len(FACE_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("face", FACE_STYLES, "face_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Tono de Piel:",
            "skin_color",
            [s["color"] for s in SKIN_TONES],
        ))
        layout.addWidget(self._create_color_swatches_row(
            "Color de Ojos:",
            "eye_color",
            [e["color"] for e in EYE_COLORS],
        ))
        return page

    def _build_torso_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(8)

        lbl = QLabel(f"Selecciona el diseño del torso ({len(TORSO_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("torso", TORSO_STYLES, "torso_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color del Torso (Túnica / Haori / Chaqueta / Armadura):",
            "top_color",
            CLOTHING_COLOR_PRESETS[:9],
        ))
        return page

    def _build_pants_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(8)

        lbl = QLabel(f"Selecciona el pantalón o falda ({len(PANTS_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("pants", PANTS_STYLES, "pants_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color del Pantalón / Hakama / Falda:",
            "bottom_color",
            CLOTHING_COLOR_PRESETS[2:11],
        ))
        return page

    def _build_shoes_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona las botas o calzado ({len(SHOE_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("shoes", SHOE_STYLES, "shoe_style", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color de las Botas / Calzado:",
            "shoe_color",
            SHOE_COLOR_PRESETS,
        ))
        return page

    def _build_accessory_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona accesorio de cabeza / rostro ({len(ACCESSORY_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("accessory", ACCESSORY_STYLES, "accessory", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color de Acento (Accesorios / Fajín / Capa / Detalles):",
            "accessory_color",
            CLOTHING_COLOR_PRESETS[4:13],
        ))
        return page

    def _build_back_gear_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        lbl = QLabel(f"Selecciona equipo de espalda / armas / capa ({len(BACK_GEAR_STYLES)} estilos):")
        lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(lbl)

        layout.addWidget(self._create_design_grid("back_gear", BACK_GEAR_STYLES, "back_gear", cols=4), stretch=1)
        layout.addWidget(self._create_color_swatches_row(
            "Color de Capa / Bufanda / Energía:",
            "accessory_color",
            CLOTHING_COLOR_PRESETS[4:13],
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
            "torso": "torso_style",
            "pants": "pants_style",
            "shoes": "shoe_style",
            "accessory": "accessory",
            "back_gear": "back_gear",
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

    def _on_anim_changed(self, idx: int):
        act_id = self.cmb_anim.itemData(idx)
        if act_id:
            self.preview_widget.set_preview_action(act_id)

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
        torso = random.choice(TORSO_STYLES)["id"]
        new_ch = {
            "name": f"Agente #{len(self.manager.get_characters()) + 1}",
            "skin_color": random.choice(SKIN_TONES)["color"],
            "eye_color": random.choice(EYE_COLORS)["color"],
            "face_style": random.choice(FACE_STYLES)["id"],
            "hair_style": random.choice(HAIR_STYLES)["id"],
            "hair_color": random.choice(HAIR_COLORS)["color"],
            "torso_style": torso,
            "outfit_style": torso,
            "top_color": random.choice(CLOTHING_COLOR_PRESETS),
            "pants_style": random.choice(PANTS_STYLES)["id"],
            "bottom_color": random.choice(CLOTHING_COLOR_PRESETS[:9]),
            "shoe_style": random.choice(SHOE_STYLES)["id"],
            "shoe_color": random.choice(SHOE_COLOR_PRESETS),
            "accessory": random.choice(ACCESSORY_STYLES)["id"],
            "accessory_color": random.choice(CLOTHING_COLOR_PRESETS[4:]),
            "back_gear": random.choice(BACK_GEAR_STYLES)["id"],
        }
        self.manager.save_character(new_ch)
        self._reload_list(select_index=len(self.manager.get_characters()) - 1)
        if self.on_changed:
            self.on_changed()

    def _randomize_current(self):
        if not self.current_char:
            return
        torso = random.choice(TORSO_STYLES)["id"]
        self.current_char.update({
            "skin_color": random.choice(SKIN_TONES)["color"],
            "eye_color": random.choice(EYE_COLORS)["color"],
            "face_style": random.choice(FACE_STYLES)["id"],
            "hair_style": random.choice(HAIR_STYLES)["id"],
            "hair_color": random.choice(HAIR_COLORS)["color"],
            "torso_style": torso,
            "outfit_style": torso,
            "top_color": random.choice(CLOTHING_COLOR_PRESETS),
            "pants_style": random.choice(PANTS_STYLES)["id"],
            "bottom_color": random.choice(CLOTHING_COLOR_PRESETS[:9]),
            "shoe_style": random.choice(SHOE_STYLES)["id"],
            "shoe_color": random.choice(SHOE_COLOR_PRESETS),
            "accessory": random.choice(ACCESSORY_STYLES)["id"],
            "accessory_color": random.choice(CLOTHING_COLOR_PRESETS[4:]),
            "back_gear": random.choice(BACK_GEAR_STYLES)["id"],
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
        self.selected_floor_material: str = "cream_tile"
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
            ("devices",     "Dispositivos"),
            ("furniture",   "Muebles"),
            ("decorations", "Decoración"),
            ("floors",      "Pisos"),
            ("walls",       "Paredes"),
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

        self.btn_floor_1x1 = QPushButton("Piso 1x1 (Uno por uno)")
        self.btn_floor_1x1.setObjectName("ToolBtn")
        self.btn_floor_1x1.setCheckable(True)
        self.btn_floor_1x1.setChecked(True)
        self.btn_floor_1x1.clicked.connect(lambda: self._set_floor_submode("floor_1x1"))
        top_row.addWidget(self.btn_floor_1x1)

        self.btn_floor_fill = QPushButton("Piso Rellenar")
        self.btn_floor_fill.setObjectName("ToolBtn")
        self.btn_floor_fill.setCheckable(True)
        self.btn_floor_fill.clicked.connect(lambda: self._set_floor_submode("floor_fill"))
        top_row.addWidget(self.btn_floor_fill)

        top_row.addStretch()

        self.lbl_selected_info = QLabel("")
        self.lbl_selected_info.setStyleSheet("color: #38bdf8; font-family: Consolas; font-size: 11px; font-weight: bold;")
        top_row.addWidget(self.lbl_selected_info)

        top_row.addSpacing(8)

        self.btn_tool_move = QPushButton("Mover")
        self.btn_tool_move.setObjectName("ToolBtn")
        self.btn_tool_move.setCheckable(True)
        self.btn_tool_move.setToolTip("Mover cualquier objeto existente de una cuadrícula a otra")
        self.btn_tool_move.clicked.connect(lambda: self._set_explicit_tool("move"))
        top_row.addWidget(self.btn_tool_move)

        self.btn_tool_del = QPushButton("Borrar")
        self.btn_tool_del.setObjectName("ToolBtn")
        self.btn_tool_del.setCheckable(True)
        self.btn_tool_del.setToolTip("Eliminar objeto o pared de la cuadrícula clicada")
        self.btn_tool_del.clicked.connect(lambda: self._set_explicit_tool("delete"))
        top_row.addWidget(self.btn_tool_del)

        btn_reset = QPushButton("Restaurar")
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
        self.lbl_selected_info.setText("Mover en Cuadrícula" if tmode == "move" else "Borrar de Cuadrícula")
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


# =============================================================================
# PANEL DE CONSUMO / VIEW USAGE (ESTILO ANTIGRAVITY USAGE)
# =============================================================================
def _format_tokens(n: int) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _format_duration(seconds: int) -> str:
    s = max(0, int(seconds or 0))
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


class UsageRingWidget(QWidget):
    """Anillo circular estilo Antigravity Usage (verde/ámbar/rojo)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fraction: float = 1.0
        self.is_remaining_mode: bool = True
        self.setFixedSize(24, 24)

    def set_value(self, fraction: float, is_remaining_mode: bool = True):
        self.fraction = max(0.0, min(1.0, float(fraction)))
        self.is_remaining_mode = is_remaining_mode
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(3.5, 3.5, self.width() - 7.0, self.height() - 7.0)

        p.setPen(QPen(QColor("#2a3447"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(rect)

        if self.is_remaining_mode:
            if self.fraction >= 0.50:
                col = QColor("#4ade80")
            elif self.fraction >= 0.20:
                col = QColor("#fbbf24")
            else:
                col = QColor("#f87171")
            span = -int(round(self.fraction * 360.0 * 16.0))
        else:
            if self.fraction < 0.60:
                col = QColor("#4ade80")
            elif self.fraction < 0.85:
                col = QColor("#fbbf24")
            else:
                col = QColor("#38bdf8")
            draw_frac = max(0.08, self.fraction) if self.fraction > 0 else 0.0
            span = -int(round(draw_frac * 360.0 * 16.0))

        if span != 0:
            p.setPen(QPen(col, 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 90 * 16, span)
        p.end()


class UsagePopupDialog(QDialog):
    """Ventana flotante de Uso / Consumo inspirada en el panel Usage de Antigravity."""

    def __init__(self, watcher, parent=None):
        super().__init__(parent)
        self.watcher = watcher
        self.setWindowTitle("Usage · Pixelavity")
        self.setMinimumWidth(440)
        self.setMaximumWidth(520)
        self._bridge_path = watcher.get_usage_bridge_path()

        self.setStyleSheet("""
            QDialog {
                background-color: #141923;
                color: #e2e8f0;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame#UsageCard {
                background-color: #19202d;
                border: 1px solid #263145;
                border-radius: 10px;
            }
            QLabel#HeaderTitle {
                font-size: 13px;
                font-weight: bold;
                color: #94a3b8;
            }
            QLabel#GroupTitle {
                font-size: 13px;
                font-weight: bold;
                color: #f8fafc;
            }
            QLabel#RowTitle {
                font-size: 12px;
                color: #cbd5e1;
            }
            QLabel#RowSub {
                font-size: 11px;
                color: #8292aa;
            }
            QLabel#RowValue {
                font-size: 12px;
                font-weight: 600;
                color: #cbd5e1;
            }
            QPushButton {
                background-color: #1d2638;
                color: #cbd5e1;
                border: 1px solid #2d3b55;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #253149;
                border-color: #38bdf8;
                color: #ffffff;
            }
        """)

        self._build_ui()
        self.refresh_usage(force=True)
        self.adjustSize()

        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.refresh_usage(force=False))
        self._timer.start(3000)

    def _make_limit_row(self, title: str):
        row = QWidget()
        row.setMinimumHeight(44)
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 4, 0, 4)
        hl.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(3)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("RowTitle")
        lbl_sub = QLabel("")
        lbl_sub.setObjectName("RowSub")
        lbl_sub.setMinimumHeight(16)
        left.addWidget(lbl_title)
        left.addWidget(lbl_sub)
        hl.addLayout(left, stretch=1)

        lbl_val = QLabel("—")
        lbl_val.setObjectName("RowValue")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ring = UsageRingWidget()
        hl.addWidget(lbl_val)
        hl.addWidget(ring, alignment=Qt.AlignmentFlag.AlignVCenter)
        return row, lbl_sub, lbl_val, ring

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Cabecera
        hdr = QHBoxLayout()
        lbl_h = QLabel("Usage")
        lbl_h.setObjectName("HeaderTitle")
        hdr.addWidget(lbl_h)

        self.lbl_mode = QLabel("● Telemetría Local")
        self.lbl_mode.setStyleSheet(
            "background: rgba(56,189,248,0.14); color: #38bdf8; border: 1px solid rgba(56,189,248,0.4);"
            "border-radius: 9px; padding: 2px 8px; font-family: Consolas; font-size: 10px; font-weight: bold;"
        )
        hdr.addWidget(self.lbl_mode)
        hdr.addStretch()

        btn_ref = QPushButton("Actualizar")
        btn_ref.clicked.connect(lambda: self.refresh_usage(force=True))
        hdr.addWidget(btn_ref)
        root.addLayout(hdr)

        # Tarjeta principal (estilo menú Usage)
        card = QFrame()
        card.setObjectName("UsageCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(12)

        lbl_g1 = QLabel("Gemini Models")
        lbl_g1.setObjectName("GroupTitle")
        cl.addWidget(lbl_g1)

        w_g7, self.gem_w_sub, self.gem_w_val, self.gem_w_ring = self._make_limit_row("Weekly limit")
        w_g5, self.gem_5_sub, self.gem_5_val, self.gem_5_ring = self._make_limit_row("5h limit")
        cl.addWidget(w_g7)
        cl.addWidget(w_g5)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #263145; max-height: 1px; border: none;")
        cl.addWidget(sep)

        lbl_g2 = QLabel("Claude and GPT models")
        lbl_g2.setObjectName("GroupTitle")
        cl.addWidget(lbl_g2)

        w_t7, self.tp_w_sub, self.tp_w_val, self.tp_w_ring = self._make_limit_row("Weekly limit")
        w_t5, self.tp_5_sub, self.tp_5_val, self.tp_5_ring = self._make_limit_row("5h limit")
        cl.addWidget(w_t7)
        cl.addWidget(w_t5)

        root.addWidget(card)

        # Desglose por modelo en los últimos 7 días
        models_card = QFrame()
        models_card.setObjectName("UsageCard")
        ml = QVBoxLayout(models_card)
        ml.setContentsMargins(14, 10, 14, 10)
        ml.setSpacing(5)

        self.lbl_models_hdr = QLabel("Consumo detectado por modelo (7 días)")
        self.lbl_models_hdr.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
        ml.addWidget(self.lbl_models_hdr)

        self.lbl_models_list = QLabel("Sin actividad registrada en los últimos 7 días.")
        self.lbl_models_list.setWordWrap(True)
        self.lbl_models_list.setStyleSheet("font-family: Consolas; font-size: 11px; color: #cbd5e1;")
        ml.addWidget(self.lbl_models_list)
        root.addWidget(models_card)

        # Nota aclaratoria + botones
        self.lbl_note = QLabel(
            "Los tokens se calculan en vivo desde transcript.jsonl. "
            "Si usas Antigravity CLI (/statusline), Pixelavity también muestra el % exacto de cuota."
        )
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setStyleSheet("font-size: 10.5px; color: #7888a0;")
        root.addWidget(self.lbl_note)

        btns = QHBoxLayout()
        self.btn_copy_bridge = QPushButton("Copiar hook /statusline (CLI)")
        self.btn_copy_bridge.setToolTip("Copia el comando PowerShell para conectar la cuota exacta desde agy /statusline")
        self.btn_copy_bridge.clicked.connect(self._copy_bridge_cmd)
        btns.addWidget(self.btn_copy_bridge)
        btns.addStretch()

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        root.addLayout(btns)

    def _copy_bridge_cmd(self):
        cmd = f'powershell -NoProfile -Command "$in=[Console]::In.ReadToEnd(); Set-Content -LiteralPath \'{self._bridge_path}\' -Value $in -Encoding UTF8"'
        cb = QApplication.clipboard()
        if cb:
            cb.setText(f"/statusline {cmd}")
        self.btn_copy_bridge.setText("¡Copiado al portapapeles!")
        QTimer.singleShot(2000, lambda: self.btn_copy_bridge.setText("Copiar hook /statusline (CLI)"))

    def refresh_usage(self, force: bool = False):
        data = self.watcher.get_usage_summary(force_refresh=force)
        self._bridge_path = data.get("bridge_path", self._bridge_path)
        quota = data.get("quota")
        now = data.get("timestamp", 0.0)

        if quota:
            self.lbl_mode.setText("● Cuota Exacta (CLI)")
            self.lbl_mode.setStyleSheet(
                "background: rgba(74,222,128,0.14); color: #4ade80; border: 1px solid rgba(74,222,128,0.45);"
                "border-radius: 9px; padding: 2px 8px; font-family: Consolas; font-size: 10px; font-weight: bold;"
            )
        else:
            self.lbl_mode.setText("● Telemetría Local")
            self.lbl_mode.setStyleSheet(
                "background: rgba(56,189,248,0.14); color: #38bdf8; border: 1px solid rgba(56,189,248,0.4);"
                "border-radius: 9px; padding: 2px 8px; font-family: Consolas; font-size: 10px; font-weight: bold;"
            )

        def _apply_row(win: Dict[str, Any], q_bucket: Optional[Dict[str, Any]], sub_lbl: QLabel, val_lbl: QLabel, ring: UsageRingWidget, is_5h: bool):
            tok_total = win.get("total_tokens", 0)
            in_t = win.get("input_tokens", 0)
            out_t = win.get("output_tokens", 0)
            cache_t = win.get("cache_read_tokens", 0)
            turns = win.get("turns", 0)

            if q_bucket is not None:
                pct = q_bucket.get("remaining_pct", 100)
                frac = q_bucket.get("remaining_fraction", 1.0)
                reset_s = q_bucket.get("reset_in_seconds", 0)
                sub_txt = f"Resets in {_format_duration(reset_s)}" if reset_s > 0 else "Ventana activa"
                if turns > 0:
                    sub_txt += f" · {_format_tokens(tok_total)} tok"
                sub_lbl.setText(sub_txt)
                val_lbl.setText(f"{pct}% left")
                ring.set_value(frac, is_remaining_mode=True)
            else:
                if turns == 0:
                    sub_lbl.setText("Sin uso registrado en esta ventana")
                    val_lbl.setText("0 tok")
                    ring.set_value(1.0, is_remaining_mode=True)
                else:
                    if is_5h:
                        oldest = win.get("oldest_ts")
                        rem_s = max(0, int((oldest + 5 * 3600) - now)) if oldest else 0
                        reset_txt = f" · ventana {_format_duration(rem_s)}" if rem_s > 0 else ""
                        sub_lbl.setText(f"{turns} pasos · in {_format_tokens(in_t)} / out {_format_tokens(out_t)}{reset_txt}")
                        soft_cap = 2_000_000.0
                    else:
                        sub_lbl.setText(
                            f"{turns} pasos · in {_format_tokens(in_t)} / out {_format_tokens(out_t)} · caché {_format_tokens(cache_t)}"
                        )
                        soft_cap = 10_000_000.0
                    val_lbl.setText(f"{_format_tokens(tok_total)} tok")
                    ring.set_value(min(1.0, tok_total / soft_cap), is_remaining_mode=False)

        gem = data.get("gemini", {})
        tp = data.get("third_party", {})
        q = quota or {}
        _apply_row(gem.get("window_7d", {}), q.get("gemini_weekly"), self.gem_w_sub, self.gem_w_val, self.gem_w_ring, is_5h=False)
        _apply_row(gem.get("window_5h", {}), q.get("gemini_5h"), self.gem_5_sub, self.gem_5_val, self.gem_5_ring, is_5h=True)
        _apply_row(tp.get("window_7d", {}), q.get("third_party_weekly"), self.tp_w_sub, self.tp_w_val, self.tp_w_ring, is_5h=False)
        _apply_row(tp.get("window_5h", {}), q.get("third_party_5h"), self.tp_5_sub, self.tp_5_val, self.tp_5_ring, is_5h=True)

        models = data.get("by_model", [])
        self.lbl_models_hdr.setText(
            f"Consumo por modelo (7 días · {data.get('conversations_7d', 0)} chats · {data.get('conversations_5h', 0)} en 5h)"
        )
        if models:
            lines = []
            for m in models[:5]:
                lines.append(
                    f"• {m['model']}: {_format_tokens(m['total_tokens'])} tok "
                    f"({m['turns']} pasos, caché {_format_tokens(m['cache_read_tokens'])})"
                )
            self.lbl_models_list.setText("\n".join(lines))
        else:
            self.lbl_models_list.setText("Sin pasos con métricas de tokens en los últimos 7 días.")

    def closeEvent(self, event):
        if hasattr(self, "_timer"):
            self._timer.stop()
        super().closeEvent(event)
