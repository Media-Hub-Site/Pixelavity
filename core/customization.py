# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Personalización por Cuadrículas (Tile-Grid 32x19) y Pool de Personajes
Estilo Pixel Agents (16px por celda escalado a 32x32 px):
  1. Pool de Personajes Personalizables (14 peinados, 8 expresiones, 12 atuendos de oficina,
     6 pantalones, 5 calzados, 12 accesorios, 6 extras de espalda)
  2. Asignación aleatoria sin repetición (solo repite si hay más agentes activos que personajes creados)
  3. Mapa de Oficina basado 100% en Cuadrículas (32 columnas x 19 filas de 32x32 px = 1024x608):
     - Piso por cuadrícula (floor_grid[row][col]) con Modo 1x1 y Modo Rellenar (Flood-Fill BFS)
     - Paredes arquitectónicas teal/ladrillo/madera/cristal por cuadrícula (wall_grid[row][col])
     - Objetos (Dispositivos, Muebles, Decoración) posicionados estrictamente en celdas (col, row)
  4. Reglas mínimas de dispositivos interactivos (mín. 1 Computador, 1 Estantería, etc.)
  5. Control de demanda y Pair-Programming / Colaboración por celdas adyacentes.
"""

import os
import json
import uuid
import copy
import random
import tempfile
import threading
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional, Any, Tuple, Set


def get_app_data_dir() -> str:
    """Devuelve una carpeta de datos con permisos de escritura garantizados en cualquier PC."""
    candidates = []
    for env_key in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        v = os.environ.get(env_key)
        if v:
            candidates.append(os.path.join(v, "MediaHub", "Pixelavity"))
    try:
        candidates.append(os.path.join(str(Path.home()), "MediaHub", "Pixelavity"))
    except Exception:
        pass
    candidates.append(os.path.join(tempfile.gettempdir(), "MediaHub", "Pixelavity"))

    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".write_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return d
        except OSError:
            continue
    return tempfile.gettempdir()


GRID_COLS = 32
GRID_ROWS = 19
TILE_SIZE = 32
WORLD_W = GRID_COLS * TILE_SIZE  # 1024
WORLD_H = GRID_ROWS * TILE_SIZE  # 608


# =============================================================================
# CATÁLOGOS DE PERSONALIZACIÓN PIXEL AGENTS (16x32 CHIBI OFICINA)
# =============================================================================
SKIN_TONES = [
    {"id": "ivory", "name": "Marfil Cálido",  "color": "#fce0c8"},
    {"id": "peach", "name": "Durazno Pixel",  "color": "#f5c59c"},
    {"id": "warm",  "name": "Trigueño",       "color": "#e5a370"},
    {"id": "olive", "name": "Oliva Dorado",   "color": "#d49c6e"},
    {"id": "tan",   "name": "Bronceado",      "color": "#cc8450"},
    {"id": "brown", "name": "Moreno",         "color": "#9d5d36"},
    {"id": "deep",  "name": "Ébano",          "color": "#6b3c22"},
]

EYE_COLORS = [
    {"id": "obsidian", "name": "Oscuro Pixel",    "color": "#18161e"},
    {"id": "ocean",    "name": "Azul Zafiro",     "color": "#2563eb"},
    {"id": "emerald",  "name": "Verde Esmeralda", "color": "#10b981"},
    {"id": "amber",    "name": "Ámbar Dorado",    "color": "#d97706"},
    {"id": "crimson",  "name": "Rojo Carmesí",    "color": "#dc2626"},
    {"id": "violet",   "name": "Violeta",         "color": "#7c3aed"},
    {"id": "cyan",     "name": "Cyan",            "color": "#0891b2"},
    {"id": "hazel",    "name": "Avellana",        "color": "#78350f"},
]

FACE_STYLES = [
    {"id": "classic",      "name": "Clásico Pixel Agents"},
    {"id": "happy",        "name": "Alegre con Rubor"},
    {"id": "focused",      "name": "Concentrado"},
    {"id": "cool",         "name": "Confiado / Guiño"},
    {"id": "sleepy",       "name": "Relajado / Chill"},
    {"id": "smile",        "name": "Sonrisa Amable"},
    {"id": "beard",        "name": "Barba y Bigote"},
    {"id": "cat",          "name": "Sonrisa Gatito (:3)"},
    {"id": "anime_starry", "name": "Ojos Estrellados Anime"},
    {"id": "anime_smirk",  "name": "Sonrisa Rival Anime"},
    {"id": "anime_blush",  "name": "Rubor Kawaii Anime"},
    {"id": "anime_scar",   "name": "Cicatriz Protagonista"},
]

HAIR_STYLES = [
    {"id": "spiky_tuft",       "name": "Mechón Puntas Clásico"},
    {"id": "parted_neat",      "name": "Ejecutivo con Raya"},
    {"id": "bob_cut",          "name": "Bob Clásico"},
    {"id": "long_straight",    "name": "Melena Larga Lisa"},
    {"id": "long_wavy",        "name": "Melena Ondulada"},
    {"id": "ponytail",         "name": "Coleta Alta"},
    {"id": "messy_fluffy",     "name": "Despeinado con Volumen"},
    {"id": "curtain_bangs",    "name": "Flequillo Cortina"},
    {"id": "buzz_short",       "name": "Corte Corto"},
    {"id": "curly_afro",       "name": "Rizado con Volumen"},
    {"id": "twin_buns",        "name": "Dos Moños"},
    {"id": "top_bun",          "name": "Moño Alto"},
    {"id": "side_swept",       "name": "Peinado al Lado"},
    {"id": "bald",             "name": "Sin Pelo"},
    {"id": "shonen_spikes",    "name": "Puntas Shonen Anime"},
    {"id": "gojo_swept",       "name": "Puntas al Viento / Gojo"},
    {"id": "levi_undercut",    "name": "Undercut Cortina Anime"},
    {"id": "samurai_ponytail", "name": "Coleta Samurái Alta"},
    {"id": "twintails_long",   "name": "Coletas Largas Anime"},
    {"id": "hime_cut",         "name": "Corte Hime Anime"},
    {"id": "wolf_mullet",      "name": "Wolf Cut / Mullet Anime"},
    {"id": "ahoge_fluff",      "name": "Despeinado con Ahoge"},
    {"id": "emo_cover",        "name": "Flequillo Ojo Tapado"},
    {"id": "drill_curls",      "name": "Rizos Dobles Anime"},
]

HAIR_COLORS = [
    {"id": "pixel_brown",   "name": "Castaño Pixel",     "color": "#946b3e"},
    {"id": "espresso",      "name": "Castaño Oscuro",    "color": "#4b352a"},
    {"id": "black",         "name": "Negro Carbón",      "color": "#262a34"},
    {"id": "white_anime",   "name": "Blanco Nieve Anime", "color": "#eef2ff"},
    {"id": "sakura_pink",   "name": "Rosa Sakura",       "color": "#f472b6"},
    {"id": "electric_blue", "name": "Azul Eléctrico",    "color": "#2563eb"},
    {"id": "emerald_anime", "name": "Verde Shonen",      "color": "#10b981"},
    {"id": "auburn",        "name": "Castaño Rojizo",    "color": "#a84c38"},
    {"id": "blonde",        "name": "Rubio Arena",       "color": "#ead2a2"},
    {"id": "gold",          "name": "Rubio Dorado",      "color": "#e5b23a"},
    {"id": "ginger",        "name": "Cobrizo Vivo",      "color": "#d95d2b"},
    {"id": "navy",          "name": "Azul Noche",        "color": "#3d4a6b"},
    {"id": "silver",        "name": "Plata / Blanco",    "color": "#cbd5e1"},
    {"id": "crimson",       "name": "Carmesí",           "color": "#b91c1c"},
    {"id": "violet",        "name": "Violeta",           "color": "#7e22ce"},
    {"id": "mint",          "name": "Esmeralda",         "color": "#0d9488"},
]

TORSO_STYLES = [
    {"id": "suit_tie",         "name": "Traje y Corbata"},
    {"id": "blazer_open",      "name": "Blazer Abierto"},
    {"id": "hoodie",           "name": "Polerón / Hoodie"},
    {"id": "shirt_collar",     "name": "Camisa de Oficina"},
    {"id": "sweater_vneck",    "name": "Suéter Cuello V"},
    {"id": "vest_shirt",       "name": "Chaleco y Camisa"},
    {"id": "tshirt_casual",    "name": "Camiseta Casual"},
    {"id": "striped_shirt",    "name": "Camiseta a Rayas"},
    {"id": "cardigan",         "name": "Cárdigan con Botones"},
    {"id": "tech_jacket",      "name": "Chaqueta Tech"},
    {"id": "lab_coat",         "name": "Bata de Laboratorio"},
    {"id": "overalls",         "name": "Overol Creativo"},
    {"id": "gakuran",          "name": "Uniforme Gakuran Anime"},
    {"id": "sailor_fuku",      "name": "Uniforme Sailor Anime"},
    {"id": "haori_kimono",     "name": "Haori / Kimono Anime"},
    {"id": "shinobi_vest",     "name": "Chaleco Shinobi"},
    {"id": "akatsuki_cloak",   "name": "Túnica Cuello Alto"},
    {"id": "techwear_coat",    "name": "Chaqueta Techwear Cyber"},
    {"id": "bomber_anime",     "name": "Bomber Urbana Anime"},
    {"id": "mage_coat",        "name": "Abrigo Hechicero"},
    {"id": "oversized_hoodie", "name": "Hoodie Streetwear"},
    {"id": "trench_detective", "name": "Gabardina Detective"},
]

# Alias de compatibilidad hacia atrás
OUTFIT_STYLES = TORSO_STYLES

PANTS_STYLES = [
    {"id": "dress_pants",   "name": "Pantalón Formal"},
    {"id": "jeans",         "name": "Jeans Clásicos"},
    {"id": "chinos",        "name": "Pantalón Chino"},
    {"id": "pleated_skirt", "name": "Falda Plisada"},
    {"id": "shorts",        "name": "Shorts Casuales"},
    {"id": "cargo",         "name": "Pantalón Cargo"},
]

SHOE_STYLES = [
    {"id": "oxfords",  "name": "Zapatos Formales"},
    {"id": "sneakers", "name": "Zapatillas Urbanas"},
    {"id": "loafers",  "name": "Mocasines"},
    {"id": "boots",    "name": "Botines"},
    {"id": "slippers", "name": "Zapatillas Cómodas"},
]

ACCESSORY_STYLES = [
    {"id": "none",             "name": "Ninguno"},
    {"id": "glasses",          "name": "Lentes de Lectura"},
    {"id": "sunglasses",       "name": "Lentes de Sol"},
    {"id": "headphones",       "name": "Audífonos Estudio"},
    {"id": "headset",          "name": "Diadema con Micrófono"},
    {"id": "baseball_cap",     "name": "Gorra Urbana"},
    {"id": "beanie",           "name": "Gorro de Lana"},
    {"id": "beret",            "name": "Boina Artística"},
    {"id": "cat_ears",         "name": "Orejas de Gato"},
    {"id": "crown",            "name": "Corona Dorada"},
    {"id": "bow",              "name": "Lazo en la Cabeza"},
    {"id": "bandana",          "name": "Cinta / Bandana"},
    {"id": "ninja_headband",   "name": "Banda Ninja Metálica"},
    {"id": "oni_mask_side",    "name": "Máscara Kitsune Lateral"},
    {"id": "cyber_visor",      "name": "Visor Cyber Neón"},
    {"id": "blindfold_cool",   "name": "Venda de Ojos Anime"},
    {"id": "eyepatch_anime",   "name": "Parche de Ojo"},
    {"id": "fox_ears",         "name": "Orejas Kitsune / Zorro"},
    {"id": "demon_horns",      "name": "Cuernos Oni"},
    {"id": "halo_neon",        "name": "Aureola Flotante"},
    {"id": "goggles_forehead", "name": "Gafas Shonen en Frente"},
    {"id": "face_mask",        "name": "Mascarilla Urbana"},
]

BACK_GEAR_STYLES = [
    {"id": "none",            "name": "Ninguno"},
    {"id": "backpack",        "name": "Mochila Tech"},
    {"id": "scarf",           "name": "Bufanda Larga"},
    {"id": "cape_mini",       "name": "Capa Ejecutiva"},
    {"id": "lanyard",         "name": "Credencial / Lanyard"},
    {"id": "angel_wings",     "name": "Alas Pixel"},
    {"id": "katana_back",     "name": "Katana en Espalda"},
    {"id": "dual_blades",     "name": "Doble Espada Cruzada"},
    {"id": "hero_scarf_long", "name": "Bufanda Anime al Viento"},
    {"id": "demon_wings",     "name": "Alas Oscuras"},
    {"id": "spirit_aura",     "name": "Aura Espiritual"},
    {"id": "guitar_case",     "name": "Guitarra en Espalda"},
]

_VALID_FACES = {item["id"] for item in FACE_STYLES}
_VALID_HAIRS = {item["id"] for item in HAIR_STYLES}
_VALID_TORSOS = {item["id"] for item in TORSO_STYLES}
_VALID_PANTS = {item["id"] for item in PANTS_STYLES}
_VALID_SHOES = {item["id"] for item in SHOE_STYLES}
_VALID_ACC = {item["id"] for item in ACCESSORY_STYLES}
_VALID_BACK = {item["id"] for item in BACK_GEAR_STYLES}

LEGACY_STYLE_MAP: Dict[str, Dict[str, str]] = {
    "face_style": {
        "determined": "classic",
        "stoic": "focused",
        "scarred": "focused",
        "beard_smile": "beard",
        "cat_smile": "cat",
        "starry": "happy",
        "surprised": "happy",
    },
    "hair_style": {
        "warrior_messy": "spiky_tuft",
        "ronin_swept": "side_swept",
        "fluffy_spiky": "messy_fluffy",
        "samurai_topknot": "top_bun",
        "short_parted": "parted_neat",
        "wavy_bob": "bob_cut",
        "wolf_cut": "messy_fluffy",
        "anime_spiky": "spiky_tuft",
        "spiky_messy": "spiky_tuft",
        "pigtails": "twin_buns",
        "low_ponytail": "ponytail",
        "braids": "long_wavy",
        "side_shave": "buzz_short",
        "mohawk": "spiky_tuft",
        "flat_top": "buzz_short",
        "receding": "parted_neat",
    },
    "torso_style": {
        "adventurer_tunic": "suit_tie",
        "samurai_haori": "cardigan",
        "bare_warrior": "tshirt_casual",
        "knight_plate": "tech_jacket",
        "shinobi_wrap": "hoodie",
        "cyber_jacket": "tech_jacket",
        "mage_robe": "cardigan",
        "trench_coat": "blazer_open",
        "leather_vest": "vest_shirt",
        "varsity_jacket": "tech_jacket",
        "striped_sweater": "striped_shirt",
        "tank_top": "tshirt_casual",
        "tshirt_jeans": "tshirt_casual",
        "dress_skirt": "tshirt_casual",
        "cloak": "cardigan",
        "kimono": "cardigan",
        "knight_armor": "tech_jacket",
    },
    "pants_style": {
        "adventurer_breeches": "dress_pants",
        "samurai_hakama": "chinos",
        "martial_baggy": "cargo",
        "slim_jeans": "jeans",
        "cargo_tactical": "cargo",
        "armored_cuisses": "dress_pants",
        "kusazuri_plates": "pleated_skirt",
        "cyber_pants": "jeans",
        "mage_skirt": "pleated_skirt",
        "dress_trousers": "dress_pants",
        "battle_shorts": "shorts",
    },
    "shoe_style": {
        "leather_boots": "boots",
        "tabi_sandals": "slippers",
        "shin_wraps": "boots",
        "knight_greaves": "boots",
        "combat_boots": "boots",
        "cyber_boots": "sneakers",
        "elf_boots": "boots",
        "high_tops": "sneakers",
        "classic": "oxfords",
        "sandals": "slippers",
    },
    "accessory": {
        "headband": "bandana",
        "eyepatch": "none",
        "scarf_mask": "bandana",
        "oni_mask": "none",
        "cyber_visor": "sunglasses",
        "aviator_goggles": "glasses",
        "fedora": "beret",
        "straw_hat": "beret",
        "witch_hat": "beret",
        "top_hat": "crown",
        "viking_helmet": "none",
        "halo": "crown",
    },
    "back_gear": {
        "adventurer_pack": "backpack",
        "scarf_flowing": "scarf",
        "hero_cape": "cape_mini",
        "cyber_wings": "angel_wings",
    },
}


def normalize_character(char: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza y migra personajes antiguos o incompletos al esquema Pixel Agents 16x32."""
    out = copy.deepcopy(char)

    if not out.get("torso_style") and out.get("outfit_style"):
        out["torso_style"] = out["outfit_style"]

    def _resolve(field: str, valid_set: Set[str], default_val: str):
        val = out.get(field, default_val)
        if val in valid_set:
            return
        mapped = LEGACY_STYLE_MAP.get(field, {}).get(val)
        out[field] = mapped if mapped in valid_set else default_val

    _resolve("face_style", _VALID_FACES, "classic")
    _resolve("hair_style", _VALID_HAIRS, "spiky_tuft")
    _resolve("torso_style", _VALID_TORSOS, "suit_tie")
    _resolve("pants_style", _VALID_PANTS, "dress_pants")
    _resolve("shoe_style", _VALID_SHOES, "oxfords")
    _resolve("accessory", _VALID_ACC, "none")
    _resolve("back_gear", _VALID_BACK, "none")

    out.setdefault("skin_color", "#f5c59c")
    out.setdefault("eye_color", "#18161e")
    out.setdefault("hair_color", "#946b3e")
    out.setdefault("top_color", "#1f6199")
    out.setdefault("bottom_color", "#1d4e78")
    out.setdefault("shoe_color", "#1a1e26")
    out.setdefault("accessory_color", "#d97706")
    out["outfit_style"] = out["torso_style"]
    return out


