# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Sprites Pixel Art RPG de Alto Detalle (36x48, 4 Direcciones)
Estética RPG indie de alto detalle (proporciones heroicas 3 cabezas, silueta atlética estilizada,
sombreado hue-shifted de 4 tonos por material, contornos oscuros estilizados #1b1118, capas modulares:
Peinado, Rostro, Torso, Pantalón, Botas, Accesorios de Cabeza y Equipo de Espalda/Armas).
  - 4 Direcciones reales: Adelante (down), Atrás (up), Izquierda 3/4 (left), Derecha 3/4 (right)
  - 4 Frames de caminata fluida con zancada, balanceo de brazos y movimiento de cabello/capa
  - Miniaturas aisladas por pieza para el Creador Visual de Personajes
"""

from typing import Dict, Any, Tuple, List, Optional
from PyQt6.QtCore import Qt, QRect, QPointF
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter, QPen

from core.customization import normalize_character


OUTLINE = "#1b1118"
SOFT_OUTLINE = "#3c2734"
WHITE = "#fff8f0"
WHITE_SH = "#d4ccc4"


def _hue_shift(hex_color: str, lum_factor: float, sat_delta: float = 0.0, warm_shadow: bool = False) -> str:
    """
    Sombreado artístico pixel-art (hue-shifting):
      - Sombras: desplaza el matiz hacia índigo/púrpura frío (o terracota cálido en piel/oro)
        y aumenta ligeramente la saturación para evitar grises apagados.
      - Luces: desplaza sutilmente hacia crema/dorado cálido.
    """
    c = QColor(hex_color or "#38bdf8")
    h, s, l, _ = c.getHslF()
    if h < 0:
        h = 0.65

    if lum_factor < 1.0:
        target_h = 0.025 if warm_shadow else 0.72
        dh = target_h - h
        if dh > 0.5:
            dh -= 1.0
        elif dh < -0.5:
            dh += 1.0
        shift_amt = min(0.18, (1.0 - lum_factor) * 0.36)
        h = (h + dh * shift_amt) % 1.0
        s = max(0.0, min(1.0, s + sat_delta + (1.0 - lum_factor) * 0.14))
        l = max(0.05, min(0.96, l * lum_factor))
    else:
        target_h = 0.13
        dh = target_h - h
        if dh > 0.5:
            dh -= 1.0
        elif dh < -0.5:
            dh += 1.0
        shift_amt = min(0.14, (lum_factor - 1.0) * 0.28)
        h = (h + dh * shift_amt) % 1.0
        s = max(0.0, min(1.0, s + sat_delta))
        l = max(0.07, min(0.97, l + (1.0 - l) * min(0.45, (lum_factor - 1.0) * 0.75)))

    out = QColor()
    out.setHslF(h, s, l, 1.0)
    return out.name()


def _build_palette(char: Dict[str, Any]) -> Dict[str, str]:
    skin = char.get("skin_color", "#f6c198")
    eye_col = char.get("eye_color", "#261a24")
    hair_col = char.get("hair_color", "#4b352a")
    top_col = char.get("top_color", "#585358")
    bot_col = char.get("bottom_color", "#2b3a55")
    shoe_col = char.get("shoe_color", "#3d261f")
    acc_col = char.get("accessory_color", "#d99b26")

    return {
        "O": OUTLINE,
        "o": SOFT_OUTLINE,
        "W": WHITE,
        "w": WHITE_SH,
        # Piel (4 tonos cálidos)
        "J": _hue_shift(skin, 1.18, -0.04, warm_shadow=True),
        "K": skin,
        "k": _hue_shift(skin, 0.80, 0.08, warm_shadow=True),
        "q": _hue_shift(skin, 0.58, 0.14, warm_shadow=True),
        # Cabello (4 tonos con brillo especular)
        "L": _hue_shift(hair_col, 1.32, -0.02),
        "H": hair_col,
        "h": _hue_shift(hair_col, 0.74, 0.06),
        "d": _hue_shift(hair_col, 0.52, 0.10),
        # Torso (4 tonos)
        "U": _hue_shift(top_col, 1.24, -0.02),
        "T": top_col,
        "t": _hue_shift(top_col, 0.75, 0.06),
        "v": _hue_shift(top_col, 0.54, 0.09),
        # Pantalón / Falda (4 tonos)
        "C": _hue_shift(bot_col, 1.24, -0.02),
        "B": bot_col,
        "b": _hue_shift(bot_col, 0.75, 0.06),
        "p": _hue_shift(bot_col, 0.52, 0.09),
        # Botas / Calzado (4 tonos)
        "X": _hue_shift(shoe_col, 1.28, -0.02),
        "Z": shoe_col,
        "z": _hue_shift(shoe_col, 0.72, 0.06),
        "x": _hue_shift(shoe_col, 0.48, 0.09),
        # Accesorio / Acento (4 tonos)
        "E": _hue_shift(acc_col, 1.34, 0.02),
        "A": acc_col,
        "a": _hue_shift(acc_col, 0.74, 0.06),
        "r": _hue_shift(acc_col, 0.52, 0.09),
        # Metales, Cuero, Oro, Ojos, Vidrio, Vaina
        "S": "#e2e8f0",
        "M": "#94a3b8",
        "m": "#526074",
        "D": "#2c3444",
        "Y": "#fde047",
        "y": "#d99b26",
        "g": "#8f5b14",
        "R": "#b06a3e",
        "N": "#784222",
        "n": "#452110",
        "P": "#f48fb1",
        "I": eye_col,
        "i": _hue_shift(eye_col, 1.35, 0.05),
        "G": "#38bdf8",
        "Q": "#e0f7ff",
        "V": "#881b25",
        "u": "#4d0e15",
    }


class ChibiSpriteRenderer:
    GRID_W = 36
    GRID_H = 48

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
            c.get("skin_color", "#f6c198"),
            c.get("eye_color", "#261a24"),
            c.get("face_style", "determined"),
            c.get("hair_style", "warrior_messy"),
            c.get("hair_color", "#4b352a"),
            c.get("torso_style", "adventurer_tunic"),
            c.get("top_color", "#585358"),
            c.get("pants_style", "adventurer_breeches"),
            c.get("bottom_color", "#2b3a55"),
            c.get("shoe_style", "leather_boots"),
            c.get("shoe_color", "#3d261f"),
            c.get("accessory", "none"),
            c.get("accessory_color", "#d99b26"),
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

    def _render_character(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        is_typing: bool,
        action: str = "idle",
        anim_frame: int = 0,
    ) -> QImage:
        if direction == "right":
            return self._render_character(char, "left", walk_frame, is_typing, action, anim_frame).mirrored(True, False)

        c = normalize_character(char)
        img = QImage(self.GRID_W, self.GRID_H, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        palette = _build_palette(c)

        is_seated = action in ("typing_seated", "browsing", "terminal", "relaxing")
        has_office_chair = action in ("typing_seated", "browsing", "terminal")
        seat_dy = 4 if is_seated else 0
        # Respiración / leve inclinación de cabeza según la acción
        head_extra_dy = 0
        if action == "idle" and anim_frame == 1:
            head_extra_dy = 1
        elif action in ("typing_seated", "terminal", "browsing") and anim_frame == 3:
            head_extra_dy = 1
        elif action == "reading" and anim_frame in (1, 2):
            head_extra_dy = 1

        px_raw, stamp_raw = self._make_helpers(img, palette, y_offset=0)
        px_body, stamp_body = self._make_helpers(img, palette, y_offset=seat_dy)
        px_head, stamp_head = self._make_helpers(img, palette, y_offset=seat_dy + head_extra_dy)

        face_style = c.get("face_style", "determined")
        # Parpadeo natural en idle (frame 3) y ojos cerrados disfrutando café (relaxing/coffee_standing frame 2)
        eff_face = face_style
        if (action == "idle" and anim_frame == 3) or (action in ("relaxing", "coffee_standing") and anim_frame == 2):
            eff_face = "sleepy"

        hair_style = c.get("hair_style", "warrior_messy")
        torso_style = c.get("torso_style", "adventurer_tunic")
        pants_style = c.get("pants_style", "adventurer_breeches")
        shoe_style = c.get("shoe_style", "leather_boots")
        acc = c.get("accessory", "none")
        back_gear = c.get("back_gear", "none")

        custom_arms = action in (
            "typing_seated", "reading", "thinking", "terminal",
            "browsing", "painting", "orchestrating", "relaxing", "coffee_standing"
        )

        # 0. SILLA DE OFICINA (CAPA TRASERA para vistas down y left)
        if has_office_chair and direction != "up":
            self._draw_office_chair(stamp_raw, direction, front_layer=False)

        # 1. EQUIPO DE ESPALDA (CAPA TRASERA)
        self._draw_back_gear_behind(stamp_body, px_body, back_gear, direction, walk_frame)

        # 2. CABELLO TRASERO
        self._draw_back_hair(stamp_head, hair_style, direction, walk_frame)

        # 3. BRAZO LEJANO EN PERFIL 3/4
        if direction == "left" and not custom_arms:
            self._draw_side_far_arm(stamp_body, torso_style, walk_frame, False)

        # 4. PIERNAS, PANTALÓN Y BOTAS (de pie o sentado con rodillas dobladas!)
        if is_seated:
            self._draw_seated_lower_body(stamp_raw, pants_style, shoe_style, direction)
        else:
            self._draw_lower_body(stamp_raw, px_raw, pants_style, shoe_style, direction, walk_frame)

        # 5. TORSO Y BRAZOS (estándar o animados por actividad)
        self._draw_torso(stamp_body, px_body, torso_style, direction, walk_frame)
        if custom_arms:
            self._draw_action_arms(stamp_body, px_body, torso_style, direction, action, anim_frame)
        else:
            self._draw_front_arms(stamp_body, torso_style, direction, walk_frame, False)

        # 6. EQUIPO EN PRIMER PLANO
        self._draw_back_gear_front(stamp_body, px_body, back_gear, direction, walk_frame)

        # 7. CABEZA ESCULPIDA
        self._draw_head(stamp_head, direction)

        # 8. ROSTRO Y EXPRESIÓN (con parpadeo natural / sorbo de café)
        self._draw_face(px_head, stamp_head, eff_face, direction)

        # 9. PEINADO ESCULPIDO
        self._draw_sculpted_hair(stamp_head, hair_style, direction, walk_frame)

        # 10. ACCESORIOS DE CABEZA
        self._draw_accessory(stamp_head, acc, direction)

        # 11. PROPS INTERACTIVOS DE LA ACTIVIDAD (Libro abierto, taza humeante, pincel, bombilla, holograma)
        if custom_arms:
            self._draw_action_props(stamp_body, px_body, direction, action, anim_frame)

        # 12. RESPALDO DE SILLA EN PRIMER PLANO (cuando el agente está sentado mirando hacia arriba al monitor!)
        if has_office_chair and direction == "up":
            self._draw_office_chair(stamp_raw, direction, front_layer=True)

        return img

    # =========================================================================
    # 1. CABEZA Y ROSTRO (36x48: Cabeza estilizada x=13..22, y=9..20)
    # =========================================================================
    def _draw_head(self, stamp, direction: str):
        if direction == "up":
            stamp(13, 9, [
                ".OOOOOOOO.",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKKKKKKKKO",
                "OKkKKKKkKO",
                ".OkkKKkkO.",
                "..OqqqqO..",
                "..OqKKqO..",
                "...OOOO...",
            ])
        elif direction == "down":
            stamp(13, 9, [
                ".OOOOOOOO.",
                "OKJKKKKJKO",
                "OKKKKKKKKO",
                "OKqqqqqqKO",
                "OKKKKKKKKO",
                "OKJKKKKJKO",
                "OKKKKKKKKO",
                "OKkKKKKkKO",
                ".OkKKKKkO.",
                "..OkkKkO..",
                "..OqqqqO..",
                "...OOOO...",
            ])
        else:
            # Perfil 3/4 heroico mirando a la izquierda (al espejar -> idéntico a Warrior Pack)
            stamp(12, 9, [
                "..OOOOOOO..",
                ".OKJKKKKkO.",
                ".OKKKKKKKkO",
                ".OKqqqqKKkO",
                "OOKKKKKKKkO",
                "OKJKKKKKKOO",
                ".OKKKKKKOkO",
                ".OKKKKKkOO.",
                "..OkKKkkO..",
                "...OqqqkO..",
                "...OqKKqO..",
                "....OOOO...",
            ])

    def _draw_face(self, px, stamp, face_style: str, direction: str):
        if direction == "up":
            return

        if direction == "down":
            # Sombra cálida bajo el flequillo
            for xx in range(14, 22):
                px(xx, 12, "k")

            # OJOS (Izquierdo x=14..15, Derecho x=20..21, y=14..15)
            if face_style == "sleepy":
                for xx in (14, 15, 20, 21):
                    px(xx, 14, "q")
                    px(xx, 15, "O")
            elif face_style == "cool":
                px(14, 13, "O"); px(15, 13, "O")
                px(14, 14, "W"); px(15, 14, "O")
                px(14, 15, "I"); px(15, 15, "O")
                px(20, 14, "O"); px(21, 15, "O")
            elif face_style == "starry":
                px(14, 14, "W"); px(15, 14, "Y")
                px(14, 15, "I"); px(15, 15, "O")
                px(20, 14, "Y"); px(21, 14, "W")
                px(20, 15, "O"); px(21, 15, "I")
            elif face_style in ("determined", "scarred"):
                px(14, 13, "O"); px(15, 13, "O")
                px(20, 13, "O"); px(21, 13, "O")
                px(14, 14, "W"); px(15, 14, "O")
                px(14, 15, "I"); px(15, 15, "O")
                px(20, 14, "O"); px(21, 14, "W")
                px(20, 15, "O"); px(21, 15, "I")
            else:
                px(14, 13, "q"); px(15, 13, "o")
                px(20, 13, "o"); px(21, 13, "q")
                px(14, 14, "W"); px(15, 14, "O")
                px(14, 15, "I"); px(15, 15, "I")
                px(20, 14, "O"); px(21, 14, "W")
                px(20, 15, "I"); px(21, 15, "I")

            # Cicatriz veterano
            if face_style == "scarred":
                px(20, 12, "q"); px(21, 13, "P"); px(21, 15, "q"); px(21, 16, "k")

            # Rubor suave
            if face_style in ("happy", "cat_smile", "starry"):
                px(14, 16, "P"); px(21, 16, "P")

            # BOCA / BARBA sutiles (sin barras negras gruesas)
            if face_style in ("smile", "happy", "starry"):
                px(16, 17, "q"); px(17, 17, "o"); px(18, 17, "o"); px(19, 17, "q")
            elif face_style in ("determined", "stoic", "focused", "scarred"):
                px(17, 17, "q"); px(18, 17, "o")
            elif face_style == "cool":
                px(16, 17, "o"); px(17, 17, "o"); px(18, 16, "q")
            elif face_style == "surprised":
                px(17, 17, "O"); px(18, 17, "o")
            elif face_style == "cat_smile":
                px(16, 17, "o"); px(17, 16, "q"); px(18, 16, "q"); px(19, 17, "o")
            elif face_style == "sleepy":
                px(17, 17, "q")
            elif face_style == "beard_smile":
                stamp(14, 16, [
                    ".OooooO.",
                    "OhWOOWhO",
                    "OhhhhhhO",
                    ".OddddO.",
                ])
        else:
            # PERFIL 3/4 IZQUIERDO (limpio y expresivo como Warrior Pack)
            for xx in range(13, 19):
                px(xx, 12, "k")

            if face_style == "sleepy":
                px(13, 14, "O")
                px(15, 14, "O"); px(16, 14, "O")
            elif face_style in ("determined", "scarred", "stoic"):
                # Ceja afilada + ojo con brillo blanco e iris oscuro
                px(13, 13, "O")
                px(15, 13, "O"); px(16, 13, "O")
                px(13, 14, "O"); px(13, 15, "I")
                px(15, 14, "O"); px(16, 14, "W")
                px(15, 15, "I"); px(16, 15, "k")
            elif face_style == "cool":
                px(13, 14, "o")
                px(15, 13, "O"); px(16, 13, "O")
                px(15, 14, "O"); px(16, 14, "W"); px(15, 15, "I")
            elif face_style == "starry":
                px(13, 14, "Y"); px(13, 15, "I")
                px(15, 14, "Y"); px(16, 14, "W"); px(15, 15, "I")
            else:
                px(13, 13, "q")
                px(15, 13, "o"); px(16, 13, "q")
                px(13, 14, "O"); px(13, 15, "I")
                px(15, 14, "O"); px(16, 14, "W")
                px(15, 15, "I"); px(16, 15, "I")

            if face_style == "scarred":
                px(16, 12, "q"); px(17, 14, "P"); px(17, 15, "q")
            if face_style in ("happy", "cat_smile", "starry"):
                px(17, 16, "P")

            # Boca en perfil 3/4: sutil y natural (como los guerreros de la referencia)
            if face_style == "beard_smile":
                stamp(12, 16, [
                    "OoooO",
                    "OWWhO",
                    "OhhhO",
                    ".OddO",
                ])
            elif face_style in ("determined", "stoic", "focused", "scarred"):
                px(13, 17, "q"); px(14, 17, "k")
            elif face_style == "surprised":
                px(13, 17, "O")
            else:
                px(13, 17, "q"); px(14, 17, "o"); px(15, 16, "k")

    # =========================================================================
    # 2. CABELLO TRASERO Y ESCULPIDO (24 PEINADOS DE ALTO DETALLE, 4 DIRECCIONES)
    # =========================================================================
    def _draw_back_hair(self, stamp, hair_style: str, direction: str, walk_frame: int):
        bob = -1 if walk_frame in (1, 3) else 0

        if hair_style == "warrior_messy":
            if direction == "left":
                stamp(19, 13 + bob, [
                    ".OOO..",
                    "OHhhO.",
                    "OhddhO",
                    ".OdddO",
                    "..OO..",
                ])
            elif direction == "down":
                stamp(11, 14 + bob, [
                    "OO..........OO",
                    "OhO........OhO",
                    ".OdO......OdO.",
                    "..O........O..",
                ])
        elif hair_style == "ronin_swept":
            if direction == "left":
                # 3 picos afilados barridos hacia atrás al viento (idéntico al samurái Warrior 2!)
                stamp(18, 6 + bob, [
                    "....OOOOOO..",
                    "..OOHLLHHOO.",
                    ".OHHHHHHhhOO",
                    "..OOHHHhhhO.",
                    ".OOHHhhhhOO.",
                    "..OOhhhddhOO",
                    "...OOhdddOO.",
                    "..OOhddOO...",
                    "...OOOO.....",
                ])
            elif direction == "down":
                stamp(9, 11 + bob, [
                    ".OO..............OO.",
                    "OHhO............OHhO",
                    "OhddO..........OddhO",
                    ".OdddO........OdddO.",
                    "..OOOO........OOOO..",
                ])
        elif hair_style == "fluffy_spiky":
            if direction == "left":
                stamp(19, 10 + bob, [
                    ".OOOO..",
                    "OHLLHO.",
                    "OHHHhhO",
                    ".OhhdO.",
                    "..OOO..",
                ])
        elif hair_style == "samurai_topknot":
            if direction == "left":
                stamp(20, 5 + bob, [
                    "..OOOO..",
                    ".OHLLHO.",
                    "OAaHHhhO",
                    ".OOhdddO",
                    "...OOOO.",
                ])
            else:
                stamp(14, 3 + bob, [
                    "..OOOO..",
                    ".OHLLHO.",
                    ".OHHHhO.",
                    "..OAAO..",
                ])
        elif hair_style == "ponytail":
            if direction == "left":
                stamp(19, 8 + bob, [
                    ".OAAO.....",
                    "OAEaHOOO..",
                    ".OAAHLLHO.",
                    "..OOHHHhhO",
                    "...OHHHhdO",
                    "...OHHhhdO",
                    "....OhhddO",
                    ".....OdddO",
                    "......OOO.",
                ])
            elif direction == "down":
                stamp(21, 8 + bob, [
                    ".OAAO...",
                    "OAEaHOO.",
                    ".OOHLLHO",
                    "..OHHHhO",
                    "..OHHHhO",
                    "..OHhhdO",
                    "...OhddO",
                    "....OOO.",
                ])
        elif hair_style == "long_straight" and direction in ("down", "left"):
            if direction == "down":
                stamp(10, 13, [
                    ".OO............OO.",
                    "OHHO..........OHHO",
                    "OHhO..........OhHO",
                    "OHhO..........OhHO",
                    "OhdO..........OdhO",
                    "OhdO..........OdhO",
                    "OhdO..........OdhO",
                    "OddO..........OddO",
                    ".OO............OO.",
                ])
            else:
                stamp(18, 13, [
                    ".OOOOO..",
                    "OHHHHHO.",
                    "OHHHHhO.",
                    "OHHHhhO.",
                    "OHHhhdO.",
                    "OHhhddO.",
                    "OhhhddO.",
                    ".OhdddO.",
                    "..OOOO..",
                ])
        elif hair_style == "long_wavy" and direction in ("down", "left"):
            if direction == "down":
                stamp(9, 12 + bob, [
                    "..OO............OO..",
                    ".OHHO..........OHHO.",
                    "OHLHO..........OHLHO",
                    "OHHhO..........OhHHO",
                    "OHhhO..........OhhHO",
                    "OhhdO..........OdhhO",
                    ".OhddO........OddhO.",
                    "OhdddO........OdddHO",
                    ".OdddO........OdddO.",
                    "..OOO..........OOO..",
                ])
            else:
                stamp(18, 12 + bob, [
                    ".OOOOOO..",
                    "OHLHHHHO.",
                    "OHHHHHhO.",
                    "OHHHHhhOO",
                    ".OHHHhhdO",
                    "OOHHhhddO",
                    "OHHhhdddO",
                    ".OhhhddO.",
                    "..OdddO..",
                    "...OOO...",
                ])
        elif hair_style == "wavy_bob" and direction in ("down", "left"):
            if direction == "down":
                stamp(10, 13 + bob, [
                    ".OO............OO.",
                    "OHHO..........OHHO",
                    "OHhO..........OhHO",
                    "OhdO..........OdhO",
                    ".OO............OO.",
                ])
            else:
                stamp(19, 13 + bob, [
                    ".OOOO..",
                    "OHHHhO.",
                    "OHHhhOO",
                    ".OhdddO",
                    "..OOOO.",
                ])
        elif hair_style == "wolf_cut":
            if direction == "down":
                stamp(9, 12 + bob, [
                    "..OO............OO..",
                    ".OHhO..........OhHO.",
                    "OHhdO..........OdhHO",
                    ".OhdO..........OdhO.",
                    "OOhdO..........OdhOO",
                    ".OddO..........OddO.",
                    "..OO............OO..",
                ])
            elif direction == "left":
                stamp(18, 12 + bob, [
                    ".OOOOO..",
                    "OHHHHhO.",
                    "OHHhhdOO",
                    ".OHhhddO",
                    "OOhdddOO",
                    "..OdddO.",
                    "...OOO..",
                ])
        elif hair_style == "pigtails":
            if direction == "down":
                stamp(6, 9 + bob, [
                    "..OOOO..............OOOO..",
                    ".OHLLHO............OHLLHO.",
                    "OOHHHhOAA........AAOhHHHOO",
                    "OHHHhdO............OdhHHHO",
                    "OHHhhdO............OdhhHHO",
                    "OhhhddO............OddhhhO",
                    ".OdddO..............OdddO.",
                    "..OOO................OOO..",
                ])
            elif direction == "left":
                stamp(19, 9 + bob, [
                    ".OAAO...",
                    "OOHLLHO.",
                    "OHHHHhhO",
                    "OHHHhhdO",
                    ".OHhhddO",
                    ".OhhhddO",
                    "..OdddO.",
                    "...OOO..",
                ])
        elif hair_style == "twin_buns":
            if direction == "down":
                stamp(8, 5 + bob, [
                    ".OOOO..........OOOO.",
                    "OHLLHO........OHLLHO",
                    "OHHHhO........OHHHhO",
                    "OOhhdO........OdhhOO",
                    ".OAAO..........OAAO.",
                ])
            else:
                stamp(18, 5 + bob, [
                    ".OOOO.",
                    "OHLLHO",
                    "OHHHhO",
                    "OOhhdO",
                    ".OAAO.",
                ])
        elif hair_style == "top_bun":
            stamp(14 if direction != "left" else 16, 4 + bob, [
                "..OOOO..",
                ".OHLLHO.",
                "OOHHHhOO",
                "OOAaaAOO",
                ".OOOOOO.",
            ])
        elif hair_style == "low_ponytail" and direction in ("down", "left"):
            if direction == "left":
                stamp(19, 15 + bob, [
                    ".OAAO..",
                    "OHHHhO.",
                    "OHHhhdO",
                    ".OhdddO",
                    "..OOOO.",
                ])
            else:
                stamp(20, 16 + bob, [
                    ".OAAO.",
                    "OHHHhO",
                    "OHhhdO",
                    ".OdddO",
                    "..OOO.",
                ])
        elif hair_style == "braids" and direction in ("down", "left"):
            if direction == "down":
                stamp(10, 15 + bob, [
                    "OOO..........OOO",
                    "OHhO........OhHO",
                    "OhHO........OHhO",
                    "OHhO........OhHO",
                    "OhHO........OHhO",
                    "OAAO........OAAO",
                    "OhdO........OdhO",
                    ".OO..........OO.",
                ])
            else:
                stamp(19, 15 + bob, [
                    "OOO.",
                    "OHhO",
                    "OhHO",
                    "OHhO",
                    "OhHO",
                    "OAAO",
                    "OhdO",
                    ".OO.",
                ])
        elif hair_style == "curly_afro":
            stamp(9, 4 + bob, [
                "....OOOOOOOOOO....",
                "..OOHLLHHHHLLHOO..",
                ".OHLHHHHHHHHHHLHO.",
                "OOHHHHHHHHHHHHHHOO",
                "OOHhHHHHHHHHHHhHOO",
                "OOhdHHHHHHHHHHdhOO",
                ".OOhhhhhhhhhhhhOO.",
                "..OddddddddddddO..",
                "...OOOOOOOOOOOO...",
            ])

    def _draw_sculpted_hair(self, stamp, hair_style: str, direction: str, walk_frame: int):
        if hair_style == "bald":
            return
        bob = -1 if walk_frame in (1, 3) else 0

        # ---- VISTA TRASERA ("up") — Cubre TODA la parte trasera del cráneo hasta la nuca (y=18)! ----
        if direction == "up":
            if hair_style == "flat_top":
                stamp(12, 5, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHHHHHO",
                    "OHHHHHHHHHHO",
                    "OHHHHHHHHHHO",
                    "OhhhhhhhhhhO",
                    "OhhhhhhhhhhO",
                    "OhhhhhhhhhhO",
                    "OhhhddddhhhO",
                    "OddddddddddO",
                    ".OddddddddO.",
                    "..OOOOOOOO..",
                ])
                return
            elif hair_style == "mohawk":
                stamp(15, 2, [
                    ".OOOO.",
                    "OHLLHO",
                    "OHHHHO",
                    "OHHHHO",
                    "OhHHhO",
                    "OhHHhO",
                    "OhHHhO",
                    "OdhhdO",
                    "OdhhdO",
                    "OddddO",
                    ".OdddO",
                    "..OOO.",
                ])
                return
            elif hair_style == "ronin_swept":
                stamp(10, 6, [
                    "...OOOOOOOOOO...",
                    ".OOHLLLLLLLLHOO.",
                    "OHLHHHHHHHHHHLHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHhHHHHHHHHHHhHO",
                    "OOhhhHHHHHHhhhOO",
                    ".OOhhhHHHHhhhOO.",
                    "..OOhdOOhhOdhO..",
                    "...OddOdddOddO..",
                    "....OO.OOO.OO...",
                ])
                return
            elif hair_style in ("warrior_messy", "fluffy_spiky", "anime_spiky", "spiky_messy"):
                stamp(10, 5, [
                    "..OO..OOOO..OO..",
                    ".OHHOOHLLHOOHHO.",
                    "OOHLLHHHHHHLLHOO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHhHHHHHHHHHHhHO",
                    "OOhhhHHHHHHhhhOO",
                    ".OOhhhHHHHhhhOO.",
                    "..OOhdOHhhOdhO..",
                    "...OddOdddOddO..",
                    "....OO.OOO.OO...",
                ])
                return

            # Base trasera completa y detallada hasta la nuca (y=6..18)
            stamp(11, 6, [
                "..OOOOOOOOOO..",
                ".OHLLLLLLLLHO.",
                "OHLHHHHHHHHHHO",
                "OHHHHHHHHHHHHO",
                "OHHHHHHHHHHHHO",
                "OHHHHHHHHHHHHO",
                "OHHHHHHHHHHHHO",
                "OHhHHHHHHHHhHO",
                "OhhhHHHHHHhhhO",
                "OhhhdHHHHdhhhO",
                ".OhdddHHdddho.",
                "..OdddOOdddO..",
                "...OOOOOOOO...",
            ])
            if hair_style in ("long_straight", "long_wavy", "wolf_cut"):
                stamp(11, 17, [
                    "OHHHHHHHHHHHHO",
                    "OHhHHHHHHHHhHO",
                    "OHhhHHHHHHhhHO",
                    "OhhhdHHHHdhhhO",
                    "OhhhddhhddhhhO",
                    ".OddddddddddO.",
                    "..OOOOOOOOOO..",
                ])
            elif hair_style == "ponytail":
                stamp(14, 8 + bob, [
                    "..OAAO..",
                    ".OAEaAO.",
                    "OOHLLHOO",
                    "OHHHHHHO",
                    "OHHHhhHO",
                    ".OHhhdO.",
                    "..OdddO.",
                    "...OOO..",
                ])
            elif hair_style == "low_ponytail":
                stamp(15, 16 + bob, [
                    ".OAAO.",
                    "OHHHHO",
                    "OHhhHO",
                    "OhdddO",
                    ".OOOO.",
                ])
            elif hair_style == "braids":
                stamp(11, 17 + bob, [
                    "OOO........OOO",
                    "OHhO......OhHO",
                    "OhHO......OHhO",
                    "OHhO......OhHO",
                    "OAAO......OAAO",
                    "OhdO......OdhO",
                    ".OO........OO.",
                ])
            return

        # ---- VISTA FRONTAL ("down") — Flequillos afilados y capas modernas ----
        if direction == "down":
            if hair_style == "warrior_messy":
                # Coronilla con pico + flequillo despeinado en mechones (Warrior 1!)
                stamp(11, 5, [
                    ".....OOOO.....",
                    "...OOHLLHOO...",
                    ".OOHLHHHHHHOO.",
                    "OOHHHHHHHHHHOO",
                    "OOHHHHHHHHHHOO",
                    "OOHHHHOOHHHHHO",
                    "OOHhHO.O.OHhHO",
                    "OOhO...O...OhO",
                    ".OdO.......OdO",
                    "..O.........O.",
                ])
            elif hair_style == "ronin_swept":
                # Raya elegante + picos laterales barridos (Warrior 2!)
                stamp(10, 6, [
                    "...OOOOOOOOOO...",
                    ".OOHLLLLLLLLHOO.",
                    "OHLHHHHHHHHHHLHO",
                    "OOHHHHHHOOHHHHOO",
                    "OOHHHHOO..OOHHHO",
                    "OOHhOO......OOhO",
                    ".OOhO........OhO",
                    "..OdO........OdO",
                ])
            elif hair_style == "fluffy_spiky":
                # Mechones esponjosos rubios con triángulo frontal (Warrior 3!)
                stamp(11, 6, [
                    "..OOO....OOO..",
                    ".OHLLHOOHLLHO.",
                    "OOHHHHHHHHHHOO",
                    "OOHHHHHHHHHHOO",
                    "OOHHHOOHHOHHHO",
                    "OOHhO.OHhO.OhO",
                    ".OhO...OO...O.",
                ])
            elif hair_style == "samurai_topknot":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHHHHHO",
                    "OHhOOooOOhHO",
                    "OhO......OhO",
                    "OdO......OdO",
                ])
            elif hair_style == "short_parted":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHHOHHHHO",
                    "OOHHHHOO.OOHHO",
                    "OOHhOO....OOhO",
                    ".OhO.......OhO",
                    "..O........OdO",
                ])
            elif hair_style == "ponytail":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHOHHHO",
                    "OHHHHHOO.OHO",
                    "OHhOO.....OO",
                    "OhO........O",
                ])
            elif hair_style == "long_straight":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHHOHHHHO",
                    "OOHHHHOO.OOHHO",
                    "OOHhO.....OhHO",
                    "OOhO.......OhO",
                    "OOdO.......OdO",
                ])
            elif hair_style == "long_wavy":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHOOHHHHO",
                    "OOHHHOO..OOHHO",
                    "OOHhO.....OhHO",
                    "OOhO.......OhO",
                ])
            elif hair_style == "wavy_bob":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHHOHHHHO",
                    "OOHHHHOO.OOHHO",
                    "OOHhO.....OhHO",
                    ".OOhO.....OhO.",
                ])
            elif hair_style == "wolf_cut":
                stamp(10, 6, [
                    "...OOOOOOOOOO...",
                    ".OOHLLHHHHLLHOO.",
                    "OHLHHHHHHHHHHLHO",
                    "OOHHHHOOOOHHHHHO",
                    "OOHHHOO..OOHHHHO",
                    "OOHhO......OhHOO",
                    ".OhO........OhO.",
                ])
            elif hair_style == "anime_spiky":
                stamp(9, 3, [
                    "....OO....OOO.....",
                    "...OHHO..OHLHO.OO.",
                    "OO.OHHHOOHLHHHOOHHO",
                    "HHOOHHHHHHHHHHHhHO",
                    ".OOHLHHHHHHHHHHLHO",
                    "OOHHHHHHOOHHOHHHHO",
                    ".OOHHHOO.OHO.OOHHO",
                    "..OOhO....O....OhO",
                ])
            elif hair_style == "curtain_bangs":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHOOHHHHO",
                    "OOHHHHO..OHHHO",
                    "OOHhHO....OHhO",
                    ".OOhO......OhO",
                ])
            elif hair_style == "spiky_messy":
                stamp(10, 4, [
                    "..OO..OOO..OO...",
                    ".OHHOOHLHOOHHO..",
                    "OOHHHLHHHOHHHHOO",
                    "OOHLHHHHHHHHHLHO",
                    "OOHHHOOHHHOHHHHO",
                    ".OOHhO..O..OOhHO",
                    "..OhO.......OhO.",
                ])
            elif hair_style == "pigtails":
                stamp(11, 7, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHHHHHHHHHHHHO",
                    "OOHHHHHOOHHHHO",
                    "OOHhOO....OOhO",
                    "OOhO.......OhO",
                ])
            elif hair_style == "twin_buns":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHHHHHO",
                    "OHHHHOOHHHHO",
                    "OHhOO...OOhO",
                ])
            elif hair_style == "top_bun":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHOHHHO",
                    "OHHHHOO..OHO",
                    "OHhO.....OhO",
                ])
            elif hair_style == "low_ponytail":
                stamp(11, 6, [
                    "..OOOOOOOOOO..",
                    ".OHLLLLLLLLHO.",
                    "OHLHHHHHHHHHHO",
                    "OOHHHHHHOHHHHO",
                    "OOHHHHOO.OOHHO",
                    "OOHhOO....OOhO",
                ])
            elif hair_style == "braids":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHOHHHHO",
                    "OHHHHOO.OHHO",
                    "OHhO.....OhO",
                    "OdO.......dO",
                ])
            elif hair_style == "side_shave":
                stamp(11, 6, [
                    "....OOOOOOOOO.",
                    "..OOHLLLLLLHOO",
                    ".OHLHHHHHHHHHO",
                    "OdhHOOHHHHHHHO",
                    "OdO....OOHHHHO",
                    "OdO......OOhHO",
                    ".O........OOhO",
                ])
            elif hair_style == "mohawk":
                stamp(14, 3, [
                    "..OOOO..",
                    ".OHLLHO.",
                    "OOHHHHOO",
                    "OOHHHHOO",
                    "OOhHHhOO",
                    "OhHHHHhO",
                    "OdOOOOdO",
                ])
            elif hair_style == "curly_afro":
                stamp(11, 6, [
                    ".OOOOOOOOOOOO.",
                    "OHLLHHHHHHLLHO",
                    "OHHHHHHHHHHHHO",
                    "OHhHOOOOOOhHHO",
                    "OOhO......OhOO",
                ])
            elif hair_style == "flat_top":
                stamp(12, 5, [
                    ".OOOOOOOOOO.",
                    "OHLLLLLLLLHO",
                    "OHHHHHHHHHHO",
                    "OHHHHHHHHHHO",
                    "OhhhhhhhhhhO",
                    "OhdOOOOOOdhO",
                    "OdO......OdO",
                ])
            elif hair_style == "receding":
                stamp(12, 7, [
                    ".OOOOOOOOOO.",
                    "OHHLLLLLLHHO",
                    "OHHOOOHOOHHO",
                    "OhO...O..OhO",
                    "OdO......OdO",
                ])
            return

        # ---- PERFIL 3/4 IZQUIERDO ("left") — Siluetas afiladas estilo Warrior Pack! ----
        if hair_style == "warrior_messy":
            # Coronilla afilada + flequillo cayendo hacia la frente + patilla larga (Warrior 1!)
            stamp(10, 5, [
                ".....OOOO......",
                "...OOHLLHOO....",
                "..OHLHHHHHHHO..",
                ".OOHHHHHHHHHHO.",
                "OOHHHHHHOHHHHhO",
                "OOHhOO.O.OHHHhO",
                ".OO......OOHhhO",
                ".........OHhhdO",
                "..........OdddO",
                "...........OOO.",
            ])
        elif hair_style == "ronin_swept":
            # Flequillo partido + volumen angular barrido atrás (Warrior 2!)
            stamp(10, 6, [
                "...OOOOOOOOO...",
                ".OOHLLLLLLLHO..",
                "OHLHHHHHHHHHHO.",
                "OOHHHHOOHHHHHhO",
                "OOHhOO..OHHHhhO",
                ".OO......OOHhdO",
                ".........OHhddO",
                "..........OdddO",
            ])
        elif hair_style == "fluffy_spiky":
            # Mechones rubios en pico al frente y nuca suave (Warrior 3!)
            stamp(10, 6, [
                "...OOO..OOO....",
                ".OOHLLHOOHLHO..",
                "OHLHHHHHHHHHHO.",
                "OOHHHHHHHHHHHhO",
                "OOHHOOHHOHHHhhO",
                ".OOhO.OO.OOHhdO",
                "..OO......OHddO",
                "...........OddO",
            ])
        elif hair_style == "flat_top":
            stamp(12, 5, [
                ".OOOOOOOOOO.",
                "OHLLLLLLLLHO",
                "OHHHHHHHHHHO",
                "OHHHHHHHHHHO",
                "OhhhhhhhhhhO",
                ".OOOOOOHHhhO",
                "......OOHhhO",
                ".......OOhdO",
                "........OOO.",
            ])
        elif hair_style == "mohawk":
            stamp(11, 3, [
                "...OOOOOOO..",
                ".OOHLLLLLHO.",
                "OOHHHHHHHHHO",
                "OOHHHHHHHHhO",
                ".OOhHHHHHhhO",
                "..OOdOOOhddO",
                "........OddO",
            ])
        elif hair_style == "anime_spiky":
            stamp(9, 3, [
                ".....OO...OOO...",
                "...OOHHO.OHLHO..",
                ".OOHHHHOOHLHHHOO",
                "OHLHHHHHHHHHHHHO",
                "OOHHHHHOOHHHHHhO",
                ".OOHhOO..OOHHHhO",
                "..OO......OOHhdO",
                "...........OdddO",
            ])
        elif hair_style == "side_shave":
            stamp(11, 6, [
                "..OOOOOOOOO.",
                ".OHLLLLLLLHO",
                "OHLHHHHHHHHhO",
                "OOHHHHOHHHHhO",
                "OOHhOO.OdddhO",
                ".OO.....OdddO",
            ])
        else:
            stamp(11, 6, [
                "..OOOOOOOOO..",
                ".OHLLLLLLLHO.",
                "OHLHHHHHHHHhO",
                "OOHHHHOHHHHhO",
                "OOHhOO.OHHHhO",
                ".OO....OOHhhO",
                "........OHhdO",
                ".........OddO",
                "..........OO.",
            ])

    # =========================================================================
    # 3. TORSO ATLÉTICO Y BRAZOS COMPLETOS (y=20..33 — CERO HUECOS EN CINTURA)
    # =========================================================================
    def _draw_torso(self, stamp, px, torso_style: str, direction: str, walk_frame: int):
        # Conector sólido de cintura/torso base (y=28..32) para garantizar CERO huecos con cualquier pantalón/falda
        if torso_style == "bare_warrior":
            c_rows_l = ["OOKKKKKkO", "OOKKKKKkO", "OOKkkkkqO", "OOqqqqqqO"]
            c_rows_d = ["OKKKKKkO", "OKKKKKkO", "OKkkkkqO", "OqqqqqqO"]
        elif torso_style == "knight_plate":
            c_rows_l = ["OOMMMMMmO", "OODDDDDDO", "OOMMmmMmO", "OOmmDDmmO"]
            c_rows_d = ["OMMMMMmO", "ODDDDDDO", "OMMmmMmO", "OmmDDmmO"]
        else:
            c_rows_l = ["OOTTTTTtO", "OOTTTTTvO", "OOTTTTTvO", "OOtttttvO"]
            c_rows_d = ["OTTTTTtO", "OTTTTTvO", "OTTTTTvO", "OtttttvO"]
        stamp(14, 28, c_rows_l if direction == "left" else c_rows_d)

        # ---- VISTA FRONTAL ("down") ----
        if direction == "down":
            if torso_style == "adventurer_tunic":
                # Túnica gris/marrón con correa diagonal, hebilla dorada, cinturón y faldón (Warrior 1!)
                stamp(13, 21, [
                    ".OTqKKqTO.",
                    "OUUNTTTUtt",
                    "OTTTNTTTtO",
                    "OTTTTYTTtO",
                    "OTTTTTNTtO",
                    "OTTTTTTNvO",
                    "OTTTTTTTvO",
                    "ONNNYYNNnO",
                    "OnnnRRnnnO",
                    "OTTTTtTTvO",
                    "OTTTTtTTvO",
                    ".OttvvttO.",
                ])
            elif torso_style == "samurai_haori":
                # Haori Ronin cruzado con solapa interior y fajín (Warrior 2!)
                stamp(13, 21, [
                    ".OTWqqWTO.",
                    "OUUTWWTUtO",
                    "OTTTTWTttO",
                    "OTTTTWTttO",
                    "OTTTWTtttO",
                    "OTTTWTttvO",
                    "OTTTTTttvO",
                    "OAAAAAAAaO",
                    "OaaaaAaaaO",
                    "OTTTvvTTvO",
                    ".OttvvttO.",
                ])
            elif torso_style == "bare_warrior":
                # Torso atlético desnudo (sin bordes negros duros en los hombros, Warrior 3!)
                stamp(13, 21, [
                    ".OJKKKKJO.",
                    "OKJKKKKJKk",
                    "OKJJkKJJkk",
                    "OKqqkKqqkk",
                    "OKKkKKkKkk",
                    "OKKqKKqKkk",
                    "OKKkKKkKkk",
                    "OKKqKKqKkk",
                    "OKkkkkkkkq",
                    ".OqqqqqqO.",
                    ".OqqqqqqO.",
                ])
            elif torso_style == "knight_plate":
                stamp(12, 20, [
                    "OOO....OOO",
                    "OSMOqqOMmO",
                    "OMSSSSSSmO",
                    "OMSMMYYMmO",
                    ".OSMMAAmO.",
                    ".OMMMMMmO.",
                    ".OMmMMmDO.",
                    ".ODDDYDDO.",
                    ".OMMmMMmO.",
                    ".OMmOOmDO.",
                    "..OOOOOO..",
                ])
            elif torso_style == "shinobi_wrap":
                stamp(13, 21, [
                    ".OTDqqDTO.",
                    "OUTDDTDUtO",
                    "OTTTDDTTtO",
                    "OTTTDDTTtO",
                    "OTTDDDDTvO",
                    "OTTDTTDTvO",
                    "OTTTTTTTvO",
                    "OAAAYYAAaO",
                    "OaaaaaaaaO",
                    "OTTTvvTTvO",
                    ".OttOOttO.",
                ])
            elif torso_style == "cyber_jacket":
                stamp(13, 20, [
                    ".OAEqqEAO.",
                    "OUUTMMTUtO",
                    "OETTMTTtEO",
                    "OTTTMTTTtO",
                    "OTTTMTTTtO",
                    "OETTMTTtEO",
                    "OTTTMMTTvO",
                    "ODDDAAADDO",
                    "OEETTTTEvO",
                    "ODDDTTDDDO",
                    ".OttttttO.",
                ])
            elif torso_style == "mage_robe":
                stamp(13, 21, [
                    ".OYTAATYO.",
                    "OUYTEEyUtO",
                    "OTTYTTyTtO",
                    "OTTTYTttvO",
                    "OTTTyTttvO",
                    "OTTTyTttvO",
                    "OTTTTTttvO",
                    "OyyyAAyyyO",
                    "OTTTyTttvO",
                    "OTTTyTttvO",
                    ".OttgttvO.",
                ])
            elif torso_style == "trench_coat":
                stamp(13, 21, [
                    ".OTWqqWTO.",
                    "OUtWMMWtUO",
                    "OTtWMMWtTO",
                    "OTTtMMtTtO",
                    "OTTTTTTTtO",
                    "OTTyTTyTtO",
                    "OTTTTTTTvO",
                    "ONNNYYNNnO",
                    "OTTTvvTTvO",
                    "OTTTvvTTvO",
                    "OTTTvvTTvO",
                    ".OttOOttO.",
                ])
            elif torso_style == "leather_vest":
                stamp(13, 21, [
                    ".OTWqqWTO.",
                    "OUtWWWWtUO",
                    "OTtWNNWtTO",
                    "OTtWYYWtTO",
                    "OTtWWWWtTO",
                    "OTtWNNWtTO",
                    "OTtWWWWtvO",
                    "ONNNYYNNnO",
                    "OTTTvvTTvO",
                    ".OttttttO.",
                ])
            elif torso_style == "suit_tie":
                stamp(13, 21, [
                    ".OTWAAWTO.",
                    "OUtWAAWtUO",
                    "OTtWAAWtTO",
                    "OTTtAAtTtO",
                    "OTTTWWTTtO",
                    "OTTTyTTTtO",
                    "OTTTTTTTvO",
                    "ODDDYYDDDO",
                    "OTTTvvTTvO",
                    ".OttOOttO.",
                ])
            elif torso_style == "hoodie":
                stamp(13, 21, [
                    ".OUtqqTUO.",
                    "OUtWTTWtUO",
                    "OTtWTTWtTO",
                    "OTtWTTWtTO",
                    "OTTTTTTTtO",
                    "OTtTTTTtTO",
                    "OTtTTTTtvO",
                    "OTttttttvO",
                    "ODDDDDDDDO",
                    "OtvvvvvvvO",
                ])
            elif torso_style == "vest_shirt":
                stamp(13, 21, [
                    ".OWWqqWWO.",
                    "OWtTWWtTWw",
                    "OWtTTTTtWw",
                    "OWtTTyTtWw",
                    "OWtTTTTtWw",
                    "OWtTTyTtWw",
                    "OWttttttWw",
                    "ONNNYYNNnO",
                    "OtvvvvvvvO",
                ])
            elif torso_style == "varsity_jacket":
                stamp(13, 21, [
                    ".OTWqqWTO.",
                    "OUtTWWtTUO",
                    "OTtTYWTtTO",
                    "OTtTWWtTtO",
                    "OTtTWWtTtO",
                    "OTtTWWtTvO",
                    "OTTTTTTTvO",
                    "OWWTAAWWWO",
                    "OtvvvvvvvO",
                ])
            elif torso_style == "lab_coat":
                stamp(13, 21, [
                    ".OWTqqTWO.",
                    "OWWTAAWTWw",
                    "OWWTTTTTWw",
                    "OWWTTTTTWw",
                    "OWWTTTTTWw",
                    "OWWTTTTTWw",
                    "OWWTTttTWw",
                    "OWWttvvTWw",
                    "OWwOvvOwWw",
                    "OWwO..OwWw",
                    ".OO....OO.",
                ])
            elif torso_style == "striped_sweater":
                stamp(13, 21, [
                    ".OTqKKqTO.",
                    "OUUTTTTUtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTvO",
                    "OtvvvvvvvO",
                ])
            elif torso_style == "overalls":
                stamp(13, 21, [
                    ".OTBqqBTO.",
                    "OTTBTTBTtO",
                    "OTTYBBYTtO",
                    "OTTBBBBTtO",
                    "OTTBBBBTvO",
                    "OTTBbbBTvO",
                    "OBBBBBBBpO",
                    "OBBBBBBBpO",
                    "OppppppppO",
                ])
            elif torso_style == "tank_top":
                stamp(13, 21, [
                    ".OKTqqTKO.",
                    "OKKTTTTKKk",
                    "OKUTTTTUkk",
                    "OKTTTTTTkk",
                    "OKTTTTTTkk",
                    "OKTTtttTkk",
                    "OKTTTTTTkk",
                    "OKTtttttkk",
                    ".OttttttO.",
                ])
            else:
                stamp(13, 21, [
                    ".OTqKKqTO.",
                    "OUUTTTTUtO",
                    "OTTTTTTTtO",
                    "OTTTTTTTtO",
                    "OTTtTTTtTO",
                    "OTTTTTTTvO",
                    "OTTTTTTTvO",
                    "ONNNYYNNnO",
                    "OtvvvvvvvO",
                ])
            return

        # ---- VISTA TRASERA ("up") ----
        if direction == "up":
            if torso_style == "bare_warrior":
                stamp(13, 21, [
                    ".OKKKKKKO.",
                    "OKJKKKKJKk",
                    "OKKKkKKKKk",
                    "OKKKkKKKKk",
                    "OKKkkkKKKk",
                    "OKKKkKKKKk",
                    "OKKKKKKKkk",
                    "OKkkkkkkkq",
                    ".OqqqqqqO.",
                    ".OqqqqqqO.",
                ])
            elif torso_style == "knight_plate":
                stamp(12, 20, [
                    "OOO....OOO",
                    "OSMOooOMmO",
                    "OMMMMMMMmO",
                    "OMMmmMMMmO",
                    ".OMmMMMmO.",
                    ".OMMMMMmO.",
                    ".OMmMMmDO.",
                    ".ODDDDDDO.",
                    ".OMMmMMmO.",
                ])
            elif torso_style == "lab_coat":
                stamp(13, 21, [
                    ".OWWWWWWO.",
                    "OWWWWWWWwO",
                    "OWWWWWWWwO",
                    "OWWWWWWWwO",
                    "OWWWwwWWwO",
                    "OWWWwwWWwO",
                    "OWWWWWWWwO",
                    "OWWwwwwWwO",
                    "OWwwOOwwWO",
                    ".OO....OO.",
                ])
            elif torso_style == "striped_sweater":
                stamp(13, 21, [
                    ".OTTTTTTO.",
                    "OTTTTTTTtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTtO",
                    "OWWWWWWWwO",
                    "OTTTTTTTvO",
                    "OtvvvvvvvO",
                ])
            elif torso_style == "adventurer_tunic":
                stamp(13, 21, [
                    ".OTTTTTTO.",
                    "OUUTTTNTtO",
                    "OTTTTNTttO",
                    "OTTTNTTTtO",
                    "OTTNTTTTtO",
                    "OTNTTTTTvO",
                    "OTTTTTTTvO",
                    "ONNNNNNNnO",
                    "OTTTTtTTvO",
                    "OTTTTtTTvO",
                    ".OttvvttO.",
                ])
            elif torso_style == "samurai_haori":
                stamp(13, 21, [
                    ".OTTTTTTO.",
                    "OUUTTTTUtO",
                    "OTTTWWTTtO",
                    "OTTTTTTTtO",
                    "OTTTTTTTtO",
                    "OTTTTTTTvO",
                    "OAAAAAAAaO",
                    "OaaaaAaaaO",
                    "OTTTvvTTvO",
                    ".OttvvttO.",
                ])
            elif torso_style == "cyber_jacket":
                stamp(13, 20, [
                    ".OAAAAAAO.",
                    "OUUTTTTUtO",
                    "OETTTTTtEO",
                    "OTTTAAAtTO",
                    "OTTTTTTTtO",
                    "OETTTTTtEO",
                    "OTTTTTTTvO",
                    "ODDDDDDDDO",
                    "OEETTTTEvO",
                    "ODDDTTDDDO",
                ])
            elif torso_style == "hoodie":
                stamp(13, 20, [
                    ".OUUUUUUO.",
                    "OUtTTTTtUO",
                    "OTtTTTTtTO",
                    "OTttttttTO",
                    "OTTTTTTTtO",
                    "OTTTTTTTtO",
                    "OTTTTTTTvO",
                    "ODDDDDDDDO",
                    "OtvvvvvvvO",
                ])
            else:
                stamp(13, 21, [
                    ".OTTTTTTO.",
                    "OUUTTTTUtO",
                    "OTTTTTTTtO",
                    "OTTTTTTTtO",
                    "OTTTtTTTtO",
                    "OTTTTTTTvO",
                    "OTTTTTTTvO",
                    "ONNNNNNNnO",
                    "OtvvvvvvvO",
                ])
            return

        # ---- PERFIL 3/4 IZQUIERDO ("left") — Silueta estilizada Warrior Pack! ----
        if torso_style == "adventurer_tunic":
            stamp(13, 21, [
                ".OTqqTTO.",
                "OUUTNTTTtO",
                "OTTTTNTTtO",
                "OTTTTYNTtO",
                "OTTTTTTNtO",
                "OTTTTTTTvO",
                "OTTTTTTTvO",
                "ONNYYNNNnO",
                "OnnRRnnnnO",
                "OTTTTtTTvO",
                "OTTTTtTTvO",
                ".OttvvttO.",
            ])
        elif torso_style == "samurai_haori":
            stamp(13, 21, [
                ".OWqqTTO.",
                "OWUTTTTTtO",
                "OTWTTTTTtO",
                "OTTWTTTTtO",
                "OTTTTTTTtO",
                "OTTTTTTTvO",
                "OTTTTTTTvO",
                "OAAAAAAAaO",
                "OaaaaaaaO.",
                "OTTTttTTvO",
                ".OttvvttO.",
            ])
        elif torso_style == "bare_warrior":
            # Torso desnudo con pectorales esculpidos, clavícula y abdominales (Warrior 3!)
            stamp(13, 21, [
                ".OJKKKJO.",
                "OKJKKKKJkO",
                "OKJJkKKJkO",
                "OKqqkKKqkO",
                "OKKkKKKkkO",
                "OKKqKKKkkO",
                "OKKkKKKkkO",
                "OKKqKKkkO.",
                "OKkkkkkkO.",
                ".OqqqqqqO.",
                ".OqqqqqqO.",
            ])
        elif torso_style == "knight_plate":
            stamp(13, 21, [
                ".OSMMmOO.",
                "OSMMMMMMmO",
                "OMSMYYMMmO",
                "OMMMMMMMmO",
                "OMmMMmMMDO",
                "OMMMMMMMDO",
                "ODDDYYDDDO",
                "OMMMmmMMmO",
                ".OmmOOmmO.",
            ])
        elif torso_style == "shinobi_wrap":
            stamp(13, 21, [
                ".ODqqTTO.",
                "OUTDDTTTtO",
                "OTTTDDTTtO",
                "OTTTDDTTtO",
                "OTTDTTDTvO",
                "OTTTTTTTvO",
                "OAAAYYAAaO",
                "OaaaaaaaO.",
                "OTTTttTTvO",
                ".OttvvttO.",
            ])
        elif torso_style == "cyber_jacket":
            stamp(13, 20, [
                ".OAqqAOO.",
                "OUETTTTTtO",
                "OTETTTTEtO",
                "OTETTTTTtO",
                "OTETTTTTtO",
                "OTETTTTEvO",
                "ODDDAAADDO",
                "OEETTTTEvO",
                "ODDDTTDDDO",
                ".OttttttO.",
            ])
        elif torso_style == "mage_robe":
            stamp(13, 21, [
                ".OYAAYOO.",
                "OUYEEYTTtO",
                "OTYTTyTTtO",
                "OTYTTyTTtO",
                "OTTTTTTTvO",
                "OTTTTTTTvO",
                "OyyyAAyyO.",
                "OTYTTyTTvO",
                "OTYTTyTTvO",
                ".OgttvvgO.",
            ])
        elif torso_style == "trench_coat":
            stamp(13, 21, [
                ".OWqqTTO.",
                "OUWMMTTTtO",
                "OTWMMTTTtO",
                "OTTTyTTTtO",
                "OTTTTTTTvO",
                "OTTTyTTTvO",
                "ONNYYNNNnO",
                "OTTTTtTTvO",
                "OTTTTtTTvO",
                "OTTTTtTTvO",
                ".OttvvttO.",
            ])
        elif torso_style == "leather_vest":
            stamp(13, 21, [
                ".OWqqTTO.",
                "OWWTNTTTtO",
                "OWWTYTTTtO",
                "OWWTTTTTtO",
                "OWWTNTTTtO",
                "OWWTTTTTvO",
                "ONNYYNNNnO",
                "OTTTTtTTvO",
                ".OttttttO.",
            ])
        elif torso_style == "suit_tie":
            stamp(13, 21, [
                ".OWAAWTO.",
                "OWATTtTTtO",
                "OWATTTTTtO",
                "OTTTTTTTtO",
                "OTTyTTTTvO",
                "OTTTTTTTvO",
                "ODDDYYDDDO",
                "OTTTTtTTvO",
                ".OttttttO.",
            ])
        elif torso_style == "hoodie":
            stamp(13, 21, [
                ".OUqqTTO.",
                "OUWTTTTTtO",
                "OTWTTTTTtO",
                "OTTTTTTTtO",
                "OTtTTTTtvO",
                "OTttttttvO",
                "ODDDDDDDO.",
                "OtvvvvvvO.",
            ])
        elif torso_style == "lab_coat":
            stamp(13, 21, [
                ".OTqqWWO.",
                "OTTAWWWWwO",
                "OTTTWWWWwO",
                "OTTTWWWWwO",
                "OTTTWWWWwO",
                "OTTTWWWWwO",
                "OTttWWWWwO",
                "OWwwWWWWwO",
                ".OwwOOwwO.",
            ])
        elif torso_style == "striped_sweater":
            stamp(13, 21, [
                ".OTqqTTO.",
                "OUUTTTTTtO",
                "OWWWWWWWwO",
                "OTTTTTTTtO",
                "OWWWWWWWwO",
                "OTTTTTTTtO",
                "OWWWWWWWwO",
                "OTTTTTTTvO",
                "OtvvvvvvO.",
            ])
        elif torso_style == "overalls":
            stamp(13, 21, [
                ".OBqqTTO.",
                "OTBTTTTTtO",
                "OTYBBTTTtO",
                "OTBBBBTTtO",
                "OTBBBBTTvO",
                "OBBBBBBBpO",
                "OBBBBBBBpO",
                "OpppppppO.",
            ])
        elif torso_style == "tank_top":
            stamp(13, 21, [
                ".OTqqKKO.",
                "OUTTTKKKkO",
                "OTTTTKKKkO",
                "OTTTTKKKkO",
                "OTTTTKKkkO",
                "OTtttKKkkO",
                "OttttkkkkO",
                ".OttttttO.",
            ])
        else:
            stamp(13, 21, [
                ".OTqqTTO.",
                "OUUTTTTTtO",
                "OTTTTTTTtO",
                "OTTTTTTTtO",
                "OTTtTTTTvO",
                "OTTTTTTTvO",
                "ONNYYNNNnO",
                "OtvvvvvvO.",
            ])

    def _arm_style_tokens(self, torso_style: str) -> Tuple[str, str, str]:
        """Devuelve (manga_superior, antebrazo/brazal, mano/guante)."""
        if torso_style in ("bare_warrior", "tank_top"):
            return ("K", "K", "K")
        if torso_style == "knight_plate":
            return ("M", "m", "D")
        if torso_style in ("vest_shirt", "lab_coat", "varsity_jacket"):
            return ("W", "w", "K")
        if torso_style in ("tshirt_casual", "overalls", "leather_vest"):
            return ("T", "K", "K")
        if torso_style == "adventurer_tunic":
            return ("T", "N", "n")  # Guantes y brazales de cuero como Warrior 1!
        if torso_style == "shinobi_wrap":
            return ("T", "D", "D")
        return ("T", "t", "K")

    def _draw_side_far_arm(self, stamp, torso_style: str, walk_frame: int, is_typing: bool):
        up_c, lo_c, hand_c = self._arm_style_tokens(torso_style)
        sh_c = "k" if up_c == "K" else ("m" if up_c == "M" else ("w" if up_c == "W" else "t"))
        if walk_frame == 1:
            dx, dy = -1, 0
        elif walk_frame == 3:
            dx, dy = 1, 0
        elif is_typing:
            dx, dy = -1, -1
        else:
            dx, dy = 0, 0

        if torso_style == "samurai_haori":
            # Manga ancha de haori extendida al frente hacia la katana (Warrior 2!)
            stamp(10 + dx, 22 + dy, [
                ".OOO.",
                "OUTtO",
                "OTTTtO",
                "OTttvO",
                "OtvvvO",
                ".OKkO.",
                "..OO..",
            ])
        else:
            # Brazo lejano natural hasta la cadera (11px de alto!)
            stamp(10 + dx, 22 + dy, [
                "..OO.",
                f".O{up_c}{sh_c}O",
                f".O{up_c}{sh_c}O",
                f".O{up_c}{sh_c}O",
                f"O{lo_c}{sh_c}O.",
                f"O{lo_c}{sh_c}O.",
                f"O{lo_c}{sh_c}O.",
                f"O{hand_c}kO.",
                f"O{hand_c}kO.",
                ".OO..",
            ])

    def _draw_front_arms(self, stamp, torso_style: str, direction: str, walk_frame: int, is_typing: bool):
        up_c, lo_c, hand_c = self._arm_style_tokens(torso_style)
        sh_c = "k" if up_c == "K" else ("m" if up_c == "M" else ("w" if up_c == "W" else "t"))

        if direction in ("down", "up"):
            l_dy = -1 if (walk_frame == 1 or is_typing) else (1 if walk_frame == 3 else 0)
            r_dy = 1 if (walk_frame == 1) else (-1 if (walk_frame == 3 or is_typing) else 0)

            if torso_style == "samurai_haori":
                arm_l = [
                    ".OOO",
                    "OUTO",
                    "OTtO",
                    "OTtO",
                    "OTvO",
                    "OTvO",
                    "OtvO",
                    "OKkO",
                    "OkqO",
                    ".OO.",
                ]
                arm_r = [
                    "OOO.",
                    "OTtO",
                    "OTtO",
                    "OTtO",
                    "OtvO",
                    "OtvO",
                    "OtvO",
                    "OkKO",
                    "OqkO",
                    ".OO.",
                ]
                stamp(10, 21 + l_dy, arm_l)
                stamp(22, 21 + r_dy, arm_r)
            elif torso_style == "bare_warrior":
                # Hombros desnudos continuos sin línea negra divisoria en la axila superior
                arm_l = [
                    ".OO.",
                    "OJKk",
                    "OKKk",
                    "OKkO",
                    "OKkO",
                    "OKkO",
                    "OKkO",
                    "OKkO",
                    "OkqO",
                    ".OO.",
                ]
                arm_r = [
                    ".OO.",
                    "kKJO",
                    "kKKO",
                    "OkKO",
                    "OkKO",
                    "OkKO",
                    "OkKO",
                    "OkKO",
                    "OqkO",
                    ".OO.",
                ]
                stamp(10, 21 + l_dy, arm_l)
                stamp(22, 21 + r_dy, arm_r)
            else:
                # Brazos proporcionados hasta la cadera (11px de largo!)
                arm_l = [
                    ".OO.",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O",
                    f"O{hand_c}kO",
                    f"O{hand_c}kO",
                    ".OO.",
                ]
                arm_r = [
                    ".OO.",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{lo_c}O",
                    f"O{sh_c}{lo_c}O",
                    f"O{sh_c}{lo_c}O",
                    f"Ok{hand_c}O",
                    f"Ok{hand_c}O",
                    ".OO.",
                ]
                stamp(10, 21 + l_dy, arm_l)
                stamp(22, 21 + r_dy, arm_r)
        else:
            # Brazo cercano en perfil 3/4 (11px de alto, doblado naturalmente hasta la cadera como Warrior Pack!)
            if walk_frame == 1:
                dx, dy = 1, -1
            elif walk_frame == 3:
                dx, dy = -1, 0
            elif is_typing:
                dx, dy = -1, -1
            else:
                dx, dy = 0, 0

            if torso_style == "samurai_haori":
                # Manga de haori sosteniendo la katana frente a la cintura (Warrior 2!)
                stamp(16 + dx, 22 + dy, [
                    "..OOOO.",
                    ".OOUTtO",
                    ".OOTTTtO",
                    "OOOTttvO",
                    "OKKOtttO",
                    "OKkOtvO.",
                    ".OO.OO..",
                ])
            elif torso_style == "bare_warrior":
                # Hombro continuo + bíceps y antebrazo musculoso hasta cadera (Warrior 3!)
                stamp(19 + dx, 21 + dy, [
                    ".OO..",
                    "JKKO.",
                    "KKkO.",
                    "OKkO.",
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    "OKKkO",
                    "OKkO.",
                    "OkqO.",
                    ".OO..",
                ])
            else:
                stamp(19 + dx, 21 + dy, [
                    ".OOO.",
                    f"O{up_c}{up_c}O.",
                    f"O{up_c}{sh_c}O.",
                    f"O{up_c}{sh_c}O.",
                    f".O{up_c}{sh_c}O",
                    f".O{lo_c}{sh_c}O",
                    f".O{lo_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O.",
                    f"O{hand_c}{hand_c}O.",
                    f"O{hand_c}kO.",
                    ".OO..",
                ])

    # =========================================================================
    # 4. PIERNAS, PANTALONES (12 ESTILOS) Y BOTAS (10 ESTILOS)
    # =========================================================================
    def _draw_lower_body(self, stamp, px, pants_style: str, shoe_style: str, direction: str, walk_frame: int):
        wide_drape = pants_style in ("samurai_hakama", "mage_skirt")
        tall_boot = shoe_style in (
            "leather_boots", "shin_wraps", "knight_greaves",
            "combat_boots", "cyber_boots", "elf_boots"
        )

        # 4A. Piernas/botas base (conectan sin hueco desde y=36 hasta el suelo y=45)
        self._draw_boots_base(stamp, shoe_style, direction, walk_frame, tall_boot and not wide_drape)

        # 4B. Pantalón / Falda / Hakama (desde y=31 cubriendo cadera y muslos)
        self._draw_pants(stamp, pants_style, direction, walk_frame)

        # 4C. Puño superior de bota alta sobre pantalones ceñidos/bombachos
        if tall_boot and not wide_drape:
            self._draw_boot_cuffs_overlay(stamp, shoe_style, direction, walk_frame)

    def _draw_boots_base(self, stamp, shoe_style: str, direction: str, walk_frame: int, is_tall: bool):
        if shoe_style == "knight_greaves":
            c1, c2, c3, trim = "S", "M", "m", "y"
        elif shoe_style == "tabi_sandals":
            c1, c2, c3, trim = "W", "w", "N", "n"
        elif shoe_style == "cyber_boots":
            c1, c2, c3, trim = "Z", "z", "x", "E"
        elif shoe_style == "sneakers":
            c1, c2, c3, trim = "X", "Z", "W", "W"
        elif shoe_style == "high_tops":
            c1, c2, c3, trim = "X", "Z", "W", "A"
        else:
            c1, c2, c3, trim = "X", "Z", "z", "x"

        if direction in ("down", "up"):
            l_up = -1 if walk_frame == 1 else 0
            r_up = -1 if walk_frame == 3 else 0

            def make_leg_boot(dy: int, is_left: bool) -> Tuple[int, int, List[str]]:
                bx = 13 if is_left else 19
                if is_tall:
                    rows = [
                        "OKkO",
                        "OKkO",
                        f"O{c1}{c2}O",
                        f"O{c2}{c3}O",
                        f"O{c1}{c2}O",
                        f"O{c2}{trim}O",
                        f"O{c2}{c3}O",
                        f"O{c3}{trim}O",
                        "OOOO",
                    ]
                    return bx, 37 + dy, rows
                elif shoe_style == "tabi_sandals":
                    rows = [
                        "OKkO",
                        "OKkO",
                        "OKkO",
                        "OKkO",
                        "OWwO",
                        "OWwO",
                        "ONnO",
                        "OOOO",
                    ]
                    return bx, 38 + dy, rows
                else:
                    rows = [
                        "OKkO",
                        "OKkO",
                        "OKkO",
                        "OKkO",
                        f"O{c1}{c2}O",
                        f"O{c2}{trim}O",
                        f"O{c3}{trim}O",
                        "OOOO",
                    ]
                    return bx, 38 + dy, rows

            lx, ly, lrows = make_leg_boot(l_up, True)
            rx, ry, rrows = make_leg_boot(r_up, False)
            stamp(lx, ly, lrows)
            stamp(rx, ry, rrows)
        else:
            # PERFIL 3/4 IZQUIERDO — Postura heroica compacta Warrior Pack!
            if walk_frame == 1:
                fx, bx = 11, 20
            elif walk_frame == 3:
                fx, bx = 19, 12
            else:
                fx, bx = 13, 18

            if is_tall:
                boot_f = [
                    ".OKkO",
                    ".OKkO",
                    f".O{c1}{c2}O",
                    f".O{c2}{c3}O",
                    f".O{c1}{c2}O",
                    f".O{c2}{trim}O",
                    f"O{c1}{c2}{c3}O",
                    f"O{c3}{c3}{trim}O",
                    "OOOOO",
                ]
                boot_b = [
                    ".OkqO",
                    ".OkqO",
                    f".O{c2}{c3}O",
                    f".O{c2}{c3}O",
                    f".O{c2}{c3}O",
                    f".O{c3}{trim}O",
                    f"O{c2}{c3}{c3}O",
                    f"O{c3}{c3}{trim}O",
                    "OOOOO",
                ]
            elif shoe_style == "tabi_sandals":
                boot_f = [
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    ".OWwO",
                    ".OWwO",
                    "OWWwO",
                    "ONNnO",
                    "OOOOO",
                ]
                boot_b = [
                    ".OkqO",
                    ".OkqO",
                    ".OkqO",
                    ".OkqO",
                    ".OwwO",
                    ".OwwO",
                    "OwwwO",
                    "ONnnO",
                    "OOOOO",
                ]
            else:
                boot_f = [
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    ".OKkO",
                    f".O{c1}{c2}O",
                    f"O{c1}{c2}{trim}O",
                    f"O{c3}{c3}{trim}O",
                    "OOOOO",
                ]
                boot_b = [
                    ".OkqO",
                    ".OkqO",
                    ".OkqO",
                    ".OkqO",
                    ".OkqO",
                    f".O{c2}{c3}O",
                    f"O{c2}{c3}{trim}O",
                    f"O{c3}{c3}{trim}O",
                    "OOOOO",
                ]

            stamp(bx, 37, boot_b)
            stamp(fx, 37, boot_f)

    def _draw_boot_cuffs_overlay(self, stamp, shoe_style: str, direction: str, walk_frame: int):
        if shoe_style == "knight_greaves":
            cuff = ["OSYMO", "OMmmO"]
        elif shoe_style == "cyber_boots":
            cuff = ["OEAAO", "OZZzO"]
        elif shoe_style == "shin_wraps":
            cuff = ["OXZXO", "OZZzO"]
        elif shoe_style == "combat_boots":
            cuff = ["OZWZO", "OZZzO"]
        elif shoe_style == "elf_boots":
            cuff = ["OXYXO", "OZZzO"]
        else:
            cuff = ["OXXXO", "OZZzO"]

        if direction in ("down", "up"):
            l_up = -1 if walk_frame == 1 else 0
            r_up = -1 if walk_frame == 3 else 0
            stamp(12, 38 + l_up, cuff)
            stamp(18, 38 + r_up, cuff)
        else:
            if walk_frame == 1:
                fx, bx = 11, 20
            elif walk_frame == 3:
                fx, bx = 19, 12
            else:
                fx, bx = 13, 18
            stamp(bx, 38, cuff)
            stamp(fx, 38, cuff)

    def _draw_pants(self, stamp, pants_style: str, direction: str, walk_frame: int):
        # ---- VISTA FRONTAL Y TRASERA ("down", "up") ----
        if direction in ("down", "up"):
            l_up = -1 if walk_frame == 1 else 0
            r_up = -1 if walk_frame == 3 else 0

            if pants_style == "samurai_hakama":
                sway = 1 if walk_frame == 1 else (-1 if walk_frame == 3 else 0)
                stamp(11 + sway // 2, 31, [
                    ".OOBBBBBBBBBOO.",
                    "OOCBbCBBbCBBbpO",
                    "OOCBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCbbpCbbpCbbppO",
                    "OObppObppObpppO",
                    ".OOOOOOOOOOOOO.",
                ])
                return

            if pants_style == "mage_skirt":
                stamp(11, 31, [
                    ".OOBBBBBBBBBOO.",
                    "OOCBBBBBBBBbbpO",
                    "OOCBBbBBBbBBbpO",
                    "OCBBBbBBBbBBbpO",
                    "OCBBBbBBBbBBbpO",
                    "OCBBBbBBBbBBbpO",
                    "OCBBBbBBBbBBbpO",
                    "OCBBBbBBBbBBbpO",
                    "OCyyyyyyyyyyypO",
                    "OOBbbbbbbbbbppO",
                    ".OOOOOOOOOOOOO.",
                ])
                return

            if pants_style == "pleated_skirt":
                stamp(11, 31, [
                    ".OOBBBBBBBBBOO.",
                    "OOCBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCBBbCBBbCBBbpO",
                    "OCbbpCbbpCbbppO",
                    ".OOOOOOOOOOOOO.",
                ])
                return

            if pants_style == "kusazuri_plates":
                stamp(12, 31, [
                    "OOBBBBBBBBOO",
                    "OOBBbOObbBBO",
                    "OOBbO..ObbBO",
                    "OOBbO..ObbBO",
                    "OOppO..OppBO",
                    ".OOO....OOO.",
                ])
                stamp(10, 31, [
                    "OOAAO......OAAOO",
                    "OAYaO......OaYAO",
                    "OAAaO......OaAAO",
                    "OArrO......OrrAO",
                    ".OOO........OOO.",
                ])
                return

            if pants_style == "martial_baggy":
                stamp(11, 31, [
                    ".OOBBBBBBBBOO.",
                    "OOCBBBBBBBBbpO",
                    "OOCBBbOObBBbpO",
                    "OOCBBbOObBBbpO",
                    "OOCBBbOObBBbpO",
                    "OOCbbpOOppbppO",
                    ".OObppOOppbpO.",
                    "..OOOO..OOOO..",
                ])
                return

            if pants_style == "adventurer_breeches":
                stamp(11, 31, [
                    ".OOBBBBBBBBOO.",
                    "OOCBBBBBBBBbpO",
                    "OOCBBbOObBBbpO",
                    "OOCBBbOObBBbpO",
                    "OOCbbpOObbppO.",
                    ".OOppO..OppO..",
                    "..OOO....OOO..",
                ])
                return

            if pants_style == "battle_shorts":
                stamp(12, 31, [
                    "OOBBBBBBBBOO",
                    "OOCBBbOObBbpO",
                    "OOCbbpOObbppO",
                    "OOAAAO..OAAAO",
                    ".OOOO....OOOO",
                ])
                return

            stamp(12, 31, [
                "OOBBBBBBBBOO",
                "OOCBBBBBBbpO",
                "OOCBBbOObBpO",
            ])
            if pants_style == "armored_cuisses":
                leg_l = ["OSMmO", "OMmmO", "OSYmO", "OMmmO", "OmmDO", "OOOOO"]
                leg_r = ["OMmSO", "OmmMO", "OmYSO", "OmmMO", "ODmmO", "OOOOO"]
            elif pants_style == "cyber_pants":
                leg_l = ["OEBBp", "OCBBp", "OEBBp", "OBbbp", "OEbpp", "OOOOO"]
                leg_r = ["OBBpE", "OBBpC", "OBBpE", "ObbpB", "ObppE", "OOOOO"]
            elif pants_style == "cargo_tactical":
                leg_l = ["OCBBp", "ObbBp", "ObbBp", "OCBBp", "OBbpp", "OOOOO"]
                leg_r = ["OBBpC", "OBbbp", "OBbbp", "OBBpC", "Obbpp", "OOOOO"]
            else:
                leg_l = ["OCBBp", "OCBBp", "OBBBp", "OBbbp", "OBbpp", "OOOOO"]
                leg_r = ["OBBpC", "OBBpC", "OBBBp", "ObbpB", "ObppB", "OOOOO"]

            stamp(12, 34 + l_up, leg_l)
            stamp(18, 34 + r_up, leg_r)
            return

        # ---- PERFIL 3/4 IZQUIERDO ("left") — Estética Warrior Pack! ----
        if walk_frame == 1:
            fx, bx = 11, 20
        elif walk_frame == 3:
            fx, bx = 19, 12
        else:
            fx, bx = 13, 18

        if pants_style == "samurai_hakama":
            stamp(10, 31, [
                "..OOBBBBBBBBBOO..",
                ".OOCBbCBBbCBBbpO.",
                ".OCBBbCBBbCBBbpO.",
                "OOCBBbCBBbCBBbpOO",
                "OCBBBbCBBbCBBbbpO",
                "OCBBBbCBBbCBBbbpO",
                "OCBBBbCBBbCBBbbpO",
                "OCBBBbCBBbCBBbbpO",
                "OCBBBbCBBbCBBbbpO",
                "OCbbbpCbbpCbbbppO",
                "OObpppObppObbpppO",
                ".OOOOOOOOOOOOOOO.",
            ])
            return

        if pants_style == "mage_skirt":
            stamp(10, 31, [
                "..OOBBBBBBBBBOO..",
                ".OOCBBBBBBBBbbpO.",
                ".OCBBbBBBBbBBbpO.",
                "OOCBBbBBBBbBBbpOO",
                "OCBBBbBBBBbBBbbpO",
                "OCBBBbBBBBbBBbbpO",
                "OCBBBbBBBBbBBbbpO",
                "OCBBBbBBBBbBBbbpO",
                "OCyyyyyyyyyyyyppO",
                "OOBbbbbbbbbbbbppO",
                ".OOOOOOOOOOOOOOO.",
            ])
            return

        if pants_style == "pleated_skirt":
            stamp(11, 31, [
                "..OOBBBBBBBOO..",
                ".OOCBbCBBbCBpO.",
                "OOCBBbCBBbCBbpO",
                "OCBBBbCBBbCBbpO",
                "OCbbbpCbbpCbppO",
                ".OOOOOOOOOOOOO.",
            ])
            return

        if pants_style == "martial_baggy":
            stamp(12, 31, [
                ".OOBBBBBBBOO.",
                "OOCBBBBBBBbpO",
                "OOCBBBbBBBbpO",
                "OOCBBbOOBBbpO",
                "OOCBbpOOBbppO",
                "OOCbpO.ObbppO",
                ".OObO...ObpO.",
                "..OO.....OO..",
            ])
            return

        if pants_style == "adventurer_breeches":
            stamp(12, 31, [
                ".OOBBBBBBBOO.",
                "OOCBBBBBBBbpO",
                "OOCBBbOOBBbpO",
                "OOCBBbOOBBbpO",
                "OOCbpOOBbbpO.",
                ".OObO..ObpO..",
                "..OO....OO...",
            ])
            return

        if pants_style == "battle_shorts":
            stamp(12, 31, [
                ".OOBBBBBBBBOO.",
                "OOCBBBBBBBBbpO",
                "OOCBBbOOBBBbpO",
                "OOAAAOO.OAAAO.",
                ".OOOO....OOOO.",
            ])
            return

        if pants_style == "kusazuri_plates":
            stamp(12, 31, [
                ".OOBBBBBBBBOO.",
                "OOCBBbOOBBBbpO",
                "OOCBBbOOBBBbpO",
                ".OObpO..ObpO..",
            ])
            stamp(14, 31, [
                "OOAAAO.",
                "OAYAaO.",
                "OAAAaO.",
                "OArrrO.",
                ".OOOO..",
            ])
            return

        stamp(13, 31, [
            "OOBBBBBBBBO",
            "OOCBBBBBBpO",
        ])
        if pants_style == "armored_cuisses":
            leg = ["OSMmO", "OMmmO", "OSYmO", "OMmmO", "OmmDO", ".OOO."]
        elif pants_style == "cyber_pants":
            leg = ["OEBBp", "OCBBp", "OEBBp", "OBbbp", "OEbpp", ".OOO."]
        elif pants_style == "cargo_tactical":
            leg = ["OCBBp", "ObbBp", "ObbBp", "OCBBp", "OBbpp", ".OOO."]
        else:
            leg = ["OCBBp", "OCBBp", "OBBBp", "OBbbp", "OBbpp", ".OOO."]
        stamp(bx, 33, leg)
        stamp(fx, 33, leg)

    # =========================================================================
    # 5. EQUIPO DE ESPALDA / ARMAS / CAPAS (12 DISEÑOS — CAPA TRASERA + FRONTAL)
    # =========================================================================
    def _draw_back_gear_behind(self, stamp, px, gear: str, direction: str, walk_frame: int):
        if gear == "none":
            return
        sway = 1 if walk_frame == 1 else (-1 if walk_frame == 3 else 0)

        if gear == "back_sword":
            if direction == "left":
                # Empuñadura y guarda metálica limpia detrás del hombro (Warrior 1!)
                stamp(20, 14, [
                    "....OO.",
                    "...ODDO",
                    "..ODDO.",
                    ".OOSMO.",
                    "OSMMmO.",
                    ".OOMmO.",
                    "..OmmO.",
                ])
                stamp(10, 34, [
                    "..OO",
                    ".ONnO",
                    "ONnO",
                    "OO..",
                ])
            elif direction == "down":
                stamp(21, 13, [
                    "...OO.",
                    "..ODDO",
                    ".ODDO.",
                    "OSMMO.",
                    ".OMmO.",
                    "..OO..",
                ])
                stamp(10, 33, [
                    "..OO",
                    ".ONnO",
                    "ONnO",
                    "OO..",
                ])
            else:
                stamp(11, 14, [
                    "...........OO.",
                    "..........ODDO",
                    ".........ODDO.",
                    "........OSMMO.",
                    ".......OSMMmO.",
                    "......ONNNnO..",
                    ".....ONNNnO...",
                    "....ONNNnO....",
                    "...ONNNnO.....",
                    "..ONNNnO......",
                    ".ONNNnO.......",
                    "ONNNnO........",
                    ".OOOO.........",
                ])

        elif gear == "back_spear":
            # Lanza larga diagonal con punta dorada brillante (Warrior 3!)
            if direction == "left":
                for i in range(36):
                    sx = 25 - int(i * 0.48)
                    sy = 5 + i
                    px(sx, sy, "O")
                    px(sx + 1, sy, "N" if i % 2 == 0 else "n")
                    px(sx + 2, sy, "O")
                stamp(6, 40, [
                    "..OO..",
                    ".OYYO.",
                    "OYYyO.",
                    "OYygO.",
                    "OygO..",
                    ".OO...",
                ])
            elif direction == "down":
                for i in range(34):
                    sx = 26 - int(i * 0.10)
                    sy = 4 + i
                    px(sx, sy, "O")
                    px(sx + 1, sy, "N")
                    px(sx + 2, sy, "O")
                stamp(24, 1, [
                    "..OO..",
                    ".OYYO.",
                    "OYYyO.",
                    "OYygO.",
                    ".OggO.",
                ])
            else:
                for i in range(34):
                    sx = 24 - int(i * 0.36)
                    sy = 5 + i
                    px(sx, sy, "O")
                    px(sx + 1, sy, "N")
                    px(sx + 2, sy, "O")
                stamp(23, 2, [
                    "..OO..",
                    ".OYYO.",
                    "OYYyO.",
                    "OYygO.",
                    ".OggO.",
                ])

        elif gear == "dual_katanas":
            if direction in ("down", "up"):
                stamp(8, 12, [
                    "OO................OO",
                    "ODDO............ODDO",
                    ".ODDO..........ODDO.",
                    "..OYYO........OYYO..",
                    "...ONnO......OnNO...",
                    "....ONnO....OnNO....",
                ])
                if direction == "up":
                    stamp(11, 18, [
                        "ONnO........OnNO",
                        ".ONnO......OnNO.",
                        "..ONnO....OnNO..",
                        "...ONnO..OnNO...",
                        "....ONnOOnNO....",
                        ".....OOnnOO.....",
                        "....OnNOONnO....",
                        "...OnNO..ONnO...",
                        "..OnNO....ONnO..",
                    ])
            else:
                stamp(20, 12, [
                    "...OO.OO.",
                    "..ODDODDO",
                    ".ODDODDO.",
                    "OYYOYYO..",
                    ".ONnOnO..",
                ])

        elif gear == "hero_cape":
            if direction == "left":
                stamp(20 + sway, 20, [
                    "OOOO...",
                    "OAAaO..",
                    "OAAAaO.",
                    "OAAAaO.",
                    "OAAaaOO",
                    "OAAaaaO",
                    "OAAaaaO",
                    "OAAaarO",
                    "OAaaarO",
                    "OAaaarrO",
                    "OaaarrrO",
                    "OarrrrrO",
                    ".OOOOOO.",
                ])
            elif direction == "down":
                stamp(8, 21, [
                    ".OO..............OO.",
                    "OAaO............OaAO",
                    "OAaO............OaAO",
                    "OAaO............OaAO",
                    "OAaO............OaAO",
                    "OarO............OraO",
                    "OarO............OraO",
                    "OarO............OraO",
                    "OarO............OraO",
                    "OrrO............OrrO",
                    ".OO..............OO.",
                ])
            else:
                stamp(9, 20, [
                    "..OOOOOOOOOOOOOO..",
                    ".OOEEAAAAAAAAEEOO.",
                    "OOAAAAAAAAAAAAAAOO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAAaAAAAAAAAAAaAAO",
                    "OAaaAAAAAAAAAAaaAO",
                    "OArrAAAAAAAAAArrAO",
                    "OrrrrrrrrrrrrrrrrO",
                    ".OOOOOOOOOOOOOOOO.",
                ])

        elif gear == "scarf_flowing":
            if direction == "left":
                stamp(20, 20 + abs(sway), [
                    ".OOOOOO..",
                    "OAEAAAAOO",
                    ".OAAaaaAO",
                    "..OAAaarO",
                    "...OaarrrO",
                    "....OrrrO.",
                    ".....OOO..",
                ])
            elif direction == "up":
                stamp(13, 20, [
                    "OOOOOOOOOO",
                    "OAEAAAAAAO",
                    ".OAAaaAAO.",
                    "..OAAarO..",
                    "..OaarO...",
                    "...OOO....",
                ])

        elif gear == "adventurer_pack":
            if direction == "left":
                stamp(20, 21, [
                    "OOOOO.",
                    "ORRRRO",
                    "ONNNnO",
                    "ONYNnO",
                    "ONNNnO",
                    "ONnnnO",
                    "ONnnnO",
                    "OnnnnO",
                    "OOOOO.",
                ])
            elif direction == "up":
                stamp(12, 21, [
                    ".OOOOOOOOOO.",
                    "ORRRRRRRRRRO",
                    "ONNNNNNNNNnO",
                    "ONNYNNNNYNnO",
                    "ONNNNNNNNNnO",
                    "ONNnnnnnnNnO",
                    "ONNnnnnnnNnO",
                    "ONnnnnnnnnnO",
                    ".OOOOOOOOOO.",
                ])
            else:
                stamp(10, 22, [
                    "OO............OO",
                    "ONO..........ONO",
                    "OnO..........OnO",
                    ".OO..........OO.",
                ])

        elif gear == "wizard_staff":
            sx0 = 24 if direction != "up" else 11
            stamp(sx0, 6, [
                ".OOOO.",
                "OGQQGO",
                "OGGGGO",
                ".OYYO.",
                "..ONO.",
                "..ONO.",
                "..ONO.",
                "..ONO.",
                "..OnO.",
                "..OnO.",
                "..OnO.",
                "..OnO.",
                "..OnO.",
                "..OnO.",
                "..OO..",
            ])

        elif gear == "bow_quiver":
            if direction == "left":
                stamp(20, 14, [
                    ".OWO..",
                    "OWWOO.",
                    ".ONnO.",
                    "OORnO.",
                    "OROnO.",
                    "OROnO.",
                    "OROnO.",
                    ".ORnO.",
                    "..OO..",
                ])
            else:
                stamp(10, 13, [
                    "..OWOWO.........",
                    ".OWWWWOO........",
                    "..ONNNnO....OO..",
                    "...ONNnO...ORRO.",
                    "....ONnO....ORO.",
                    ".....ONnO....ORO",
                    "......ONnO...ORO",
                    ".......OO...ORRO",
                    "............OO..",
                ])

        elif gear == "round_shield":
            if direction == "up":
                stamp(12, 20, [
                    "...OOOOOO...",
                    ".OOMMMMMMOO.",
                    "OOMRNNNNRMOO",
                    "OMRNYYYYNRMO",
                    "OMRNYEEYNRMO",
                    "OMRNYYYYNRMO",
                    "OOMRNNNNRMOO",
                    ".OOMmmmmMOO.",
                    "...OOOOOO...",
                ])
            elif direction == "left":
                stamp(20, 20, [
                    "OOO.",
                    "OMMO",
                    "OMYO",
                    "OMYO",
                    "OMMO",
                    "OmmO",
                    "OOO.",
                ])

        elif gear == "cyber_wings":
            if direction in ("down", "up"):
                stamp(2, 16 + sway, [
                    "OOOO........................OOOO",
                    "OEEEOO....................OOEEEO",
                    ".OEEAAOO................OOAAEEO.",
                    "..OEEAAAOO............OOAAAEEO..",
                    "...OEEAAAAO..........OAAAAEEO...",
                    "....OAAaaAO..........OAaaAAO....",
                    ".....OOaaO............OaaOO.....",
                    ".......OO..............OO.......",
                ])
            else:
                stamp(20, 15 + sway, [
                    "....OOOOOO",
                    "..OOEEEEEO",
                    ".OEEAAAAEO",
                    "OEEAAAaaO.",
                    "OAAaaaaO..",
                    ".OaaarrO..",
                    "..OOOOO...",
                ])

    def _draw_back_gear_front(self, stamp, px, gear: str, direction: str, walk_frame: int):
        if gear == "waist_katana":
            # Katana delgada y elegante cruzando la cintura (Warrior 2!)
            if direction == "left":
                for i in range(21):
                    kx = 8 + i
                    ky = 27 + int(i * 0.42)
                    px(kx, ky, "O")
                    px(kx, ky + 1, "V" if i > 4 else "D")
                    px(kx, ky + 2, "O")
                px(12, 28, "Y"); px(12, 29, "y"); px(12, 30, "O")
                px(28, 35, "Y"); px(28, 36, "y")
            elif direction == "down":
                for i in range(18):
                    kx = 9 + i
                    ky = 28 + int(i * 0.35)
                    px(kx, ky, "O")
                    px(kx, ky + 1, "V" if i > 4 else "D")
                    px(kx, ky + 2, "O")
                px(13, 29, "Y"); px(13, 30, "y")

        elif gear == "scarf_flowing" and direction in ("down", "left"):
            stamp(13 if direction == "down" else 12, 20, [
                "OOOOOOOOOO",
                "OAEAAAAAAO",
                ".OaaaaaaO.",
                "..OOOOOO..",
            ])

        elif gear == "hero_cape" and direction == "down":
            stamp(13, 20, [
                "OYO....OYO",
                ".OAAAAAAO.",
            ])

    # =========================================================================
    # 6. ACCESORIOS DE CABEZA Y ROSTRO (20 ESTILOS DETALLADOS)
    # =========================================================================
    def _draw_accessory(self, stamp, acc: str, direction: str):
        if acc == "none":
            return

        if acc == "headband":
            if direction == "left":
                stamp(11, 10, [
                    ".OOOOOOOOOOO.",
                    "OAAEEAAAAAAAO",
                    ".OOOOOOOOOOO.",
                ])
                stamp(22, 11, [
                    "OOO.",
                    "OAAO",
                    ".OaO",
                    "..O.",
                ])
            else:
                stamp(12, 10, [
                    ".OOOOOOOOOO.",
                    "OAAEEAAAAAAO",
                    ".OOOOOOOOOO.",
                ])
                if direction == "up":
                    stamp(16, 12, [
                        "OAAO",
                        "OaOa",
                        "O..O",
                    ])

        elif acc == "eyepatch" and direction != "up":
            if direction == "down":
                stamp(13, 13, [
                    "OOOOOoooo.",
                    ".ODDDDO...",
                    "..OOOO....",
                ])
            else:
                stamp(12, 13, [
                    "..OOOOooo",
                    "..ODDDDO.",
                    "...OOOO..",
                ])

        elif acc == "scarf_mask" and direction != "up":
            if direction == "down":
                stamp(13, 16, [
                    ".OOOOOOOO.",
                    "OAEAAAAAAO",
                    "OAAaaaaAAO",
                    ".OrrrrrrO.",
                    "..OOOOOO..",
                ])
            else:
                stamp(12, 16, [
                    ".OOOOOOOO.",
                    "OAEAAAAAAaO",
                    "OAAaaaaaarO",
                    ".OrrrrrrrO.",
                    "..OOOOOOO..",
                ])

        elif acc == "oni_mask":
            if direction == "left":
                stamp(18, 7, [
                    ".O....O.",
                    "OWOOOOwO",
                    "OWWWWWWO",
                    "OWAWWAWO",
                    ".OWWWWO.",
                    "..OOOO..",
                ])
            elif direction == "down":
                stamp(19, 6, [
                    ".O....O.",
                    "OWOOOOwO",
                    "OWWWWWWO",
                    "OWAWWAWO",
                    ".OWWWWO.",
                    "..OOOO..",
                ])

        elif acc == "glasses" and direction != "up":
            if direction == "down":
                stamp(13, 13, [
                    "OOOO..OOOO",
                    "OGQGOOGQGO",
                    "OGGGO.OGGO",
                    "OOOO..OOOO",
                ])
            else:
                stamp(12, 13, [
                    "OOO.OOOO",
                    "OGQOOGQO",
                    "OGGOOGGO",
                    "OOO.OOOO",
                ])

        elif acc == "sunglasses" and direction != "up":
            if direction == "down":
                stamp(13, 13, [
                    "OOOO..OOOO",
                    "ODWDOODWDO",
                    "ODDDODDDDO",
                    ".OOO..OOO.",
                ])
            else:
                stamp(12, 13, [
                    "OOO.OOOO",
                    "ODWODWDO",
                    "ODDODDDO",
                    ".OO..OOO",
                ])

        elif acc == "cyber_visor" and direction != "up":
            stamp(12 if direction == "left" else 13, 13, [
                ".OOOOOOOO.",
                "OAAEEEEAAO",
                "OAAAAAAAAO",
                ".OOOOOOOO.",
            ])

        elif acc == "headphones":
            if direction in ("down", "up"):
                stamp(10, 6, [
                    "...OOOOOOOOOO...",
                    ".OOAAAAAAAAAAOO.",
                    "OO............OO",
                    "OO............OO",
                    "OO............OO",
                    "OAAO........OAAO",
                    "OAEAO......OAEAO",
                    "OAAO........OAAO",
                    ".OO..........OO.",
                ])
            else:
                stamp(16, 6, [
                    ".OOOO.",
                    "OAAAO.",
                    ".OAAO.",
                    ".OAAO.",
                    ".OAAO.",
                    "OAAAAO",
                    "OAEAAO",
                    "OAAAAO",
                    ".OOOO.",
                ])

        elif acc == "aviator_goggles":
            stamp(12, 9, [
                "OOOOOOOOOOOO",
                "OGQGOOOOGQGO",
                "OGGGOOOOGGGO",
                "OOOOOOOOOOOO",
            ])

        elif acc == "baseball_cap":
            if direction == "down":
                stamp(11, 5, [
                    "..OOOOOOOOOO..",
                    ".OAAAAAAAAAAO.",
                    "OAAEEAAAAAAAAO",
                    "OAAAAAAAAAAAAO",
                    "OOOOOOOOOOOOOO",
                    ".OaaaaaaaaaaO.",
                ])
            else:
                stamp(9, 5, [
                    "....OOOOOOOOOO.",
                    "..OOAAAAAAAAAAO",
                    ".OOAAEEAAAAAAAO",
                    "OOOAAAAAAAAAAAO",
                    "OOOOOOOOOOOOOOO",
                ])

        elif acc == "beanie":
            stamp(11, 4, [
                "...OOOOOOOO...",
                ".OOAAAAAAAAOO.",
                "OOAAEEAAAAAAOO",
                "OAAAAAAAAAAAAO",
                "OaaAAaaAAaaAAO",
                "OOOOOOOOOOOOOO",
            ])

        elif acc == "fedora":
            stamp(9, 5, [
                "....OOOOOOOOOO....",
                "...OODDDDDDDDOO...",
                "..OODDDDDDDDDDOO..",
                "..OOAAAAAAAAAAOO..",
                "OOOOOOOOOOOOOOOOOO",
            ])

        elif acc == "straw_hat":
            stamp(6, 4, [
                ".........OOOOOO.........",
                ".......OOYYYYYYOO.......",
                ".....OOYYYYyyyyYYOO.....",
                "...OOYYYYAAyyAAYYYYOO...",
                ".OOyyyyyyyyyyyyyyyyyyOO.",
                "OOOOOOOOOOOOOOOOOOOOOOOO",
            ])

        elif acc == "witch_hat":
            stamp(8, 2, [
                "........OOOOO.......",
                ".......OODDDDOO.....",
                "......OODDDDDDOO....",
                ".....OODDDDDDDDO....",
                "....OODDDDDDDDOO....",
                "...OOAAAYYYAAAAOO...",
                "OOOOOOOOOOOOOOOOOOOO",
            ])

        elif acc == "top_hat":
            stamp(10, 2, [
                "..OOOOOOOOOOOO..",
                "..OODDDDDDDDOO..",
                "..OODDDDDDDDOO..",
                "..OODDDDDDDDOO..",
                "..OODDDDDDDDOO..",
                "..OOAAAAAAAAOO..",
                "OOOOOOOOOOOOOOOO",
            ])

        elif acc == "viking_helmet":
            stamp(7, 3, [
                ".OO..................OO.",
                "OWWO....OOOOOOOO....OWWO",
                "OWWOO..OOSMMMMMOO..OOWWO",
                ".OOWWOOSMMMMMMMMSOOWWOO.",
                "..OOOOOMMMMMMMMMMOOOOO..",
                ".....OOMmYYYYYYmMOO.....",
                ".....OOOOOOOOOOOOOO.....",
            ])

        elif acc == "crown":
            stamp(11, 3, [
                ".OO....OO....OO.",
                "OYYO..OYYO..OYYO",
                "OYYOOOOYYOOOOYYO",
                "OYYYYAAYYAAYYYYO",
                "OyyyyyyyyyyyyyyO",
                ".OOOOOOOOOOOOOO.",
            ])

        elif acc == "cat_ears":
            stamp(10, 4, [
                ".OO..........OO.",
                "OAAO........OAAO",
                "OAPAO......OAPAO",
                "OAPPAO....OAPPAO",
                ".OOOO......OOOO.",
            ])

        elif acc == "halo":
            stamp(12, 2, [
                "..OOOOOOOO..",
                ".OOYYYYYYOO.",
                "OYYO....OYYO",
                ".OOYYYYYYOO.",
                "..OOOOOOOO..",
            ])

    # =========================================================================
    # 7. POSTURA SENTADA, SILLAS Y ANIMACIONES INTERACTIVAS POR ESTACIÓN
    # =========================================================================
    def _draw_office_chair(self, stamp, direction: str, front_layer: bool):
        """Dibuja la silla ergonómica de oficina integrada con el personaje sentado."""
        if direction == "up" and front_layer:
            # Respaldo ergonómico + pistón y ruedas visibles detrás del personaje sentado mirando al monitor
            stamp(11, 29, [
                "..OOOOOOOOOO..",
                ".OOMMMMMMMMOO.",
                "OOMDDDDDDDDmOO",
                "OMDDDDGDDDDDmO",
                "OMDDDDDDDDDDmO",
                "OMDmmmmmmmmDmO",
                ".OODDDDDDDDOO.",
                "..OOOOOOOOOO..",
                ".....OMMO.....",
                ".....OmmO.....",
                "..OOMMMMMMOO..",
                ".OO..OmmO..OO.",
            ])
        elif direction == "down" and not front_layer:
            # Respaldo detrás del torso/hombros + ruedas abajo
            stamp(11, 24, [
                "..OOOOOOOOOO..",
                ".OOMMMMMMMMOO.",
                "OOMDDDDDDDDmOO",
                "OMDDDDDDDDDDmO",
                "OMDDDDDDDDDDmO",
                "OMDDDDDDDDDDmO",
                "OMDDDDDDDDDDmO",
                "OMDmmmmmmmmDmO",
                "OODDDDDDDDDDOO",
                "..OOOOOOOOOO..",
            ])
            stamp(12, 41, [
                ".....OMMO.....",
                "..OOMMMMMMOO..",
                ".OO..OmmO..OO.",
            ])
        elif direction == "left" and not front_layer:
            # Perfil 3/4 de silla giratoria (respaldo atrás a la derecha, asiento y ruedas abajo)
            stamp(13, 25, [
                ".......OOOO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                "......OMmDO.",
                ".OOOOOOMmDO.",
                "OMMMMMMMMMO.",
                ".OODDDDDDO..",
                "....OMMO....",
                "....OmmO....",
                ".OOMMMMMMOO.",
                "OO..OmmO..OO",
            ])

    def _draw_seated_lower_body(self, stamp, pants_style: str, shoe_style: str, direction: str):
        """Piernas y botas con rodillas flexionadas en postura sentada (y=35..44)."""
        if shoe_style == "knight_greaves":
            c1, c2, c3 = "S", "M", "m"
        elif shoe_style == "tabi_sandals":
            c1, c2, c3 = "W", "w", "N"
        elif shoe_style == "cyber_boots":
            c1, c2, c3 = "E", "Z", "x"
        elif shoe_style in ("sneakers", "high_tops"):
            c1, c2, c3 = "X", "Z", "W"
        else:
            c1, c2, c3 = "X", "Z", "z"

        if direction in ("down", "up"):
            if pants_style in ("samurai_hakama", "mage_skirt"):
                stamp(10, 35, [
                    ".OOBBBBBBBBBBOO.",
                    "OOCBbCBBbCBBbBpO",
                    "OCBBbCBBbCBBbbpO",
                    "OCBBbCBBbCBBbbpO",
                    "OCbbpCbbpCbbbppO",
                    ".OOOOOOOOOOOOOO.",
                ])
                stamp(12, 41, [
                    f"O{c1}{c2}O....O{c1}{c2}O",
                    f"O{c2}{c3}O....O{c2}{c3}O",
                    "OOOO....OOOO",
                ])
            elif pants_style == "pleated_skirt":
                stamp(10, 35, [
                    ".OOBBBBBBBBBBOO.",
                    "OOCBbCBBbCBBbBpO",
                    "OCbbpCbbpCbbbppO",
                    ".OOOOOOOOOOOOOO.",
                ])
                stamp(12, 39, [
                    "OKkO....OKkO",
                    f"O{c1}{c2}O....O{c1}{c2}O",
                    f"O{c2}{c3}O....O{c2}{c3}O",
                    "OOOO....OOOO",
                ])
            else:
                # Muslos flexionados hacia adelante con rodillas claras y pies descansando abajo
                stamp(11, 35, [
                    ".OOBBBBBBBBOO.",
                    "OOCBBbOObBBbpO",
                    "OOCBBbOObBBbpO",
                    "OObbppOObbpppO",
                    ".OOOO....OOOO.",
                ])
                stamp(12, 40, [
                    f"O{c1}{c2}O....O{c1}{c2}O",
                    f"O{c2}{c3}O....O{c2}{c3}O",
                    f"O{c3}{c3}O....O{c3}{c3}O",
                    "OOOO....OOOO",
                ])
        else:
            # Perfil 3/4 sentado: muslos proyectados a la izquierda y pantorrillas colgando!
            if pants_style in ("samurai_hakama", "mage_skirt"):
                stamp(8, 35, [
                    "...OOBBBBBBBBOO.",
                    ".OOCBBBBBBBBBbpO",
                    "OOCBBbCBBbCBBbpO",
                    "OCBBBbCBBbCBBbpO",
                    "OCbbbpCbbpCbbppO",
                    ".OOOOO.OOOOOOOO.",
                ])
                stamp(8, 41, [
                    f".O{c1}{c2}O.",
                    f"O{c1}{c2}{c3}O",
                    "OOOOO",
                ])
            else:
                stamp(8, 35, [
                    "...OOBBBBBBBBO.",
                    ".OOCBBBBBBBBbpO",
                    "OOCBBBBBBbBBbpO",
                    "OOCBBbOOOObbppO",
                    ".OOBbO....OOOO.",
                    ".OOppO.........",
                ])
                stamp(8, 40, [
                    f".O{c1}{c2}O.",
                    f".O{c2}{c3}O.",
                    f"O{c1}{c2}{c3}O",
                    "OOOOO",
                ])

    def _draw_action_arms(self, stamp, px, torso_style: str, direction: str, action: str, anim_frame: int):
        """Brazos animados personalizados para cada actividad (escribir, leer, pensar, pintar, café, etc.)."""
        up_c, lo_c, hand_c = self._arm_style_tokens(torso_style)
        sh_c = "k" if up_c == "K" else ("m" if up_c == "M" else ("w" if up_c == "W" else "t"))

        # ---- 1. TECLEANDO SENTADO / TERMINAL / NAVEGANDO ----
        if action in ("typing_seated", "terminal", "browsing"):
            l_tap = -1 if anim_frame in (0, 3) else 0
            r_tap = -1 if anim_frame in (1, 2) else 0
            if action == "browsing":
                l_tap = 0
                r_tap = -1 if anim_frame in (1, 3) else 0
            if direction == "up":
                # Brazos adelantados tecleando sobre el escritorio delante del agente
                stamp(9, 21 + l_tap, [
                    ".OO.",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O",
                    f"O{hand_c}kO",
                    ".OO.",
                ])
                stamp(23, 21 + r_tap, [
                    ".OO.",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{up_c}O",
                    f"O{sh_c}{lo_c}O",
                    f"Ok{hand_c}O",
                    ".OO.",
                ])
            elif direction == "down":
                stamp(10, 21 + l_tap, [
                    ".OO..",
                    f"O{up_c}{sh_c}O.",
                    f"O{up_c}{sh_c}O.",
                    f".O{lo_c}{hand_c}O",
                    ".OOO.",
                ])
                stamp(21, 21 + r_tap, [
                    "..OO.",
                    f".O{sh_c}{up_c}O",
                    f".O{sh_c}{up_c}O",
                    f"O{hand_c}{lo_c}O.",
                    ".OOO.",
                ])
            else:
                # Perfil 3/4: ambos brazos extendidos hacia la izquierda tecleando!
                stamp(10, 24 + l_tap, [
                    ".OOOO.",
                    f"O{hand_c}{lo_c}{up_c}O",
                    ".OOOO.",
                ])
                stamp(12, 22 + r_tap, [
                    "......OOO.",
                    f".....O{up_c}{up_c}O",
                    f"....O{up_c}{sh_c}O.",
                    f".OOO{lo_c}{sh_c}O.",
                    f"O{hand_c}{hand_c}{lo_c}OO..",
                    ".OOOO.....",
                ])

        # ---- 2. LEYENDO LIBRO / BUSCANDO EN BIBLIOTECA ----
        elif action == "reading":
            if direction == "up":
                if anim_frame in (0, 1):
                    # Brazo derecho estirado ARRIBA buscando libros en el estante!
                    reach_dx = 0 if anim_frame == 0 else -1
                    stamp(10, 21, [
                        ".OO.",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{hand_c}kO",
                        ".OO.",
                    ])
                    stamp(22 + reach_dx, 14, [
                        ".OO.",
                        f"O{hand_c}kO",
                        f"O{lo_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        ".OO.",
                    ])
                else:
                    # Sosteniendo libro abierto visible a la derecha pasando página!
                    stamp(10, 21, [
                        ".OO.",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{lo_c}{hand_c}O",
                        ".OO.",
                    ])
                    stamp(22, 21, [
                        ".OO...",
                        f"O{sh_c}{up_c}O..",
                        f"O{sh_c}{up_c}{lo_c}O.",
                        f".OO{hand_c}O",
                        "...OO.",
                    ])
            elif direction == "down":
                flip_dy = -1 if anim_frame == 2 else 0
                stamp(10, 21, [
                    ".OO..",
                    f"O{up_c}{sh_c}O.",
                    f"O{up_c}{sh_c}O.",
                    f".O{lo_c}{hand_c}O",
                    "..OO.",
                ])
                stamp(21, 21 + flip_dy, [
                    "..OO.",
                    f".O{sh_c}{up_c}O",
                    f".O{sh_c}{up_c}O",
                    f"O{hand_c}{lo_c}O.",
                    ".OO..",
                ])
            else:
                flip_dy = -1 if anim_frame == 2 else 0
                stamp(13, 22 + flip_dy, [
                    ".....OOO.",
                    f"....O{up_c}{up_c}O",
                    f"...O{up_c}{sh_c}O.",
                    f"OO{lo_c}{lo_c}O..",
                    f"O{hand_c}{hand_c}OO...",
                    ".OO......",
                ])

        # ---- 3. PENSANDO / ESCRIBIENDO EN PIZARRA ----
        elif action == "thinking":
            if anim_frame in (0, 1):
                # Pose de pensador: mano en el mentón / cadera + bombilla flotante
                if direction == "down":
                    stamp(10, 21, [
                        ".OO.",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{hand_c}kO",
                        ".OO.",
                    ])
                    stamp(20, 18, [
                        ".OO...",
                        f"O{hand_c}kO..",
                        f".O{lo_c}{up_c}O.",
                        f"..O{sh_c}{up_c}O",
                        f"..O{sh_c}{up_c}O",
                        "...OO.",
                    ])
                elif direction == "up":
                    stamp(10, 21, [
                        ".OO.",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{hand_c}kO",
                        ".OO.",
                    ])
                    stamp(22, 20, [
                        "..OO",
                        f".O{hand_c}O",
                        f"O{sh_c}{lo_c}O",
                        f"O{sh_c}{up_c}O",
                        f"O{sh_c}{up_c}O",
                        ".OO.",
                    ])
                else:
                    stamp(14, 18, [
                        "OO....",
                        f"O{hand_c}O...",
                        f".O{lo_c}O..",
                        f"..O{up_c}{up_c}O",
                        f"...O{up_c}{sh_c}O",
                        "....OO",
                    ])
            else:
                # Escribiendo / señalando arriba en la pizarra con plumón!
                sweep = 0 if anim_frame == 2 else 2
                if direction in ("up", "down"):
                    stamp(10, 21, [
                        ".OO.",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{hand_c}kO",
                        ".OO.",
                    ])
                    stamp(22 + sweep, 14, [
                        ".OO.",
                        f"O{hand_c}kO",
                        f"O{lo_c}{sh_c}O",
                        f"O{lo_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        f"O{up_c}{sh_c}O",
                        ".OO.",
                    ])
                else:
                    stamp(11, 16 + (0 if anim_frame == 2 else -1), [
                        ".OO.....",
                        f"O{hand_c}kO....",
                        f".O{lo_c}O...",
                        f"..O{lo_c}{up_c}O..",
                        f"...O{up_c}{up_c}O.",
                        f"....O{up_c}{sh_c}O",
                        ".....OO.",
                    ])

        # ---- 4. PINTANDO EN ESTUDIO UI (PALETA + PINCEL) ----
        elif action == "painting":
            stroke_dy = (0, -2, -1, 1)[anim_frame]
            stroke_dx = (0, 1, 2, 0)[anim_frame]
            if direction in ("up", "down"):
                # Brazo izq sostiene paleta, brazo der pinta con pincel!
                stamp(8, 21, [
                    "..OO.",
                    f".O{up_c}{sh_c}O",
                    f"O{lo_c}{up_c}O.",
                    f"O{hand_c}OO..",
                    ".OO..",
                ])
                stamp(22 + stroke_dx, 16 + stroke_dy, [
                    ".OO.",
                    f"O{hand_c}kO",
                    f"O{lo_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    ".OO.",
                ])
            else:
                stamp(12, 18 + stroke_dy, [
                    ".OO....",
                    f"O{hand_c}kO...",
                    f".O{lo_c}{up_c}O.",
                    f"..O{up_c}{up_c}O",
                    f"...O{up_c}{sh_c}O",
                    "....OO.",
                ])

        # ---- 5. ORQUESTANDO (BRAZOS EN ALTO DIRIGIENDO HOLOGRAMAS) ----
        elif action == "orchestrating":
            wave_l = -1 if anim_frame in (0, 1) else 1
            wave_r = 1 if anim_frame in (0, 1) else -1
            if direction in ("up", "down"):
                stamp(7, 17 + wave_l, [
                    ".OO...",
                    f"O{hand_c}kO..",
                    f".O{lo_c}{up_c}O.",
                    f"..O{up_c}{sh_c}O",
                    f"...O{up_c}O",
                    "....OO",
                ])
                stamp(23, 17 + wave_r, [
                    "...OO.",
                    f"..O{hand_c}kO",
                    f".O{up_c}{lo_c}O.",
                    f"O{sh_c}{up_c}O..",
                    f"O{up_c}O...",
                    "OO....",
                ])
            else:
                stamp(11, 18 + wave_l, [
                    ".OO....",
                    f"O{hand_c}kO...",
                    f".O{lo_c}{up_c}O.",
                    f"..O{up_c}{up_c}O",
                    f"...O{up_c}{sh_c}O",
                    "....OO.",
                ])

        # ---- 6. RELAJADO EN SOFÁ / BARRA TOMANDO CAFÉ ----
        elif action in ("relaxing", "coffee_standing"):
            sip_dy = (0, -2, -4, -1)[anim_frame]
            if direction in ("down", "up"):
                stamp(10, 21, [
                    ".OO.",
                    f"O{up_c}{sh_c}O",
                    f"O{up_c}{sh_c}O",
                    f"O{lo_c}{sh_c}O",
                    f"O{hand_c}kO",
                    ".OO.",
                ])
                stamp(21, 21 + sip_dy, [
                    "..OO.",
                    f".O{sh_c}{up_c}O",
                    f"O{hand_c}{lo_c}O.",
                    ".OOO.",
                ])
            else:
                stamp(12, 22 + sip_dy, [
                    ".....OOO.",
                    f"....O{up_c}{up_c}O",
                    f"...O{up_c}{sh_c}O.",
                    f".OO{lo_c}{sh_c}O.",
                    f"O{hand_c}{hand_c}OO...",
                    ".OO......",
                ])

    def _draw_action_props(self, stamp, px, direction: str, action: str, anim_frame: int):
        """Dibuja los objetos interactivos animados (libro abierto, taza de café, bombilla, pincel, hologramas)."""
        # ---- LIBRO ABIERTO + PÁGINA VOLANDO (Biblioteca) ----
        if action == "reading":
            if direction == "down":
                stamp(12, 24, [
                    "OOOOOOOOOOOO",
                    "ONWWWoOWWWNO",
                    "ONWWWoOWWWNO",
                    "ONWoooOoooNO",
                    "ONWWWoOWWWNO",
                    "ONNNNOONNNNO",
                    ".OOOOOOOOOO.",
                ])
                if anim_frame == 2:
                    # Página levantándose en arco al pasar la hoja!
                    stamp(16, 21, [
                        ".OOO.",
                        "OWWWO",
                        "OwwWO",
                    ])
                elif anim_frame == 3:
                    px(24, 22, "Y"); px(25, 21, "W")
            elif direction == "left":
                stamp(6, 24, [
                    ".OOOOOO.",
                    "ONWWWWNO",
                    "ONWoooNO",
                    "ONWWWWNO",
                    "ONNNNNNO",
                    ".OOOOOO.",
                ])
                if anim_frame == 2:
                    stamp(8, 21, [
                        ".OO.",
                        "OWWO",
                        "OwWO",
                    ])
            elif direction == "up":
                if anim_frame in (0, 1):
                    # Lomo de libro colorido siendo sacado del estante
                    bx = 22 if anim_frame == 0 else 21
                    stamp(bx, 11, [
                        "OOOO",
                        "OAAO",
                        "OYYO",
                        "OAAO",
                        "OOOO",
                    ])
                else:
                    # Libro abierto visible a la derecha pasando página!
                    stamp(23, 21, [
                        "OOOOOOOOO",
                        "ONWWOWWNO",
                        "ONWoOWoNO",
                        "ONWWOWWNO",
                        "ONNNOONNO",
                        ".OOOOOOO.",
                    ])
                    if anim_frame == 2:
                        stamp(26, 19, ["OO", "WW"])

        # ---- BOMBILLA DE IDEA + PLUMÓN DE PIZARRA (Estrategia) ----
        elif action == "thinking":
            if anim_frame in (0, 1):
                glow_y = 2 if anim_frame == 0 else 1
                stamp(24 if direction != "left" else 4, glow_y, [
                    "..OOO..",
                    ".OYWYO.",
                    "OYYWYYO",
                    ".OYYYO.",
                    "..OMO..",
                    "..OOO..",
                ])
                if anim_frame == 1:
                    sx = 23 if direction != "left" else 3
                    px(sx, glow_y + 2, "Y")
                    px(sx + 8, glow_y + 2, "Y")
                    px(sx + 4, max(0, glow_y - 1), "W")
            else:
                # Plumón trazando sobre la pizarra con chispas cyan
                if direction in ("up", "down"):
                    mx = 24 if anim_frame == 2 else 26
                    stamp(mx, 11, [
                        "OGG",
                        "OWO",
                        "ODO",
                    ])
                    px(mx - 1, 11, "Q")
                else:
                    stamp(8, 13 if anim_frame == 2 else 12, [
                        "GGO",
                        "OWO",
                        ".DO",
                    ])

        # ---- PALETA DE COLORES + PINCEL ANIMADO (Estudio UI) ----
        elif action == "painting":
            stroke_dy = (0, -2, -1, 1)[anim_frame]
            stroke_dx = (0, 1, 2, 0)[anim_frame]
            if direction in ("up", "down"):
                # Paleta de madera con manchas de pintura (izquierda)
                stamp(4, 22, [
                    ".OOOOO.",
                    "ORPRGRO",
                    "ORRYRRO",
                    ".OOOOO.",
                ])
                # Pincel con punta de color (derecha)
                tip = ("P", "G", "Y", "E")[anim_frame]
                stamp(24 + stroke_dx, 13 + stroke_dy, [
                    f".{tip}O",
                    "ONO",
                    "OnO",
                ])
            else:
                tip = ("P", "G", "Y", "E")[anim_frame]
                stamp(8, 15 + stroke_dy, [
                    f"{tip}O.",
                    "ONO",
                    ".nO",
                ])

        # ---- HOLOGRAMA DE TERMINAL / RADAR WEB / TECLADO GLOW ----
        elif action == "typing_seated":
            if direction == "down":
                # Brillo sutil del monitor/teclado
                c = "G" if anim_frame % 2 == 0 else "Q"
                px(14, 26, c); px(18, 26, c); px(21, 26, c)
            elif direction == "left":
                c = "G" if anim_frame % 2 == 0 else "Q"
                px(8, 25, c); px(9, 24, c)

        elif action == "terminal":
            # Consola holográfica flotante verde/ámbar
            hx = 25 if direction != "left" else 4
            hy = 18 + (0 if anim_frame % 2 == 0 else 1)
            bar1 = "GGG" if anim_frame % 2 == 0 else "YYY"
            bar2 = "YYY" if anim_frame % 2 == 0 else "GGG"
            stamp(hx, hy, [
                "OOOOOOO",
                f"OD{bar1}DO",
                f"OD{bar2}DO",
                "ODDDDDO",
                "OOOOOOO",
            ])

        elif action == "browsing":
            # Retícula / lupa radar cyan pulsante
            rx = 25 if direction != "left" else 4
            ry = 17 + (0 if anim_frame % 2 == 0 else -1)
            stamp(rx, ry, [
                ".OOOO.",
                "OGQQGO",
                "OGGGGO",
                ".OOOO.",
                "...OO.",
            ])

        # ---- ORBES HOLOGRÁFICOS DE ORQUESTACIÓN ----
        elif action == "orchestrating":
            dy1 = 0 if anim_frame in (0, 1) else 2
            dy2 = 2 if anim_frame in (0, 1) else 0
            c1 = "Y" if anim_frame % 2 == 0 else "G"
            c2 = "G" if anim_frame % 2 == 0 else "Y"
            if direction in ("up", "down"):
                stamp(4, 13 + dy1, [
                    ".OO.",
                    f"O{c1}WO",
                    ".OO.",
                ])
                stamp(28, 13 + dy2, [
                    ".OO.",
                    f"O{c2}WO",
                    ".OO.",
                ])
            else:
                stamp(6, 13 + dy1, [
                    ".OOO.",
                    f"O{c1}W{c2}O",
                    ".OOO.",
                ])

        # ---- TAZA DE CAFÉ HUMEANTE (Lounge / Sofá / Barra) ----
        elif action in ("relaxing", "coffee_standing"):
            sip_dy = (0, -2, -4, -1)[anim_frame]
            steam_dx = 0 if anim_frame % 2 == 0 else 1
            if direction == "down":
                # Taza cerámica blanca con café y vapor animado
                stamp(19, 22 + sip_dy, [
                    ".OOOO.",
                    "OWnnWO",
                    "OWWWWO",
                    "OwwwWO",
                    ".OOOO.",
                ])
                px(21 + steam_dx, 20 + sip_dy, "Q")
                px(22 - steam_dx, 18 + sip_dy, "W")
            elif direction == "left":
                stamp(8, 22 + sip_dy, [
                    ".OOOO.",
                    "OWnnWO",
                    "OWWWWO",
                    "OwwwWO",
                    ".OOOO.",
                ])
                px(10 + steam_dx, 20 + sip_dy, "Q")
                px(11 - steam_dx, 18 + sip_dy, "W")
            else:
                # Vista trasera: vapor subiendo por encima del hombro derecho
                px(24 + steam_dx, 19 + sip_dy, "Q")
                px(25 - steam_dx, 17 + sip_dy, "W")

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
            "part_preview_v3",
            part_kind,
            style_id,
            c.get("skin_color", "#f6c198"),
            c.get("eye_color", "#261a24"),
            c.get("hair_color", "#4b352a"),
            c.get("top_color", "#585358"),
            c.get("bottom_color", "#2b3a55"),
            c.get("shoe_color", "#3d261f"),
            c.get("accessory_color", "#d99b26"),
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
                for xx in range(14, 22):
                    px(xx, 10, "#475569")
                    px(xx, 19, "#475569")
                for yy in range(11, 19):
                    px(13, yy, "#475569")
                    px(22, yy, "#475569")
            else:
                self._draw_back_hair(stamp, style_id, "down", 0)
                self._draw_sculpted_hair(stamp, style_id, "down", 0)
            crop_rect = QRect(5, 2, 26, 22)

        elif part_kind == "face":
            self._draw_head(stamp, "down")
            self._draw_face(px, stamp, style_id, "down")
            crop_rect = QRect(11, 8, 14, 14)

        elif part_kind in ("torso", "outfit"):
            self._draw_torso(stamp, px, style_id, "down", 0)
            self._draw_front_arms(stamp, style_id, "down", 0, False)
            crop_rect = QRect(9, 19, 18, 16)

        elif part_kind == "pants":
            self._draw_pants(stamp, style_id, "down", 0)
            crop_rect = QRect(9, 30, 18, 14)

        elif part_kind == "shoes":
            tall = style_id in (
                "leather_boots", "shin_wraps", "knight_greaves",
                "combat_boots", "cyber_boots", "elf_boots"
            )
            self._draw_boots_base(stamp, style_id, "down", 0, tall)
            if tall:
                self._draw_boot_cuffs_overlay(stamp, style_id, "down", 0)
            crop_rect = QRect(10, 36, 16, 11)

        elif part_kind == "accessory":
            if style_id == "none":
                for i in range(13, 23):
                    px(i, 8, "#64748b"); px(i, 17, "#64748b")
                    px(13, i - 5, "#64748b"); px(22, i - 5, "#64748b")
                    px(i, i - 5, "#ef4444")
                crop_rect = QRect(11, 6, 14, 14)
            else:
                self._draw_accessory(stamp, style_id, "down")
                crop_rect = QRect(5, 1, 26, 19)

        elif part_kind == "back_gear":
            if style_id == "none":
                for i in range(13, 23):
                    px(i, 16, "#64748b"); px(i, 25, "#64748b")
                    px(13, i + 3, "#64748b"); px(22, i + 3, "#64748b")
                    px(i, i + 3, "#ef4444")
                crop_rect = QRect(11, 14, 14, 14)
            elif style_id == "waist_katana":
                self._draw_back_gear_front(stamp, px, style_id, "left", 0)
                crop_rect = QRect(7, 25, 24, 15)
            elif style_id in ("back_sword", "dual_katanas", "round_shield", "adventurer_pack", "hero_cape"):
                self._draw_back_gear_behind(stamp, px, style_id, "up", 0)
                crop_rect = QRect(7, 11, 22, 23)
            elif style_id == "back_spear":
                self._draw_back_gear_behind(stamp, px, style_id, "left", 0)
                crop_rect = QRect(5, 4, 24, 42)
            else:
                self._draw_back_gear_behind(stamp, px, style_id, "down", 0)
                self._draw_back_gear_front(stamp, px, style_id, "down", 0)
                crop_rect = QRect(2, 6, 32, 26)

        min_x, min_y, max_x, max_y = self.GRID_W, self.GRID_H, -1, -1
        for yy in range(max(0, crop_rect.top()), min(self.GRID_H, crop_rect.bottom() + 1)):
            for xx in range(max(0, crop_rect.left()), min(self.GRID_W, crop_rect.right() + 1)):
                if canvas.pixelColor(xx, yy).alpha() > 0:
                    if xx < min_x: min_x = xx
                    if yy < min_y: min_y = yy
                    if xx > max_x: max_x = xx
                    if yy > max_y: max_y = yy

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
        if target_w < box_size * 0.55 and target_h < box_size * 0.55:
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
    # MINIATURAS AISLADAS PARA EL CONSTRUCTOR DE OFICINA (MUEBLES, PISOS, PAREDES)
    # =========================================================================
    def get_office_preview_pixmap(
        self,
        category: str,
        item_key: str,
        spec: Dict[str, Any],
        box_size: int = 52,
    ) -> QPixmap:
        key = ("office_preview", category, item_key, box_size)
        if key in self._cache:
            return self._cache[key]

        out = QImage(box_size, box_size, QImage.Format.Format_ARGB32)
        out.fill(Qt.GlobalColor.transparent)
        p = QPainter(out)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        def rfill(x, y, w, h, fill: str, stroke: Optional[str] = None):
            p.fillRect(int(x), int(y), int(w), int(h), QColor(fill))
            if stroke:
                p.setPen(QPen(QColor(stroke), 1))
                p.drawRect(int(x), int(y), int(w) - 1, int(h) - 1)

        if category == "floors":
            cA, cB = QColor(spec["colorA"]), QColor(spec["colorB"])
            pat = spec.get("pattern", "tiles")
            m = 6
            s = box_size - m * 2
            if pat == "planks":
                for row in range(4):
                    p.fillRect(m, m + row * (s // 4), s, s // 4, cA if row % 2 == 0 else cB)
                    p.fillRect(m, m + (row + 1) * (s // 4) - 1, s, 1, cB)
            elif pat == "grate":
                p.fillRect(m, m, s, s, cA)
                p.fillRect(m + 4, m + 4, s - 8, s - 8, cB)
            elif pat == "checkers":
                h2 = s // 2
                p.fillRect(m, m, h2, h2, cA)
                p.fillRect(m + h2, m, h2, h2, cB)
                p.fillRect(m, m + h2, h2, h2, cB)
                p.fillRect(m + h2, m + h2, h2, h2, cA)
            else:
                h2 = s // 2
                p.fillRect(m, m, s, s, cA)
                p.fillRect(m, m, h2, h2, cB)
                p.fillRect(m + h2, m + h2, h2, h2, cB)
            p.setPen(QPen(QColor("#475569"), 1))
            p.drawRect(m, m, s - 1, s - 1)

        elif category == "walls":
            m = 10
            s = box_size - m * 2
            if item_key == "__erase_wall__":
                p.setPen(QPen(QColor("#f87171"), 2, Qt.PenStyle.DashLine))
                p.drawRect(m, m, s - 1, s - 1)
                p.drawLine(m + 5, m + 5, m + s - 6, m + s - 6)
                p.drawLine(m + s - 6, m + 5, m + 5, m + s - 6)
            else:
                p.fillRect(m, m, s, s - 8, QColor(spec["top"]))
                p.fillRect(m, m + s - 8, s, 8, QColor(spec["front"]))
                p.setPen(QPen(QColor(spec["border"]), 1))
                p.drawRect(m, m, s - 1, s - 1)

        else:
            otype = item_key
            if otype == "computer_desk":
                rfill(6, 12, 40, 22, "#1e293b", "#34d399")
                rfill(9, 15, 15, 11, "#062116", "#34d399")
                rfill(27, 15, 15, 11, "#062116", "#38bdf8")
                p.fillRect(11, 18, 9, 2, QColor("#34d399"))
                p.fillRect(29, 18, 9, 2, QColor("#38bdf8"))
                rfill(18, 36, 16, 8, "#334155", "#64748b")
            elif otype == "laptop_desk":
                rfill(12, 14, 28, 22, "#292524", "#57534e")
                rfill(17, 17, 18, 13, "#062116", "#38bdf8")
                p.fillRect(20, 21, 11, 2, QColor("#34d399"))
            elif otype in ("bookshelf", "bookshelf_single"):
                w = 40 if otype == "bookshelf" else 24
                x0 = (box_size - w) // 2
                rfill(x0, 10, w, 32, "#3e2723", "#d49a6a")
                cols = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ec4899"]
                nb = 5 if w > 30 else 3
                for r_i in range(2):
                    ry = 14 + r_i * 13
                    p.fillRect(x0 + 3, ry + 8, w - 6, 2, QColor("#271612"))
                    for b in range(nb):
                        p.fillRect(x0 + 4 + b * 6, ry, 5, 8, QColor(cols[(r_i * 3 + b) % len(cols)]))
            elif otype == "server_terminal":
                rfill(8, 10, 16, 32, "#0f131a", "#fb923c")
                rfill(28, 10, 16, 32, "#0f131a", "#fb923c")
                for rx in (8, 28):
                    p.fillRect(rx + 3, 15, 4, 4, QColor("#34d399"))
                    p.fillRect(rx + 9, 15, 4, 4, QColor("#38bdf8"))
                    p.fillRect(rx + 3, 24, 10, 3, QColor("#fb923c"))
            elif otype == "whiteboard":
                rfill(4, 13, 44, 26, "#0d1726", "#38bdf8")
                p.fillRect(9, 19, 9, 7, QColor("#38bdf8"))
                p.fillRect(22, 19, 9, 7, QColor("#fbbf24"))
                p.fillRect(35, 19, 9, 7, QColor("#34d399"))
            elif otype == "orchestrator_core":
                rfill(8, 8, 36, 36, "#19130b", "#fbbf24")
                p.setPen(QPen(QColor("#fbbf24"), 2))
                p.drawEllipse(QPointF(26, 26), 11, 11)
            elif otype == "web_radar":
                rfill(7, 12, 38, 28, "#0a1724", "#22d3ee")
                p.setPen(QPen(QColor("#22d3ee"), 1))
                p.drawEllipse(QPointF(26, 26), 9, 9)
                p.drawLine(17, 26, 35, 26)
                p.drawLine(26, 17, 26, 35)
            elif otype == "art_easel":
                rfill(8, 12, 36, 28, "#2e1065", "#e879f9")
                rfill(13, 16, 26, 20, "#fef3c7", "#d97706")
                p.fillRect(16, 19, 9, 8, QColor("#f43f5e"))
                p.fillRect(26, 22, 10, 9, QColor("#38bdf8"))
            elif otype == "coffee_sofa":
                rfill(6, 14, 40, 24, "#881337", "#f43f5e")
                rfill(10, 19, 32, 14, "#be123c")
            elif otype == "lounge_armchair":
                rfill(10, 10, 32, 32, "#881337", "#f43f5e")
                rfill(15, 16, 22, 20, "#be123c", "#fb7185")
                rfill(10, 16, 5, 22, "#9f1239")
                rfill(37, 16, 5, 22, "#9f1239")
            elif otype == "office_chair":
                rfill(15, 10, 22, 18, "#334155", "#94a3b8")
                rfill(13, 26, 26, 10, "#1e293b", "#64748b")
                p.fillRect(24, 36, 4, 6, QColor("#94a3b8"))
                p.fillRect(15, 40, 22, 3, QColor("#64748b"))
            elif otype == "gaming_chair":
                rfill(15, 8, 22, 20, "#0f172a", "#38bdf8")
                rfill(19, 12, 14, 12, "#1e293b", "#f43f5e")
                rfill(13, 27, 26, 10, "#0f172a", "#38bdf8")
                p.fillRect(24, 37, 4, 5, QColor("#94a3b8"))
                p.fillRect(15, 40, 22, 3, QColor("#38bdf8"))
            elif otype == "coffee_bar":
                rfill(6, 14, 40, 24, "#451a03", "#a16207")
                rfill(11, 17, 14, 16, "#991b1b", "#f87171")
                rfill(32, 20, 8, 9, "#ffffff", "#38bdf8")
            elif otype in ("reading_table", "meeting_table"):
                rfill(7, 13, 38, 26, "#5c3a21", "#854d0e")
                rfill(16, 19, 14, 11, "#fef3c7", "#a16207")
            elif otype == "filing_cabinet":
                rfill(14, 10, 24, 32, "#334155", "#64748b")
                p.fillRect(18, 16, 16, 4, QColor("#94a3b8"))
                p.fillRect(18, 26, 16, 4, QColor("#94a3b8"))
            elif otype in ("plant_monstera", "plant_cactus"):
                rfill(19, 28, 14, 13, "#9a3412", "#23110d")
                lc = "#10b981" if otype == "plant_monstera" else "#22c55e"
                rfill(14, 12, 24, 17, lc, "#064e3b")
                p.fillRect(21, 8, 10, 6, QColor("#34d399"))
            elif otype == "arcade_machine":
                rfill(14, 8, 24, 36, "#3b0764", "#e879f9")
                rfill(17, 12, 18, 13, "#090d16", "#38bdf8")
                p.fillRect(20, 16, 5, 5, QColor("#f43f5e"))
            elif otype == "water_cooler":
                rfill(17, 23, 18, 19, "#e2e8f0", "#64748b")
                rfill(18, 9, 16, 15, "#bae6fd", "#38bdf8")
            elif otype in ("rug_persian", "rug_cyber"):
                c1 = "#7f1d1d" if otype == "rug_persian" else "#0f2942"
                c2 = "#f59e0b" if otype == "rug_persian" else "#38bdf8"
                rfill(6, 12, 40, 28, c1, c2)
                rfill(12, 17, 28, 18, c1, c2)
            elif otype == "floor_lamp":
                p.fillRect(25, 22, 3, 20, QColor("#94a3b8"))
                rfill(16, 10, 20, 12, "#fef08a", "#ca8a04")
            elif otype == "trophy":
                rfill(19, 30, 14, 10, "#451a03", "#23110d")
                rfill(16, 12, 20, 18, "#facc15", "#ca8a04")

        p.end()
        pix = QPixmap.fromImage(out)
        self._cache[key] = pix
        return pix


SPRITE_ENGINE = ChibiSpriteRenderer()
