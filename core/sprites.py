# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Sprites Pixel Art Chibi (4 Direcciones + Animación)
Renderiza personajes estilo Chibi Pixel Art con contorno oscuro (#23110d) inspirados
en la imagen de referencia adjunta por el usuario, con soporte completo para:
  - 4 Direcciones: "down" (Adelante), "up" (Atrás), "left" (Izquierda), "right" (Derecha)
  - 4 Frames de caminata (0: reposo, 1: paso izq, 2: neutro, 3: paso der)
  - Personalización por capas: Piel, Cara/Expresión, Pelo (9 estilos), Ropa (8 estilos),
    Zapatos (3 estilos) y Accesorios/Sombreros (10 estilos).
  - Caché de QPixmap de alta velocidad para renderizado a 60 FPS en PyQt6.
"""

from typing import Dict, Any, Tuple, Optional
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor


OUTLINE = "#23110d"
WHITE = "#fff8f0"


def _darken(hex_color: str, factor: float = 0.78) -> str:
    c = QColor(hex_color or "#38bdf8")
    return QColor(
        max(0, int(c.red() * factor)),
        max(0, int(c.green() * factor)),
        max(0, int(c.blue() * factor)),
    ).name()


def _lighten(hex_color: str, factor: float = 1.22) -> str:
    c = QColor(hex_color or "#38bdf8")
    return QColor(
        min(255, int(c.red() * factor)),
        min(255, int(c.green() * factor)),
        min(255, int(c.blue() * factor)),
    ).name()


class ChibiSpriteRenderer:
    """
    Genera y almacena en caché sprites de 22x28 píxeles lógicos escalados con Nearest-Neighbor
    para conservar bordes 100% pixel art nítidos.
    """

    GRID_W = 22
    GRID_H = 28

    def __init__(self):
        self._cache: Dict[Tuple, QPixmap] = {}

    def clear_cache(self):
        self._cache.clear()

    def _char_cache_key(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        scale: int,
        is_typing: bool = False,
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
        key = self._char_cache_key(char, direction, walk_frame, scale, is_typing)
        if key in self._cache:
            return self._cache[key]

        img = self._render_grid_image(char, direction, walk_frame % 4, is_typing)
        scaled = img.scaled(
            self.GRID_W * scale,
            self.GRID_H * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        pix = QPixmap.fromImage(scaled)
        if len(self._cache) > 1200:
            self._cache.clear()
        self._cache[key] = pix
        return pix

    def _render_grid_image(
        self,
        char: Dict[str, Any],
        direction: str,
        walk_frame: int,
        is_typing: bool,
    ) -> QImage:
        # Si es "right", renderizamos "left" y espejamos horizontalmente para simetría pixel-perfect
        if direction == "right":
            left_img = self._render_grid_image(char, "left", walk_frame, is_typing)
            return left_img.mirrored(True, False)

        img = QImage(self.GRID_W, self.GRID_H, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        skin = char.get("skin_color", "#ffcca8")
        skin_sh = _darken(skin, 0.86)
        face_style = char.get("face_style", "smile")
        hair_style = char.get("hair_style", "short_parted")
        hair_col = char.get("hair_color", "#eab308")
        hair_sh = _darken(hair_col, 0.76)
        hair_hi = _lighten(hair_col, 1.18)
        outfit = char.get("outfit_style", "suit_tie")
        top_col = char.get("top_color", "#334155")
        top_sh = _darken(top_col, 0.75)
        bot_col = char.get("bottom_color", "#1e293b")
        bot_sh = _darken(bot_col, 0.75)
        shoe_style = char.get("shoe_style", "classic")
        shoe_col = char.get("shoe_color", "#451a03")
        acc = char.get("accessory", "none")
        acc_col = char.get("accessory_color", "#ef4444")

        def px(x: int, y: int, c: str):
            if 0 <= x < self.GRID_W and 0 <= y < self.GRID_H:
                img.setPixelColor(x, y, QColor(c))

        def rect(x0: int, y0: int, w: int, h: int, c: str):
            qc = QColor(c)
            for yy in range(y0, y0 + h):
                for xx in range(x0, x0 + w):
                    if 0 <= xx < self.GRID_W and 0 <= yy < self.GRID_H:
                        img.setPixelColor(xx, yy, qc)

        # Desplazamientos de piernas y brazos por caminata
        leg_l_dy = -1 if walk_frame == 1 else (0 if walk_frame != 3 else 0)
        leg_r_dy = -1 if walk_frame == 3 else 0
        arm_l_dy = 1 if (walk_frame == 1 or is_typing) else (-1 if walk_frame == 3 else 0)
        arm_r_dy = -1 if (walk_frame == 1 or is_typing) else (1 if walk_frame == 3 else 0)

        # ---------------------------------------------------------------------
        # 1. PELO TRASERO (Para estilos largos o cuando mira hacia adelante/lado)
        # ---------------------------------------------------------------------
        if hair_style == "long_straight" and direction in ("down", "left"):
            rect(5, 11, 12, 8, OUTLINE)
            rect(6, 11, 10, 7, hair_sh)
        elif hair_style == "wavy_bob" and direction in ("down", "left"):
            rect(4, 10, 14, 6, OUTLINE)
            rect(5, 10, 12, 5, hair_sh)
        elif hair_style == "ponytail":
            if direction == "down":
                # Coleta asomando a la derecha con moño (igual a fila 3 col 1 de la imagen)
                rect(15, 7, 4, 6, OUTLINE)
                rect(16, 8, 2, 4, hair_col)
                px(15, 7, acc_col)
                px(16, 7, WHITE)
            elif direction == "left":
                rect(15, 8, 5, 6, OUTLINE)
                rect(16, 9, 3, 4, hair_col)
                px(15, 8, acc_col)
        elif hair_style == "pigtails" and direction in ("down", "up"):
            # Dos coletas altas a ambos lados
            rect(2, 6, 4, 7, OUTLINE)
            rect(3, 7, 2, 5, hair_col)
            rect(16, 6, 4, 7, OUTLINE)
            rect(17, 7, 2, 5, hair_col)
            px(5, 7, acc_col)
            px(16, 7, acc_col)
        elif hair_style == "top_bun":
            # Moño alto en la coronilla
            rect(8, 2, 6, 4, OUTLINE)
            rect(9, 3, 4, 2, hair_col)

        # ---------------------------------------------------------------------
        # 2. PIERNAS Y ZAPATOS (y: 21..26)
        # ---------------------------------------------------------------------
        if outfit == "cloak":
            # Capa larga de mago/arquitecto hasta los pies
            rect(6, 16, 10, 10, OUTLINE)
            rect(7, 16, 8, 9, top_col)
            rect(10, 16, 2, 9, top_sh)
            # Punta de zapatos asomando abajo
            rect(6, 25, 4, 2, OUTLINE)
            rect(12, 25, 4, 2, OUTLINE)
            px(7, 25, shoe_col)
            px(13, 25, shoe_col)
        else:
            # Pierna Izquierda (x: 7..10) y Pierna Derecha (x: 11..14)
            if direction in ("down", "up"):
                # Contorno exterior de piernas y separación central en x=10,11
                rect(7, 20, 4, 7 + leg_l_dy, OUTLINE)
                rect(11, 20, 4, 7 + leg_r_dy, OUTLINE)

                if outfit == "dress_skirt":
                    # Falda en y: 20..22 + piernas color piel en y: 23..24
                    rect(7, 20, 8, 3, OUTLINE)
                    rect(8, 20, 6, 2, bot_col)
                    rect(8, 22, 2, 2 + leg_l_dy, skin)
                    rect(12, 22, 2, 2 + leg_r_dy, skin)
                else:
                    # Pantalón
                    rect(8, 20, 2, 4 + leg_l_dy, bot_col)
                    rect(12, 20, 2, 4 + leg_r_dy, bot_col)

                # Zapatos
                sy_l = 24 + leg_l_dy
                sy_r = 24 + leg_r_dy
                rect(8, sy_l, 2, 2, shoe_col)
                rect(12, sy_r, 2, 2, shoe_col)
                if shoe_style == "sneakers":
                    px(8, sy_l + 1, WHITE)
                    px(12, sy_r + 1, WHITE)
                elif shoe_style == "boots":
                    rect(8, sy_l - 1, 2, 2, shoe_col)
                    rect(12, sy_r - 1, 2, 2, shoe_col)
            else:
                # Vista lateral ("left"): piernas de perfil con paso adelante/atrás
                step_spread = 1 if walk_frame in (1, 3) else 0
                rect(8 - step_spread, 20, 6 + step_spread * 2, 7, OUTLINE)
                if outfit == "dress_skirt":
                    rect(9 - step_spread, 20, 4 + step_spread, 2, bot_col)
                    rect(9 - step_spread, 22, 2, 2, skin)
                    rect(11, 22, 2, 2, skin_sh)
                else:
                    rect(9 - step_spread, 20, 2, 4, bot_col)
                    rect(11, 20, 2, 4, bot_sh)
                rect(9 - step_spread, 24, 2, 2, shoe_col)
                rect(11, 24, 2, 2, _darken(shoe_col, 0.8))
                if shoe_style == "sneakers":
                    px(9 - step_spread, 25, WHITE)

        # ---------------------------------------------------------------------
        # 3. TORSO Y BRAZOS (y: 15..20)
        # ---------------------------------------------------------------------
        if outfit != "cloak":
            # Torso central (x: 7..14, y: 15..20)
            rect(7, 15, 8, 6, OUTLINE)
            rect(8, 16, 6, 4, top_col)

            # Detalles del torso según el estilo de ropa
            if direction == "down":
                if outfit == "suit_tie":
                    # Camisa blanca y corbata
                    rect(10, 16, 2, 3, WHITE)
                    px(10, 16, acc_col)
                    px(11, 17, acc_col)
                elif outfit == "vest_shirt":
                    rect(10, 16, 2, 4, WHITE)
                    px(10, 18, OUTLINE)
                elif outfit == "overalls":
                    # Tirantes y pechera de jardinera en bottom_color
                    rect(9, 17, 4, 3, bot_col)
                    px(9, 16, bot_col)
                    px(12, 16, bot_col)
                elif outfit == "hoodie":
                    rect(9, 18, 4, 2, top_sh)
                elif outfit == "tank_top":
                    px(10, 16, skin)
                    px(11, 16, skin)

            # Brazos
            arm_skin = outfit in ("tshirt_jeans", "tank_top", "dress_skirt", "overalls")
            sleeve_c = skin if outfit == "tank_top" else (WHITE if outfit == "vest_shirt" else top_col)

            if direction in ("down", "up"):
                # Brazo izquierdo (x: 5..6) y derecho (x: 15..16)
                rect(5, 16 + arm_l_dy, 3, 5, OUTLINE)
                rect(6, 17 + arm_l_dy, 1, 2, sleeve_c)
                px(6, 19 + arm_l_dy, skin if arm_skin else sleeve_c)
                px(6, 19 + arm_l_dy, skin)

                rect(14, 16 + arm_r_dy, 3, 5, OUTLINE)
                rect(15, 17 + arm_r_dy, 1, 2, sleeve_c)
                px(15, 19 + arm_r_dy, skin)
            else:
                # Vista lateral ("left"): brazo visible en el centro del torso con balanceo
                ax = 10 + (1 if walk_frame == 1 else (-1 if walk_frame == 3 else 0))
                rect(ax, 16, 4, 5, OUTLINE)
                rect(ax + 1, 17, 2, 2, sleeve_c)
                rect(ax + 1, 19, 2, 1, skin)

        # ---------------------------------------------------------------------
        # 4. CABEZA CHIBI CON CONTORNO COMPLETO (y: 5..15, x: 5..16)
        # ---------------------------------------------------------------------
        # Contorno redondeado de la cabeza
        rect(6, 5, 10, 11, OUTLINE)
        rect(5, 6, 12, 9, OUTLINE)
        # Relleno de piel
        rect(6, 6, 10, 9, skin)
        # Sombra sutil en el borde inferior de la barbilla
        rect(7, 14, 8, 1, skin_sh)

        # ---------------------------------------------------------------------
        # 5. RASGOS DE LA CARA SEGÚN DIRECCIÓN
        # ---------------------------------------------------------------------
        if direction == "down":
            # Ojos verticales 1x2 estilo imagen de referencia
            rect(8, 9, 1, 2, OUTLINE)
            rect(13, 9, 1, 2, OUTLINE)
            if face_style == "cool":
                px(13, 9, skin)  # Guiño

            # Boca / Sonrisa pixelada (╰‿╯)
            if face_style in ("smile", "happy"):
                px(9, 12, OUTLINE)
                px(10, 13, OUTLINE)
                px(11, 13, OUTLINE)
                px(12, 12, OUTLINE)
                if face_style == "happy":
                    px(7, 11, "#f472b6")
                    px(14, 11, "#f472b6")
            elif face_style == "focused":
                rect(9, 12, 4, 1, OUTLINE)
            elif face_style == "cool":
                px(10, 13, OUTLINE)
                px(11, 13, OUTLINE)
                px(12, 12, OUTLINE)

        elif direction == "left":
            # Ojos y sonrisa desplazados a la izquierda (perfil 3/4)
            rect(7, 9, 1, 2, OUTLINE)
            rect(10, 9, 1, 2, OUTLINE)
            px(8, 12, OUTLINE)
            px(9, 13, OUTLINE)
            px(10, 12, OUTLINE)

        # ---------------------------------------------------------------------
        # 6. PELO SUPERIOR / FRONTAL / TRASERO SEGÚN DIRECCIÓN
        # ---------------------------------------------------------------------
        if hair_style != "bald":
            if direction == "up":
                # Vista trasera ("up"): el cabello cubre toda la nuca
                rect(6, 5, 10, 10, OUTLINE)
                rect(5, 6, 12, 8, OUTLINE)
                rect(6, 6, 10, 8, hair_col)
                rect(7, 12, 8, 2, hair_sh)
                rect(8, 7, 6, 1, hair_hi)
                if hair_style == "long_straight":
                    rect(5, 12, 12, 7, OUTLINE)
                    rect(6, 12, 10, 6, hair_col)
                    rect(7, 16, 8, 2, hair_sh)
                elif hair_style == "ponytail":
                    rect(9, 8, 4, 8, OUTLINE)
                    rect(10, 9, 2, 6, hair_sh)
                    rect(10, 8, 2, 1, acc_col)
                elif hair_style == "flat_top":
                    rect(5, 3, 12, 5, OUTLINE)
                    rect(6, 4, 10, 4, hair_col)
            elif direction == "down":
                if hair_style == "flat_top":
                    rect(5, 3, 12, 5, OUTLINE)
                    rect(6, 4, 10, 3, hair_col)
                    rect(6, 7, 1, 3, hair_col)
                    rect(15, 7, 1, 3, hair_col)
                elif hair_style == "receding":
                    rect(6, 5, 10, 2, OUTLINE)
                    rect(6, 6, 2, 3, hair_col)
                    rect(14, 6, 2, 3, hair_col)
                else:
                    # Casquete de cabello frontal con flequillo y volumen como en ref_sprites.png
                    rect(5, 4, 12, 4, OUTLINE)
                    rect(6, 5, 10, 3, hair_col)
                    rect(7, 5, 6, 1, hair_hi)
                    # Mechones laterales
                    rect(6, 7, 2, 3, hair_col)
                    rect(14, 7, 2, 3, hair_col)
                    px(8, 7, hair_sh)
            elif direction == "left":
                if hair_style == "flat_top":
                    rect(5, 3, 12, 5, OUTLINE)
                    rect(6, 4, 10, 3, hair_col)
                    rect(12, 7, 4, 6, hair_col)
                else:
                    rect(5, 4, 12, 4, OUTLINE)
                    rect(6, 5, 10, 3, hair_col)
                    # Parte posterior del pelo a la derecha (nuca de perfil)
                    rect(12, 7, 4, 7, hair_col)
                    rect(15, 7, 2, 7, OUTLINE)
                    if hair_style == "long_straight":
                        rect(12, 12, 5, 7, OUTLINE)
                        rect(13, 12, 3, 6, hair_col)

        # ---------------------------------------------------------------------
        # 7. ACCESORIOS Y SOMBREROS (Los 10 estilos de la imagen de referencia)
        # ---------------------------------------------------------------------
        if acc == "headphones":
            if direction in ("down", "up"):
                rect(4, 8, 2, 5, OUTLINE)
                px(5, 9, acc_col)
                px(5, 10, acc_col)
                rect(16, 8, 2, 5, OUTLINE)
                px(16, 9, acc_col)
                px(16, 10, acc_col)
                rect(6, 4, 10, 1, acc_col)
            else:
                rect(11, 8, 3, 5, OUTLINE)
                rect(12, 9, 1, 3, acc_col)
                rect(11, 4, 2, 5, acc_col)

        elif acc == "glasses" and direction in ("down", "left"):
            if direction == "down":
                rect(7, 8, 3, 3, OUTLINE)
                rect(12, 8, 3, 3, OUTLINE)
                rect(10, 9, 2, 1, OUTLINE)
                px(8, 9, "#bae6fd")
                px(13, 9, "#bae6fd")
            else:
                rect(6, 8, 3, 3, OUTLINE)
                rect(9, 8, 3, 3, OUTLINE)
                px(7, 9, "#bae6fd")
                px(10, 9, "#bae6fd")

        elif acc == "fedora":
            # Sombrero detective con ala ancha y cinta (fila 1 col 1)
            rect(3, 5, 16, 2, OUTLINE)
            rect(6, 2, 10, 4, OUTLINE)
            rect(7, 3, 8, 2, "#475569")
            rect(7, 4, 8, 1, acc_col)

        elif acc == "witch_hat":
            # Sombrero de mago con punta y hebilla dorada (fila 1 col 2)
            rect(3, 5, 16, 2, OUTLINE)
            rect(6, 2, 10, 4, OUTLINE)
            rect(8, 0, 7, 3, OUTLINE)
            rect(7, 3, 8, 2, "#334155")
            rect(9, 1, 4, 2, "#334155")
            rect(7, 4, 8, 1, acc_col)
            px(10, 4, "#facc15")

        elif acc == "top_hat":
            # Sombrero de copa (fila 1 col 3)
            rect(4, 5, 14, 2, OUTLINE)
            rect(6, 1, 10, 5, OUTLINE)
            rect(7, 2, 8, 3, "#1e293b")
            rect(7, 4, 8, 1, acc_col)

        elif acc == "aviator_goggles":
            # Casco con gafas celestes (fila 1 col 4)
            rect(5, 4, 12, 4, OUTLINE)
            rect(6, 5, 10, 2, "#eab308")
            if direction != "up":
                rect(7, 8, 8, 3, OUTLINE)
                rect(8, 9, 6, 1, "#7dd3fc")

        elif acc == "viking_helmet":
            # Casco vikingo con cuernos (fila 2 col 1)
            rect(5, 4, 12, 4, OUTLINE)
            rect(6, 5, 10, 2, "#64748b")
            rect(3, 2, 3, 4, OUTLINE)
            px(4, 3, WHITE)
            rect(16, 2, 3, 4, OUTLINE)
            px(17, 3, WHITE)

        elif acc == "nurse_cap":
            # Gorro blanco con cruz (fila 2 col 3)
            rect(6, 2, 10, 5, OUTLINE)
            rect(7, 3, 8, 3, WHITE)
            if direction != "up":
                px(10, 4, acc_col)
                px(11, 4, acc_col)

        elif acc == "straw_hat":
            # Sombrero de paja (fila 3 col 4)
            rect(3, 5, 16, 2, OUTLINE)
            rect(6, 2, 10, 4, OUTLINE)
            rect(7, 3, 8, 2, "#facc15")
            rect(4, 5, 14, 1, "#eab308")

        return img


# Instancia global compartida para reutilizar caché de pixmaps
SPRITE_ENGINE = ChibiSpriteRenderer()