DEFAULT_CHARACTERS: List[Dict[str, Any]] = [
    {
        "id": "char-pa-alex",
        "name": "Alex",
        "skin_color": "#f5c59c",
        "eye_color": "#18161e",
        "face_style": "classic",
        "hair_style": "spiky_tuft",
        "hair_color": "#946b3e",
        "torso_style": "suit_tie",
        "outfit_style": "suit_tie",
        "top_color": "#1f6199",
        "pants_style": "dress_pants",
        "bottom_color": "#1d4e78",
        "shoe_style": "oxfords",
        "shoe_color": "#1a1e26",
        "accessory": "none",
        "accessory_color": "#d97706",
        "back_gear": "none",
    },
    {
        "id": "char-pa-sofia",
        "name": "Sofía",
        "skin_color": "#fce0c8",
        "eye_color": "#18161e",
        "face_style": "happy",
        "hair_style": "bob_cut",
        "hair_color": "#a84c38",
        "torso_style": "cardigan",
        "outfit_style": "cardigan",
        "top_color": "#942c4f",
        "pants_style": "pleated_skirt",
        "bottom_color": "#334155",
        "shoe_style": "loafers",
        "shoe_color": "#3d261f",
        "accessory": "glasses",
        "accessory_color": "#d97706",
        "back_gear": "none",
    },
    {
        "id": "char-pa-mateo",
        "name": "Mateo",
        "skin_color": "#e5a370",
        "eye_color": "#18161e",
        "face_style": "focused",
        "hair_style": "parted_neat",
        "hair_color": "#262a34",
        "torso_style": "hoodie",
        "outfit_style": "hoodie",
        "top_color": "#2a7a64",
        "pants_style": "jeans",
        "bottom_color": "#2b3a55",
        "shoe_style": "sneakers",
        "shoe_color": "#e2e8f0",
        "accessory": "headphones",
        "accessory_color": "#38bdf8",
        "back_gear": "none",
    },
    {
        "id": "char-pa-luna",
        "name": "Luna",
        "skin_color": "#f5c59c",
        "eye_color": "#7c3aed",
        "face_style": "smile",
        "hair_style": "ponytail",
        "hair_color": "#ead2a2",
        "torso_style": "blazer_open",
        "outfit_style": "blazer_open",
        "top_color": "#3d4a6b",
        "pants_style": "chinos",
        "bottom_color": "#a89282",
        "shoe_style": "oxfords",
        "shoe_color": "#3d261f",
        "accessory": "none",
        "accessory_color": "#e879f9",
        "back_gear": "lanyard",
    },
    {
        "id": "char-pa-diego",
        "name": "Diego",
        "skin_color": "#9d5d36",
        "eye_color": "#18161e",
        "face_style": "beard",
        "hair_style": "curly_afro",
        "hair_color": "#262a34",
        "torso_style": "vest_shirt",
        "outfit_style": "vest_shirt",
        "top_color": "#78350f",
        "pants_style": "dress_pants",
        "bottom_color": "#1e293b",
        "shoe_style": "boots",
        "shoe_color": "#3d261f",
        "accessory": "none",
        "accessory_color": "#d97706",
        "back_gear": "none",
    },
    {
        "id": "char-pa-valentina",
        "name": "Valentina",
        "skin_color": "#d49c6e",
        "eye_color": "#0891b2",
        "face_style": "cool",
        "hair_style": "long_wavy",
        "hair_color": "#4b352a",
        "torso_style": "sweater_vneck",
        "outfit_style": "sweater_vneck",
        "top_color": "#0e7490",
        "pants_style": "jeans",
        "bottom_color": "#1d4e78",
        "shoe_style": "sneakers",
        "shoe_color": "#1e293b",
        "accessory": "beret",
        "accessory_color": "#942c4f",
        "back_gear": "none",
    },
    {
        "id": "char-pa-kaito",
        "name": "Kaito",
        "skin_color": "#fce0c8",
        "eye_color": "#0891b2",
        "face_style": "anime_smirk",
        "hair_style": "gojo_swept",
        "hair_color": "#eef2ff",
        "torso_style": "techwear_coat",
        "outfit_style": "techwear_coat",
        "top_color": "#1e293b",
        "pants_style": "jeans",
        "bottom_color": "#0f172a",
        "shoe_style": "sneakers",
        "shoe_color": "#1a1e26",
        "accessory": "cyber_visor",
        "accessory_color": "#38bdf8",
        "back_gear": "katana_back",
    },
    {
        "id": "char-pa-sakura",
        "name": "Sakura",
        "skin_color": "#fce0c8",
        "eye_color": "#dc2626",
        "face_style": "anime_starry",
        "hair_style": "twintails_long",
        "hair_color": "#f472b6",
        "torso_style": "sailor_fuku",
        "outfit_style": "sailor_fuku",
        "top_color": "#1d4e78",
        "pants_style": "pleated_skirt",
        "bottom_color": "#1e293b",
        "shoe_style": "loafers",
        "shoe_color": "#3d261f",
        "accessory": "fox_ears",
        "accessory_color": "#f472b6",
        "back_gear": "hero_scarf_long",
    },
]


