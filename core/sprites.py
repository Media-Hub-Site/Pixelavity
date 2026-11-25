# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Sprites Pixel Art Chibi de Alto Detalle (4 Direcciones)
Fiel a la estética de la imagen de referencia:
  - Piernas juntas con costura central de 1-2px de contorno oscuro (#23110d)
  - Peinados con flequillos diagonales asimétricos, líneas de contorno interior,
    coletas altas con moño grande, melenas largas laterales, moño esquinado,
    dos coletas altas tipo alas y ondas con volumen.
  - 4 Direcciones reales: Adelante (down), Atrás (up), Izquierda (left), Derecha (right)
  - 4 Frames de caminata fluida.
"""

from typing import Dict, Any, Tuple, List
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor


OUTLINE = "#23110d"
WHITE = "#fff9f2"


def _shade(hex_color: str, factor: float) -> str:
    c = QColor(hex_color or "#38bdf8")
    return QColor(
        max(0, min(255, int(c.red() * factor))),
        max(0, min(255, int(c.green() * factor))),
        max(0, min(255, int(c.blue() * factor))),
    ).name()


class ChibiSpriteRenderer:
    GRID_W = 28
    GRID_H = 34

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
    ) -> Tuple:
        return (
            char.get("skin_color", "#ffcca8"),
            char.get("face_style", "smile"),
            char.get("hair_style", "short_parted"),
            char.get("hair_color", "#eab308"),
            char.get("outfit_style", "suit_tie"),
            char.get("top_color", "#334155"),
            char.get("bottom_color", "#1e293b"),
            char.get("shoe_style", "classic"),
            char.get("shoe_color", "#451a03"),
            char.get("accessory", "none"),
            char.get("accessory_color", "#ef4444"),
            direction,
            walk_frame % 4,
            scale,
            is_typing,
        )

    def get_pixmap(
        self,
        char: Dict[str, Any],
        direction: str = "down",
        walk_frame: int = 0,
        scale: int = 2,
        is_typing: bool = False,
    ) -> QPixmap:
        if direction not in ("down", "up", "left", "right"):
            direction = "down"
        key = self._cache_key(char, direction, walk_frame, scale, is_typing)
        if key in self._cache:
            return self._cache[key]

        img = self._render_character(char, direction, walk_frame % 4, is_typing)
        scaled = img.scaled(
            self.GRID_W * scale,
            self.GRID_H * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pix = QPixmap.fromImage(scaled)
        if len(self._cache) > 1500:
            self._cache.clear()
        self._cache[key] = pix
        return pix

    def _render_character(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        is_typing: bool,
    ) -> QImage:
        if direction == "right":
            return self._render_character(char, "left", walk_frame, is_typing).mirrored(True, False)

        img = QImage(self.GRID_W, self.GRID_H, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        skin = char.get("skin_color", "#ffcca8")
        skin_sh = _shade(skin, 0.86)

        hair_col = char.get("hair_color", "#eab308")
        hair_sh = _shade(hair_col, 0.76)
        hair_hi = _shade(hair_col, 1.18)

        top_col = char.get("top_color", "#334155")
        top_sh = _shade(top_col, 0.78)

        bot_col = char.get("bottom_color", "#1e293b")
        bot_sh = _shade(bot_col, 0.78)

        shoe_col = char.get("shoe_color", "#451a03")
        shoe_sh = _shade(shoe_col, 0.75)

        acc_col = char.get("accessory_color", "#ef4444")
        acc_hi = _shade(acc_col, 1.25)

        face_style = char.get("face_style", "smile")
        hair_style = char.get("hair_style", "short_parted")
        outfit = char.get("outfit_style", "suit_tie")
        shoe_style = char.get("shoe_style", "classic")
        acc = char.get("accessory", "none")

        palette = {
            "O": OUTLINE,
            "W": WHITE,
            "K": skin,
            "k": skin_sh,
            "H": hair_col,
            "h": hair_sh,
            "L": hair_hi,
            "T": top_col,
            "t": top_sh,
            "B": bot_col,
            "b": bot_sh,
            "Z": shoe_col,
            "z": shoe_sh,
            "A": acc_col,
            "e": acc_hi,
            "G": "#7dd3fc",
            "g": "#e0f2fe",
            "Y": "#facc15",
            "M": "#64748b",
            "m": "#475569",
            "D": "#334155",
            "N": "#1e293b",
            "P": "#f472b6",
            "F": "#fde047",
            "f": "#eab308",
        }

        def px(x: int, y: int, col_hex: str):
            if 0 <= x < self.GRID_W and 0 <= y < self.GRID_H:
                img.setPixelColor(x, y, QColor(col_hex))

        def stamp(x0: int, y0: int, rows: List[str]):
            for dy, row_str in enumerate(rows):
                yy = y0 + dy
                if not (0 <= yy < self.GRID_H):
                    continue
                for dx, ch_code in enumerate(row_str):
                    if ch_code in (".", " "):
                        continue
                    xx = x0 + dx
                    if 0 <= xx < self.GRID_W and ch_code in palette:
                        img.setPixelColor(xx, yy, QColor(palette[ch_code]))

        leg_l_dy = -1 if walk_frame == 1 else 0
        leg_r_dy = -1 if walk_frame == 3 else 0
        arm_l_dy = 1 if (walk_frame == 1 or is_typing) else (-1 if walk_frame == 3 else 0)
        arm_r_dy = -1 if (walk_frame == 1 or is_typing) else (1 if walk_frame == 3 else 0)

        # 1. CABELLO TRASERO (Melenas, coletas laterales, moños)
        self._draw_back_hair(stamp, hair_style, direction, walk_frame)

        # 2. CUERPO COMPACTO Y PIERNAS JUNTAS (y: 19..32, idéntico en proporciones a ref_sprites.png)
        self._draw_body_and_legs(stamp, outfit, shoe_style, direction, walk_frame, leg_l_dy, leg_r_dy, arm_l_dy, arm_r_dy)

        # 3. CABEZA CHIBI (x: 7..20, y: 7..19)
        head_rows = [
            "...OOOOOOOOOO...",
            "..OKKKKKKKKKKO..",
            ".OKKKKKKKKKKKKO.",
            ".OKKKKKKKKKKKKO.",
            "OKKKKKKKKKKKKKKO",
            "OKKKKKKKKKKKKKKO",
            "OKKKKKKKKKKKKKKO",
            "OKKKKKKKKKKKKKKO",
            "OKKKKKKKKKKKKKKO",
            ".OKKKKKKKKKKKkO.",
            "..OKKKKKKKKKkO..",
            "...OOOOOOOOOO...",
        ]
        stamp(6, 8, head_rows)

        # 4. OJOS Y SONRISA (Adelante y Perfil Izquierdo)
        self._draw_face(px, face_style, direction)

        # 5. PEINADOS ESCULPIDOS CON FLEQUILLO DIAGONAL Y VOLUMEN LATERAL
        self._draw_sculpted_hair(stamp, hair_style, direction)

        # 6. SOMBREROS Y ACCESORIOS
        self._draw_accessory(stamp, acc, direction)

        return img

    def _draw_back_hair(self, stamp, hair_style: str, direction: str, walk_frame: int):
        bob = -1 if walk_frame in (1, 3) else 0
        if hair_style == "ponytail":
            # Gran coleta alta lateral con moño de 2 lazos (idéntica a fila 3 col 1 de ref_sprites.png)
            stamp(17, 5 + bob, [
                "..OOOO....",
                ".OAeeAO...",
                "OOAOOAOO..",
                ".OAOOHHOO.",
                "..OOHLLHOO",
                "...OHHHHhO",
                "...OHHHHhO",
                "...OOhhhhO",
                "....OOOhOO",
                "......OOO.",
            ])
        elif hair_style == "long_straight" and direction in ("down", "left"):
            # Cortina de cabello largo que cae por el lado derecho hasta la cintura (fila 3 col 2 / fila 4 col 4)
            stamp(16, 12 + bob, [
                "..OOOOO.",
                ".OHHHHHO",
                ".OHHHHHO",
                ".OHHHHhO",
                ".OHHHHhO",
                ".OHHHHhO",
                ".OHHHhhO",
                ".OOhhhhO",
                "..OOhhhO",
                "...OOOO.",
            ])
        elif hair_style == "wavy_bob" and direction in ("down", "left"):
            # Onda curva baja que sobresale a la derecha a la altura del cuello (fila 3 col 3)
            stamp(16, 13 + bob, [
                "..OOOO..",
                ".OHHHHO.",
                ".OHHHHHO",
                "OOHHHHhO",
                "OOhhhhhO",
                ".OOhhhO.",
                "..OOOO..",
            ])
        elif hair_style == "pigtails":
            # Dos coletas altas tipo alas a ambos lados de la cabeza (fila 3 col 5)
            stamp(1, 4 + bob, [
                "..OOOO..............OOOO..",
                ".OHLLHO............OHLLHO.",
                "OOHHHhOO..........OOHHHhOO",
                "OHHHhhOO..........OOhhHHHO",
                "OhhhOOO............OOOhhhO",
                "OOOO..................OOOO",
            ])
        elif hair_style == "low_ponytail" and direction in ("down", "left"):
            # Coleta baja de oficina que asoma a la altura del hombro (fila 2 col 2 y 4)
            stamp(16, 14 + bob, [
                "..OOOO..",
                ".OHHHHO.",
                ".OOHHHhO",
                "..OOhhhO",
                "...OOOO.",
            ])
        elif hair_style == "curly_afro":
            # Volumen rizado redondo alrededor de toda la cabeza
            stamp(3, 3 + bob, [
                ".....OOOOOOOOOOOO.....",
                "...OOHLLHHHHHHLLHOO...",
                "..OHLHHHHHHHHHHHHLHO..",
                ".OHHHHHHHHHHHHHHHHHHO.",
                "OOHHHHHHHHHHHHHHHHHHOO",
                "OOHHHHHHHHHHHHHHHHHHOO",
                "OOhHHHHHHHHHHHHHHHHhOO",
                ".OOhhhhhhhhhhhhhhhhOO.",
                "..OOOOOOOOOOOOOOOOOO..",
            ])
        elif hair_style == "top_bun":
            # Moño redondo alto inclinado en la esquina superior derecha (fila 4 col 1)
            stamp(15, 3 + bob, [
                "..OOOO..",
                ".OHLLHO.",
                "OOHHHhOO",
                "OOhhhhOO",
                ".OOOOOO.",
            ])

    def _draw_sculpted_hair(self, stamp, hair_style: str, direction: str):
        if hair_style == "bald":
            return

        if direction == "up":
            # Vista trasera completa del cabello
            if hair_style == "flat_top":
                stamp(6, 4, [
                    ".OOOOOOOOOOOOOO.",
                    "OHLLLLLLLLLLLLHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OhhhhhhhhhhhhhhO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OhhhhhhhhhhhhhhO",
                    ".OhhhhhhhhhhhhO.",
                    "..OOOOOOOOOOOO..",
                ])
            else:
                stamp(6, 5, [
                    "..OOOOOOOOOOOO..",
                    ".OHLLLLLLLLLLHO.",
                    "OHLHHHHHHHHHHLHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OhhhhhhhhhhhhhhO",
                    "OhhhhhOhhOhhhhhO",
                    ".OhhhhOhhOhhhhO.",
                    "..OOOOOOOOOOOO..",
                ])
                if hair_style == "long_straight":
                    stamp(7, 15, [
                        "OHHHHHHHHHHHHO",
                        "OHHHHHHHHHHHHO",
                        "OhhhhhhhhhhhhO",
                        "OhhhhhhhhhhhhO",
                        ".OhhhhhhhhhhO.",
                        "..OOOOOOOOOO..",
                    ])
            return

        if direction == "down":
            if hair_style == "short_parted":
                # Rubio con flequillo diagonal asimétrico y volumen lateral derecho (fila 2 col 5)
                stamp(5, 5, [
                    "....OOOOOOOOOO....",
                    "..OOHLLLLLLLLHOO..",
                    ".OOHLHHHHHHHHHHOO.",
                    "OOHHHHHHHHHHHHHHOO",
                    "OOHHHHHHOOOHHHHHHO",
                    "OOHHHHOO...OOHHHHO",
                    "OOHHOO.......OOHHO",
                    ".OOO..........OHHO",
                    "..............OhHO",
                    "..............OhhO",
                    "...............OO.",
                ])
            elif hair_style == "ponytail":
                # Flequillo con raya diagonal marcada y contorno interior (fila 3 col 1)
                stamp(6, 6, [
                    "...OOOOOOOOOO...",
                    "..OHLLLLLLLLHO..",
                    ".OHLHHHHHHHHHHO.",
                    "OOHHHHHHHOHHHHHO",
                    "OHHHHHOOO.OOHHHO",
                    "OHHHOO.....OOHHO",
                    "OHOO.........OHO",
                    ".OO...........OO",
                ])
            elif hair_style == "long_straight":
                # Flequillo diagonal elegante + caída larga lateral (fila 3 col 2 / fila 4 col 4)
                stamp(6, 6, [
                    "...OOOOOOOOOO...",
                    "..OHLLLLLLLLHO..",
                    ".OHHHHHHHHHHHHO.",
                    "OOHHHHHHOHHHHHHO",
                    "OHHHHOOO.OOHHHHO",
                    "OHHOO......OOHHO",
                    "OHO.........OHHO",
                    "OHO..........OHO",
                    ".OO..........OHO",
                ])
            elif hair_style == "wavy_bob":
                # Melena curva con raya lateral y volumen (fila 3 col 3)
                stamp(5, 5, [
                    "....OOOOOOOOOO....",
                    "..OOHLLLLLLLLHOO..",
                    ".OOHHHHHHHHHHHHOO.",
                    "OOHHHHHHOOHHHHHHOO",
                    "OOHHHHOO..OOHHHHOO",
                    ".OOHHOO.....OOHHOO",
                    "..OOO........OHHOO",
                ])
            elif hair_style == "pigtails":
                # Flequillo con mechones laterales en las mejillas (fila 3 col 5)
                stamp(4, 6, [
                    ".....OOOOOOOOOO.....",
                    "...OOHLLLLLLLLHOO...",
                    "..OOHHHHHHHHHHHHOO..",
                    "..OHHHHHOOOHHHHHHO..",
                    ".OOHHHOO....OOHHHOO.",
                    "OOHHOO........OOHHOO",
                    ".OOOO..........OOOO.",
                ])
            elif hair_style == "top_bun":
                # Cabello envolvente con raya lateral y caída en mejilla derecha (fila 4 col 1)
                stamp(6, 6, [
                    "...OOOOOOOOOO...",
                    "..OHLLLLLLLLHO..",
                    ".OHHHHHHHHHHHHO.",
                    "OOHHHHHHOHHHHHHO",
                    "OHHHHOOO.OOHHHHO",
                    "OHHOO.....OOHHHO",
                    "OHO........OOHHO",
                    ".OO.........OHHO",
                    "............OhhO",
                    ".............OO.",
                ])
            elif hair_style == "flat_top":
                # Corte alto cuadrado con línea frontal limpia (fila 4 col 5)
                stamp(6, 4, [
                    ".OOOOOOOOOOOOOO.",
                    "OHLLLLLLLLLLLLHO",
                    "OHHHHHHHHHHHHHHO",
                    "OHHHHHHHHHHHHHHO",
                    "OhhhhhhhhhhhhhhO",
                    "OhhOOOOOOOOOOhhO",
                    "OhO..........OhO",
                    "OhO..........OhO",
                    ".OO..........OO.",
                ])
            elif hair_style == "receding":
                # Corte con entradas en M / pico de viuda (fila 1 col 5 y fila 4 col 2)
                stamp(6, 6, [
                    "...OOOOOOOOOO...",
                    "..OHHLLLLLLHHO..",
                    ".OHHOOOHOOOOHHO.",
                    "OHHO...O....OHHO",
                    "OhO..........OhO",
                    "OhO..........OhO",
                    ".OO..........OO.",
                ])
            elif hair_style == "low_ponytail":
                # Cabello ejecutivo con flequillo diagonal amplio y coleta baja (fila 2 col 2 y 4)
                stamp(5, 5, [
                    "....OOOOOOOOOO....",
                    "..OOHLLLLLLLLHOO..",
                    ".OOHHHHHHHHHHHHOO.",
                    "OOHHHHHHHOHHHHHHOO",
                    "OOHHHHHOO.OOHHHHOO",
                    "OOHHHOO....OOHHHOO",
                    ".OOHHO.......OHHOO",
                    "..OOO.........OHOO",
                ])
            elif hair_style == "spiky_messy":
                # Peinado moderno con mechones en punta asimétricos
                stamp(4, 3, [
                    "...OO....OOO...OO...",
                    "..OHHO..OHLHO.OHHO..",
                    ".OOHHHOOHLHHHOHHHHO.",
                    "OOHLHHHHHHHHHHHHHHOO",
                    "OOHHHHOOHHHOOHHHHHHO",
                    ".OOHHOO..OO..OOHHHOO",
                    "..OOO..........OOOO.",
                ])
            elif hair_style == "curly_afro":
                stamp(5, 5, [
                    "...OOOOOOOOOOOO...",
                    ".OOHLLHHHHHHLLHOO.",
                    "OOHHHHHHHHHHHHHHOO",
                    "OOHHHHOOOOOOHHHHOO",
                    "OOHHOO......OOHHOO",
                    ".OOO..........OOO.",
                ])
            return

        # Vista lateral ("left"): Flequillo al frente (izquierda) y nuca cubierta (derecha)
        if hair_style == "flat_top":
            stamp(6, 4, [
                ".OOOOOOOOOOOOOO.",
                "OHLLLLLLLLLLLLHO",
                "OHHHHHHHHHHHHHHO",
                "OHHHHHHHHHHHHHHO",
                "OhhhhhhhhhhhhhhO",
                ".OOOOOOOHHHHHHhO",
                ".......OOHHHHHhO",
                "........OOhhhhhO",
                ".........OOOhhhO",
                "...........OOOO.",
            ])
        else:
            stamp(6, 6, [
                "...OOOOOOOOOO...",
                "..OHLLLLLLLLHO..",
                ".OHLHHHHHHHHHHO.",
                "OOHHHHHOHHHHHHHO",
                "OOHHOO..OHHHHHhO",
                ".OOO....OOHHHHhO",
                ".........OOhhhhO",
                ".........OOhhhhO",
                "..........OOhhhO",
                "...........OOOO.",
            ])

    def _draw_face(self, px, face_style: str, direction: str):
        if direction == "up":
            return

        if direction == "down":
            # Ojos verticales 1x2 + sonrisa pixelada (proporción exacta de ref_sprites.png)
            px(11, 13, OUTLINE)
            px(11, 14, OUTLINE)
            if face_style == "cool":
                px(15, 14, OUTLINE)
                px(16, 14, OUTLINE)
            else:
                px(16, 13, OUTLINE)
                px(16, 14, OUTLINE)

            if face_style in ("smile", "happy"):
                px(11, 16, OUTLINE)
                px(12, 17, OUTLINE)
                px(13, 17, OUTLINE)
                px(14, 17, OUTLINE)
                px(15, 16, OUTLINE)
                if face_style == "happy":
                    px(9, 15, "#f472b6")
                    px(18, 15, "#f472b6")
            elif face_style == "focused":
                px(12, 17, OUTLINE)
                px(13, 17, OUTLINE)
                px(14, 17, OUTLINE)
            elif face_style == "cool":
                px(12, 17, OUTLINE)
                px(13, 17, OUTLINE)
                px(14, 17, OUTLINE)
                px(15, 16, OUTLINE)
        else:
            # Perfil izquierdo ("left")
            px(9, 13, OUTLINE)
            px(9, 14, OUTLINE)
            px(13, 13, OUTLINE)
            px(13, 14, OUTLINE)
            px(9, 16, OUTLINE)
            px(10, 17, OUTLINE)
            px(11, 17, OUTLINE)
            px(12, 16, OUTLINE)

    def _draw_body_and_legs(
        self,
        stamp,
        outfit: str,
        shoe_style: str,
        direction: str,
        walk_frame: int,
        leg_l_dy: int,
        leg_r_dy: int,
        arm_l_dy: int,
        arm_r_dy: int,
    ):
        if outfit == "cloak":
            # Capa larga acampanada con cuello blanco (exacta a fila 1 col 2)
            stamp(7, 19, [
                "..OOOOOOOOOO..",
                ".OOWWOOOOWWOO.",
                ".OOTTTTTTTtOO.",
                ".OTTTTTTTTtOO.",
                "OOTTTTTTTTtOO.",
                "OOTTTTtTTTtOO.",
                "OOTTTTtTTTtOO.",
                "OOTTTTtTTTtOOO",
                "OOttttttttttOO",
                "OOOOOOOOOOOOOO",
            ])
            return

        # 1. Torso compacto (x: 10..17, y: 19..25)
        if direction == "down":
            if outfit == "suit_tie":
                torso = [
                    "OOOOOOOO",
                    "OTWAAWTO",
                    "OTWAAWTO",
                    "OTTWWtTO",
                    "OTTTTTtO",
                    "OOOOOOOO",
                ]
            elif outfit == "vest_shirt":
                torso = [
                    "OOOOOOOO",
                    "OTWKKWTO",
                    "OTTWWtTO",
                    "OTTWWtTO",
                    "OTTOOTtO",
                    "OOOOOOOO",
                ]
            elif outfit == "overalls":
                torso = [
                    "OOOOOOOO",
                    "OTBTTBTO",
                    "OTBBBBTO",
                    "OTBBBBbO",
                    "OTBBBBbO",
                    "OOOOOOOO",
                ]
            elif outfit == "tank_top":
                torso = [
                    "OOOOOOOO",
                    "OKTTTTKO",
                    "OTTTTTTO",
                    "OTTTTTtO",
                    "OTTtttTO",
                    "OOOOOOOO",
                ]
            else:
                torso = [
                    "OOOOOOOO",
                    "OTTKKTTO",
                    "OTTTTTTO",
                    "OTTTTTtO",
                    "OTTtttTO",
                    "OOOOOOOO",
                ]
        else:
            torso = [
                "OOOOOOOO",
                "OTTTTTTO",
                "OTTTTTTO",
                "OTTTTTtO",
                "OTTtttTO",
                "OOOOOOOO",
            ]
        stamp(10, 19, torso)

        # 2. Brazos pegados al torso (x: 8..9 izquierda, x: 18..19 derecha)
        bare_arm = outfit == "tank_top"
        short_sleeve = outfit in ("tshirt_jeans", "dress_skirt", "overalls", "vest_shirt")
        if bare_arm:
            arm_l = ["OO", "KO", "KO", "KO", "kO", "OO"]
            arm_r = ["OO", "OK", "OK", "OK", "Ok", "OO"]
        elif short_sleeve:
            c_top = "W" if outfit == "vest_shirt" else "T"
            arm_l = ["OO", f"{c_top}O", f"{c_top}O", "KO", "kO", "OO"]
            arm_r = ["OO", f"O{c_top}", f"O{c_top}", "OK", "Ok", "OO"]
        else:
            arm_l = ["OO", "TO", "TO", "tO", "KO", "OO"]
            arm_r = ["OO", "OT", "OT", "Ot", "OK", "OO"]

        if direction in ("down", "up"):
            stamp(8, 20 + arm_l_dy, arm_l)
            stamp(18, 20 + arm_r_dy, arm_r)
        else:
            ax = 12 + (1 if walk_frame == 1 else (-1 if walk_frame == 3 else 0))
            stamp(ax, 20, ["OOOO", "OTTO", "OTtO", "OKkO", "OOOO"])

        # 3. Piernas JUNTAS con costura central oscura (x: 10..17, y: 25..30, idénticas a ref_sprites.png)
        shoe_c = "W" if shoe_style == "sneakers" else "Z"
        if outfit == "dress_skirt":
            # Falda + piernas juntas con zapatos
            stamp(10, 24, [
                "OOOOOOOO",
                "OBBBBBbO",
                "OBBBBBbO",
                "OOOOOOOO",
            ])
            l_row = "OKkO" if leg_l_dy == 0 else "OZZO"
            r_row = "OKkO" if leg_r_dy == 0 else "OZZO"
            stamp(10, 27, [
                f"{l_row}{r_row}",
                f"OZZOOZZO",
                f"O{shoe_c}zOO{shoe_c}zO",
                "OOOOOOOO",
            ])
        else:
            l_leg = "OBbO" if leg_l_dy == 0 else "OZZO"
            r_leg = "OBbO" if leg_r_dy == 0 else "OZZO"
            stamp(10, 25, [
                "OBbOOBbO",
                f"{l_leg}{r_leg}",
                "OZZOOZZO",
                f"O{shoe_c}zOO{shoe_c}zO",
                "OOOOOOOO",
            ])

    def _draw_accessory(self, stamp, acc: str, direction: str):
        if acc == "none":
            return

        if acc == "fedora":
            stamp(4, 3, [
                ".....OOOOOOOOOO.....",
                "....OODDDDDDDDOO....",
                "...OODDDDDDDDDDOO...",
                "...OOAAAAAAAAAAOO...",
                "OOOOOOOOOOOOOOOOOOOO",
            ])
        elif acc == "witch_hat":
            stamp(4, 1, [
                "........OOOOO.......",
                ".......OODDDDOO.....",
                "......OODDDDDDOO....",
                ".....OODDDDDDDDO....",
                "....OODDDDDDDDOO....",
                "...OOAAAYYYAAAAOO...",
                "OOOOOOOOOOOOOOOOOOOO",
            ])
        elif acc == "top_hat":
            stamp(5, 1, [
                "...OOOOOOOOOOOO...",
                "...OONNNNNNNNOO...",
                "...OONNNNNNNNOO...",
                "...OONNNNNNNNOO...",
                "...OOAAAAAAAAOO...",
                "OOOOOOOOOOOOOOOOOO",
            ])
        elif acc == "straw_hat":
            stamp(4, 3, [
                ".....OOOOOOOOOO.....",
                "....OOFFFFFFFFOO....",
                "...OOFFFFFFFFFFOO...",
                "...OOAAAAAAAAAAOO...",
                "OOOOOOOOOOOOOOOOOOOO",
                ".OOffffffffffffffOO.",
            ])
        elif acc == "viking_helmet":
            stamp(3, 2, [
                ".OO................OO.",
                "OWWO...OOOOOOOO...OWWO",
                "OWWOO.OOMMMMMMOO.OOWWO",
                ".OOWWOOMMMMMMMMOOWWOO.",
                "..OOOOOMMMMMMMMOOOOO..",
                ".....OOmmmmmmmmOO.....",
                ".....OOOOOOOOOOOO.....",
            ])
        elif acc == "nurse_cap":
            stamp(7, 3, [
                "..OOOOOOOOOO..",
                ".OOWWWWWWWWOO.",
                "OOWWWWAAWWWWOO",
                "OOWWWAAAAWWWOO",
                "OOWWWWAAWWWWOO",
                ".OOOOOOOOOOOO.",
            ])
        elif acc == "aviator_goggles":
            stamp(6, 4, [
                "..OOOOOOOOOOOO..",
                ".OOFFFFFFFFFFOO.",
                "OOFFFFFFFFFFFFOO",
                "OOffffffffffffOO",
            ])
            if direction != "up":
                stamp(8, 11, [
                    "OOOOOOOOOOOO",
                    "OGgGGOOGgGGO",
                    "OGGGGOOGGGGO",
                    "OOOOOOOOOOOO",
                ])
        elif acc == "glasses" and direction != "up":
            if direction == "down":
                stamp(8, 12, [
                    "OOOOO..OOOOO",
                    "OGgGOOOOGgGO",
                    "OGGGO..OGGGO",
                    "OOOOO..OOOOO",
                ])
            else:
                stamp(7, 12, [
                    "OOOO.OOOO",
                    "OGgGOOGgGO",
                    "OGGGOOGGGO",
                    "OOOO.OOOO",
                ])
        elif acc == "headphones":
            if direction in ("down", "up"):
                stamp(5, 5, [
                    "....OOOOOOOOOO....",
                    "..OOAAAAAAAAAAOO..",
                    ".OO............OO.",
                    ".OO............OO.",
                    "OOAO..........OAOO",
                    "OAAO..........OAAO",
                    "OAAO..........OAAO",
                    "OOOO..........OOOO",
                ])
            else:
                stamp(12, 5, [
                    ".OOOO.",
                    "OAAAO.",
                    ".OAAO.",
                    ".OAAO.",
                    "OAAAAO",
                    "OAeeAO",
                    "OAAAAO",
                    ".OOOO.",
                ])


SPRITE_ENGINE = ChibiSpriteRenderer()
