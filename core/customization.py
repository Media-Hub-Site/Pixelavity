# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Personalización por Cuadrículas (Tile-Grid 32x19) y Pool de Personajes
Gestiona:
  1. Pool de Personajes Personalizables (12 estilos de pelo esculpidos, caras, ropa, zapatos, accesorios)
  2. Asignación aleatoria sin repetición (solo repite si hay más agentes activos que personajes creados)
  3. Mapa de Oficina basado 100% en Cuadrículas (32 columnas x 19 filas de 32x32 px = 1024x608):
     - Piso por cuadrícula (floor_grid[row][col]) con dos modos de pintado:
         * Modo 1x1 (Uno por uno)
         * Modo Rellenar (Flood-Fill BFS limitado por paredes o pisos distintos)
     - Paredes por cuadrícula (wall_grid[row][col]) con 5 estilos de muro
     - Objetos (Dispositivos, Muebles, Decoración) posicionados estrictamente en celdas (col, row)
       con tamaño en celdas (tile_w x tile_h) y prevención de solapamiento.
  4. Reglas mínimas de dispositivos interactivos (mín. 1 Computador, 1 Mueble de Libros, etc.)
  5. Control de demanda y Pair-Programming / Colaboración por celdas adyacentes.
"""

import os
import json
import uuid
import copy
import random
import threading
from collections import deque
from typing import Dict, List, Optional, Any, Tuple, Set


GRID_COLS = 32
GRID_ROWS = 19
TILE_SIZE = 32
WORLD_W = GRID_COLS * TILE_SIZE  # 1024
WORLD_H = GRID_ROWS * TILE_SIZE  # 608


# =============================================================================
# CATÁLOGOS DE PERSONALIZACIÓN DE PERSONAJES (12 PEINADOS DETALLADOS)
# =============================================================================
SKIN_TONES = [
    {"id": "peach", "name": "Durazno Claro", "color": "#ffcca8"},
    {"id": "light", "name": "Marfil Cálido", "color": "#ffe0c8"},
    {"id": "warm",  "name": "Trigueño",      "color": "#f1b280"},
    {"id": "tan",   "name": "Bronceado",     "color": "#d9915b"},
    {"id": "brown", "name": "Moreno",        "color": "#a8653a"},
    {"id": "deep",  "name": "Ébano",         "color": "#6e3f23"},
]

FACE_STYLES = [
    {"id": "smile",       "name": "Sonrisa Clásica"},
    {"id": "happy",       "name": "Alegre con Rubor"},
    {"id": "focused",     "name": "Concentrado"},
    {"id": "cool",        "name": "Guiño / Cool"},
    {"id": "surprised",   "name": "Sorprendido"},
    {"id": "cat_smile",   "name": "Sonrisa Gatito (:3)"},
    {"id": "determined",  "name": "Determinado / Pro"},
    {"id": "sleepy",      "name": "Relajado / Chill"},
    {"id": "starry",      "name": "Ojos Estrellados"},
    {"id": "beard_smile", "name": "Con Barba"},
]

HAIR_STYLES = [
    {"id": "short_parted",  "name": "Corto Raya Diagonal"},
    {"id": "ponytail",      "name": "Coleta Alta con Moño"},
    {"id": "long_straight", "name": "Melena Larga Lateral"},
    {"id": "wavy_bob",      "name": "Melena Ondulada Curva"},
    {"id": "pigtails",      "name": "Dos Coletas Altas"},
    {"id": "top_bun",       "name": "Moño Alto Esquinado"},
    {"id": "low_ponytail",  "name": "Coleta Baja Ejecutiva"},
    {"id": "spiky_messy",   "name": "Mechones en Punta"},
    {"id": "curly_afro",    "name": "Rizado con Volumen"},
    {"id": "flat_top",      "name": "Corte Alto (Flat-Top)"},
    {"id": "receding",      "name": "Ejecutivo en M"},
    {"id": "wolf_cut",      "name": "Wolf Cut / Capas"},
    {"id": "anime_spiky",   "name": "Puntas Anime / Cyber"},
    {"id": "twin_buns",     "name": "Dos Moños (Space Buns)"},
    {"id": "mohawk",        "name": "Cresta Punk / Mohawk"},
    {"id": "side_shave",    "name": "Rapado Lateral / Undercut"},
    {"id": "braids",        "name": "Dos Trenzas Largas"},
    {"id": "curtain_bangs", "name": "Flequillo Cortina (K-Pop)"},
    {"id": "long_wavy",     "name": "Melena Larga Ondulada"},
    {"id": "bald",          "name": "Sin Pelo"},
]

HAIR_COLORS = [
    {"id": "gold",     "name": "Rubio Dorado",   "color": "#eab308"},
    {"id": "auburn",   "name": "Castaño Rojizo", "color": "#c2593f"},
    {"id": "navy",     "name": "Azul Noche",     "color": "#2b3a55"},
    {"id": "espresso", "name": "Castaño Oscuro", "color": "#432818"},
    {"id": "black",    "name": "Negro Carbón",   "color": "#1e2229"},
    {"id": "ginger",   "name": "Pelirrojo Vivo", "color": "#e05a2b"},
    {"id": "silver",   "name": "Plata / Blanco", "color": "#cbd5e1"},
    {"id": "violet",   "name": "Violeta Cyber",  "color": "#9333ea"},
    {"id": "mint",     "name": "Menta Neon",     "color": "#10b981"},
]

OUTFIT_STYLES = [
    {"id": "suit_tie",        "name": "Traje Formal y Corbata"},
    {"id": "tshirt_jeans",    "name": "Camiseta y Pantalón"},
    {"id": "hoodie",          "name": "Polerón / Hoodie"},
    {"id": "vest_shirt",      "name": "Chaleco y Camisa"},
    {"id": "overalls",        "name": "Overol / Jardinera"},
    {"id": "dress_skirt",     "name": "Blusa y Falda"},
    {"id": "cloak",           "name": "Capa Larga"},
    {"id": "tank_top",        "name": "Deportivo Sin Mangas"},
    {"id": "cyber_jacket",    "name": "Chaqueta Cyber / Bomber"},
    {"id": "lab_coat",        "name": "Bata de Laboratorio"},
    {"id": "kimono",          "name": "Kimono / Haori"},
    {"id": "striped_sweater", "name": "Suéter a Rayas"},
    {"id": "knight_armor",    "name": "Armadura Tech"},
    {"id": "varsity_jacket",  "name": "Chaqueta Universitaria"},
]

SHOE_STYLES = [
    {"id": "classic",     "name": "Zapatos Clásicos"},
    {"id": "sneakers",    "name": "Zapatillas Suela Blanca"},
    {"id": "boots",       "name": "Botas Altas"},
    {"id": "high_tops",   "name": "Zapatillas Botín"},
    {"id": "cyber_boots", "name": "Botas Cyber Neón"},
    {"id": "sandals",     "name": "Sandalias"},
    {"id": "loafers",     "name": "Mocasines con Hebilla"},
]

ACCESSORY_STYLES = [
    {"id": "none",            "name": "Ninguno"},
    {"id": "headphones",      "name": "Audífonos Cyber"},
    {"id": "glasses",         "name": "Lentes Pixel"},
    {"id": "sunglasses",      "name": "Lentes de Sol"},
    {"id": "cyber_visor",     "name": "Visor Futurista Neón"},
    {"id": "baseball_cap",    "name": "Gorra Urbana"},
    {"id": "beanie",          "name": "Gorro de Lana"},
    {"id": "fedora",          "name": "Sombrero Detective"},
    {"id": "witch_hat",       "name": "Sombrero de Mago"},
    {"id": "top_hat",         "name": "Sombrero de Copa"},
    {"id": "straw_hat",       "name": "Sombrero de Paja"},
    {"id": "crown",           "name": "Corona Dorada"},
    {"id": "cat_ears",        "name": "Orejas de Gato"},
    {"id": "halo",            "name": "Aureola Flotante"},
    {"id": "headband",        "name": "Cinta Ninja / Deportiva"},
    {"id": "aviator_goggles", "name": "Casco y Gafas"},
    {"id": "viking_helmet",   "name": "Casco Vikingo"},
    {"id": "nurse_cap",       "name": "Gorro Blanco"},
]

DEFAULT_CHARACTERS: List[Dict[str, Any]] = [
    {
        "id": "char-default-alex",
        "name": "Alex",
        "skin_color": "#ffcca8",
        "face_style": "smile",
        "hair_style": "short_parted",
        "hair_color": "#eab308",
        "outfit_style": "suit_tie",
        "top_color": "#334155",
        "bottom_color": "#1e293b",
        "shoe_style": "classic",
        "shoe_color": "#451a03",
        "accessory": "fedora",
        "accessory_color": "#ef4444",
    },
    {
        "id": "char-default-sofia",
        "name": "Sofía",
        "skin_color": "#ffe0c8",
        "face_style": "happy",
        "hair_style": "ponytail",
        "hair_color": "#c2593f",
        "outfit_style": "dress_skirt",
        "top_color": "#7dd3fc",
        "bottom_color": "#f472b6",
        "shoe_style": "sneakers",
        "shoe_color": "#be185d",
        "accessory": "none",
        "accessory_color": "#f472b6",
    },
    {
        "id": "char-default-marco",
        "name": "Marco",
        "skin_color": "#d9915b",
        "face_style": "cool",
        "hair_style": "flat_top",
        "hair_color": "#2b3a55",
        "outfit_style": "hoodie",
        "top_color": "#10b981",
        "bottom_color": "#1e293b",
        "shoe_style": "sneakers",
        "shoe_color": "#38bdf8",
        "accessory": "headphones",
        "accessory_color": "#38bdf8",
    },
]


# =============================================================================
# MATERIALES DE PISO Y PARED POR CUADRÍCULA (32x32)
# =============================================================================
FLOOR_MATERIALS: Dict[str, Dict[str, str]] = {
    "oak_wood":      {"name": "Madera Roble",       "colorA": "#4a3222", "colorB": "#3d281b", "pattern": "planks"},
    "walnut_wood":   {"name": "Madera Nogal",       "colorA": "#2d201a", "colorB": "#241914", "pattern": "planks"},
    "parquet_gold":  {"name": "Parquet Dorado",     "colorA": "#5c3d24", "colorB": "#4d321c", "pattern": "checkers"},
    "navy_carpet":   {"name": "Alfombra Azul",      "colorA": "#162436", "colorB": "#131e2e", "pattern": "grid"},
    "emerald_tile":  {"name": "Baldosa Esmeralda",  "colorA": "#132620", "colorB": "#0f1e1a", "pattern": "tiles"},
    "metal_grate":   {"name": "Metal Industrial",   "colorA": "#1e242e", "colorB": "#171c24", "pattern": "grate"},
    "cyber_grid":    {"name": "Cyber Grid Cyan",    "colorA": "#112430", "colorB": "#0d1c26", "pattern": "grid"},
    "amber_tech":    {"name": "Hex Tech Ámbar",     "colorA": "#261e13", "colorB": "#1f180f", "pattern": "tiles"},
    "studio_purple": {"name": "Estudio Violeta",    "colorA": "#241730", "colorB": "#1d1226", "pattern": "checkers"},
    "cafe_warm":     {"name": "Cerámica Cafetería", "colorA": "#2e1d24", "colorB": "#25171d", "pattern": "checkers"},
    "marble_slate":  {"name": "Pasillo Pizarra",    "colorA": "#1a2232", "colorB": "#161d2b", "pattern": "tiles"},
    "marble_white":  {"name": "Mármol Claro",       "colorA": "#475569", "colorB": "#3b4759", "pattern": "tiles"},
}

WALL_MATERIALS: Dict[str, Dict[str, str]] = {
    "dark_tech":  {"name": "Muro Tech Oscuro",   "top": "#334155", "front": "#1e293b", "border": "#475569"},
    "brick_wall": {"name": "Pared de Ladrillo",  "top": "#7c2d12", "front": "#5c210d", "border": "#9a3412"},
    "wood_panel": {"name": "Tabique de Madera",  "top": "#78350f", "front": "#451a03", "border": "#92400e"},
    "glass_wall": {"name": "División Cristal",   "top": "#38bdf8", "front": "#0284c7", "border": "#7dd3fc"},
    "cyber_neon": {"name": "Muro Cyber Neon",    "top": "#a855f7", "front": "#581c87", "border": "#d8b4fe"},
}


# =============================================================================
# CATÁLOGO UNIFICADO POR CATEGORÍAS (TAMAÑOS EN CUADRÍCULAS tile_w x tile_h)
# Categorías:
#   - "devices":     Dispositivos tecnológicos e interactivos
#   - "furniture":   Muebles de oficina, estanterías, sofás y mesas
#   - "decorations": Plantas, alfombras, máquinas y accesorios
# =============================================================================
OBJECT_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- CATEGORÍA 1: DISPOSITIVOS ---
    "computer_desk": {
        "type": "computer_desk",
        "category": "devices",
        "station": "coding_desk",
        "name": "Computador Dual (PC)",
        "icon": "💻",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right"), (0, 2, "up")],
    },
    "laptop_desk": {
        "type": "laptop_desk",
        "category": "devices",
        "station": "coding_desk",
        "name": "Laptop Compacta",
        "icon": "💻",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(-1, 1, "right"), (1, 1, "left")],
    },
    "server_terminal": {
        "type": "server_terminal",
        "category": "devices",
        "station": "server_lab",
        "name": "Servidor / Terminal",
        "icon": "⚡",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },
    "whiteboard": {
        "type": "whiteboard",
        "category": "devices",
        "station": "strategy_board",
        "name": "Pizarra Estrategia",
        "icon": "💭",
        "tile_w": 3,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (1, 1, "up"),
        "collab_cells": [(0, 1, "right"), (2, 1, "left")],
    },
    "orchestrator_core": {
        "type": "orchestrator_core",
        "category": "devices",
        "station": "orchestrator_hub",
        "name": "Núcleo Orchestrator",
        "icon": "🎛️",
        "tile_w": 2,
        "tile_h": 2,
        "blocking": True,
        "seat_cell": (0, 2, "up"),
        "collab_cells": [(1, 2, "left"), (-1, 2, "right")],
    },
    "web_radar": {
        "type": "web_radar",
        "category": "devices",
        "station": "web_station",
        "name": "Cabina Web / Radar",
        "icon": "🌐",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },
    "art_easel": {
        "type": "art_easel",
        "category": "devices",
        "station": "art_studio",
        "name": "Mesa Estudio UI",
        "icon": "🎨",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },

    # --- CATEGORÍA 2: MUEBLES ---
    "bookshelf": {
        "type": "bookshelf",
        "category": "furniture",
        "station": "library",
        "name": "Estantería de Libros",
        "icon": "📚",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },
    "bookshelf_single": {
        "type": "bookshelf_single",
        "category": "furniture",
        "station": "library",
        "name": "Librero Compacto",
        "icon": "📖",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(-1, 1, "right"), (1, 1, "left")],
    },
    "coffee_sofa": {
        "type": "coffee_sofa",
        "category": "furniture",
        "station": "lounge",
        "name": "Sofá Lounge Rojo",
        "icon": "🛋️",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },
    "coffee_bar": {
        "type": "coffee_bar",
        "category": "furniture",
        "station": "lounge",
        "name": "Barra Cafetería",
        "icon": "☕",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 1, "up"),
        "collab_cells": [(1, 1, "left"), (-1, 1, "right")],
    },
    "reading_table": {
        "type": "reading_table",
        "category": "furniture",
        "station": None,
        "name": "Mesa de Lectura",
        "icon": "🪑",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
    },
    "meeting_table": {
        "type": "meeting_table",
        "category": "furniture",
        "station": None,
        "name": "Mesa de Reuniones",
        "icon": "📋",
        "tile_w": 3,
        "tile_h": 2,
        "blocking": True,
    },
    "filing_cabinet": {
        "type": "filing_cabinet",
        "category": "furniture",
        "station": None,
        "name": "Archivador Metálico",
        "icon": "🗄️",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },

    # --- CATEGORÍA 3: DECORACIÓN ---
    "plant_monstera": {
        "type": "plant_monstera",
        "category": "decorations",
        "station": None,
        "name": "Planta Monstera",
        "icon": "🪴",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "plant_cactus": {
        "type": "plant_cactus",
        "category": "decorations",
        "station": None,
        "name": "Cactus Pixel",
        "icon": "🌵",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "arcade_machine": {
        "type": "arcade_machine",
        "category": "decorations",
        "station": None,
        "name": "Máquina Arcade",
        "icon": "🕹️",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "water_cooler": {
        "type": "water_cooler",
        "category": "decorations",
        "station": None,
        "name": "Dispensador Agua",
        "icon": "🚰",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "rug_persian": {
        "type": "rug_persian",
        "category": "decorations",
        "station": None,
        "name": "Alfombra Persa",
        "icon": "🟥",
        "tile_w": 3,
        "tile_h": 2,
        "blocking": False,  # Las alfombras se pueden pisar
    },
    "rug_cyber": {
        "type": "rug_cyber",
        "category": "decorations",
        "station": None,
        "name": "Alfombra Cyber",
        "icon": "💠",
        "tile_w": 3,
        "tile_h": 2,
        "blocking": False,
    },
    "floor_lamp": {
        "type": "floor_lamp",
        "category": "decorations",
        "station": None,
        "name": "Lámpara de Pie",
        "icon": "💡",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "trophy": {
        "type": "trophy",
        "category": "decorations",
        "station": None,
        "name": "Trofeo MediaHub",
        "icon": "🏆",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
}

# Reglas mínimas por estación de actividad para que los agentes siempre tengan dónde interactuar
REQUIRED_STATIONS: Dict[str, str] = {
    "coding_desk":      "💻 Computador (PC o Laptop)",
    "library":          "📚 Mueble de Libros / Estantería",
    "server_lab":       "⚡ Servidor / Terminal",
    "strategy_board":   "💭 Pizarra Estrategia",
    "orchestrator_hub": "🎛️ Núcleo Orchestrator",
    "web_station":      "🌐 Cabina Web / Radar",
    "art_studio":       "🎨 Mesa Estudio UI",
    "lounge":           "☕ Sofá o Barra de Cafetería",
}


def build_default_office_layout() -> Dict[str, Any]:
    """
    Construye el mapa por defecto en una cuadrícula exacta de 32x19 celdas (32x32 px cada una).
    Incluye 8 salas con sus pisos, muros divisorios con puertas abiertas al corredor central (filas 8..9),
    dispositivos interactivos, muebles y decoración.
    """
    floor_grid = [["marble_slate" for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    wall_grid: List[List[Optional[str]]] = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    #Definir zonas superiores (filas 0..7) e inferiores (filas 10..18)
    top_zones = [
        (0, 7,   "walnut_wood",   3),  # Biblioteca (cols 0..7, puerta en col 3..4)
        (8, 15,  "navy_carpet",   11), # Estrategia (cols 8..15, puerta en col 11..12)
        (16, 23, "amber_tech",    19), # Orchestrator (cols 16..23, puerta en col 19..20)
        (24, 31, "cyber_grid",    27), # Cabina Web (cols 24..31, puerta en col 27..28)
    ]
    bot_zones = [
        (0, 10,  "emerald_tile",  5),  # Computadores (cols 0..10, puerta en col 5..6)
        (11, 17, "metal_grate",   14), # Terminal Lab (cols 11..17, puerta en col 14..15)
        (18, 22, "studio_purple", 20), # Estudio UI (cols 18..22, puerta en col 20)
        (23, 31, "cafe_warm",     27), # Cafetería (cols 23..31, puerta en col 27..28)
    ]

    for c0, c1, mat, door_c in top_zones:
        for r in range(0, 8):
            for c in range(c0, c1 + 1):
                floor_grid[r][c] = mat
        # Muro horizontal en fila 7 (con abertura de puerta de 2 celdas)
        for c in range(c0, c1 + 1):
            if c not in (door_c, door_c + 1):
                wall_grid[7][c] = "dark_tech"
        # Muro vertical derecho entre salas
        if c1 < GRID_COLS - 1:
            for r in range(0, 8):
                wall_grid[r][c1] = "dark_tech"

    for c0, c1, mat, door_c in bot_zones:
        for r in range(10, GRID_ROWS):
            for c in range(c0, c1 + 1):
                floor_grid[r][c] = mat
        # Muro horizontal en fila 10 (con abertura de puerta)
        for c in range(c0, c1 + 1):
            if c not in (door_c, door_c + 1):
                wall_grid[10][c] = "dark_tech"
        if c1 < GRID_COLS - 1:
            for r in range(10, GRID_ROWS):
                wall_grid[r][c1] = "dark_tech"

    items = [
        # Biblioteca (cols 0..6, rows 1..6)
        {"id": "obj-lib-1", "type": "bookshelf",       "col": 1,  "row": 1},
        {"id": "obj-lib-2", "type": "bookshelf",       "col": 4,  "row": 1},
        {"id": "obj-lib-3", "type": "reading_table",   "col": 2,  "row": 4},
        {"id": "obj-lib-4", "type": "plant_monstera",  "col": 0,  "row": 6},

        # Estrategia (cols 8..14, rows 1..6)
        {"id": "obj-str-1", "type": "whiteboard",      "col": 10, "row": 1},
        {"id": "obj-str-2", "type": "rug_cyber",       "col": 10, "row": 4},

        # Orchestrator (cols 16..22, rows 1..6)
        {"id": "obj-orc-1", "type": "orchestrator_core", "col": 18, "row": 2},
        {"id": "obj-orc-2", "type": "floor_lamp",        "col": 16, "row": 1},

        # Cabina Web (cols 24..30, rows 1..6)
        {"id": "obj-web-1", "type": "web_radar",       "col": 25, "row": 1},
        {"id": "obj-web-2", "type": "web_radar",       "col": 28, "row": 1},

        # Sala de Computadores (cols 0..9, rows 11..17)
        {"id": "obj-pc-1",  "type": "computer_desk",   "col": 1,  "row": 12},
        {"id": "obj-pc-2",  "type": "computer_desk",   "col": 6,  "row": 12},
        {"id": "obj-pc-3",  "type": "computer_desk",   "col": 1,  "row": 15},
        {"id": "obj-pc-4",  "type": "computer_desk",   "col": 6,  "row": 15},
        {"id": "obj-pc-5",  "type": "plant_cactus",    "col": 9,  "row": 11},

        # Terminal Lab (cols 11..16, rows 11..17)
        {"id": "obj-srv-1", "type": "server_terminal", "col": 12, "row": 12},
        {"id": "obj-srv-2", "type": "server_terminal", "col": 14, "row": 15},

        # Estudio UI (cols 18..21, rows 11..17)
        {"id": "obj-art-1", "type": "art_easel",       "col": 19, "row": 13},
        {"id": "obj-art-2", "type": "trophy",          "col": 18, "row": 11},

        # Cafetería & Lounge (cols 23..31, rows 11..17)
        {"id": "obj-lng-1", "type": "coffee_bar",      "col": 24, "row": 11},
        {"id": "obj-lng-2", "type": "water_cooler",    "col": 29, "row": 11},
        {"id": "obj-lng-3", "type": "arcade_machine",  "col": 30, "row": 11},
        {"id": "obj-lng-4", "type": "coffee_sofa",     "col": 24, "row": 15},
        {"id": "obj-lng-5", "type": "coffee_sofa",     "col": 28, "row": 15},
        {"id": "obj-lng-6", "type": "rug_persian",     "col": 25, "row": 13},
    ]

    return {
        "schema": "grid_v2",
        "floor_grid": floor_grid,
        "wall_grid": wall_grid,
        "items": items,
    }


# =============================================================================
# GESTOR CENTRAL DE PERSONALIZACIÓN, CUADRÍCULA, PATHFINDING A* Y DEMANDA
# =============================================================================
class CustomizationManager:
    def __init__(self, storage_path: Optional[str] = None):
        if not storage_path:
            appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            data_dir = os.path.join(appdata, "MediaHub", "Pixelavity")
            os.makedirs(data_dir, exist_ok=True)
            storage_path = os.path.join(data_dir, "customization_v2.json")
        self.storage_path = storage_path
        self.lock = threading.RLock()

        self.characters: List[Dict[str, Any]] = copy.deepcopy(DEFAULT_CHARACTERS)
        self.office: Dict[str, Any] = build_default_office_layout()
        self.agent_to_character: Dict[str, str] = {}
        self._load()

    def _load(self):
        if not os.path.isfile(self.storage_path):
            self._save()
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw.get("characters"), list) and len(raw["characters"]) > 0:
                self.characters = raw["characters"]
            off = raw.get("office")
            if isinstance(off, dict) and off.get("schema") == "grid_v2":
                self.office = off
        except Exception as e:
            print(f"[CustomizationManager] Error cargando configuración: {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"characters": self.characters, "office": self.office},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print(f"[CustomizationManager] Error guardando configuración: {e}")

    # -------------------------------------------------------------------------
    # PERSONAJES Y ASIGNACIÓN SIN REPETICIÓN
    # -------------------------------------------------------------------------
    def get_characters(self) -> List[Dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.characters)

    def save_character(self, char_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            cid = char_data.get("id") or f"char-{uuid.uuid4().hex[:8]}"
            char_data["id"] = cid
            for idx, existing in enumerate(self.characters):
                if existing["id"] == cid:
                    self.characters[idx] = copy.deepcopy(char_data)
                    self._save()
                    return copy.deepcopy(char_data)
            self.characters.append(copy.deepcopy(char_data))
            self._save()
            return copy.deepcopy(char_data)

    def delete_character(self, char_id: str) -> Tuple[bool, str]:
        with self.lock:
            if len(self.characters) <= 1:
                return False, "Debe existir al menos 1 personaje en tu colección."
            self.characters = [c for c in self.characters if c["id"] != char_id]
            for aid, assigned_cid in list(self.agent_to_character.items()):
                if assigned_cid == char_id:
                    del self.agent_to_character[aid]
            self._save()
            return True, "Personaje eliminado."

    def reset_characters_to_default(self):
        with self.lock:
            self.characters = copy.deepcopy(DEFAULT_CHARACTERS)
            self.agent_to_character.clear()
            self._save()

    def assign_characters_to_agents(self, active_agent_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        with self.lock:
            if not self.characters:
                self.characters = copy.deepcopy(DEFAULT_CHARACTERS)
            char_by_id = {c["id"]: c for c in self.characters}
            active_set = set(active_agent_ids)

            for old_aid in list(self.agent_to_character.keys()):
                if old_aid not in active_set or self.agent_to_character[old_aid] not in char_by_id:
                    del self.agent_to_character[old_aid]

            usage_count: Dict[str, int] = {c["id"]: 0 for c in self.characters}
            for aid in active_agent_ids:
                cid = self.agent_to_character.get(aid)
                if cid and cid in usage_count:
                    usage_count[cid] += 1

            for aid in active_agent_ids:
                if aid not in self.agent_to_character:
                    min_use = min(usage_count.values())
                    candidates = [cid for cid, cnt in usage_count.items() if cnt == min_use]
                    chosen_cid = random.choice(candidates)
                    self.agent_to_character[aid] = chosen_cid
                    usage_count[chosen_cid] += 1

            return {
                aid: copy.deepcopy(char_by_id[self.agent_to_character[aid]])
                for aid in active_agent_ids
                if self.agent_to_character.get(aid) in char_by_id
            }

    # -------------------------------------------------------------------------
    # OPERACIONES POR CUADRÍCULA: PISOS (1x1 Y RELLENAR), PAREDES Y OBJETOS
    # -------------------------------------------------------------------------
    def get_office_layout(self) -> Dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.office)

    def reset_office_to_default(self):
        with self.lock:
            self.office = build_default_office_layout()
            self._save()

    def paint_floor_tile(self, col: int, row: int, material_id: str) -> bool:
        """Modo 1x1 (Uno por uno): Pinta una sola cuadrícula de piso."""
        with self.lock:
            if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
                return False
            if material_id not in FLOOR_MATERIALS:
                return False
            if self.office["floor_grid"][row][col] == material_id:
                return False
            self.office["floor_grid"][row][col] = material_id
            self._save()
            return True

    def flood_fill_floor(self, start_col: int, start_row: int, new_material: str) -> int:
        """
        Modo Rellenar (Bote de pintura): Rellena todas las cuadrículas conectadas
        que tengan el mismo material de piso, deteniéndose ante paredes o pisos diferentes.
        """
        with self.lock:
            if not (0 <= start_col < GRID_COLS and 0 <= start_row < GRID_ROWS):
                return 0
            if new_material not in FLOOR_MATERIALS:
                return 0

            fgrid = self.office["floor_grid"]
            wgrid = self.office["wall_grid"]
            target_mat = fgrid[start_row][start_col]
            if target_mat == new_material:
                return 0

            queue = deque([(start_col, start_row)])
            visited = {(start_col, start_row)}
            filled = 0

            while queue:
                c, r = queue.popleft()
                fgrid[r][c] = new_material
                filled += 1

                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS and (nc, nr) not in visited:
                        # Detener el relleno si hay una pared en la celda vecina o si el piso es distinto
                        if wgrid[nr][nc] is not None:
                            continue
                        if fgrid[nr][nc] == target_mat:
                            visited.add((nc, nr))
                            queue.append((nc, nr))

            if filled > 0:
                self._save()
            return filled

    def set_wall_tile(self, col: int, row: int, wall_material: Optional[str]) -> bool:
        """Coloca o borra (None) un bloque de pared 1x1 en la cuadrícula (col, row)."""
        with self.lock:
            if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
                return False
            # Si vamos a colocar una pared, verificar que no haya un objeto ocupando esa celda
            if wall_material is not None:
                if wall_material not in WALL_MATERIALS:
                    return False
                if self.find_object_at_cell(col, row) is not None:
                    return False
            if self.office["wall_grid"][row][col] == wall_material:
                return False
            self.office["wall_grid"][row][col] = wall_material
            self._save()
            return True

    def find_object_at_cell(self, col: int, row: int) -> Optional[Dict[str, Any]]:
        """Devuelve el objeto que ocupa la cuadrícula (col, row), priorizando muebles/dispositivos sobre alfombras."""
        with self.lock:
            items = self.office.get("items", [])
            # Primero buscar objetos bloqueantes (encima de alfombras)
            for pass_blocking in (True, False):
                for item in reversed(items):
                    spec = OBJECT_CATALOG.get(item.get("type", ""))
                    if not spec:
                        continue
                    if bool(spec.get("blocking", True)) != pass_blocking:
                        continue
                    ic, ir = int(item["col"]), int(item["row"])
                    tw, th = int(spec["tile_w"]), int(spec["tile_h"])
                    if ic <= col < ic + tw and ir <= row < ir + th:
                        return copy.deepcopy(item)
            return None

    def can_place_object(
        self,
        obj_type: str,
        col: int,
        row: int,
        ignore_item_id: Optional[str] = None,
    ) -> bool:
        """
        Verifica si un objeto de tamaño (tile_w x tile_h) cabe en las cuadrículas
        a partir de (col, row) sin salirse del mapa ni chocar con paredes u otros objetos.
        """
        spec = OBJECT_CATALOG.get(obj_type)
        if not spec:
            return False
        tw, th = int(spec["tile_w"]), int(spec["tile_h"])
        if col < 0 or row < 0 or (col + tw) > GRID_COLS or (row + th) > GRID_ROWS:
            return False

        is_blocking = bool(spec.get("blocking", True))
        with self.lock:
            wgrid = self.office["wall_grid"]
            for r in range(row, row + th):
                for c in range(col, col + tw):
                    if wgrid[r][c] is not None:
                        return False

            # Verificar colisión con otros objetos en la cuadrícula
            for other in self.office.get("items", []):
                if other.get("id") == ignore_item_id:
                    continue
                ospec = OBJECT_CATALOG.get(other.get("type", ""))
                if not ospec:
                    continue
                # Una alfombra (blocking=False) puede coexistir debajo de un mueble (blocking=True)
                if is_blocking != bool(ospec.get("blocking", True)):
                    continue
                oc, orow = int(other["col"]), int(other["row"])
                otw, oth = int(ospec["tile_w"]), int(ospec["tile_h"])
                if not (col + tw <= oc or oc + otw <= col or row + th <= orow or orow + oth <= row):
                    return False

        return True

    def place_new_object(self, obj_type: str, col: int, row: int) -> Tuple[bool, str]:
        with self.lock:
            if not self.can_place_object(obj_type, col, row):
                return False, "La cuadrícula está ocupada por una pared u otro objeto."
            new_item = {
                "id": f"obj-{uuid.uuid4().hex[:7]}",
                "type": obj_type,
                "col": int(col),
                "row": int(row),
            }
            self.office.setdefault("items", []).append(new_item)
            self._save()
            return True, new_item["id"]

    def move_object_to_cell(self, item_id: str, col: int, row: int) -> bool:
        with self.lock:
            target = None
            for it in self.office.get("items", []):
                if it.get("id") == item_id:
                    target = it
                    break
            if not target:
                return False
            if not self.can_place_object(target["type"], col, row, ignore_item_id=item_id):
                return False
            target["col"] = int(col)
            target["row"] = int(row)
            self._save()
            return True

    def validate_minimum_stations(self, items: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Verifica que exista al menos 1 dispositivo/mueble para cada estación esencial
        (mín. 1 Computador, mín. 1 Estantería de Libros, etc.).
        """
        station_counts: Dict[str, int] = {}
        for it in items:
            spec = OBJECT_CATALOG.get(it.get("type", ""))
            if spec and spec.get("station"):
                st = spec["station"]
                station_counts[st] = station_counts.get(st, 0) + 1

        for req_station, label in REQUIRED_STATIONS.items():
            if station_counts.get(req_station, 0) < 1:
                return (
                    False,
                    f"⚠️ Regla de la oficina: Debe existir como mínimo 1 {label} en la cuadrícula "
                    f"para que los agentes puedan trabajar.",
                )
        return True, "OK"

    def remove_object(self, item_id: str) -> Tuple[bool, str]:
        with self.lock:
            items = self.office.get("items", [])
            remaining = [it for it in items if it.get("id") != item_id]
            ok, msg = self.validate_minimum_stations(remaining)
            if not ok:
                return False, msg
            self.office["items"] = remaining
            self._save()
            return True, "Objeto eliminado."

    # -------------------------------------------------------------------------
    # PATHFINDING POR CUADRÍCULA (BFS EN EL MAPA 32x19)
    # -------------------------------------------------------------------------
    def get_blocked_cells(self) -> Set[Tuple[int, int]]:
        with self.lock:
            blocked: Set[Tuple[int, int]] = set()
            wgrid = self.office["wall_grid"]
            for r in range(GRID_ROWS):
                for c in range(GRID_COLS):
                    if wgrid[r][c] is not None:
                        blocked.add((c, r))
            for it in self.office.get("items", []):
                spec = OBJECT_CATALOG.get(it.get("type", ""))
                if spec and spec.get("blocking", True):
                    ic, ir = int(it["col"]), int(it["row"])
                    for r in range(ir, min(GRID_ROWS, ir + int(spec["tile_h"]))):
                        for c in range(ic, min(GRID_COLS, ic + int(spec["tile_w"]))):
                            blocked.add((c, r))
            return blocked

    def find_grid_path(
        self,
        start_cell: Tuple[int, int],
        goal_cell: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """
        Encuentra el camino más corto por cuadrículas (arriba, abajo, izquierda, derecha)
        esquivando paredes y muebles colocados por el usuario.
        """
        sc, sr = max(0, min(GRID_COLS - 1, start_cell[0])), max(0, min(GRID_ROWS - 1, start_cell[1]))
        gc, gr = max(0, min(GRID_COLS - 1, goal_cell[0])), max(0, min(GRID_ROWS - 1, goal_cell[1]))
        if (sc, sr) == (gc, gr):
            return []

        blocked = self.get_blocked_cells()
        blocked.discard((sc, sr))
        blocked.discard((gc, gr))

        queue = deque([(sc, sr)])
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {(sc, sr): None}

        while queue:
            curr = queue.popleft()
            if curr == (gc, gr):
                break
            cc, cr = curr
            for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nc, nr = cc + dc, cr + dr
                if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS:
                    if (nc, nr) not in came_from and (nc, nr) not in blocked:
                        came_from[(nc, nr)] = curr
                        queue.append((nc, nr))

        if (gc, gr) not in came_from:
            # Si el usuario encerró la celda con paredes, camino directo de emergencia
            return [(gc, gr)]

        path: List[Tuple[int, int]] = []
        node: Optional[Tuple[int, int]] = (gc, gr)
        while node and node != (sc, sr):
            path.append(node)
            node = came_from.get(node)
        path.reverse()
        return path

    # -------------------------------------------------------------------------
    # CONTROL DE DEMANDA Y PAIR-PROGRAMMING EN CUADRÍCULAS
    # -------------------------------------------------------------------------
    def allocate_station_positions(self, agents_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Asigna cada agente a una celda de cuadrícula frente a un dispositivo de su estación.
        Si hay menos dispositivos que agentes (ej. 2 computadores y 3 agentes):
          - 1 agente usa el computador 1
          - Los otros 2 comparten el computador 2: uno en la celda principal programando
            y el otro en la celda contigua mirándolo de lado (revisando / discutiendo juntos).
        """
        with self.lock:
            items = self.office.get("items", [])
            devices_by_station: Dict[str, List[Dict[str, Any]]] = {}
            for it in items:
                spec = OBJECT_CATALOG.get(it.get("type", ""))
                if spec and spec.get("station"):
                    devices_by_station.setdefault(spec["station"], []).append(it)

            agents_by_station: Dict[str, List[Dict[str, Any]]] = {}
            for ag in agents_list:
                st = ag.get("station", "lounge")
                agents_by_station.setdefault(st, []).append(ag)

            allocations: Dict[str, Dict[str, Any]] = {}

            for st, st_agents in agents_by_station.items():
                st_devs = devices_by_station.get(st, [])
                if not st_devs:
                    for idx, ag in enumerate(st_agents):
                        c, r = 25 + (idx % 4), 14 + (idx // 4)
                        allocations[ag["id"]] = {
                            "device_id": None,
                            "col": c,
                            "row": r,
                            "x": c * TILE_SIZE + TILE_SIZE // 2,
                            "y": r * TILE_SIZE + TILE_SIZE // 2,
                            "face": "down",
                            "role": "primary",
                            "is_collaborating": False,
                            "partner_name": None,
                        }
                    continue

                st_agents_sorted = sorted(st_agents, key=lambda a: a["id"])
                num_devs = len(st_devs)
                assigned_per_dev: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_devs)}
                for idx, ag in enumerate(st_agents_sorted):
                    assigned_per_dev[idx % num_devs].append(ag)

                for dev_idx, dev_agents in assigned_per_dev.items():
                    dev = st_devs[dev_idx]
                    spec = OBJECT_CATALOG[dev["type"]]
                    dc, dr = int(dev["col"]), int(dev["row"])
                    sc_dx, sc_dy, sface = spec.get("seat_cell", (0, 1, "up"))
                    collab_cells = spec.get("collab_cells", [(1, 1, "left"), (-1, 1, "right")])

                    has_collaborators = len(dev_agents) > 1
                    primary_ag = dev_agents[0] if dev_agents else None

                    for rank, ag in enumerate(dev_agents):
                        if rank == 0:
                            tc = max(0, min(GRID_COLS - 1, dc + sc_dx))
                            tr = max(0, min(GRID_ROWS - 1, dr + sc_dy))
                            partners = [a.get("name", a["id"][:6]) for a in dev_agents[1:]]
                            allocations[ag["id"]] = {
                                "device_id": dev["id"],
                                "col": tc,
                                "row": tr,
                                "x": tc * TILE_SIZE + TILE_SIZE // 2,
                                "y": tr * TILE_SIZE + TILE_SIZE // 2,
                                "face": sface,
                                "role": "primary",
                                "is_collaborating": has_collaborators,
                                "partner_name": ", ".join(partners) if partners else None,
                            }
                        else:
                            cdx, cdy, cface = collab_cells[(rank - 1) % len(collab_cells)]
                            tc = max(0, min(GRID_COLS - 1, dc + cdx))
                            tr = max(0, min(GRID_ROWS - 1, dr + cdy))
                            allocations[ag["id"]] = {
                                "device_id": dev["id"],
                                "col": tc,
                                "row": tr,
                                "x": tc * TILE_SIZE + TILE_SIZE // 2,
                                "y": tr * TILE_SIZE + TILE_SIZE // 2,
                                "face": cface,
                                "role": "collaborator",
                                "is_collaborating": True,
                                "partner_name": primary_ag.get("name", primary_ag["id"][:6]) if primary_ag else None,
                            }

            return allocations
