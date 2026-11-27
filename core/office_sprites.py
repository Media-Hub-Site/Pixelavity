# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Sprites de Oficina Estilo Pixel Agents (16px por Celda Nativo)
Dibuja pisos, paredes auto-tileadas, muebles, PCs retro CRT, libreros, sofás carmesí,
plantas y decoración con exactamente la misma densidad de píxeles que los personajes 16x32.
"""

from typing import Dict, Any, Tuple, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QColor, QPainter

from core.customization import FLOOR_MATERIALS, WALL_MATERIALS


# Paleta unificada Pixel Agents para muebles, madera cálida, CRT, plantas y sofás
OFFICE_PALETTE: Dict[str, str] = {
    "O": "#18161e",  # Contorno oscuro nítido
    "d": "#2d1b12",  # Contorno madera muy oscuro
    # Madera roble miel (escritorios, mesas, sillas, libreros)
    "W": "#d9a973",  # Brillo madera
    "w": "#c4925c",  # Madera clara
    "m": "#a67443",  # Madera media
    "M": "#7d522c",  # Madera sombra
    "n": "#54351c",  # Madera profunda
    # PC retro beige / plata / pantalla
    "C": "#ece9df",  # Carcasa beige muy clara
    "c": "#d2cec2",  # Carcasa beige media
    "g": "#9e9a8f",  # Gris sombra carcasa / papelera
    "G": "#666b78",  # Gris oscuro
    "s": "#242b38",  # Pantalla apagada
    "S": "#112a22",  # Pantalla encendida oscura
    "e": "#34d399",  # Código verde
    "b": "#38bdf8",  # Código cyan
    "y": "#fde047",  # Amarillo / oro
    "Y": "#ca8a04",  # Oro sombra
    # Sofá / alfombra carmesí-burdeos
    "R": "#c95078",  # Brillo tapiz rosa-burdeos
    "r": "#a8365c",  # Tapiz medio
    "v": "#7d2141",  # Tapiz sombra
    "V": "#4a1125",  # Tapiz oscuro
    "K": "#a31c24",  # Rojo alfombra
    "k": "#d8b786",  # Borde crema dorado alfombra
    # Plantas verdes + maceta terracota
    "L": "#5cb860",  # Hoja brillo
    "l": "#368a47",  # Hoja media
    "f": "#1d5730",  # Hoja oscura
    "P": "#b56a3f",  # Maceta clara
    "p": "#7d4323",  # Maceta oscura
    # Libros coloridos y varios
    "B": "#3b82f6",  # Libro azul
    "E": "#ef4444",  # Libro rojo
    "U": "#f5f0e1",  # Blanco cálido (pizarra / taza / papel)
    "u": "#cbd5e1",  # Sombra blanca
    "T": "#14b8a6",  # Teal brillante
    "t": "#0f766e",  # Teal oscuro
    "Q": "#e0f7ff",  # Agua / vapor / cristal
}


def _stamp_rows(img: QImage, x0: int, y0: int, rows: List[str], pal: Dict[str, str]):
    w, h = img.width(), img.height()
    for dy, row in enumerate(rows):
        yy = y0 + dy
        if not (0 <= yy < h):
            continue
        for dx, ch in enumerate(row):
            if ch in (".", " "):
                continue
            xx = x0 + dx
            if 0 <= xx < w and ch in pal:
                img.setPixelColor(xx, yy, QColor(pal[ch]))


def _scale_pix(img: QImage, scale: int) -> QPixmap:
    if scale == 1:
        return QPixmap.fromImage(img)
    return QPixmap.fromImage(
        img.scaled(
            img.width() * scale,
            img.height() * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    )


class OfficeSpriteRenderer:
    """Genera y cachea sprites nativos 16px/celda para todo el entorno de oficina."""

    NATIVE_TILE = 16

    def __init__(self):
        self._cache: Dict[Tuple, Any] = {}

    def clear_cache(self):
        self._cache.clear()

    # =========================================================================
    # PISOS (16x16 NATIVO)
    # =========================================================================
    def get_floor_pixmap(self, material_id: str, scale: int = 2) -> QPixmap:
        key = ("floor", material_id, scale)
        if key in self._cache:
            return self._cache[key]

        mat = FLOOR_MATERIALS.get(material_id, FLOOR_MATERIALS["cream_tile"])
        cA = QColor(mat["colorA"])
        cB = QColor(mat["colorB"])
        grout = QColor(mat.get("grout", mat["colorB"]))
        pat = mat.get("pattern", "office_tile")

        img = QImage(16, 16, QImage.Format.Format_ARGB32)
        img.fill(cA)

        if pat == "office_tile":
            # Baldosa 16x16 estilo Referencia 1: borde junta sutil, centro crema cálido
            hi = QColor(cA).lighter(104)
            for y in range(16):
                for x in range(16):
                    if x == 15 or y == 15:
                        img.setPixelColor(x, y, grout)
                    elif x == 0 or y == 0:
                        img.setPixelColor(x, y, hi)
                    elif x == 14 or y == 14:
                        img.setPixelColor(x, y, cB)
        elif pat == "planks":
            for y in range(16):
                for x in range(16):
                    if y in (0, 8):
                        img.setPixelColor(x, y, grout)
                    elif (y < 8 and x == 8) or (y >= 8 and x == 2):
                        img.setPixelColor(x, y, grout)
                    elif y % 8 in (1, 2):
                        img.setPixelColor(x, y, cA)
                    elif y % 8 in (6, 7):
                        img.setPixelColor(x, y, cB)
        elif pat == "checkers":
            for y in range(16):
                for x in range(16):
                    quad = ((x // 8) + (y // 8)) % 2
                    img.setPixelColor(x, y, cA if quad == 0 else cB)
                    if x in (0, 8) or y in (0, 8):
                        img.setPixelColor(x, y, grout)
        elif pat == "carpet":
            for y in range(16):
                for x in range(16):
                    img.setPixelColor(x, y, cA if ((x + y) % 2 == 0 or (x * 3 + y) % 5 != 0) else cB)
        elif pat == "grate":
            img.fill(cA)
            for y in range(16):
                for x in range(16):
                    if x in (0, 15) or y in (0, 15):
                        img.setPixelColor(x, y, grout)
                    elif (x % 4 == 2) and (y % 4 == 2):
                        img.setPixelColor(x, y, cB)

        pix = _scale_pix(img, scale)
        self._cache[key] = pix
        return pix

    # =========================================================================
    # PAREDES AUTO-TILEADAS (16x16 NATIVO, ESTILO REFERENCIA 1)
    # =========================================================================
    def get_wall_pixmap(
        self,
        wall_id: str,
        has_north: bool,
        has_south: bool,
        has_west: bool,
        has_east: bool,
        scale: int = 2,
    ) -> QPixmap:
        key = ("wall", wall_id, has_north, has_south, has_west, has_east, scale)
        if key in self._cache:
            return self._cache[key]

        wspec = WALL_MATERIALS.get(wall_id, WALL_MATERIALS["dark_tech"])
        top_c = QColor(wspec["top"])
        front_c = QColor(wspec["front"])
        trim_c = QColor(wspec.get("trim", wspec["top"]))
        border_c = QColor(wspec["border"])

        img = QImage(16, 16, QImage.Format.Format_ARGB32)
        img.fill(top_c)

        if not has_south:
            # Cara frontal visible del muro (como el muro superior de Referencia 1)
            for y in range(4, 15):
                for x in range(16):
                    img.setPixelColor(x, y, front_c)
            for x in range(16):
                img.setPixelColor(x, 4, border_c)
                img.setPixelColor(x, 14, trim_c)
                img.setPixelColor(x, 15, border_c)
            if wall_id == "brick_wall":
                for y in (7, 11):
                    for x in range(16):
                        img.setPixelColor(x, y, trim_c)
                for x in (4, 12):
                    for y in range(5, 8):
                        img.setPixelColor(x, y, trim_c)
                for x in (0, 8):
                    for y in range(8, 12):
                        img.setPixelColor(x, y, trim_c)
        else:
            # Tope arquitectónico visto desde arriba (muros laterales/verticales)
            bevel = QColor(top_c).lighter(115)
            if not has_north:
                for x in range(16):
                    img.setPixelColor(x, 1, bevel)

        # Contornos exteriores limpios en los bordes expuestos
        if not has_north:
            for x in range(16):
                img.setPixelColor(x, 0, border_c)
        if not has_west:
            for y in range(16):
                img.setPixelColor(0, y, border_c)
        if not has_east:
            for y in range(16):
                img.setPixelColor(15, y, border_c)

        pix = _scale_pix(img, scale)
        self._cache[key] = pix
        return pix

    # =========================================================================
    # SILLAS DE OFICINA (16x18 NATIVO -> OVERHANG 2px)
    # =========================================================================
    def get_chair_sprite(self, chair_kind: str = "wood", scale: int = 2) -> Tuple[QPixmap, int]:
        key = ("chair", chair_kind, scale)
        if key in self._cache:
            return self._cache[key]

        img = QImage(16, 18, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        if chair_kind == "gaming":
            _stamp_rows(img, 3, 2, [
                ".OOOOOOOO.",
                "OttttttttO",
                "OtTTTTTTtO",
                "OtTTbbTTtO",
                "OttttttttO",
                ".OmmmmmmO.",
                "OGGGGGGGGO",
                "OGGggggGGO",
                ".OOOOOOOO.",
                "....OO....",
                "..OOOOOO..",
                "..O....O..",
            ], OFFICE_PALETTE)
        else:
            # Silla de madera estilo Pixel Agents (Referencia 1)
            _stamp_rows(img, 3, 3, [
                ".OOOOOOOO.",
                "OwwwwwwwwO",
                "OwmmwwmmwO",
                "OmmmmmmmmO",
                "OwwwwwwwwO",
                "OmmmmmmmmO",
                "OMMMMMMMMO",
                ".OOOOOOOO.",
                ".OM....MO.",
                ".On....nO.",
                ".OO....OO.",
            ], OFFICE_PALETTE)

        res = (_scale_pix(img, scale), 2 * scale)
        self._cache[key] = res
        return res

    # =========================================================================
    # MUEBLES, DISPOSITIVOS Y DECORACIÓN (16px/TILE + OVERHANG SUPERIOR)
    # =========================================================================
    def get_item_sprite(
        self,
        otype: str,
        is_active: bool = False,
        anim_tick: int = 0,
        scale: int = 2,
    ) -> Tuple[QPixmap, int]:
        """Devuelve (QPixmap escalado, overhang_y_px escalado arriba de su celda base)."""
        anim_phase = (anim_tick % 3) if is_active else 0
        key = ("item", otype, is_active, anim_phase, scale)
        if key in self._cache:
            return self._cache[key]

        overhang_native = 0
        if otype == "computer_desk":
            overhang_native = 6
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Escritorio de madera miel completo hasta el borde inferior (y=21)
            _stamp_rows(img, 0, overhang_native, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                ".dMMd......................dMMd.",
                ".dMMd......................dMMd.",
                ".dnnO......................Onnd.",
                "..dd........................dd..",
            ], OFFICE_PALETTE)
            scr = "S" if is_active else "s"
            # Monitor CRT principal + torre CPU horizontal + teclado
            _stamp_rows(img, 3, 0, [
                ".OOOOOOOO.",
                "OCCCCCCCCO",
                f"OC{scr * 6}CO",
                f"OC{scr * 6}CO",
                f"OC{scr * 6}CO",
                "OCCCCCCCCO",
                "OccccccggO",
                "OCCCCCCCCO",
                "OcGGGGGGcO",
                ".OOOOOOOO.",
                ".OCUUUUCO.",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)
            # Monitor secundario o impresora/lector + taza + mouse
            _stamp_rows(img, 18, 1, [
                "..OOOOOO..",
                ".OCCCCCCo.",
                f".OC{scr * 4}Co.",
                f".OC{scr * 4}Co.",
                ".OccccccO.",
                ".OOOOOOOO.",
                ".OCUUUUCO.",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 27, 9, ["OUUO", "UnUO", ".OO."], OFFICE_PALETTE)
            if is_active:
                c_line = "e" if anim_phase % 2 == 0 else "b"
                _stamp_rows(img, 5, 2, [f"{c_line * 4}.", f"..{c_line * 3}", f"{c_line * 5}"], OFFICE_PALETTE)
                _stamp_rows(img, 20, 3, [f"{c_line * 3}", "b.e"], OFFICE_PALETTE)

        elif otype == "laptop_desk":
            overhang_native = 6
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 0, overhang_native, [
                ".dWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnd",
                "dMMMMMMMMMMMMMMd",
                ".dMMd......dMMd.",
                ".dMMd......dMMd.",
                ".dnnO......Onnd.",
                "..dd........dd..",
            ], OFFICE_PALETTE)
            scr = "S" if is_active else "s"
            _stamp_rows(img, 3, 1, [
                ".OOOOOOOO.",
                "OCCCCCCCCO",
                f"OC{scr * 6}CO",
                f"OC{scr * 6}CO",
                "OccccccccO",
                "OCCCCCCCCO",
                "OcUUUUUUcO",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)
            if is_active:
                _stamp_rows(img, 5, 3, ["eee.b", "bb.ee"], OFFICE_PALETTE)

        elif otype in ("bookshelf", "bookshelf_single"):
            overhang_native = 6
            w_px = 32 if otype == "bookshelf" else 16
            img = QImage(w_px, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            if otype == "bookshelf":
                _stamp_rows(img, 0, 0, [
                    ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                    "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                    "dwOnnOnnOnnOnnOnnOnnOnnOnnOnnOwd",
                    "dwOEEOBBOllOUUOEeOyyOBBOllOEEOwd",
                    "dwOEEOBBOllOUUOEeOyyOBBOllOEEOwd",
                    "dwOEEOBBOllOUUOEeOyyOBBOllOEEOwd",
                    "dwOEEOBBOllOUUOEeOyyOBBOllOEEOwd",
                    "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                    "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                    "dmOnnOnnOnnOnnOnnOnnOnnOnnOnnOmM",
                    "dmOllOEEOyyOBBOUPOllOEEOBBOyyOmM",
                    "dmOllOEEOyyOBBOUPOllOEEOBBOyyOmM",
                    "dmOllOEEOyyOBBOUPOllOEEOBBOyyOmM",
                    "dmOllOEEOyyOBBOUPOllOEEOBBOyyOmM",
                    "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                    "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                    "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                    ".ddMMMMMMMMMMMMMMMMMMMMMMMMMMdd.",
                    "..dMMd....................dMMd..",
                ], OFFICE_PALETTE)
            else:
                _stamp_rows(img, 0, 0, [
                    ".dWWWWWWWWWWWWd.",
                    "dWWWWWWWWWWWWWWd",
                    "dwOnnOnnOnnOnOwd",
                    "dwOEEOBBOllOUOwd",
                    "dwOEEOBBOllOUOwd",
                    "dwOEEOBBOllOUOwd",
                    "dmmmmmmmmmmmmmmM",
                    "dnnnnnnnnnnnnnnd",
                    "dmOnnOnnOnnOnOmM",
                    "dmOllOyyOEEOBOmM",
                    "dmOllOyyOEEOBOmM",
                    "dmOllOyyOEEOBOmM",
                    "dMMMMMMMMMMMMMMd",
                    "dnnnnnnnnnnnnnnd",
                    "dMMMMMMMMMMMMMMd",
                    ".ddMMMMMMMMMMdd.",
                    "..dMMd....dMMd..",
                ], OFFICE_PALETTE)

        elif otype == "whiteboard":
            overhang_native = 4
            img = QImage(48, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 1, 1, [
                ".OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO.",
                "OGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGO",
                "OGUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGO",
                "OGU.GGGG....GG.G....UUU.bbbb....eee..y.y..UUGO",
                "OGU.G..G....GGG.....UUU.b..b....e....yyy..UUGO",
                "OGU.GGGG............UUU.bbbb....eee.......UUGO",
                "OGU.................UUU...................UUGO",
                "OGU..GGG...GG.......UUU..r.r...bbb..GGG...UUGO",
                "OGU..G.....GGG......UUU..rrr...b.b..G.....UUGO",
                "OGU.................UUU...................UUGO",
                "OGuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuGO",
                "OGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGO",
                ".OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO.",
                "....OO..................................OO....",
            ], OFFICE_PALETTE)

        elif otype == "coffee_sofa":
            overhang_native = 4
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 1, 3, [
                "..OOOOOOOOOOOOOOOOOOOOOOOOOO..",
                ".ORRRRRRRRRRRRRRRRRRRRRRRRRRO.",
                ".OrrrrrrrrrrrrrrrrrrrrrrrrrrO.",
                "OORvvvvvvvvvvvvvvvvvvvvvvvvROO",
                "ORrRRRRRRRRRRRRRRRRRRRRRRRRrRO",
                "ORrRRRRRRRRRRRvRRRRRRRRRRRRrRO",
                "ORrrrrrrrrrrrrvrrrrrrrrrrrrrrO",
                "ORrrrrrrrrrrrrvrrrrrrrrrrrrrrO",
                "ORrrrrrrrrrrrrvrrrrrrrrrrrrrrO",
                "OvvvvvvvvvvvvvvvvvvvvvvvvvvvvO",
                "OVVVVVVVVVVVVVVVVVVVVVVVVVVVVO",
                ".OOOOOOOOOOOOOOOOOOOOOOOOOOOO.",
                "..OO......................OO..",
                "..OO......................OO..",
            ], OFFICE_PALETTE)

        elif otype == "lounge_armchair":
            overhang_native = 4
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 1, 3, [
                "..OOOOOOOOOO..",
                ".ORRRRRRRRRRO.",
                "OORvvvvvvvvROO",
                "ORrRRRRRRRRrRO",
                "ORrrrrrrrrrrrO",
                "ORrrrrrrrrrrrO",
                "ORrrrrrrrrrrrO",
                "OvvvvvvvvvvvvO",
                "OVVVVVVVVVVVVO",
                ".OOOOOOOOOOOO.",
                "..OO......OO..",
                "..OO......OO..",
            ], OFFICE_PALETTE)

        elif otype == "coffee_table":
            overhang_native = 2
            img = QImage(32, 32 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 2, 4, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".ddMMMMMMMMMMMMMMMMMMMMMMMMdd.",
                ".dMMd....................dMMd.",
                ".dnnO....................Onnd.",
                "..dd......................dd..",
            ], OFFICE_PALETTE)
            # Dos tazas sobre la mesa de centro
            _stamp_rows(img, 8, 8, ["OUUO", "UnUO", ".OO."], OFFICE_PALETTE)
            _stamp_rows(img, 20, 11, ["OUUO", "UnUO", ".OO."], OFFICE_PALETTE)

        elif otype == "reading_table":
            overhang_native = 2
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 1, 2, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwOUUUOwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwOUGGOwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".dMMd......................dMMd.",
                ".dnnO......................Onnd.",
            ], OFFICE_PALETTE)

        elif otype == "meeting_table":
            overhang_native = 2
            img = QImage(48, 32 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 2, 3, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwOUUUOwwwwwwwwwwwwwwwwwwwwOUUOwwwwwwwwwd",
                "dwwwwwwOUssOwwwwwwwwwwwwwwwwwwwwOnUOwwwwwwwwwd",
                "dwwwwwwOUUUOwwwwwwwwwwwwwwwwwwwwwOOwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwOUUOwwwwwwwwwwwwOUUUOwwwwwwwwwwwwwwd",
                "dwwwwwwwwwOnUOwwwwwwwwwwwwOUssOwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwOOwwwwwwwwwwwwwOUUUOwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".ddMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMdd.",
                ".dMMd....................................dMMd.",
                ".dnnO....................................Onnd.",
            ], OFFICE_PALETTE)

        elif otype == "server_terminal":
            overhang_native = 6
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            blink_a = "e" if anim_phase % 2 == 0 else "y"
            blink_b = "b" if anim_phase % 2 == 0 else "e"
            _stamp_rows(img, 1, 0, [
                ".OOOOOOOOOOOOO..OOOOOOOOOOOOO.",
                "OGGGGGGGGGGGGGOOGGGGGGGGGGGGGO",
                "OGsssssssssssGOOGsssssssssssGO",
                f"OGs{blink_a}s{blink_b}ssssssGsGOOGs{blink_b}s{blink_a}ssssssGsGO",
                "OGsssssssssssGOOGsssssssssssGO",
                "OGGGGGGGGGGGGGOOGGGGGGGGGGGGGO",
                f"OGs{blink_b}seeeeeeeesGOOGs{blink_a}sbbbbbbbbsGO",
                "OGsssssssssssGOOGsssssssssssGO",
                "OGGGGGGGGGGGGGOOGGGGGGGGGGGGGO",
                "OGGggggggggggGOOGGggggggggggGO",
                f"OGs{blink_a}s{blink_b}ssssssGsGOOGs{blink_b}s{blink_a}ssssssGsGO",
                "OGGggggggggggGOOGGggggggggggGO",
                "OGGGGGGGGGGGGGOOGGGGGGGGGGGGGO",
                ".OOOOOOOOOOOOO..OOOOOOOOOOOOO.",
                "..OO.......OO....OO.......OO..",
            ], OFFICE_PALETTE)

        elif otype == "web_radar":
            overhang_native = 6
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 0, overhang_native, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".dMMd......................dMMd.",
                ".dnnO......................Onnd.",
            ], OFFICE_PALETTE)
            scr = "T" if is_active else "s"
            _stamp_rows(img, 3, 1, [
                ".OOOOOOOO.",
                "OCCCCCCCCO",
                f"OC{scr}b{scr}b{scr}bCO",
                f"OCb{scr}b{scr}b{scr}CO",
                "OccccccccO",
                "OCCCCCCCCO",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 18, 1, [
                ".OOOOOOOO.",
                "OCCCCCCCCO",
                f"OC{scr * 6}CO",
                f"OC{scr}QQQ{scr * 2}CO",
                "OccccccccO",
                "OCCCCCCCCO",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)

        elif otype == "orchestrator_core":
            overhang_native = 4
            img = QImage(32, 32 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 1, 4, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dwwwwOCCCCCCCCCCCCCCCCCCCCOwwwwd",
                "dwwwwOCssssssssssssssssssCOwwwwd",
                "dwwwwOCssbbbbssssssyyysssCOwwwwd",
                "dwwwwOCssbQQb--ee--yYysssCOwwwwd",
                "dwwwwOCssbbbbssssssyyysssCOwwwwd",
                "dwwwwOCssssss--bb--ssssssCOwwwwd",
                "dwwwwOCssseeeessssseeeessCOwwwwd",
                "dwwwwOCssssssssssssssssssCOwwwwd",
                "dwwwwOCCCCCCCCCCCCCCCCCCCCOwwwwd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".ddMMMMMMMMMMMMMMMMMMMMMMMMMMdd.",
                ".dMMd......................dMMd.",
                ".dnnO......................Onnd.",
            ], OFFICE_PALETTE)
            if is_active:
                dot = "y" if anim_phase % 2 == 0 else "e"
                _stamp_rows(img, 14, 10, [dot, "b"], OFFICE_PALETTE)

        elif otype == "art_easel":
            overhang_native = 6
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 0, overhang_native, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".dMMd......................dMMd.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 4, 0, [
                ".OOOOOOOOOOOOOO.",
                "OmmmmmmmmmmmmmmO",
                "OmUUUUUUUUUUUUwO",
                "OmUbbbbbbbbbbUwO",
                "OmUbQQbbbyybbUwO",
                "OmUllLLLLllllUwO",
                "OmUffffffffffUwO",
                "OmmmmmmmmmmmmmmO",
                ".OOOOOOOOOOOOOO.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 22, 4, [
                "OmmO",
                "OERbO",
                "OyblO",
                ".OOO.",
            ], OFFICE_PALETTE)

        elif otype == "coffee_bar":
            overhang_native = 4
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 0, overhang_native, [
                ".dWWWWWWWWWWWWWWWWWWWWWWWWWWWWd.",
                "dWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWd",
                "dwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwd",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmM",
                "dMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMd",
                "dnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnd",
                ".ddMMMMMMMMMMMMMMMMMMMMMMMMMMdd.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 4, 0, [
                ".OOOOOOOO.",
                "ORRRRRRRRO",
                "OrCCCCCCrO",
                "OrCssssCrO",
                "OrCUUUUCrO",
                "OGGGGGGGGO",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)
            _stamp_rows(img, 18, 3, ["OUUO.OUUO", "UnUO.UnUO", ".OO...OO."], OFFICE_PALETTE)

        elif otype == "plant_monstera":
            overhang_native = 8
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Árbol de interior frondoso en maceta terracota anclado al piso (Referencia 1)
            _stamp_rows(img, 1, 2, [
                ".....OOOO.....",
                "...OOLLLLOO...",
                "..OLlLllLlLO..",
                ".OLlLLllLLlLO.",
                "OOllLffffLllOO",
                "OLllfLLLLfllLO",
                "OLlLfllllfLlLO",
                ".OOlfllllflOO.",
                "..OLlfLLflLO..",
                "..OlLffffLlO..",
                "...OOlfflOO...",
                ".....OmmO.....",
                ".....OmmO.....",
                "....OPPPPO....",
                "....OPppPO....",
                "....OppppO....",
                "....OppppO....",
                ".....OOOO.....",
            ], OFFICE_PALETTE)

        elif otype == "plant_cactus":
            overhang_native = 6
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Planta espada ancha y densa en maceta marrón (Referencia 1)
            _stamp_rows(img, 2, 2, [
                "...OO..OO...",
                "..OLlOOlLO..",
                ".OLlLOOLlLO.",
                "OOlLllLllLOO",
                "OLlfLLfLLflO",
                "OLlflLlfllLO",
                "OlfllfllfllO",
                ".OlflfflfLO.",
                "..OlfffflO..",
                "..OOffffOO..",
                "...OPPPPO...",
                "...OPppPO...",
                "...OppppO...",
                "...OppppO...",
                "....OOOO....",
            ], OFFICE_PALETTE)

        elif otype == "trash_bin":
            overhang_native = 0
            img = QImage(16, 16, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Papelera metálica redondeada (Referencia 1 abajo izquierda)
            _stamp_rows(img, 4, 3, [
                ".OOOOOO.",
                "OCCCCCCo",
                "OCssssCO",
                "OCCCCCCo",
                "OccccccO",
                "OcggggcO",
                "OcggggcO",
                "OGGGGGGO",
                ".OOOOOO.",
            ], OFFICE_PALETTE)

        elif otype == "wall_painting":
            overhang_native = 2
            img = QImage(32, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Cuadro paisaje enmarcado en madera (Referencia 1)
            _stamp_rows(img, 2, 2, [
                "OOOOOOOOOOOOOOOOOOOOOOOOOOOO",
                "OWWWWWWWWWWWWWWWWWWWWWWWWWWO",
                "OWObbbbbbbbbbbbbbbbbbbbbbOWO",
                "OWObQQbbbyyybbbbbbQQbbbbbOWO",
                "OWObbbbbbbybbbbbbbbbbllbbOWO",
                "OWOllLLllmmllLLllLLllLLllOWO",
                "OWOffffffMMffffffffffffffOWO",
                "OWOMMMMMMMMMMMMMMMMMMMMMMOWO",
                "OWOOOOOOOOOOOOOOOOOOOOOOOOWO",
                "OmmmmmmmmmmmmmmmmmmmmmmmmmmO",
                "OOOOOOOOOOOOOOOOOOOOOOOOOOOO",
            ], OFFICE_PALETTE)

        elif otype == "wall_clock":
            overhang_native = 0
            img = QImage(16, 16, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            # Reloj redondo rojo y blanco centrado sobre la cara frontal de la pared (y=5..13)
            _stamp_rows(img, 3, 5, [
                "..OOOOOO..",
                ".OEEEEEEO.",
                "OEUUUUUUEO",
                "OEUUOOuUEO",
                "OEUUUOOUEO",
                "OEUUUUUUEO",
                ".OEEEEEEO.",
                "..OOOOOO..",
            ], OFFICE_PALETTE)

        elif otype == "filing_cabinet":
            overhang_native = 4
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 2, 2, [
                ".OOOOOOOOOO.",
                "OCCCCCCCCCCO",
                "OCCCCCCCCCCO",
                "OggggggggggO",
                "OcCGGGGGGCco",
                "OcCccccccCco",
                "OggggggggggO",
                "OcCGGGGGGCco",
                "OcCccccccCco",
                "OGGGGGGGGGGO",
                ".OOOOOOOOOO.",
            ], OFFICE_PALETTE)

        elif otype == "water_cooler":
            overhang_native = 6
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 3, 1, [
                "..OOOOOO..",
                ".OQQbbQQO.",
                ".OQbQQbQO.",
                ".ObbbbbbO.",
                "OCCCCCCCCO",
                "OCCCCCCCCO",
                "OccbOOEccO",
                "OccccccccO",
                "OccccccccO",
                "OGGGGGGGGO",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)

        elif otype == "arcade_machine":
            overhang_native = 8
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 2, 1, [
                ".OOOOOOOOOO.",
                "ORRRRRRRRRRO",
                "ORybbbbbbERO",
                "OssssssssssO",
                "OsbbbbbbbbsO",
                "OsbEEbyyybsO",
                "OssssssssssO",
                "ORRRRRRRRRRO",
                "ORyRbbRRRRRO",
                "ORrrrrrrrrRO",
                "OvvvvvvvvvvO",
                "OvvvvvvvvvvO",
                ".OOOOOOOOOO.",
            ], OFFICE_PALETTE)

        elif otype == "floor_lamp":
            overhang_native = 8
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 3, 1, [
                "..OOOOOO..",
                ".OUyyyyUO.",
                "OUyyyyyyUO",
                "OYYYYYYYYO",
                ".OOOOOOOO.",
                "....OO....",
                "....OG....",
                "....OG....",
                "....OG....",
                "....OG....",
                "....OG....",
                "....OG....",
                "..OOOOOO..",
            ], OFFICE_PALETTE)

        elif otype == "trophy":
            overhang_native = 4
            img = QImage(16, 16 + overhang_native, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            _stamp_rows(img, 3, 2, [
                ".OOOOOOOO.",
                "OyyyyyyyyO",
                "OyyUyyUyyO",
                ".OyyyyyyO.",
                "..OYYYYO..",
                "...OYYO...",
                "..OmmmmO..",
                "..OMMMMO..",
                ".OOOOOOOO.",
            ], OFFICE_PALETTE)

        elif otype in ("rug_persian", "rug_cyber", "rug_lounge"):
            overhang_native = 0
            rw = 80 if otype == "rug_lounge" else 48
            rh = 64 if otype == "rug_lounge" else 32
            img = QImage(rw, rh, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            fill_c = QColor("#26415c" if otype == "rug_cyber" else "#a31c24")
            trim_c = QColor("#78bdd6" if otype == "rug_cyber" else "#d8b786")
            edge_c = QColor("#17293b" if otype == "rug_cyber" else "#6d1016")
            for y in range(rh):
                for x in range(rw):
                    if x in (0, rw - 1) or y in (0, rh - 1):
                        img.setPixelColor(x, y, edge_c)
                    elif x in (2, rw - 3) or y in (2, rh - 3):
                        img.setPixelColor(x, y, trim_c)
                    else:
                        img.setPixelColor(x, y, fill_c)

        elif otype in ("office_chair", "gaming_chair"):
            return self.get_chair_sprite("gaming" if otype == "gaming_chair" else "wood", scale=scale)

        else:
            img = QImage(16, 16, QImage.Format.Format_ARGB32)
            img.fill(QColor("#a67443"))

        res = (_scale_pix(img, scale), overhang_native * scale)
        self._cache[key] = res
        return res

    # =========================================================================
    # MINIATURA PARA EL CONSTRUCTOR DE OFICINA (MUEBLES, PISOS, PAREDES)
    # =========================================================================
    def get_preview_pixmap(
        self,
        category: str,
        item_key: str,
        spec: Dict[str, Any],
        box_size: int = 52,
    ) -> QPixmap:
        key = ("office_preview_v2", category, item_key, box_size)
        if key in self._cache:
            return self._cache[key]

        out = QImage(box_size, box_size, QImage.Format.Format_ARGB32)
        out.fill(Qt.GlobalColor.transparent)

        if category == "floors":
            src = self.get_floor_pixmap(item_key, scale=2).toImage()
        elif category == "walls":
            if item_key == "__erase_wall__":
                p = QPainter(out)
                p.setPen(QColor("#f87171"))
                p.drawRect(8, 8, box_size - 16, box_size - 16)
                p.drawLine(12, 12, box_size - 12, box_size - 12)
                p.drawLine(box_size - 12, 12, 12, box_size - 12)
                p.end()
                pix = QPixmap.fromImage(out)
                self._cache[key] = pix
                return pix
            src = self.get_wall_pixmap(item_key, False, False, False, False, scale=2).toImage()
        else:
            pix_item, _ = self.get_item_sprite(item_key, is_active=True, anim_tick=0, scale=2)
            src = pix_item.toImage()

        scaled = src.scaled(
            box_size - 6,
            box_size - 6,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        p = QPainter(out)
        p.drawImage((box_size - scaled.width()) // 2, (box_size - scaled.height()) // 2, scaled)
        p.end()

        pix = QPixmap.fromImage(out)
        self._cache[key] = pix
        return pix


OFFICE_SPRITES = OfficeSpriteRenderer()