# =============================================================================
# MATERIALES DE PISO Y PARED POR CUADRÍCULA (16x16 NATIVO -> 32x32)
# =============================================================================
FLOOR_MATERIALS: Dict[str, Dict[str, str]] = {
    "cream_tile":    {"name": "Beige Oficina",       "colorA": "#ddd0b6", "colorB": "#c9b899", "grout": "#a89070", "pattern": "office_tile"},
    "oak_wood":      {"name": "Madera Roble",        "colorA": "#b8844f", "colorB": "#9e6b3b", "grout": "#784d27", "pattern": "planks"},
    "walnut_wood":   {"name": "Madera Nogal",        "colorA": "#7d522c", "colorB": "#684222", "grout": "#452a18", "pattern": "planks"},
    "parquet_gold":  {"name": "Parquet Cálido",      "colorA": "#c4925c", "colorB": "#a67443", "grout": "#7d522c", "pattern": "checkers"},
    "red_carpet":    {"name": "Alfombra Carmesí",    "colorA": "#a31c24", "colorB": "#8b161d", "grout": "#6d1016", "pattern": "carpet"},
    "navy_carpet":   {"name": "Alfombra Azul",       "colorA": "#26415c", "colorB": "#20374f", "grout": "#17293b", "pattern": "carpet"},
    "emerald_tile":  {"name": "Baldosa Salvia",      "colorA": "#a8c4b0", "colorB": "#93b29c", "grout": "#6e8d78", "pattern": "office_tile"},
    "metal_grate":   {"name": "Piso Técnico",        "colorA": "#5b6778", "colorB": "#485363", "grout": "#2f3845", "pattern": "grate"},
    "cyber_grid":    {"name": "Pizarra Azul",        "colorA": "#7892a8", "colorB": "#667f94", "grout": "#4a5f72", "pattern": "office_tile"},
    "amber_tech":    {"name": "Terracota Suave",     "colorA": "#cfa783", "colorB": "#bc916b", "grout": "#966f4d", "pattern": "office_tile"},
    "studio_purple": {"name": "Baldosa Lavanda",     "colorA": "#b4a6c9", "colorB": "#9f90b5", "grout": "#7a6c91", "pattern": "checkers"},
    "cafe_warm":     {"name": "Cerámica Café",       "colorA": "#d4beaa", "colorB": "#bfa48c", "grout": "#997d65", "pattern": "checkers"},
    "marble_slate":  {"name": "Baldosa Gris",        "colorA": "#9fa8b8", "colorB": "#8a94a6", "grout": "#687285", "pattern": "office_tile"},
    "marble_white":  {"name": "Mármol Crema",        "colorA": "#ece4d3", "colorB": "#ded3be", "grout": "#b8ab94", "pattern": "office_tile"},
}

