# -*- coding: utf-8 -*-
"""
Pixelavity - Diálogo Creador de Personajes (4 Direcciones) y Barra Editora de Oficina / Background
"""

import copy
import random
from typing import Dict, Any, Optional, Callable

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QListWidget,
    QListWidgetItem, QFrame, QColorDialog, QMessageBox, QCheckBox
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
    DEVICE_CATALOG,
    DECORATION_CATALOG,
)
from core.sprites import SPRITE_ENGINE


class FourDirPreviewWidget(QWidget):
    """
    Muestra el personaje editado en las 4 direcciones simultáneamente:
    Adelante (down), Atrás (up), Izquierda (left) y Derecha (right),
    animando su ciclo de caminata en tiempo real.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character: Dict[str, Any] = {}
        self.walk_frame = 0
        self.animate_walk = True
        self.setMinimumSize(310, 270)

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
        cell_h = (self.height() - 20) / 2
        scale = 4

        for idx, (dir_id, label) in enumerate(directions):
            r = idx // cols
            c = idx % cols
            cx = c * cell_w + cell_w / 2
            cy = 10 + r * cell_h + cell_h / 2

            # Tarjeta de cada dirección
            card_rect = QRectF(c * cell_w + 12, 10 + r * cell_h + 6, cell_w - 24, cell_h - 12)
            p.setBrush(QColor("#131b2e"))
            p.setPen(QPen(QColor("#24334f"), 1))
            p.drawRoundedRect(card_rect, 8, 8)

            # Sombra en el piso
            p.setBrush(QColor(0, 0, 0, 110))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - 24, cy + 28, 48, 12))

            # Dibujar el sprite escalado 4x (88x112 px)
            pix = SPRITE_ENGINE.get_pixmap(self.character, direction=dir_id, walk_frame=self.walk_frame, scale=scale)
            bob = -3 if (self.animate_walk and self.walk_frame % 2 == 1) else 0
            p.drawPixmap(int(cx - pix.width() / 2), int(cy - pix.height() / 2 - 6 + bob), pix)

            # Etiqueta de dirección
            p.setPen(QColor("#94a3b8"))
            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            p.drawText(
                QRectF(card_rect.left(), card_rect.bottom() - 22, card_rect.width(), 18),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        p.end()


class CharacterCreatorDialog(QDialog):
    """
    Editor interactivo de personajes para Pixelavity.
    Permite modificar pelo, cara, piel, ropa, zapatos y accesorios, y gestionar el pool
    de personajes que la aplicación asigna aleatoriamente sin repetir a los agentes activos.
    """

    def __init__(self, manager: CustomizationManager, on_changed: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_changed = on_changed
        self.setWindowTitle("Pixelavity · Creador y Personalización de Personajes")
        self.resize(960, 620)
        self.setMinimumSize(880, 560)

        self.current_char: Dict[str, Any] = {}
        self._updating_ui = False

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
            QLineEdit, QComboBox {
                background-color: #151d2e;
                color: #ffffff;
                border: 1px solid #283754;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
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

        # 1. COLUMNA IZQUIERDA: LISTA DE PERSONAJES EN EL POOL
        left_card = QFrame()
        left_card.setObjectName("Card")
        left_card.setFixedWidth(235)
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        lbl_pool = QLabel("👥 TUS PERSONAJES")
        lbl_pool.setObjectName("SectionTitle")
        left_layout.addWidget(lbl_pool)

        self.list_chars = QListWidget()
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

        # 2. COLUMNA CENTRAL: VISTA PREVIA 4 DIRECCIONES (ADELANTE, ATRÁS, IZQ, DER)
        center_card = QFrame()
        center_card.setObjectName("Card")
        center_layout = QVBoxLayout(center_card)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)

        top_prev = QHBoxLayout()
        lbl_prev = QLabel("🎮 VISTA PREVIA (4 DIRECCIONES)")
        lbl_prev.setObjectName("SectionTitle")
        top_prev.addWidget(lbl_prev)
        top_prev.addStretch()

        self.chk_anim = QCheckBox("Animar caminata")
        self.chk_anim.setChecked(True)
        self.chk_anim.toggled.connect(self._toggle_walk_anim)
        top_prev.addWidget(self.chk_anim)
        center_layout.addLayout(top_prev)

        self.preview_widget = FourDirPreviewWidget()
        center_layout.addWidget(self.preview_widget, stretch=1)

        hint_lbl = QLabel(
            "💡 Pixelavity asigna tus personajes al azar a cada agente activo sin repetirlos. "
            "Solo se repite alguno cuando hay más agentes trabajando simultáneamente que personajes creados."
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #8b9bb4; font-size: 11px; padding: 6px; background: #131b2e; border-radius: 6px;")
        center_layout.addWidget(hint_lbl)

        root.addWidget(center_card, stretch=1)

        # 3. COLUMNA DERECHA: CONTROLES DE PERSONALIZACIÓN POR CAPAS
        right_card = QFrame()
        right_card.setObjectName("Card")
        right_card.setFixedWidth(340)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        lbl_edit = QLabel("✨ PERSONALIZAR ATRIBUTOS")
        lbl_edit.setObjectName("SectionTitle")
        right_layout.addWidget(lbl_edit)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        # Nombre
        form.addWidget(QLabel("Nombre:"), 0, 0)
        self.inp_name = QLineEdit()
        self.inp_name.textEdited.connect(self._on_field_edited)
        form.addWidget(self.inp_name, 0, 1, 1, 2)

        # Piel
        form.addWidget(QLabel("Piel:"), 1, 0)
        self.cmb_skin = QComboBox()
        for st in SKIN_TONES:
            self.cmb_skin.addItem(st["name"], st["color"])
        self.cmb_skin.currentIndexChanged.connect(self._on_skin_preset_changed)
        form.addWidget(self.cmb_skin, 1, 1)
        self.btn_skin_col = QPushButton("Color")
        self.btn_skin_col.clicked.connect(lambda: self._pick_color("skin_color", self.btn_skin_col))
        form.addWidget(self.btn_skin_col, 1, 2)

        # Cara / Expresión
        form.addWidget(QLabel("Cara:"), 2, 0)
        self.cmb_face = QComboBox()
        for fs in FACE_STYLES:
            self.cmb_face.addItem(fs["name"], fs["id"])
        self.cmb_face.currentIndexChanged.connect(self._on_field_edited)
        form.addWidget(self.cmb_face, 2, 1, 1, 2)

        # Pelo (Estilo + Color)
        form.addWidget(QLabel("Pelo:"), 3, 0)
        self.cmb_hair = QComboBox()
        for hs in HAIR_STYLES:
            self.cmb_hair.addItem(hs["name"], hs["id"])
        self.cmb_hair.currentIndexChanged.connect(self._on_field_edited)
        form.addWidget(self.cmb_hair, 3, 1)
        self.btn_hair_col = QPushButton("Color")
        self.btn_hair_col.clicked.connect(lambda: self._pick_color("hair_color", self.btn_hair_col))
        form.addWidget(self.btn_hair_col, 3, 2)

        # Ropa (Estilo + Color Superior + Color Inferior)
        form.addWidget(QLabel("Ropa:"), 4, 0)
        self.cmb_outfit = QComboBox()
        for os_item in OUTFIT_STYLES:
            self.cmb_outfit.addItem(os_item["name"], os_item["id"])
        self.cmb_outfit.currentIndexChanged.connect(self._on_field_edited)
        form.addWidget(self.cmb_outfit, 4, 1, 1, 2)

        form.addWidget(QLabel("Colores Ropa:"), 5, 0)
        self.btn_top_col = QPushButton("Superior")
        self.btn_top_col.clicked.connect(lambda: self._pick_color("top_color", self.btn_top_col))
        form.addWidget(self.btn_top_col, 5, 1)
        self.btn_bot_col = QPushButton("Inferior")
        self.btn_bot_col.clicked.connect(lambda: self._pick_color("bottom_color", self.btn_bot_col))
        form.addWidget(self.btn_bot_col, 5, 2)

        # Zapatos (Estilo + Color)
        form.addWidget(QLabel("Zapatos:"), 6, 0)
        self.cmb_shoes = QComboBox()
        for sh in SHOE_STYLES:
            self.cmb_shoes.addItem(sh["name"], sh["id"])
        self.cmb_shoes.currentIndexChanged.connect(self._on_field_edited)
        form.addWidget(self.cmb_shoes, 6, 1)
        self.btn_shoe_col = QPushButton("Color")
        self.btn_shoe_col.clicked.connect(lambda: self._pick_color("shoe_color", self.btn_shoe_col))
        form.addWidget(self.btn_shoe_col, 6, 2)

        # Accesorios / Sombrero
        form.addWidget(QLabel("Accesorio:"), 7, 0)
        self.cmb_acc = QComboBox()
        for ac in ACCESSORY_STYLES:
            self.cmb_acc.addItem(ac["name"], ac["id"])
        self.cmb_acc.currentIndexChanged.connect(self._on_field_edited)
        form.addWidget(self.cmb_acc, 7, 1)
        self.btn_acc_col = QPushButton("Color")
        self.btn_acc_col.clicked.connect(lambda: self._pick_color("accessory_color", self.btn_acc_col))
        form.addWidget(self.btn_acc_col, 7, 2)

        right_layout.addLayout(form)
        right_layout.addStretch()

        btn_close = QPushButton("✓ Guardar y Volver a la Oficina")
        btn_close.setObjectName("PrimaryBtn")
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        right_layout.addWidget(btn_close)

        root.addWidget(right_card)

    def _toggle_walk_anim(self, checked: bool):
        self.preview_widget.animate_walk = checked

    def _style_color_btn(self, btn: QPushButton, hex_col: str):
        btn.setStyleSheet(
            f"background-color: {hex_col}; color: #ffffff; "
            f"border: 2px solid #cbd5e1; border-radius: 5px; font-weight: bold;"
        )

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
        self._load_char_into_form()

    def _load_char_into_form(self):
        self._updating_ui = True
        ch = self.current_char
        self.inp_name.setText(ch.get("name", "Personaje"))

        self._set_combo_by_data(self.cmb_skin, ch.get("skin_color", "#ffcca8"))
        self._set_combo_by_data(self.cmb_face, ch.get("face_style", "smile"))
        self._set_combo_by_data(self.cmb_hair, ch.get("hair_style", "short_parted"))
        self._set_combo_by_data(self.cmb_outfit, ch.get("outfit_style", "suit_tie"))
        self._set_combo_by_data(self.cmb_shoes, ch.get("shoe_style", "classic"))
        self._set_combo_by_data(self.cmb_acc, ch.get("accessory", "none"))

        self._style_color_btn(self.btn_skin_col, ch.get("skin_color", "#ffcca8"))
        self._style_color_btn(self.btn_hair_col, ch.get("hair_color", "#eab308"))
        self._style_color_btn(self.btn_top_col, ch.get("top_color", "#334155"))
        self._style_color_btn(self.btn_bot_col, ch.get("bottom_color", "#1e293b"))
        self._style_color_btn(self.btn_shoe_col, ch.get("shoe_color", "#451a03"))
        self._style_color_btn(self.btn_acc_col, ch.get("accessory_color", "#ef4444"))

        self.preview_widget.set_character(ch)
        self._updating_ui = False

    def _set_combo_by_data(self, cmb: QComboBox, val: Any):
        for i in range(cmb.count()):
            if cmb.itemData(i) == val:
                cmb.setCurrentIndex(i)
                return

    def _on_skin_preset_changed(self):
        if self._updating_ui:
            return
        col = self.cmb_skin.currentData()
        if col:
            self.current_char["skin_color"] = col
            self._style_color_btn(self.btn_skin_col, col)
            self._persist_current()

    def _pick_color(self, key: str, btn: QPushButton):
        initial = QColor(self.current_char.get(key, "#38bdf8"))
        chosen = QColorDialog.getColor(initial, self, "Seleccionar Color")
        if chosen.isValid():
            hex_c = chosen.name()
            self.current_char[key] = hex_c
            self._style_color_btn(btn, hex_c)
            self._persist_current()

    def _on_field_edited(self):
        if self._updating_ui or not self.current_char:
            return
        self.current_char["name"] = self.inp_name.text().strip() or "Personaje"
        self.current_char["face_style"] = self.cmb_face.currentData()
        self.current_char["hair_style"] = self.cmb_hair.currentData()
        self.current_char["outfit_style"] = self.cmb_outfit.currentData()
        self.current_char["shoe_style"] = self.cmb_shoes.currentData()
        self.current_char["accessory"] = self.cmb_acc.currentData()
        self._persist_current()

    def _persist_current(self):
        saved = self.manager.save_character(self.current_char)
        self.current_char = saved
        self.preview_widget.set_character(saved)
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
            "shoe_color": random.choice(["#1e293b", "#451a03", "#be185d", "#0284c7"]),
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
            "shoe_color": random.choice(["#1e293b", "#451a03", "#be185d", "#0284c7"]),
            "accessory": random.choice(ACCESSORY_STYLES)["id"],
            "accessory_color": random.choice(palette),
        })
        self._load_char_into_form()
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


class OfficeEditorBar(QFrame):
    """
    Barra de herramientas para personalizar el Background (Pisos, Paredes, Dispositivos y Decoración).
    Incluye validación de reglas mínimas (ej. mínimo 1 computador y 1 mueble de libros).
    """

    def __init__(self, manager: CustomizationManager, on_layout_changed: Callable, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.on_layout_changed = on_layout_changed
        self.setObjectName("EditorBar")
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QFrame#EditorBar {
                background-color: #121a2b;
                border: 1px solid #38bdf8;
                border-radius: 9px;
            }
            QLabel {
                font-size: 11px;
                color: #cbd5e1;
            }
            QComboBox {
                background-color: #172238;
                color: #ffffff;
                border: 1px solid #2b3d5e;
                border-radius: 5px;
                padding: 3px 7px;
                font-size: 11px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # 1. Selector de Piso (clic en sala para pintar)
        layout.addWidget(QLabel("🎨 Piso al clicar sala:"))
        self.cmb_floor = QComboBox()
        for fid, fspec in FLOOR_MATERIALS.items():
            self.cmb_floor.addItem(fspec["name"], fid)
        layout.addWidget(self.cmb_floor)

        # 2. Paredes ON/OFF
        self.chk_walls = QCheckBox("Paredes")
        self.chk_walls.setChecked(bool(self.manager.get_office_layout().get("show_room_walls", True)))
        self.chk_walls.toggled.connect(self._on_walls_toggled)
        layout.addWidget(self.chk_walls)

        # 3. Agregar Dispositivo Interactivo
        layout.addWidget(QLabel("|  Dispositivo:"))
        self.cmb_device = QComboBox()
        for dtype, dspec in DEVICE_CATALOG.items():
            self.cmb_device.addItem(f"{dspec['icon']} {dspec['name']}", dtype)
        layout.addWidget(self.cmb_device)

        btn_add_dev = QPushButton("➕ Añadir")
        btn_add_dev.clicked.connect(self._on_add_device)
        layout.addWidget(btn_add_dev)

        # 4. Agregar Decoración
        layout.addWidget(QLabel("|  Decoración:"))
        self.cmb_dec = QComboBox()
        for dtype, dspec in DECORATION_CATALOG.items():
            self.cmb_dec.addItem(f"{dspec['icon']} {dspec['name']}", dtype)
        layout.addWidget(self.cmb_dec)

        btn_add_dec = QPushButton("➕ Añadir")
        btn_add_dec.clicked.connect(self._on_add_decoration)
        layout.addWidget(btn_add_dec)

        layout.addStretch()

        hint = QLabel("🖱️ Arrastra muebles con clic izq · Clic der para eliminar")
        hint.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 10.5px;")
        layout.addWidget(hint)

        btn_reset = QPushButton("↺ Restaurar Mapa")
        btn_reset.clicked.connect(self._on_reset_office)
        layout.addWidget(btn_reset)

    def selected_floor_material(self) -> str:
        return self.cmb_floor.currentData() or "walnut_wood"

    def _on_walls_toggled(self, checked: bool):
        self.manager.set_show_room_walls(checked)
        self.on_layout_changed()

    def _on_add_device(self):
        dtype = self.cmb_device.currentData()
        # Colocar cerca del centro del mapa para que el usuario lo arrastre a donde quiera
        self.manager.add_device(dtype, random.randint(240, 780), random.randint(180, 420))
        self.on_layout_changed()

    def _on_add_decoration(self):
        dtype = self.cmb_dec.currentData()
        self.manager.add_decoration(dtype, random.randint(200, 820), random.randint(160, 450))
        self.on_layout_changed()

    def _on_reset_office(self):
        self.manager.reset_office_to_default()
        self.chk_walls.setChecked(True)
        self.on_layout_changed()
