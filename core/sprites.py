# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Sprites Pixel Art Estilo Pixel Agents (16x32 nativo, 4 Direcciones)
Diseño compacto 16x32 píxeles por frame (idéntico al formato de hoja 128x96 = 8x16 x 3x32):
  - Contorno oscuro nítido #18161e, sombreado hue-shifted de 4 tonos por material
  - Cabello voluminoso con mechones texturizados, ojos 2x2 expresivos (blanco + pupila)
  - 4 Direcciones reales: Adelante (down), Atrás (up), Derecha (right), Izquierda (left = espejo)
  - Poses completas: walk1/walk2/walk3, idle (con parpadeo), type1/type2 (tecleando sentado),
    read1/read2 (con lentes de lectura y libro abierto), café, pensar, pintar, orquestar
  - Miniaturas aisladas por pieza para el Creador Visual de Personajes
  - Miniaturas de oficina delegadas a OFFICE_SPRITES (100% fieles al mapa)
"""

from typing import Dict, Any, Tuple, List, Optional
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter

from core.customization import normalize_character


OUTLINE = "#18161e"
SOFT_OUTLINE = "#3b2a22"
WHITE = "#f8fafc"
WHITE_SH = "#cbd5e1"


def _hue_shift(hex_color: str, lum_factor: float, sat_delta: float = 0.0, warm_shadow: bool = False) -> str:
    """Sombreado pixel-art con desplazamiento de matiz (hue-shifting) para evitar grises planos."""
    c = QColor(hex_color or "#1f6199")
    h, s, l, _ = c.getHslF()
    if h < 0:
        h = 0.60

    if lum_factor < 1.0:
        target_h = 0.04 if warm_shadow else 0.69
        dh = target_h - h
        if dh > 0.5:
            dh -= 1.0
        elif dh < -0.5:
            dh += 1.0
        shift_amt = min(0.16, (1.0 - lum_factor) * 0.32)
        h = (h + dh * shift_amt) % 1.0
        s = max(0.0, min(1.0, s + sat_delta + (1.0 - lum_factor) * 0.12))
        l = max(0.06, min(0.95, l * lum_factor))
    else:
        target_h = 0.13
        dh = target_h - h
        if dh > 0.5:
            dh -= 1.0
        elif dh < -0.5:
            dh += 1.0
        shift_amt = min(0.14, (lum_factor - 1.0) * 0.25)
        h = (h + dh * shift_amt) % 1.0
        s = max(0.0, min(1.0, s + sat_delta))
        l = max(0.08, min(0.96, l + (1.0 - l) * min(0.42, (lum_factor - 1.0) * 0.7)))

    out = QColor()
    out.setHslF(h, s, l, 1.0)
    return out.name()


def _build_palette(char: Dict[str, Any]) -> Dict[str, str]:
    skin = char.get("skin_color", "#f5c59c")
    eye_col = char.get("eye_color", "#18161e")
    hair_col = char.get("hair_color", "#946b3e")
    top_col = char.get("top_color", "#1f6199")
    bot_col = char.get("bottom_color", "#1d4e78")
    shoe_col = char.get("shoe_color", "#1a1e26")
    acc_col = char.get("accessory_color", "#d97706")

    return {
        "O": OUTLINE,
        "o": SOFT_OUTLINE,
        "W": WHITE,
        "w": WHITE_SH,
        # Piel
        "J": _hue_shift(skin, 1.15, -0.03, warm_shadow=True),
        "K": skin,
        "k": _hue_shift(skin, 0.80, 0.08, warm_shadow=True),
        "q": _hue_shift(skin, 0.58, 0.12, warm_shadow=True),
        # Cabello
        "L": _hue_shift(hair_col, 1.28, -0.02),
        "H": hair_col,
        "h": _hue_shift(hair_col, 0.74, 0.06),
        "d": _hue_shift(hair_col, 0.50, 0.10),
        # Torso / Ropa
        "U": _hue_shift(top_col, 1.24, -0.02),
        "T": top_col,
        "t": _hue_shift(top_col, 0.74, 0.06),
        "v": _hue_shift(top_col, 0.52, 0.08),
        # Pantalón / Falda
        "C": _hue_shift(bot_col, 1.22, -0.02),
        "B": bot_col,
        "b": _hue_shift(bot_col, 0.74, 0.06),
        "p": _hue_shift(bot_col, 0.50, 0.08),
        # Calzado
        "X": _hue_shift(shoe_col, 1.32, -0.02),
        "Z": shoe_col,
        "z": _hue_shift(shoe_col, 0.70, 0.04),
        "x": _hue_shift(shoe_col, 0.48, 0.06),
        # Accesorio / Acento
        "E": _hue_shift(acc_col, 1.30, 0.02),
        "A": acc_col,
        "a": _hue_shift(acc_col, 0.74, 0.06),
        "r": _hue_shift(acc_col, 0.52, 0.08),
        # Ojos, metales, libro, taza
        "I": eye_col,
        "i": _hue_shift(eye_col, 1.35, 0.04),
        "P": "#f48fb1",      # Rubor
        "Y": "#fde047",      # Dorado brillo
        "y": "#d99b26",      # Dorado medio
        "M": "#94a3b8",      # Metal claro
        "m": "#475569",      # Metal oscuro
        "R": "#b84066",      # Cubierta libro / detalle
        "N": "#4b182a",      # Borde libro oscuro
        "G": "#38bdf8",      # Pantalla cyan / lentes
        "Q": "#e0f7ff",      # Vapor / brillo
    }


class ChibiSpriteRenderer:
    """Renderizador Pixel Agents 16x32 nativo (escalado nearest-neighbor)."""

    GRID_W = 16
    GRID_H = 32

    def __init__(self):
        self._cache: Dict[Tuple, QPixmap] = {}

    def clear_cache(self):
        self._cache.clear()

    def _cache_key(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        scale: int,
        is_typing: bool,
        action: str = "idle",
        anim_frame: int = 0,
    ) -> Tuple:
        c = normalize_character(char)
        return (
            "pa_16x32_v1",
            c.get("skin_color", "#f5c59c"),
            c.get("eye_color", "#18161e"),
            c.get("face_style", "classic"),
            c.get("hair_style", "spiky_tuft"),
            c.get("hair_color", "#946b3e"),
            c.get("torso_style", "suit_tie"),
            c.get("top_color", "#1f6199"),
            c.get("pants_style", "dress_pants"),
            c.get("bottom_color", "#1d4e78"),
            c.get("shoe_style", "oxfords"),
            c.get("shoe_color", "#1a1e26"),
            c.get("accessory", "none"),
            c.get("accessory_color", "#d97706"),
            c.get("back_gear", "none"),
            direction,
            walk_frame % 4,
            scale,
            is_typing,
            action,
            anim_frame % 4,
        )

    def get_pixmap(
        self,
        char: Dict[str, Any],
        direction: str = "down",
        walk_frame: int = 0,
        scale: int = 2,
        is_typing: bool = False,
        action: Optional[str] = None,
        anim_frame: Optional[int] = None,
    ) -> QPixmap:
        if direction not in ("down", "up", "left", "right"):
            direction = "down"
        if action is None:
            if is_typing:
                action = "typing_seated"
            elif walk_frame % 4 != 0:
                action = "walk"
            else:
                action = "idle"
        aframe = (walk_frame if anim_frame is None else anim_frame) % 4
        wframe = (walk_frame % 4) if action == "walk" else 0

        key = self._cache_key(char, direction, wframe, scale, is_typing, action, aframe)
        if key in self._cache:
            return self._cache[key]

        img = self._render_character(char, direction, wframe, is_typing, action, aframe)
        scaled = img.scaled(
            self.GRID_W * scale,
            self.GRID_H * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pix = QPixmap.fromImage(scaled)
        if len(self._cache) > 4000:
            self._cache.clear()
        self._cache[key] = pix
        return pix

    def _make_helpers(self, img: QImage, palette: Dict[str, str], y_offset: int = 0):
        w, h = img.width(), img.height()

        def px(x: int, y: int, code_or_hex: str):
            yy = y + y_offset
            if 0 <= x < w and 0 <= yy < h:
                col = palette.get(code_or_hex, code_or_hex)
                img.setPixelColor(x, yy, QColor(col))

        def stamp(x0: int, y0: int, rows: List[str]):
            for dy, row_str in enumerate(rows):
                yy = y0 + dy + y_offset
                if not (0 <= yy < h):
                    continue
                for dx, ch_code in enumerate(row_str):
                    if ch_code in (".", " "):
                        continue
                    xx = x0 + dx
                    if 0 <= xx < w and ch_code in palette:
                        img.setPixelColor(xx, yy, QColor(palette[ch_code]))

        return px, stamp

    # =========================================================================
    # COMPOSICIÓN PRINCIPAL 16x32 (DOWN, UP, RIGHT; LEFT = MIRROR(RIGHT))
    # =========================================================================
    def _render_character(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        is_typing: bool,
        action: str = "idle",
        anim_frame: int = 0,
    ) -> QImage:
        if direction == "left":
            return self._render_character(char, "right", walk_frame, is_typing, action, anim_frame).mirrored(True, False)

        c = normalize_character(char)
        img = QImage(self.GRID_W, self.GRID_H, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        palette = _build_palette(c)

        is_seated = action in ("typing_seated", "browsing", "terminal", "relaxing")
        is_reading = action == "reading"
        is_typing_pose = action in ("typing_seated", "browsing", "terminal")

        # Desplazamiento vertical al sentarse o alternar frames de acción (type1/type2, read1/read2)
        body_dy = 2 if (is_seated or is_reading) else 0
        head_extra_dy = 0
        if is_typing_pose and (anim_frame % 2 == 1):
            head_extra_dy = 1
        elif is_reading and (anim_frame % 2 == 1):
            head_extra_dy = 1
        elif action == "idle" and anim_frame == 1:
            head_extra_dy = 1

        px_body, stamp_body = self._make_helpers(img, palette, y_offset=body_dy)
        px_head, stamp_head = self._make_helpers(img, palette, y_offset=body_dy + head_extra_dy)

        face_style = c.get("face_style", "classic")
        eff_face = face_style
        if (action == "idle" and anim_frame == 3) or (action in ("relaxing", "coffee_standing") and anim_frame == 2):
            eff_face = "sleepy"

        hair_style = c.get("hair_style", "spiky_tuft")
        torso_style = c.get("torso_style", "suit_tie")
        pants_style = c.get("pants_style", "dress_pants")
        shoe_style = c.get("shoe_style", "oxfords")
        acc = c.get("accessory", "none")
        back_gear = c.get("back_gear", "none")

        # 1. Equipo trasero (detrás en down/right)
        if direction != "up":
            self._draw_back_gear(stamp_body, px_body, back_gear, direction, walk_frame, behind=True)

        # 2. Cabello trasero (para melenas largas / coletas en vista frontal o lateral)
        self._draw_back_hair(stamp_head, hair_style, direction, walk_frame)

        # 3. Piernas y calzado (o piernas recogidas al estar sentado/leyendo)
        if is_seated or is_reading:
            self._draw_seated_legs(stamp_body, pants_style, shoe_style, direction)
        else:
            self._draw_legs_and_shoes(stamp_body, pants_style, shoe_style, direction, walk_frame)

        # 4. Torso
        self._draw_torso(stamp_body, px_body, torso_style, direction)

        # 5. Brazos (estándar caminando/quieto o pose específica de acción)
        if action == "walk":
            self._draw_arms_walk(stamp_body, torso_style, direction, walk_frame)
        elif is_typing_pose:
            self._draw_arms_typing(stamp_body, px_body, torso_style, direction, anim_frame)
        elif is_reading:
            self._draw_arms_reading(stamp_body, px_body, torso_style, direction, anim_frame)
        elif action in ("relaxing", "coffee_standing"):
            self._draw_arms_coffee(stamp_body, px_body, torso_style, direction, anim_frame)
        elif action in ("thinking", "painting", "orchestrating"):
            self._draw_arms_special(stamp_body, px_body, torso_style, direction, action, anim_frame)
        else:
            self._draw_arms_walk(stamp_body, torso_style, direction, 0)

        # 6. Cabeza y rostro
        self._draw_head(stamp_head, direction)
        self._draw_face(px_head, stamp_head, eff_face, direction)

        # Lentes de lectura automáticos en pose 'reading' (como en Imagen de Referencia 2!)
        if is_reading and acc not in ("sunglasses",):
            self._draw_reading_glasses(px_head, direction)

        # 7. Cabello frontal / corona / vista trasera completa
        self._draw_hair(stamp_head, hair_style, direction, walk_frame)

        # 8. Accesorios de cabeza / rostro
        if acc != "none":
            self._draw_accessory(stamp_head, px_head, acc, direction)

        # 9. Equipo trasero en vista UP o detalles frontales (lanyard, bufanda)
        self._draw_back_gear(stamp_body, px_body, back_gear, direction, walk_frame, behind=False)

        return img

    # =========================================================================
    # CABEZA (x=3..12, y=10..17) Y EXPRESIONES
    # =========================================================================
    def _draw_head(self, stamp, direction: str):
        if direction == "down":
            stamp(3, 10, [
                ".OOOOOOOO.",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                ".OkKKKKkO.",
                "..OOOOOO..",
            ])
        elif direction == "up":
            stamp(3, 10, [
                ".OOOOOOOO.",
                "OkkkkkkkkO",
                "OkkkkkkkkO",
                "OkkkkkkkkO",
                "OkkkkkkkkO",
                "OkkkkkkkkO",
                ".OkkkkkkO.",
                "..OOOOOO..",
            ])
        else:  # right: rostro compacto, la nuca queda cubierta por el cabello
            stamp(4, 10, [
                ".OOOOOOO.",
                "OKKKKKKKO",
                "OKKKKKKKO",
                "OKKKKKKKO",
                "OKKKKKKKO",
                "OKKKKKKKO",
                ".OkKKKKO.",
                "..OOOOO..",
            ])

    def _draw_face(self, px, stamp, face_style: str, direction: str):
        if direction == "up":
            return

        if direction == "down":
            # Ojos 2x2 característicos de Pixel Agents: esclerótica blanca externa + pupila oscura interna
            if face_style == "sleepy":
                px(5, 14, "O"); px(6, 14, "O")
                px(9, 14, "O"); px(10, 14, "O")
            elif face_style == "cool":
                stamp(5, 13, ["WI", "WI"])
                px(9, 14, "O"); px(10, 14, "O")
            elif face_style == "focused":
                px(5, 12, "o"); px(6, 12, "O")
                px(9, 12, "O"); px(10, 12, "o")
                stamp(5, 13, ["WI", "WI"])
                stamp(9, 13, ["IW", "IW"])
            elif face_style == "anime_starry":
                stamp(5, 13, ["WY", "WI"])
                stamp(9, 13, ["YW", "IW"])
                px(4, 15, "P"); px(11, 15, "P")
                px(7, 15, "o"); px(8, 15, "o")
            elif face_style == "anime_smirk":
                px(5, 12, "o"); px(6, 12, "O")
                px(9, 12, "O"); px(10, 12, "o")
                stamp(5, 13, ["WI", "WI"])
                stamp(9, 13, ["IW", "IW"])
                px(7, 15, "o"); px(8, 15, "o"); px(9, 14, "k")
            elif face_style == "anime_blush":
                stamp(5, 13, ["WI", "WI"])
                stamp(9, 13, ["IW", "IW"])
                px(4, 15, "P"); px(5, 15, "P")
                px(10, 15, "P"); px(11, 15, "P")
                px(7, 15, "o"); px(8, 15, "o")
            elif face_style == "anime_scar":
                px(5, 12, "o"); px(6, 12, "O")
                px(9, 12, "O"); px(10, 12, "o")
                stamp(5, 13, ["WI", "WI"])
                stamp(9, 13, ["IW", "IW"])
                px(9, 12, "R"); px(10, 15, "R"); px(11, 16, "R")
            else:
                stamp(5, 13, ["WI", "WI"])
                stamp(9, 13, ["IW", "IW"])

            # Detalles de expresión (classic queda limpio debajo de los ojos como Referencia 2)
            if face_style == "happy":
                px(4, 15, "P"); px(11, 15, "P")
                px(7, 15, "o"); px(8, 15, "o")
            elif face_style == "smile":
                px(7, 15, "o"); px(8, 15, "o")
            elif face_style == "beard":
                stamp(4, 15, [
                    "d......d",
                    ".ddoood.",
                    "..dddd..",
                ])
            elif face_style == "cat":
                px(4, 15, "P"); px(11, 15, "P")
                px(6, 15, "o"); px(7, 16, "o"); px(8, 16, "o"); px(9, 15, "o")

        else:  # right
            if face_style == "sleepy":
                px(9, 14, "O"); px(10, 14, "O")
            elif face_style in ("focused", "anime_smirk", "anime_scar"):
                px(9, 12, "O"); px(10, 12, "o")
                stamp(9, 13, ["WI", "WI"])
                if face_style == "anime_scar":
                    px(9, 15, "R"); px(10, 16, "R")
            elif face_style == "anime_starry":
                stamp(9, 13, ["WY", "WI"])
                px(8, 15, "P")
            else:
                stamp(9, 13, ["WI", "WI"])

            if face_style in ("happy", "cat", "anime_blush"):
                px(8, 15, "P")
            if face_style == "beard":
                stamp(8, 15, [
                    "dddo",
                    ".ddd",
                ])

    def _draw_reading_glasses(self, px, direction: str):
        """Dibuja lentes oscuros de lectura estilo Pixel Agents (como en read1/read2 de Referencia 2)."""
        if direction == "down":
            for x in (4, 5, 6, 7, 8, 9, 10, 11):
                px(x, 12, "O")
            px(4, 13, "O"); px(7, 13, "O"); px(8, 13, "O"); px(11, 13, "O")
            px(5, 14, "O"); px(6, 14, "O"); px(9, 14, "O"); px(10, 14, "O")
        elif direction == "right":
            px(8, 12, "O"); px(9, 12, "O"); px(10, 12, "O"); px(11, 12, "O")
            px(8, 13, "O"); px(11, 13, "O")
            px(9, 14, "O"); px(10, 14, "O")

    # =========================================================================
    # CABELLO (14 ESTILOS CRISP 16x32)
    # =========================================================================
    def _draw_back_hair(self, stamp, hair_style: str, direction: str, walk_frame: int):
        if direction == "up" or hair_style == "bald":
            return
        sway = 1 if walk_frame == 1 else (-1 if walk_frame == 3 else 0)
        if hair_style == "long_straight":
            if direction == "down":
                stamp(2, 11, [
                    "OhhhhhhhhhhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhhhhhhhhhhO",
                    "OhhhhhhhhhhO",
                    ".OhhhhhhhhO.",
                ])
            else:
                stamp(3, 11, [
                    "OhhhO",
                    "OhHHO",
                    "OhHHO",
                    "OhHHO",
                    "OhHHO",
                    "OhHHO",
                    "OhhhO",
                    ".OhO.",
                ])
        elif hair_style == "long_wavy":
            if direction == "down":
                stamp(2, 11, [
                    "OhhhhhhhhhhO",
                    "OHHHHHHHHHHO",
                    "OhHhhhhhhHhO",
                    "OHHHHHHHHHHO",
                    "OhHhhhhhhHhO",
                    "OHHHHHHHHHHO",
                    "OhhhhhhhhhhO",
                    ".OhhhhhhhhO.",
                    "..OhhhhhhO..",
                ])
            else:
                stamp(2 + max(0, sway), 11, [
                    ".OhhhO",
                    "OhHHOO",
                    "OhHHO.",
                    "OhHHOO",
                    "OhHHO.",
                    "OhHHOO",
                    ".OhhhO",
                ])
        elif hair_style == "ponytail" and direction == "right":
            stamp(1, 7 + (1 if walk_frame % 2 == 1 else 0), [
                ".OOO.",
                "OLHHO",
                "OHhHO",
                ".OhO.",
                ".OdO.",
            ])
        elif hair_style == "bob_cut" and direction == "down":
            stamp(2, 11, [
                "OhhhhhhhhhhO",
                "OhHHHHHHHHhO",
                "OhHHHHHHHHhO",
                "OhhhhhhhhhhO",
                ".OhO....OhO.",
            ])
        elif hair_style == "hime_cut":
            if direction == "down":
                stamp(2, 11, [
                    "OhhhhhhhhhhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhHHHHHHHHhO",
                    "OhhhhhhhhhhO",
                    "OhhhhhhhhhhO",
                    ".OhhhhhhhhO.",
                ])
            else:
                stamp(3, 11, ["OhhhO", "OhHHO", "OhHHO", "OhHHO", "OhHHO", "OhhhO"])
        elif hair_style == "twintails_long":
            if direction == "down":
                stamp(0, 9, [
                    ".OA..........AO.",
                    "OLHO........OHLO",
                    "OHhO........OhHO",
                    "OHHO........OHHO",
                    "OHhO........OhHO",
                    "OHHO........OHHO",
                    "OhHO........OHhO",
                    "OhHO........OHhO",
                    "OhHO........OHhO",
                    ".OhO........OhO.",
                    ".OdO........OdO.",
                ])
            else:
                stamp(1, 9 + (1 if walk_frame % 2 == 1 else 0), [
                    ".OAO.",
                    "OLHHO",
                    "OHhHO",
                    "OHHHO",
                    "OhHHO",
                    "OhhhO",
                    ".OdO.",
                ])
        elif hair_style == "drill_curls":
            if direction == "down":
                stamp(0, 10, [
                    "OLHO........OHLO",
                    "OHhO........OhHO",
                    "OLhO........OhLO",
                    "OHhO........OhHO",
                    "OLhO........OhLO",
                    "OhdO........OdHO",
                    ".OdO........OdO.",
                ])
            else:
                stamp(2, 10, ["OLHO", "OHhO", "OLhO", "OHhO", "OhdO", ".OO."])
        elif hair_style == "wolf_mullet":
            if direction == "down":
                stamp(1, 14, [
                    "OhO..........OhO",
                    "OHhO........OhHO",
                    "OhdO........OdHO",
                    ".OO..........OO.",
                ])
            else:
                stamp(2, 13, ["OLHO", "OHhO", "OhHO", "OdO."])
        elif hair_style == "samurai_ponytail":
            if direction == "down":
                stamp(5, 1, ["..OOOO..", ".OLLLLhO", "OLHHHHHO", ".OAAAAO."])
            else:
                stamp(0, 4 + (1 if walk_frame % 2 == 1 else 0), [
                    "..OOO..",
                    ".OLHHO.",
                    "OLHhHO.",
                    "OHhOAO.",
                    "OhO....",
                    "OdO....",
                ])

    def _draw_hair(self, stamp, hair_style: str, direction: str, walk_frame: int):
        if hair_style == "bald":
            return

        if direction == "up":
            if hair_style in ("spiky_tuft", "gojo_swept"):
                stamp(1, 2 if hair_style == "gojo_swept" else 3, [
                    "..OO..OO..OO..",
                    ".OLHOOLHOOLHO.",
                    ".OLLLLLLLLLLhO",
                    "OLHHHHHHHHHHHhO",
                    "OHHHHHHHHHHHHhO",
                    "OHHHHHHHHHHHHhO",
                    "OHHHHHHHHHHHHhO",
                    "OhhhhhhhhhhhhO",
                    "OhhhhhhhhhhhhO",
                    ".OhhhhhhhhhhO.",
                    "..OhhhhhhhhO..",
                    "...OhhhhhhO...",
                    "....OOOOOO....",
                ])
            elif hair_style == "shonen_spikes":
                stamp(0, 1, [
                    "...OO......OO...",
                    "..OLHO.OO.OLHO..",
                    "OOLLHOOLHOOLHHOO",
                    "OLHHHHHHHHHHHHhO",
                    ".OLHHHHHHHHHHhO.",
                    "OLHHHHHHHHHHHHhO",
                    ".OHHHHHHHHHHHhO.",
                    ".OHHHHHHHHHHHhO.",
                    "..OhhhhhhhhhhO..",
                    "...OhhhhhhhhO...",
                    "....OOOOOOOO....",
                ])
            elif hair_style == "ahoge_fluff":
                stamp(2, 1, [
                    ".....OOO....",
                    "....OLhO....",
                    "....OHO.....",
                    "..OOOOOOOO..",
                    ".OLLLLLLLLhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    "..OhhhhhhhhO.",
                    "...OhhhhhhO..",
                ])
            elif hair_style == "samurai_ponytail":
                stamp(2, 1, [
                    "...OOOOOO...",
                    "..OLLLLLLhO.",
                    ".OLHHHHHHHhO",
                    "..OOAAAAOO..",
                    ".OLLLLLLLLhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    "..OhhhhhhhhO.",
                    "...OhhhhhhO..",
                ])
            elif hair_style == "twintails_long":
                stamp(0, 5, [
                    "....OOOOOOOO....",
                    "...OLLLLLLLLhO..",
                    ".OOOHHHHHHHHHhOO",
                    "OLAOOHHHHHHHHOAO",
                    "OHhOOHHHHHHHHOhO",
                    "OHHO.OhhhhhhO.HO",
                    "OHhO..OhhhhO..hO",
                    "OhHO..........HO",
                    ".OdO..........dO",
                ])
            elif hair_style == "wolf_mullet":
                stamp(1, 3, [
                    "...OO....OO...",
                    "..OLHOOOOLHO..",
                    ".OLLLLLLLLLLhO",
                    ".OHHHHHHHHHHhO",
                    ".OHHHHHHHHHHhO",
                    ".OhhhhhhhhhhhO",
                    "OLhhOOOOOOOOhO",
                    "OHhO........hO",
                    ".OdO........dO",
                ])
            elif hair_style == "levi_undercut":
                stamp(2, 5, [
                    "..OOOOOOOO..",
                    ".OLLLLLLLLhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    "..OddddddOO..",
                    "...OddddO...",
                ])
            elif hair_style in ("long_straight", "long_wavy", "hime_cut"):
                stamp(2, 5, [
                    "..OOOOOOOO..",
                    ".OLLLLLLLLhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    ".OhhhhhhhhhhO",
                    ".OhhhhhhhhhhO",
                    ".OhhhhhhhhhhO",
                    "..OhhhhhhhhO.",
                    "...OhhhhhhO..",
                ])
            elif hair_style == "ponytail":
                stamp(2, 4, [
                    "....OOOO....",
                    "...OLLLLhO..",
                    ".OOOHHHHHhOO",
                    "OLLLLHHHHHhO",
                    "OHHHOrrrrOHhO",
                    "OHHHOrAArOHhO",
                    ".OHHOHHHHhO.",
                    ".OHHOHHHHhO.",
                    "..OhHOhhHO..",
                    "..OhhhhhhO..",
                    "...OhhhhO...",
                ])
            elif hair_style == "twin_buns":
                stamp(1, 4, [
                    ".OOO....OOO.",
                    "OLHHOOOOLHHO",
                    "OHhHLLLLHhHO",
                    ".OOHHHHHHHO.",
                    "..OHHHHHHHO.",
                    "..OHHHHHHHO.",
                    "..OHHHHHHHO.",
                    "..OhhhhhhhO.",
                    "...OhhhhhO..",
                ])
            elif hair_style == "top_bun":
                stamp(3, 2, [
                    "...OOOO...",
                    "..OLLLLhO.",
                    "..OHHHHhO.",
                    ".OLLLLLLhO",
                    "OHHHHHHHHhO",
                    "OHHHHHHHHhO",
                    "OHHHHHHHHhO",
                    "OHHHHHHHHhO",
                    "OHHHHHHHHhO",
                    ".OhhhhhhhO",
                    "..OhhhhhO.",
                ])
            elif hair_style == "curly_afro":
                stamp(1, 3, [
                    "...OOOOOOOO...",
                    ".OOLHHHHHHhOO.",
                    "OLHHhHHHHhHHhO",
                    "OHHhHHHHHHhHHO",
                    "OHHHHHHHHHHHHO",
                    "OHhHHHHHHHHhHO",
                    "OHhHHHHHHHHhHO",
                    ".OhhhhhhhhhhO.",
                    "..OhhhhhhhhO..",
                    "...OhhhhhhO...",
                ])
            elif hair_style == "buzz_short":
                stamp(3, 7, [
                    ".OOOOOOOO.",
                    "OLHHHHHHhO",
                    "OHHHHHHHhO",
                    "OHHHHHHHhO",
                    "OHHHHHHHhO",
                    "OhhhhhhhhO",
                    ".OhhhhhhO.",
                    "..OOOOOO..",
                ])
            else:
                stamp(2, 5, [
                    "..OOOOOOOO..",
                    ".OLLLLLLLLhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OHHHHHHHHHhO",
                    ".OhhhhhhhhhhO",
                    ".OhhhhhhhhhhO",
                    "..OhhhhhhhhO.",
                    "...OhhhhhhO..",
                ])
            return

        if direction == "right":
            if hair_style in ("spiky_tuft", "gojo_swept"):
                stamp(3, 2 if hair_style == "gojo_swept" else 3, [
                    "..OO.OO.OO..",
                    ".OLHOLHOLHO.",
                    ".OLLLLLLLLhO",
                    "OLHHHHHHHHhO",
                    "OHHHHHHHHHhO",
                    "OHHHHHHHHHhO",
                    "OHHHHHHhHHO.",
                    "OhhhhhOO....",
                    "OhhhhO......",
                    "OhhhO.......",
                    ".OOO........",
                ])
            elif hair_style == "shonen_spikes":
                stamp(1, 1, [
                    "..OO....OO...",
                    ".OLHO.O.OLHO.",
                    "OLLHOOLHOLHHO",
                    ".OLHHHHHHHHhO",
                    "OLHHHHHHHHhO.",
                    ".OHHHHHHHhO..",
                    ".OHHHHHhOO...",
                    "OhhhhhO......",
                    ".OhhhO.......",
                ])
            elif hair_style == "ahoge_fluff":
                stamp(3, 1, [
                    "...OOO....",
                    "..OLhO....",
                    "...OHO....",
                    ".OOOOOOO..",
                    "OLLLLLLhO.",
                    "OLHHHHHHhO",
                    "OHHHHHHHhO",
                    "OHHHHHhOO.",
                    "OhhhhO....",
                ])
            elif hair_style == "levi_undercut":
                stamp(3, 6, [
                    "..OOOOOOO.",
                    ".OLLLLLLhO",
                    "OLHHHHHHhO",
                    "OHHHHHHHhO",
                    "OhhhhddOO.",
                    "OdddO.....",
                ])
            elif hair_style == "emo_cover":
                stamp(3, 5, [
                    "..OOOOOOO.",
                    ".OLLLLLLhO",
                    "OLHHHHHHhO",
                    "OHHHHHHHhO",
                    "OHHHHHhHHO",
                    "OhhhhOHhhO",
                    "OhhhO..OdO",
                ])
            elif hair_style == "curly_afro":
                stamp(2, 3, [
                    "..OOOOOOO..",
                    ".OLHHHHHHhO",
                    "OLHHhHHHHhO",
                    "OHHHHHHHHHhO",
                    "OHhHHHHHHhO",
                    "OHHHHHHHhO.",
                    "OHHHHHhO...",
                    "OhhhhhO....",
                    ".OhhhO.....",
                    "..OOO......",
                ])
            elif hair_style == "buzz_short":
                stamp(3, 7, [
                    "..OOOOOOO.",
                    ".OLHHHHHhO",
                    ".OHHHHHHhO",
                    ".OHHHHHhO.",
                    ".OhhhhO...",
                    ".OhhhO....",
                    "..OOO.....",
                ])
            elif hair_style in ("top_bun", "twin_buns"):
                stamp(3, 2, [
                    "..OOOO...",
                    ".OLLLLhO.",
                    ".OHHHHhO.",
                    "OLLLLLLHO",
                    "OHHHHHHhO",
                    "OHHHHHHhO",
                    "OHHHHHhO.",
                    "OhhhhO...",
                    "OhhhO....",
                    ".OOO.....",
                ])
            else:
                stamp(3, 5, [
                    "..OOOOOOO.",
                    ".OLLLLLLhO",
                    "OLHHHHHHHhO",
                    "OHHHHHHHHhO",
                    "OHHHHHHHhO",
                    "OHHHHHhO..",
                    "OhhhhO....",
                    "OhhhO.....",
                    "OhhhO.....",
                    ".OOO......",
                ])
            return

        # VISTA FRONTAL (DOWN) — flequillo enmarcando la frente sobre y=11..12
        if hair_style == "spiky_tuft":
            stamp(1, 3, [
                ".....OO..OO...",
                "....OLHOOLHO..",
                "..OOLLLLLLhO..",
                ".OLHHHHHHHHhO.",
                "OLHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                ".OhHhhhhHhHhO.",
                ".OhH..hh..HhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "parted_neat":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHhhhHHhHO",
                ".OhH...OhHO.",
                ".OdO....OdO.",
            ])
        elif hair_style == "bob_cut":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHHhhHHHhO",
                ".OhO....OhO.",
                ".OhO....OhO.",
                ".OdO....OdO.",
            ])
        elif hair_style in ("long_straight", "long_wavy"):
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHHhhHHHhO",
                ".OhO....OhO.",
                ".OhO....OhO.",
            ])
        elif hair_style == "ponytail":
            stamp(2, 4, [
                "....OOOO....",
                "...OLLLLhO..",
                "..OOHHHHhOO.",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OhHHhhHHHhO",
                ".OhH....HhO.",
                ".OhO....OhO.",
            ])
        elif hair_style == "messy_fluffy":
            stamp(1, 4, [
                "..OO..OO..OO..",
                ".OLHOOLHOOLHO.",
                ".OLHHHHHHHHhO.",
                "OLHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                ".OhHhhHhhHhHO.",
                ".OhO......OhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "curtain_bangs":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHhhhhHHHhO",
                ".OhHO..OHhHO",
                ".OdO....OdO.",
            ])
        elif hair_style == "buzz_short":
            stamp(3, 7, [
                ".OOOOOOOO.",
                "OLHHHHHHhO",
                "OHHHHHHHhO",
                "OhhhhhhhhO",
                "OhO....OhO",
            ])
        elif hair_style == "curly_afro":
            stamp(1, 3, [
                "...OOOOOOOO...",
                ".OOLHHHHHHhOO.",
                "OLHHhHHHHhHHhO",
                "OHHhHHHHHHhHHO",
                "OHHHHHHHHHHHHO",
                ".OhHhhHHhhHhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "twin_buns":
            stamp(1, 4, [
                ".OOO....OOO.",
                "OLHHOOOOLHHO",
                "OHhHLLLLHhHO",
                ".OOHHHHHHHO.",
                "..OHHHHHHHO.",
                "..OhHhhHhHO.",
                "..OdO..OdO..",
            ])
        elif hair_style == "top_bun":
            stamp(3, 2, [
                "...OOOO...",
                "..OLLLLhO.",
                "..OHHHHhO.",
                ".OLLLLLLhO",
                "OHHHHHHHHhO",
                "OHHHHHHHHhO",
                "OhHHhhHHHhO",
                "OhO....OhO.",
            ])
        elif hair_style == "side_swept":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHHHHHhhHO",
                ".OhO...OhdO.",
            ])
        elif hair_style == "shonen_spikes":
            stamp(0, 1, [
                "...OO......OO...",
                "..OLHO.OO.OLHO..",
                "OOLLHOOLHOOLHHOO",
                ".OLHHHHHHHHHHhO.",
                "OLHHHHHHHHHHHHhO",
                "OHHHHHHHHHHHHHhO",
                ".OLHHHHHHHHHHhO.",
                ".OhHhhHhhHhhHhO.",
                ".OhH..hh..hhHhO.",
                "..OdO......OdO..",
            ])
        elif hair_style == "gojo_swept":
            stamp(1, 2, [
                "..OO..OO..OO..",
                ".OLHOOLHOOLHO.",
                ".OLLLLLLLLLLhO",
                "OLHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                ".OhHHhHhhHHhO.",
                ".OhH.hh..hHhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "levi_undercut":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHHh..hHHhO",
                ".OhHO....OHhO",
                ".OdO......OdO",
            ])
        elif hair_style == "samurai_ponytail":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHhhhhHHHhO",
                ".OhO.hh..OhO.",
                ".OdO......OdO",
            ])
        elif hair_style == "twintails_long":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHhhhhHHHhO",
                ".OhHO....OHhO",
                ".OdO......OdO",
            ])
        elif hair_style == "hime_cut":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHhhhhhhHhO",
                ".OhO......OhO",
                ".OhO......OhO",
                ".OhO......OhO",
                ".OdO......OdO",
            ])
        elif hair_style == "wolf_mullet":
            stamp(1, 4, [
                "..OO......OO..",
                ".OLHOOOOOOLHO.",
                ".OLLLLLLLLLLhO",
                "OLHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                ".OhHhhHhhHhHO.",
                ".OhO......OhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "ahoge_fluff":
            stamp(1, 1, [
                ".....OOO......",
                "....OLhO......",
                ".....OHO......",
                "..OOOOOOOOOO..",
                ".OLLLLLLLLLLhO",
                "OLHHHHHHHHHHhO",
                "OHHHHHHHHHHHhO",
                ".OhHhhHhhHhHO.",
                ".OhH..hh..HhO.",
                ".OdO......OdO.",
            ])
        elif hair_style == "emo_cover":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHHHHHHHHhO",
                ".OhHhhhHHHHhO",
                ".OhO...OhHHhO",
                ".......OhHhO.",
                "........OdO..",
            ])
        elif hair_style == "drill_curls":
            stamp(2, 6, [
                "..OOOOOOOO..",
                ".OLLLLLLLLhO",
                ".OHHHHHHHHHhO",
                ".OHHhhhhHHHhO",
                ".OhHO....OHhO",
                ".OdO......OdO",
            ])

    # =========================================================================
    # TORSO (12 ESTILOS, y=18..25)
    # =========================================================================
    def _draw_torso(self, stamp, px, torso_style: str, direction: str):
        if direction == "up":
            if torso_style == "hoodie":
                stamp(3, 18, [
                    ".OOOOOOOO.",
                    "OUUUUUUUUO",
                    "OTTTTTTTTO",
                    "OthhhhhhtO",
                    "OTTTTTTTTO",
                    "OttttttttO",
                    ".OOOOOOOO.",
                ])
            elif torso_style == "overalls":
                stamp(3, 18, [
                    ".OOOOOOOO.",
                    "OWWTTTTWWO",
                    "OTTTTTTTTO",
                    "OBBBBBBBBO",
                    "OBBBBBBBBO",
                    "ObbbbbbbbO",
                    ".OOOOOOOO.",
                ])
            else:
                stamp(3, 18, [
                    ".OOOOOOOO.",
                    "OUUUUUUUUO",
                    "OTTTTTTTTO",
                    "OTTTTTTTTO",
                    "OttttttttO",
                    "OvvvvvvvvO",
                    ".OOOOOOOO.",
                ])
            return

        if direction == "right":
            if torso_style in ("suit_tie", "blazer_open", "vest_shirt"):
                stamp(4, 18, [
                    ".OOOOOO.",
                    "OUUUWWWO",
                    "OTTTTWWO",
                    "OTTTTWWO",
                    "OtttttwO",
                    "OvvvvvvO",
                    ".OOOOOO.",
                ])
            elif torso_style == "lab_coat":
                stamp(4, 18, [
                    ".OOOOOO.",
                    "OWWWWWWO",
                    "OWWTTWWO",
                    "OWWTTWWO",
                    "OwwwwwwO",
                    "OwwwwwwO",
                    ".OOOOOO.",
                ])
            elif torso_style == "striped_shirt":
                stamp(4, 18, [
                    ".OOOOOO.",
                    "OUUUUUUO",
                    "OWWWWWWO",
                    "OTTTTTTO",
                    "OwwwwwwO",
                    "OvvvvvvO",
                    ".OOOOOO.",
                ])
            else:
                stamp(4, 18, [
                    ".OOOOOO.",
                    "OUUUUUUO",
                    "OTTTTTTO",
                    "OTTTTTTO",
                    "OttttttO",
                    "OvvvvvvO",
                    ".OOOOOO.",
                ])
            return

        # VISTA FRONTAL (DOWN)
        if torso_style == "suit_tie":
            # Referencia 2: chaqueta azul con camisa blanca limpia y corbata oscura central
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTTWWTTUO",
                "OTTWOWWTTO",
                "OTTWOWWTTO",
                "OttWOWWttO",
                "OvvWWWWvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "blazer_open":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTTWWTTUO",
                "OTTAWWATTO",
                "OTTWWWWtTO",
                "OttWWWWttO",
                "OvvwwwwvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "hoodie":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUtUUUUUtO",
                "OTTWTTWTTO",
                "OTTWTTWTTO",
                "OtttAAtttO",
                "OvvttttvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "shirt_collar":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUWWKKWWUO",
                "OTTTTTTTTO",
                "OTTTtTTTTO",
                "OttttttttO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "sweater_vneck":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUWKKKKWUO",
                "OTWWKKWWTO",
                "OTTTTTTTTO",
                "OttttttttO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "vest_shirt":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OWWTKKTWWO",
                "OWTTTTTTWO",
                "OWTTTTTTWO",
                "OwttttttwO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "striped_shirt":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUUUUUUUUO",
                "OWWWWWWWWO",
                "OTTTTTTTTO",
                "OwwwwwwwwO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "cardigan":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTWKKWTUO",
                "OTTWYYWTTO",
                "OTTWwwWTTO",
                "OttWYYWttO",
                "OvvwwwwvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "tech_jacket":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUtAAKKtUO",
                "OTTATTTTTO",
                "OTTAATTTTO",
                "OttaAAattO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "lab_coat":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OWWUTTUWWO",
                "OWWTTTTWWO",
                "OWWTTTTWWO",
                "OwwttttwwO",
                "OwwwwwwwwO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "overalls":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OWBKKKKBWO",
                "OWBBBBBBWO",
                "OBBBBBBBBO",
                "OBBYYYYBBO",
                "ObbbbbbbbO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "gakuran":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTTYUTTUO",
                "OTTTYTTTTO",
                "OTTTYTTTTO",
                "OtttYttttO",
                "OvvvYvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "sailor_fuku":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTWKKWTUO",
                "OTWWAWWTTO",
                "OWWWAAWWWO",
                "OwwwwwwwwO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "haori_kimono":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTOmmOTUO",
                "OTTOmmOTTO",
                "OTAYYYYATO",
                "OtaTTTTatO",
                "OvATTTTAvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "shinobi_vest":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUtmmmmtUO",
                "OTtTTTTtTO",
                "OtvvTTvvTO",
                "OttTTTTttO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "akatsuki_cloak":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTTTTTTUO",
                "OTTAWWATTO",
                "OTTTWWTTTO",
                "OttAaatttO",
                "OvvvAAvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "techwear_coat":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUUAAKKUUO",
                "OTTTATAAUO",
                "OTTAATTTTO",
                "OttaYYattO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "bomber_anime":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OWUTTTTUWO",
                "OWTTTTTTWO",
                "OWTTYYTTWO",
                "OttttttttO",
                "OWWWWWWWWO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "mage_coat":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUYWWWWYUO",
                "OTTYAAYTTO",
                "OTTYTTYTTO",
                "OttYttYttO",
                "OvvYvvYvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "oversized_hoodie":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUUWWWWUUO",
                "OTWTTTTWTO",
                "OAAAAAAAAO",
                "OttttttttO",
                "OvvttttvvO",
                ".OOOOOOOO.",
            ])
        elif torso_style == "trench_detective":
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUTWWWWUTU",
                "OTTWOWWTTO",
                "OTTTTTTTTO",
                "OoooYYoooO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])
        else:  # tshirt_casual
            stamp(3, 18, [
                ".OOOOOOOO.",
                "OUUKKKKUUO",
                "OTTTTTTTTO",
                "OTTTTTTTTO",
                "OttttttttO",
                "OvvvvvvvvO",
                ".OOOOOOOO.",
            ])

    # =========================================================================
    # BRAZOS Y POSES DE ACCIÓN
    # =========================================================================
    def _arm_tokens(self, torso_style: str) -> Tuple[str, str]:
        if torso_style in ("lab_coat", "sailor_fuku", "bomber_anime"):
            return "W", "w"
        if torso_style in ("vest_shirt", "overalls"):
            return "W", "w"
        if torso_style == "shinobi_vest":
            return "B", "b"
        if torso_style == "tshirt_casual":
            return "T", "K"
        return "T", "t"

    def _draw_arms_walk(self, stamp, torso_style: str, direction: str, walk_frame: int):
        a_top, a_mid = self._arm_tokens(torso_style)
        f = walk_frame % 4
        if direction in ("down", "up"):
            # Balanceo sutil de brazos al caminar (walk1 = izq arriba, walk3 = der arriba)
            ldy = -1 if f == 1 else (1 if f == 3 else 0)
            rdy = 1 if f == 1 else (-1 if f == 3 else 0)
            hand = a_mid if direction == "up" else "K"
            cuff = a_mid if direction == "up" else ("W" if torso_style in ("suit_tie", "blazer_open") else a_mid)
            stamp(1, 19 + ldy, [
                ".OO",
                f"O{a_top}O",
                f"O{a_mid}O",
                f"O{cuff}O",
                f"O{hand}O",
                ".OO",
            ])
            stamp(12, 19 + rdy, [
                "OO.",
                f"O{a_top}O",
                f"O{a_mid}O",
                f"O{cuff}O",
                f"O{hand}O",
                "OO.",
            ])
        else:  # right
            dx = -1 if f == 1 else (1 if f == 3 else 0)
            stamp(6 + dx, 19, [
                ".OO.",
                f"O{a_top}{a_top}O",
                f"O{a_mid}{a_mid}O",
                "OWWO",
                "OKKO",
                ".OO.",
            ])

    def _draw_arms_typing(self, stamp, px, torso_style: str, direction: str, anim_frame: int):
        """Pose type1 / type2 de Referencia 2: brazos elevados tecleando alternadamente."""
        a_top, a_mid = self._arm_tokens(torso_style)
        f = anim_frame % 2
        if direction == "down":
            l_dy = 0 if f == 0 else 1
            r_dy = 1 if f == 0 else 0
            stamp(1, 18 + l_dy, [
                ".OO",
                f"O{a_top}O",
                "OWO",
                "OKO",
                ".OO",
            ])
            stamp(12, 18 + r_dy, [
                "OO.",
                f"O{a_top}O",
                "OWO",
                "OKO",
                "OO.",
            ])
        elif direction == "up":
            l_dy = 0 if f == 0 else 1
            r_dy = 1 if f == 0 else 0
            stamp(1, 18 + l_dy, [".OO", f"O{a_top}O", f"O{a_mid}O", ".OO"])
            stamp(12, 18 + r_dy, ["OO.", f"O{a_top}O", f"O{a_mid}O", "OO."])
        else:  # right: brazo extendido hacia el teclado
            dy = 0 if f == 0 else 1
            stamp(7, 19 + dy, [
                ".OOO.",
                f"O{a_top}{a_top}WO",
                f"O{a_mid}KKO",
                ".OOO.",
            ])

    def _draw_arms_reading(self, stamp, px, torso_style: str, direction: str, anim_frame: int):
        """Pose read1 / read2 de Referencia 2: sosteniendo libro/documento blanco abierto."""
        a_top, a_mid = self._arm_tokens(torso_style)
        bob = 1 if (anim_frame % 2 == 1) else 0
        if direction == "down":
            stamp(2, 19, [
                f"O{a_top}O",
                "OKO",
                ".OO",
            ])
            stamp(11, 19, [
                f"O{a_top}O",
                "OKO",
                "OO.",
            ])
            # Libro / hoja blanca abierta al frente (igual que read1/read2 en Referencia 2)
            stamp(5, 20 + bob, [
                "NOOOON",
                "NWWWWN",
                "NWOOWN",
                "NWWWWN",
                "NWOOWN",
                "NWWWWN",
                "NOOOON",
            ])
        elif direction == "up":
            stamp(1, 19, [".OO", f"O{a_top}O", f"O{a_mid}O", ".OO"])
            stamp(12, 19, ["OO.", f"O{a_top}O", f"O{a_mid}O", "OO."])
        else:  # right: sosteniendo documento en diagonal hacia adelante
            stamp(7, 19 + bob, [
                ".OO..",
                f"O{a_top}O..",
                "OKWWO",
                ".OOWO",
                "...OO",
            ])
            px(11, 19 + bob, "N"); px(12, 19 + bob, "W"); px(12, 20 + bob, "N")

    def _draw_arms_coffee(self, stamp, px, torso_style: str, direction: str, anim_frame: int):
        a_top, a_mid = self._arm_tokens(torso_style)
        sip = -1 if anim_frame in (1, 2) else 0
        steam_x = 1 if anim_frame % 2 == 0 else 0
        if direction == "down":
            stamp(1, 19, [".OO", f"O{a_top}O", f"O{a_mid}O", "OKO", ".OO"])
            stamp(11, 19 + sip, [
                f"O{a_top}O",
                "OKWWWO",
                ".OWoWO",
                ".OWWWO",
                "..OOO.",
            ])
            px(13 + steam_x, 18 + sip, "Q")
            px(14 - steam_x, 17 + sip, "W")
        elif direction == "up":
            stamp(1, 19, [".OO", f"O{a_top}O", f"O{a_mid}O", ".OO"])
            stamp(12, 19, ["OO.", f"O{a_top}O", f"O{a_mid}O", "OO."])
            px(13 + steam_x, 17, "Q")
        else:  # right
            stamp(8, 19 + sip, [
                ".OO...",
                f"O{a_top}O...",
                "OKWWWO",
                ".OWoWO",
                "..OOO.",
            ])
            px(11 + steam_x, 18 + sip, "Q")
            px(12 - steam_x, 17 + sip, "W")

    def _draw_arms_special(self, stamp, px, torso_style: str, direction: str, action: str, anim_frame: int):
        a_top, a_mid = self._arm_tokens(torso_style)
        bob = 1 if (anim_frame % 2 == 1) else 0
        if direction == "up":
            stamp(1, 19, [".OO", f"O{a_top}O", f"O{a_mid}O", ".OO"])
            stamp(12, 19, ["OO.", f"O{a_top}O", f"O{a_mid}O", "OO."])
            return

        if action == "thinking":
            if direction == "down":
                stamp(1, 19, [".OO", f"O{a_top}O", f"O{a_mid}O", "OKO", ".OO"])
                stamp(10, 17 + bob, ["OKO", f".O{a_top}O", "..OO"])
            else:
                stamp(8, 17 + bob, ["OKO", f"O{a_top}O", ".OO"])
        elif action == "painting":
            if direction == "down":
                stamp(1, 19, [".OO", f"O{a_top}O", "OKO", ".OO"])
                stamp(12, 18 + bob, ["OAO", f"O{a_top}O", "OKO", ".OO"])
                px(13, 17 + bob, "R")
            else:
                stamp(8, 18 + bob, [".OAO", f"O{a_top}KO", ".OOO"])
                px(11, 17 + bob, "R")
        else:  # orchestrating (tablet holográfica)
            if direction == "down":
                stamp(2, 19, [f"O{a_top}O", "OKO", ".OO"])
                stamp(11, 19, [f"O{a_top}O", "OKO", "OO."])
                stamp(5, 20 + bob, [
                    "OOOOOO",
                    "OGGGGO",
                    "OGQQGO",
                    "OOOOOO",
                ])
            else:
                stamp(8, 19 + bob, [
                    "O.OOO",
                    f"O{a_top}GGO",
                    "OKQGO",
                    ".OOOO",
                ])

    # =========================================================================
    # PIERNAS Y CALZADO (y=25..29)
    # =========================================================================
    def _draw_seated_legs(self, stamp, pants_style: str, shoe_style: str, direction: str):
        p_col = "b" if pants_style == "dress_pants" else "B"
        if direction in ("down", "up"):
            stamp(4, 24, [
                f"O{p_col}{p_col}OO{p_col}{p_col}O",
                "OZZOOZZO",
                ".OOOOOO.",
            ])
        else:
            stamp(5, 24, [
                f"O{p_col}{p_col}{p_col}{p_col}O",
                "OZZZZZO",
                ".OOOOO.",
            ])

    def _draw_legs_and_shoes(self, stamp, pants_style: str, shoe_style: str, direction: str, walk_frame: int):
        f = walk_frame % 4
        p_main = "B"
        p_sh = "b"
        if pants_style == "shorts":
            p_sh = "K"
        elif pants_style == "pleated_skirt" and direction in ("down", "up"):
            stamp(3, 24, [
                "OBBBBBBBBO",
                "ObBbBbBbBO",
            ])

        shoe_hi = "W" if shoe_style == "sneakers" else "X"
        if direction in ("down", "up"):
            # walk1 (f=1): izq arriba 1px; walk3 (f=3): der arriba 1px
            ldy = -1 if f == 1 else 0
            rdy = -1 if f == 3 else 0
            start_y = 26 if pants_style == "pleated_skirt" else 25
            if pants_style != "pleated_skirt":
                stamp(4, 25, [f"O{p_main}{p_main}OO{p_main}{p_main}O"])
            stamp(4, start_y + ldy, [
                f"O{p_sh}{p_sh}O",
                f"O{shoe_hi}ZO",
                ".OO.",
            ])
            stamp(8, start_y + rdy, [
                f"O{p_sh}{p_sh}O",
                f"OZ{shoe_hi}O",
                ".OO.",
            ])
        else:  # right
            if f == 1:
                stamp(3, 25, [
                    f".O{p_main}{p_main}{p_main}{p_main}O.",
                    f"O{p_sh}{p_sh}OO{p_sh}{p_sh}O",
                    f"OZ{shoe_hi}OOZ{shoe_hi}O",
                    ".OO..OO.",
                ])
            elif f == 3:
                stamp(3, 25, [
                    f".O{p_main}{p_main}{p_main}{p_main}O.",
                    f"O{p_sh}{p_sh}OO{p_sh}{p_sh}O",
                    f"O{shoe_hi}ZOO{shoe_hi}ZO",
                    ".OO..OO.",
                ])
            else:
                stamp(5, 25, [
                    f"O{p_main}{p_main}{p_main}{p_main}O",
                    f"O{p_sh}{p_sh}{p_sh}O",
                    f"OZ{shoe_hi}ZO",
                    ".OOOO.",
                ])

    # =========================================================================
    # ACCESORIOS Y EQUIPO TRASERO
    # =========================================================================
    def _draw_accessory(self, stamp, px, acc: str, direction: str):
        if acc == "glasses":
            if direction == "down":
                px(4, 13, "O"); px(7, 13, "O"); px(8, 13, "O"); px(11, 13, "O")
                px(4, 14, "O"); px(11, 14, "O")
                px(5, 15, "o"); px(6, 15, "o"); px(9, 15, "o"); px(10, 15, "o")
            elif direction == "right":
                px(7, 13, "O"); px(8, 13, "O"); px(11, 13, "O")
                px(8, 14, "O"); px(9, 15, "o"); px(10, 15, "o")
        elif acc == "sunglasses":
            if direction == "down":
                stamp(4, 13, ["OOOOOOOO", "OIIOOIIO"])
            elif direction == "right":
                stamp(8, 13, ["OOOO", "OIIO"])
        elif acc == "headphones":
            if direction == "down":
                stamp(2, 6, [
                    "..OOOOOOOO..",
                    ".OAAAAAAAAO.",
                    ".OA......AO.",
                    ".OA......AO.",
                    "OAA......AAO",
                    "Oaa......aaO",
                ])
            elif direction == "up":
                stamp(2, 6, [
                    "..OOOOOOOO..",
                    ".OAAAAAAAAO.",
                    "OAA......AAO",
                    "Oaa......aaO",
                ])
            else:
                stamp(4, 6, [
                    "..OOOO..",
                    ".OAAAAO.",
                    "OAA..AAO",
                    "Oaa..aaO",
                ])
        elif acc == "headset":
            if direction == "down":
                stamp(2, 7, ["OAA......AAO", "Oaa......aaO"])
                px(4, 15, "O"); px(5, 15, "G")
            elif direction == "right":
                stamp(5, 11, ["OAAO", "OaaO"])
                px(8, 15, "O"); px(9, 15, "G")
        elif acc == "baseball_cap":
            if direction == "down":
                stamp(2, 6, [
                    "..OOOOOOOO..",
                    ".OEEEEEEEEO.",
                    ".OAAAAAAAAO.",
                    "OaaaaaaaaaaO",
                ])
            elif direction == "up":
                stamp(2, 6, [
                    "..OOOOOOOO..",
                    ".OEEEEEEEEO.",
                    ".OAAAAAAAAO.",
                    ".OaaaaaaaaO.",
                ])
            else:
                stamp(3, 6, [
                    "..OOOOOOO..",
                    ".OEEEEEEEo.",
                    ".OAAAAAAAAAAO",
                    ".OaaaaaaaaaaO",
                ])
        elif acc == "beanie":
            stamp(3, 4 if direction != "right" else 4, [
                "...OOOO...",
                "..OEEEEO..",
                ".OAAAAAAO.",
                ".OaaaaaaO.",
            ] if direction != "right" else [
                "..OOOO..",
                ".OEEEEO.",
                "OAAAAAAO",
                "OaaaaaaO",
            ])
        elif acc == "beret":
            stamp(2, 5, [
                "...OOOOOO..",
                ".OOAAAAAAO.",
                "OAAAAAAAAAO",
                ".OaaaaaaaO.",
            ])
        elif acc == "cat_ears":
            if direction in ("down", "up"):
                stamp(3, 4, [
                    "OO......OO",
                    "OAO....OAO",
                    "OAPO..OPAO",
                ])
            else:
                stamp(4, 4, ["OO..OO", "OAO.OAO"])
        elif acc == "crown":
            stamp(4, 4, [
                "O.OO.OO.O",
                "OYOYOYOYO",
                "OyyyyyyyO",
                ".OOOOOOO.",
            ])
        elif acc == "bow":
            stamp(5, 5, [
                "OO.OO",
                "OAOAO",
                "OO.OO",
            ])
        elif acc == "bandana":
            if direction == "down":
                stamp(3, 10, ["OAAAAAAAAO"])
            elif direction == "up":
                stamp(3, 10, ["OAAAAAAAAO", "...OAAO..."])
            else:
                stamp(4, 10, ["OAAAAAAAO"])
        elif acc == "ninja_headband":
            if direction == "down":
                stamp(3, 10, ["OAAWWWWAAO", "...OMMO..."])
            elif direction == "up":
                stamp(3, 10, ["OAAAAAAAAO", "..OAA..AAO"])
            else:
                stamp(4, 10, ["OAAAAWWWO"])
        elif acc == "oni_mask_side":
            if direction == "down":
                stamp(9, 5, ["OO..OO", "OWWWWO", "OWoWoO", ".OWWO."])
            elif direction == "right":
                stamp(4, 6, ["OO.OO", "OWWWO", "OWoWO", ".OWO."])
        elif acc == "cyber_visor":
            if direction == "down":
                stamp(3, 12, ["OAAAAAAAAO", "OGGQQQQGGO"])
            elif direction == "right":
                stamp(8, 12, ["OAAAAO", "OGQQGO"])
        elif acc == "blindfold_cool":
            if direction == "down":
                stamp(3, 12, ["OOOOOOOOOO", "OmmmmmmmmO", "OOOOOOOOOO"])
            elif direction == "up":
                stamp(3, 13, ["OmmmmmmmmO"])
            else:
                stamp(4, 12, ["OOOOOOOOO", "OmmmmmmmO", "OOOOOOOOO"])
        elif acc == "eyepatch_anime":
            if direction == "down":
                stamp(4, 12, ["OOoo....", "OIIOoooo", ".OO....."])
            elif direction == "right":
                stamp(8, 12, ["OOoo", "OIIO", ".OO."])
        elif acc == "fox_ears":
            if direction in ("down", "up"):
                stamp(2, 2, [
                    ".OO......OO.",
                    "OAEO....OEAO",
                    "OAAO....OAAO",
                    "OAWO....OWAO",
                ])
            else:
                stamp(4, 2, [".OO.OO.", "OAEOAEO", "OAAOAAO"])
        elif acc == "demon_horns":
            if direction in ("down", "up"):
                stamp(2, 2, [
                    "OO........OO",
                    "OAO......OAO",
                    ".OAO....OAO.",
                    "..OO....OO..",
                ])
            else:
                stamp(5, 2, ["OO..OO", "OAO.OAO", ".OO..OO"])
        elif acc == "halo_neon":
            stamp(4, 1, [
                ".OOOOOO.",
                "OYEEEEYO",
                ".OOOOOO.",
            ])
        elif acc == "goggles_forehead":
            if direction == "down":
                stamp(3, 8, [
                    ".OOO..OOO.",
                    "OYGQOOQGYO",
                    ".OOO..OOO.",
                ])
            elif direction == "up":
                stamp(3, 9, ["OooooooooO"])
            else:
                stamp(6, 8, [".OOO.", "OYGQO", ".OOO."])
        elif acc == "face_mask":
            if direction == "down":
                stamp(4, 15, [
                    "OmmmmmmO",
                    "OmmGGmmO",
                    ".OOOOOO.",
                ])
            elif direction == "right":
                stamp(7, 15, [
                    "OmmmO",
                    "OmGmO",
                    ".OOO.",
                ])

    def _draw_back_gear(self, stamp, px, gear: str, direction: str, walk_frame: int, behind: bool):
        if gear == "none":
            return
        if gear == "lanyard" and not behind and direction == "down":
            px(6, 19, "A"); px(9, 19, "A")
            px(7, 20, "A"); px(8, 20, "A")
            px(7, 21, "W"); px(8, 21, "W")
            return
        if gear in ("scarf", "hero_scarf_long"):
            flutter = 1 if walk_frame % 2 == 1 else 0
            if (behind and direction != "up") or (not behind and direction == "up"):
                stamp(4, 17, ["OAAAAAAO", "OaaaaaaO"])
                if gear == "hero_scarf_long":
                    stamp(10, 17 + flutter, ["OAAAOO", ".OaaAO", "..OrrO"])
            elif not behind and direction == "down":
                stamp(5, 18, ["OAAAAO", "..OAAO", "..OaaO"])
                if gear == "hero_scarf_long":
                    stamp(11, 18 + flutter, ["OAAO", ".OaO", ".OrO"])
            return
        if gear == "backpack":
            if (not behind and direction == "up") or (behind and direction == "right"):
                bx = 4 if direction == "up" else 2
                stamp(bx, 18, [
                    ".OOOO.",
                    "OAAAAO",
                    "OAaaAO",
                    "OaaaaO",
                    ".OOOO.",
                ])
        elif gear == "cape_mini":
            if (not behind and direction == "up") or (behind and direction != "up"):
                bx = 3 if direction != "right" else 2
                stamp(bx, 18, [
                    ".OOOOOO.",
                    "OAAAAAAO",
                    "OaaaaaaO",
                    "OrrrrrrO",
                    ".OOOOOO.",
                ])
        elif gear == "angel_wings":
            if (not behind and direction == "up") or (behind and direction == "down"):
                stamp(0, 17, [
                    "OO............OO",
                    "OWO..........OWO",
                    "OWwO........OwWO",
                    ".OWO........OWO.",
                ])
        elif gear == "demon_wings":
            if (not behind and direction == "up") or (behind and direction != "up"):
                stamp(0, 15, [
                    "OO............OO",
                    "OAO..........OAO",
                    "OAaO........OaAO",
                    "OaOO........OOaO",
                    ".OO..........OO.",
                ])
        elif gear == "katana_back":
            if (not behind and direction == "up") or (behind and direction != "up"):
                stamp(1, 12, [
                    "..........OO..",
                    ".........OYYO.",
                    "........OMMMO.",
                    ".......OmmO...",
                    "......OmmO....",
                    ".....OmmO.....",
                    "....OmmO......",
                    "...OmmO.......",
                    "..OOO.........",
                ])
        elif gear == "dual_blades":
            if (not behind and direction == "up") or (behind and direction != "up"):
                stamp(1, 12, [
                    ".OO........OO.",
                    "OYYO......OYYO",
                    ".OMMO....OMMO.",
                    "..OmmO..OmmO..",
                    "...OmmmmmmO...",
                    "..OmmO..OmmO..",
                    ".OOO......OOO.",
                ])
        elif gear == "spirit_aura":
            bob = 1 if walk_frame % 2 == 1 else 0
            if behind or direction == "up":
                px(1, 16 + bob, "G"); px(2, 15 + bob, "Q")
                px(14, 17 - bob, "G"); px(13, 16 - bob, "Q")
                px(0, 21 - bob, "E"); px(15, 20 + bob, "E")
        elif gear == "guitar_case":
            if (not behind and direction == "up") or (behind and direction != "up"):
                stamp(2, 13, [
                    "........OO..",
                    ".......OYYO.",
                    "......OmmO..",
                    "....OOmmO...",
                    "...OAAAAO...",
                    "..OAaaaAO...",
                    "..OaaaaaO...",
                    "...OOOOO....",
                ])

    # =========================================================================
    # MINIATURAS AISLADAS POR SECCIÓN PARA EL CREADOR VISUAL DE PERSONAJES
    # =========================================================================
    def get_part_preview_pixmap(
        self,
        part_kind: str,
        style_id: str,
        char: Dict[str, Any],
        box_size: int = 62,
    ) -> QPixmap:
        c = normalize_character(char)
        key = (
            "pa_part_v1",
            part_kind,
            style_id,
            c.get("skin_color", "#f5c59c"),
            c.get("eye_color", "#18161e"),
            c.get("hair_color", "#946b3e"),
            c.get("top_color", "#1f6199"),
            c.get("bottom_color", "#1d4e78"),
            c.get("shoe_color", "#1a1e26"),
            c.get("accessory_color", "#d97706"),
            box_size,
        )
        if key in self._cache:
            return self._cache[key]

        canvas = QImage(self.GRID_W, self.GRID_H, QImage.Format.Format_ARGB32)
        canvas.fill(Qt.GlobalColor.transparent)
        palette = _build_palette(c)
        px, stamp = self._make_helpers(canvas, palette)

        crop_rect = QRect(0, 0, self.GRID_W, self.GRID_H)

        if part_kind == "hair":
            if style_id == "bald":
                for xx in range(5, 11):
                    px(xx, 10, "#475569")
                    px(xx, 16, "#475569")
                for yy in range(11, 16):
                    px(4, yy, "#475569")
                    px(11, yy, "#475569")
            else:
                self._draw_back_hair(stamp, style_id, "down", 0)
                self._draw_hair(stamp, style_id, "down", 0)
            crop_rect = QRect(0, 0, 16, 23)

        elif part_kind == "face":
            self._draw_head(stamp, "down")
            self._draw_face(px, stamp, style_id, "down")
            crop_rect = QRect(2, 9, 12, 10)

        elif part_kind in ("torso", "outfit"):
            self._draw_torso(stamp, px, style_id, "down")
            self._draw_arms_walk(stamp, style_id, "down", 0)
            crop_rect = QRect(0, 17, 16, 9)

        elif part_kind == "pants":
            self._draw_legs_and_shoes(stamp, style_id, "oxfords", "down", 0)
            crop_rect = QRect(2, 23, 12, 7)

        elif part_kind == "shoes":
            self._draw_legs_and_shoes(stamp, "dress_pants", style_id, "right", 0)
            crop_rect = QRect(3, 25, 10, 6)

        elif part_kind == "accessory":
            if style_id == "none":
                for i in range(4, 12):
                    px(i, 9, "#64748b"); px(i, 16, "#64748b")
                    px(4, i + 5, "#64748b"); px(11, i + 5, "#64748b")
                    px(i, i + 5, "#ef4444")
                crop_rect = QRect(3, 8, 10, 10)
            else:
                self._draw_accessory(stamp, px, style_id, "down")
                crop_rect = QRect(1, 0, 14, 19)

        elif part_kind == "back_gear":
            if style_id == "none":
                for i in range(4, 12):
                    px(i, 14, "#64748b"); px(i, 21, "#64748b")
                    px(4, i + 10, "#64748b"); px(11, i + 10, "#64748b")
                    px(i, i + 10, "#ef4444")
                crop_rect = QRect(3, 13, 10, 10)
            elif style_id == "lanyard":
                self._draw_back_gear(stamp, px, style_id, "down", 0, behind=False)
                crop_rect = QRect(4, 17, 8, 7)
            else:
                self._draw_back_gear(stamp, px, style_id, "up", 0, behind=False)
                crop_rect = QRect(0, 10, 16, 16)

        min_x, min_y, max_x, max_y = self.GRID_W, self.GRID_H, -1, -1
        for yy in range(max(0, crop_rect.top()), min(self.GRID_H, crop_rect.bottom() + 1)):
            for xx in range(max(0, crop_rect.left()), min(self.GRID_W, crop_rect.right() + 1)):
                if canvas.pixelColor(xx, yy).alpha() > 0:
                    if xx < min_x:
                        min_x = xx
                    if yy < min_y:
                        min_y = yy
                    if xx > max_x:
                        max_x = xx
                    if yy > max_y:
                        max_y = yy

        if max_x >= min_x and max_y >= min_y:
            pad = 1
            crop_rect = QRect(
                max(0, min_x - pad),
                max(0, min_y - pad),
                min(self.GRID_W, max_x + pad + 1) - max(0, min_x - pad),
                min(self.GRID_H, max_y + pad + 1) - max(0, min_y - pad),
            )

        cropped = canvas.copy(crop_rect)
        out = QImage(box_size, box_size, QImage.Format.Format_ARGB32)
        out.fill(Qt.GlobalColor.transparent)

        scale_f = min((box_size - 8) / max(1, cropped.width()), (box_size - 8) / max(1, cropped.height()))
        int_scale = max(1, int(scale_f))
        target_w = cropped.width() * int_scale
        target_h = cropped.height() * int_scale
        if target_w < box_size * 0.50 and target_h < box_size * 0.50:
            target_w = max(1, int(cropped.width() * scale_f))
            target_h = max(1, int(cropped.height() * scale_f))

        scaled = cropped.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        p = QPainter(out)
        p.drawImage((box_size - scaled.width()) // 2, (box_size - scaled.height()) // 2, scaled)
        p.end()

        pix = QPixmap.fromImage(out)
        self._cache[key] = pix
        return pix

    # =========================================================================
    # MINIATURAS DE OFICINA DELEGADAS AL MOTOR PIXEL AGENTS OFFICE_SPRITES
    # =========================================================================
    def get_office_preview_pixmap(
        self,
        category: str,
        item_key: str,
        spec: Dict[str, Any],
        box_size: int = 52,
    ) -> QPixmap:
        from core.office_sprites import OFFICE_SPRITES
        return OFFICE_SPRITES.get_preview_pixmap(category, item_key, spec, box_size=box_size)


SPRITE_ENGINE = ChibiSpriteRenderer()