WALL_MATERIALS: Dict[str, Dict[str, str]] = {
    "dark_tech":  {"name": "Muro Teal Oficina",  "top": "#1e4255", "front": "#45738c", "trim": "#2c4e61", "border": "#131820"},
    "brick_wall": {"name": "Pared de Ladrillo",  "top": "#5c261c", "front": "#964433", "trim": "#6e2e22", "border": "#261310"},
    "wood_panel": {"name": "Tabique de Madera",  "top": "#52321b", "front": "#8a5832", "trim": "#663e22", "border": "#24150c"},
    "glass_wall": {"name": "División Cristal",   "top": "#2d5f78", "front": "#78bdd6", "trim": "#4e92ab", "border": "#182c38"},
    "cyber_neon": {"name": "Muro Crema Oficina", "top": "#59554d", "front": "#b8b09c", "trim": "#8c8472", "border": "#24211c"},
}


# =============================================================================
# CATÁLOGO UNIFICADO POR CATEGORÍAS (TAMAÑOS EN CUADRÍCULAS tile_w x tile_h)
# =============================================================================
OBJECT_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- CATEGORÍA 1: DISPOSITIVOS ---
    "computer_desk": {
        "type": "computer_desk",
        "category": "devices",
        "station": "coding_desk",
        "name": "Escritorio PC Retro",
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
        "name": "Escritorio Compacto PC",
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
        "name": "Estación Terminal / Rack",
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
        "name": "Pizarra de Estrategia",
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
        "name": "Mesa Mando Orchestrator",
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
        "name": "Estación Web Dual",
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
        "name": "Mesa Estudio Diseño",
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
        "name": "Sofá Lounge Carmesí",
        "icon": "🛋️",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 0, "down"),
        "collab_cells": [(1, 0, "down"), (0, 1, "up")],
    },
    "lounge_armchair": {
        "type": "lounge_armchair",
        "category": "furniture",
        "station": "lounge",
        "name": "Sillón Lounge Individual",
        "icon": "🪑",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
        "seat_cell": (0, 0, "down"),
        "collab_cells": [(1, 0, "left"), (-1, 0, "right")],
    },
    "office_chair": {
        "type": "office_chair",
        "category": "furniture",
        "station": None,
        "name": "Silla de Madera",
        "icon": "🪑",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": False,
    },
    "gaming_chair": {
        "type": "gaming_chair",
        "category": "furniture",
        "station": None,
        "name": "Silla Giratoria",
        "icon": "💺",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": False,
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
    "coffee_table": {
        "type": "coffee_table",
        "category": "furniture",
        "station": None,
        "name": "Mesa de Centro",
        "icon": "🪵",
        "tile_w": 2,
        "tile_h": 2,
        "blocking": True,
    },
    "reading_table": {
        "type": "reading_table",
        "category": "furniture",
        "station": None,
        "name": "Mesa de Madera",
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
        "name": "Planta de Interior",
        "icon": "🪴",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "plant_cactus": {
        "type": "plant_cactus",
        "category": "decorations",
        "station": None,
        "name": "Planta Espada",
        "icon": "🌿",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "trash_bin": {
        "type": "trash_bin",
        "category": "decorations",
        "station": None,
        "name": "Papelera Oficina",
        "icon": "🗑️",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "wall_painting": {
        "type": "wall_painting",
        "category": "decorations",
        "station": None,
        "name": "Cuadro Paisaje",
        "icon": "🖼️",
        "tile_w": 2,
        "tile_h": 1,
        "blocking": True,
    },
    "wall_clock": {
        "type": "wall_clock",
        "category": "decorations",
        "station": None,
        "name": "Reloj de Pared",
        "icon": "🕒",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": False,
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
        "name": "Dispensador de Agua",
        "icon": "🚰",
        "tile_w": 1,
        "tile_h": 1,
        "blocking": True,
    },
    "rug_persian": {
        "type": "rug_persian",
        "category": "decorations",
        "station": None,
        "name": "Alfombra Carmesí (3x2)",
        "icon": "🟥",
        "tile_w": 3,
        "tile_h": 2,
        "blocking": False,
    },
    "rug_lounge": {
        "type": "rug_lounge",
        "category": "decorations",
        "station": None,
        "name": "Alfombra Lounge Grande (5x4)",
        "icon": "🟥",
        "tile_w": 5,
        "tile_h": 4,
        "blocking": False,
    },
    "rug_cyber": {
        "type": "rug_cyber",
        "category": "decorations",
        "station": None,
        "name": "Alfombra Azul",
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
    "coding_desk":      "Computador (PC o Laptop)",
    "library":          "Estantería de Libros",
    "server_lab":       "Estación Terminal / Rack",
    "strategy_board":   "Pizarra de Estrategia",
    "orchestrator_hub": "Mesa Mando Orchestrator",
    "web_station":      "Estación Web Dual",
    "art_studio":       "Mesa Estudio Diseño",
    "lounge":           "Sofá o Barra de Cafetería",
}


def build_default_office_layout() -> Dict[str, Any]:
    """
    Construye el mapa por defecto en una cuadrícula exacta de 32x19 celdas (32x32 px)
    inspirado directamente en la estética Pixel Agents:
      - Piso beige/crema cálido con juntas limpias
      - Paredes perimetrales teal arquitectónicas y divisiones con puertas amplias
      - Sala Lounge con alfombra carmesí, sofás rosado-burdeos y mesa de centro
      - Islas de escritorios de madera con PCs retro CRT, sillas de madera y tazas
      - Libreros coloridos, pizarras, reloj de pared, cuadro paisaje y plantas
    """
    floor_grid = [["cream_tile" for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    wall_grid: List[List[Optional[str]]] = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    # Pisos cálidos por zona para dar lectura espacial clara sin romper la armonía
    for r in range(1, 7):
        for c in range(1, 8):
            floor_grid[r][c] = "oak_wood"      # Biblioteca (arriba-izquierda)
        for c in range(23, 31):
            floor_grid[r][c] = "cyber_grid"    # Cabina Web & Terminal (arriba-derecha)
    for r in range(12, 18):
        for c in range(1, 7):
            floor_grid[r][c] = "oak_wood"      # Estudio Diseño (abajo-izquierda)

    # Paredes perimetrales (estilo Pixel Agents)
    for c in range(GRID_COLS):
        wall_grid[0][c] = "dark_tech"
        wall_grid[GRID_ROWS - 1][c] = "dark_tech"
    for r in range(GRID_ROWS):
        wall_grid[r][0] = "dark_tech"
        wall_grid[r][GRID_COLS - 1] = "dark_tech"

    # Nicho arquitectónico superior izquierdo para separar Biblioteca de Estrategia
    for r in range(1, 5):
        wall_grid[r][8] = "dark_tech"
    # Pared separadora parcial en el ala derecha superior
    for r in range(1, 4):
        wall_grid[r][22] = "dark_tech"
    # Ala inferior izquierda (Estudio UI) con abertura amplia
    for r in range(13, 18):
        wall_grid[r][7] = "dark_tech"

    items = [
        # --- BIBLIOTECA (arriba-izquierda, cols 1..7) ---
        {"id": "obj-lib-1", "type": "bookshelf",       "col": 1,  "row": 1},
        {"id": "obj-lib-2", "type": "bookshelf",       "col": 3,  "row": 1},
        {"id": "obj-lib-3", "type": "bookshelf_single","col": 5,  "row": 1},
        {"id": "obj-lib-4", "type": "plant_monstera",  "col": 7,  "row": 1},
        {"id": "obj-lib-5", "type": "reading_table",   "col": 2,  "row": 4},
        {"id": "obj-lib-6", "type": "office_chair",    "col": 2,  "row": 5},
        {"id": "obj-lib-7", "type": "office_chair",    "col": 3,  "row": 5},

        # --- ESTRATEGIA & ORCHESTRATOR (arriba-centro, cols 9..21) ---
        {"id": "obj-str-1", "type": "whiteboard",        "col": 10, "row": 1},
        {"id": "obj-clk-1", "type": "wall_clock",        "col": 13, "row": 0},
        {"id": "obj-str-2", "type": "whiteboard",        "col": 14, "row": 1},
        {"id": "obj-pnt-1", "type": "wall_painting",     "col": 18, "row": 1},
        {"id": "obj-orc-1", "type": "orchestrator_core", "col": 18, "row": 4},
        {"id": "obj-orc-2", "type": "plant_monstera",    "col": 21, "row": 1},

        # --- CABINA WEB & TERMINAL LAB (arriba-derecha, cols 23..30) ---
        {"id": "obj-web-1", "type": "web_radar",       "col": 23, "row": 1},
        {"id": "obj-web-2", "type": "web_radar",       "col": 26, "row": 1},
        {"id": "obj-srv-1", "type": "server_terminal", "col": 24, "row": 4},
        {"id": "obj-srv-2", "type": "server_terminal", "col": 28, "row": 4},
        {"id": "obj-srv-3", "type": "plant_cactus",    "col": 30, "row": 1},

        # --- LOUNGE / CAFETERÍA CENTRAL (alfombra carmesí continua + sofás burdeos, cols 3..7, rows 7..10) ---
        {"id": "obj-lng-r1", "type": "rug_lounge",      "col": 3,  "row": 7},
        {"id": "obj-lng-s1", "type": "coffee_sofa",     "col": 4,  "row": 7},
        {"id": "obj-lng-t1", "type": "coffee_table",    "col": 4,  "row": 8},
        {"id": "obj-lng-s2", "type": "coffee_sofa",     "col": 4,  "row": 10},
        {"id": "obj-lng-a1", "type": "lounge_armchair", "col": 7,  "row": 8},
        {"id": "obj-lng-b1", "type": "coffee_bar",      "col": 1,  "row": 7},
        {"id": "obj-lng-w1", "type": "water_cooler",    "col": 1,  "row": 9},

        # --- COMPUTADORES / WORKSTATIONS (centro y derecha, cols 11..30, rows 9..17) ---
        {"id": "obj-pc-1", "type": "computer_desk", "col": 12, "row": 10},
        {"id": "obj-pc-2", "type": "computer_desk", "col": 16, "row": 10},
        {"id": "obj-pc-3", "type": "computer_desk", "col": 12, "row": 14},
        {"id": "obj-pc-4", "type": "computer_desk", "col": 16, "row": 14},
        {"id": "obj-pc-5", "type": "computer_desk", "col": 23, "row": 10},
        {"id": "obj-pc-6", "type": "laptop_desk",   "col": 27, "row": 10},
        {"id": "obj-pc-7", "type": "computer_desk", "col": 24, "row": 14},
        {"id": "obj-mtg-1","type": "meeting_table", "col": 27, "row": 14},
        {"id": "obj-dec-1","type": "plant_cactus",  "col": 30, "row": 9},
        {"id": "obj-dec-2","type": "plant_monstera","col": 21, "row": 12},
        {"id": "obj-dec-3","type": "trash_bin",     "col": 10, "row": 16},

        # --- ESTUDIO UI / ARTE (abajo-izquierda, cols 1..6, rows 13..17) ---
        {"id": "obj-art-1", "type": "art_easel",      "col": 2, "row": 14},
        {"id": "obj-art-2", "type": "filing_cabinet", "col": 1, "row": 13},
        {"id": "obj-art-3", "type": "trophy",         "col": 5, "row": 13},
        {"id": "obj-art-4", "type": "plant_cactus",   "col": 1, "row": 17},
        {"id": "obj-art-5", "type": "plant_cactus",   "col": 2, "row": 17},
    ]

    return {
        "schema": "pixel_agents_v3",
        "floor_grid": floor_grid,
        "wall_grid": wall_grid,
        "items": items,
    }


# =============================================================================
# GESTOR CENTRAL DE PERSONALIZACIÓN, CUADRÍCULA, PATHFINDING BFS Y DEMANDA
# =============================================================================
class CustomizationManager:
    def __init__(self, storage_path: Optional[str] = None):
        if not storage_path:
            data_dir = get_app_data_dir()
            storage_path = os.path.join(data_dir, "customization_v3.json")
        self.storage_path = storage_path
        self.lock = threading.RLock()

        self.characters: List[Dict[str, Any]] = copy.deepcopy(DEFAULT_CHARACTERS)
        self.office: Dict[str, Any] = build_default_office_layout()
        self.agent_to_character: Dict[str, str] = {}
        self.custom_brain_dir: Optional[str] = None
        self._load()

    def _load(self):
        if not os.path.isfile(self.storage_path):
            # Conservar únicamente la ruta personalizada de Antigravity desde v2 si existe
            legacy_v2 = os.path.join(os.path.dirname(self.storage_path), "customization_v2.json")
            if os.path.isfile(legacy_v2):
                try:
                    with open(legacy_v2, "r", encoding="utf-8") as f:
                        v2 = json.load(f)
                    cbd = v2.get("custom_brain_dir")
                    if isinstance(cbd, str) and cbd.strip():
                        self.custom_brain_dir = cbd.strip()
                except Exception:
                    pass
            self._save()
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw.get("characters"), list) and len(raw["characters"]) > 0:
                self.characters = [normalize_character(c) for c in raw["characters"]]
            off = raw.get("office")
            if isinstance(off, dict) and off.get("schema") == "pixel_agents_v3":
                self.office = off
            cbd = raw.get("custom_brain_dir")
            if isinstance(cbd, str) and cbd.strip():
                self.custom_brain_dir = cbd.strip()
        except Exception as e:
            print(f"[CustomizationManager] Error cargando configuración: {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "characters": self.characters,
                        "office": self.office,
                        "custom_brain_dir": self.custom_brain_dir,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print(f"[CustomizationManager] Error guardando configuración: {e}")

    def get_custom_brain_dir(self) -> Optional[str]:
        with self.lock:
            return self.custom_brain_dir

    def set_custom_brain_dir(self, path: Optional[str]):
        with self.lock:
            cleaned = path.strip() if isinstance(path, str) and path.strip() else None
            self.custom_brain_dir = cleaned
            self._save()

    # -------------------------------------------------------------------------
    # PERSONAJES Y ASIGNACIÓN SIN REPETICIÓN
    # -------------------------------------------------------------------------
    def get_characters(self) -> List[Dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.characters)

    def save_character(self, char_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            char_data = normalize_character(char_data)
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
        spec = OBJECT_CATALOG.get(obj_type)
        if not spec:
            return False
        tw, th = int(spec["tile_w"]), int(spec["tile_h"])
        if col < 0 or row < 0 or (col + tw) > GRID_COLS or (row + th) > GRID_ROWS:
            return False

        is_blocking = bool(spec.get("blocking", True))
        with self.lock:
            wgrid = self.office["wall_grid"]
            if obj_type != "wall_clock":
                for r in range(row, row + th):
                    for c in range(col, col + tw):
                        if wgrid[r][c] is not None:
                            return False

            for other in self.office.get("items", []):
                if other.get("id") == ignore_item_id:
                    continue
                ospec = OBJECT_CATALOG.get(other.get("type", ""))
                if not ospec:
                    continue
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
                    f"Regla de la oficina: Debe existir como mínimo 1 {label} en la cuadrícula "
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
                        c, r = 4 + (idx % 4), 8 + (idx // 4)
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
                                "device_type": dev["type"],
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
                                "device_type": dev["type"],
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
