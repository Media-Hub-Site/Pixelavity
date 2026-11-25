# -*- coding: utf-8 -*-
"""
Pixelavity - Motor de Personalización de Personajes, Background (Oficina) y Control de Demanda
Gestiona:
  1. Pool de Personajes Personalizables (3 por defecto + creados por el usuario)
  2. Asignación aleatoria sin repetición (solo repite cuando hay más agentes activos que personajes creados)
  3. Personalización completa del Background (materiales de piso, colores de pared, dispositivos y decoraciones)
  4. Reglas de validación de dispositivos mínimos (mín. 1 Computador, 1 Estantería de Libros, etc.)
  5. Asignación inteligente de dispositivos bajo demanda (Pair-Programming / Revisión colaborativa cuando
     hay más agentes que computadores o muebles disponibles).
"""

import os
import json
import uuid
import copy
import random
import threading
from typing import Dict, List, Optional, Any, Tuple


# =============================================================================
# CATÁLOGOS DE OPCIONES DE PERSONALIZACIÓN DE PERSONAJES
# =============================================================================
SKIN_TONES = [
    {"id": "peach",   "name": "Durazno Claro", "color": "#ffcca8", "shadow": "#e0a57e"},
    {"id": "light",   "name": "Marfil Cálido", "color": "#ffe0c8", "shadow": "#e5b898"},
    {"id": "warm",    "name": "Trigueño",      "color": "#f1b280", "shadow": "#c98a5b"},
    {"id": "tan",     "name": "Bronceado",     "color": "#d9915b", "shadow": "#b36f3c"},
    {"id": "brown",   "name": "Moreno",        "color": "#a8653a", "shadow": "#824924"},
    {"id": "deep",    "name": "Ébano",         "color": "#6e3f23", "shadow": "#4d2914"},
]

FACE_STYLES = [
    {"id": "smile",   "name": "Sonrisa Clásica"},
    {"id": "happy",   "name": "Alegre"},
    {"id": "focused", "name": "Concentrado"},
    {"id": "cool",    "name": "Guiño / Cool"},
]

HAIR_STYLES = [
    {"id": "short_parted",  "name": "Corto Clásico"},
    {"id": "ponytail",      "name": "Coleta con Moño"},
    {"id": "long_straight", "name": "Largo Liso"},
    {"id": "wavy_bob",      "name": "Melena Ondulada"},
    {"id": "pigtails",      "name": "Dos Coletas"},
    {"id": "top_bun",       "name": "Moño Alto"},
    {"id": "flat_top",      "name": "Corte Alto (Flat-Top)"},
    {"id": "receding",      "name": "Corto Despejado"},
    {"id": "bald",          "name": "Sin Pelo"},
]

HAIR_COLORS = [
    {"id": "gold",     "name": "Rubio Dorado",    "color": "#eab308"},
    {"id": "auburn",   "name": "Castaño Rojizo",  "color": "#c2593f"},
    {"id": "navy",     "name": "Azul Noche",      "color": "#2b3a55"},
    {"id": "espresso", "name": "Castaño Oscuro",  "color": "#432818"},
    {"id": "black",    "name": "Negro Carbón",    "color": "#1e2229"},
    {"id": "ginger",   "name": "Pelirrojo",       "color": "#e05a2b"},
    {"id": "silver",   "name": "Plata / Blanco",  "color": "#cbd5e1"},
    {"id": "violet",   "name": "Violeta Cyber",   "color": "#9333ea"},
    {"id": "mint",     "name": "Menta Neon",      "color": "#10b981"},
]

OUTFIT_STYLES = [
    {"id": "suit_tie",     "name": "Traje Formal y Corbata"},
    {"id": "tshirt_jeans", "name": "Camiseta y Pantalón"},
    {"id": "hoodie",       "name": "Polerón / Hoodie"},
    {"id": "vest_shirt",   "name": "Chaleco y Camisa"},
    {"id": "overalls",     "name": "Overol / Jardinera"},
    {"id": "dress_skirt",  "name": "Blusa y Falda"},
    {"id": "cloak",        "name": "Capa Larga"},
    {"id": "tank_top",     "name": "Deportivo Sin Mangas"},
]

SHOE_STYLES = [
    {"id": "classic",  "name": "Zapatos Clásicos"},
    {"id": "sneakers", "name": "Zapatillas Deportivas"},
    {"id": "boots",    "name": "Botas"},
]

ACCESSORY_STYLES = [
    {"id": "none",            "name": "Ninguno"},
    {"id": "headphones",      "name": "Audífonos Cyber"},
    {"id": "glasses",         "name": "Lentes Pixel"},
    {"id": "fedora",          "name": "Sombrero Detective"},
    {"id": "witch_hat",       "name": "Sombrero de Mago"},
    {"id": "top_hat",         "name": "Sombrero de Copa"},
    {"id": "aviator_goggles", "name": "Casco y Gafas"},
    {"id": "viking_helmet",   "name": "Casco Vikingo"},
    {"id": "nurse_cap",       "name": "Gorro Blanco"},
    {"id": "straw_hat",       "name": "Sombrero de Paja"},
]


# =============================================================================
# 3 PERSONAJES POR DEFECTO (INSPIRADOS EN LA IMAGEN DE REFERENCIA)
# =============================================================================
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
# MATERIALES DE PISO, DISPOSITIVOS Y DECORACIÓN DEL BACKGROUND
# =============================================================================
FLOOR_MATERIALS: Dict[str, Dict[str, str]] = {
    "oak_wood":      {"name": "Madera Roble",       "colorA": "#3d291e", "colorB": "#332219", "pattern": "planks"},
    "walnut_wood":   {"name": "Madera Nogal",       "colorA": "#271d18", "colorB": "#211814", "pattern": "planks"},
    "navy_carpet":   {"name": "Alfombra Azul",      "colorA": "#141f2e", "colorB": "#111a27", "pattern": "grid"},
    "emerald_tile":  {"name": "Baldosa Esmeralda",  "colorA": "#12211c", "colorB": "#0f1c18", "pattern": "tiles"},
    "metal_grate":   {"name": "Metal Industrial",   "colorA": "#1d222b", "colorB": "#171b22", "pattern": "grate"},
    "cyber_grid":    {"name": "Cyber Grid Cyan",    "colorA": "#10212b", "colorB": "#0c1a22", "pattern": "grid"},
    "amber_tech":    {"name": "Hex Tech Ámbar",     "colorA": "#221b12", "colorB": "#1c160e", "pattern": "tiles"},
    "studio_purple": {"name": "Estudio Violeta",    "colorA": "#21152c", "colorB": "#1b1124", "pattern": "checkers"},
    "cafe_warm":     {"name": "Cerámica Cafetería", "colorA": "#281a20", "colorB": "#21151a", "pattern": "checkers"},
    "marble_slate":  {"name": "Mármol Pizarra",     "colorA": "#27303f", "colorB": "#222a38", "pattern": "tiles"},
}

# Catálogo de dispositivos interactivos y reglas de cantidad mínima obligatoria
DEVICE_CATALOG: Dict[str, Dict[str, Any]] = {
    "computer_desk": {
        "type": "computer_desk",
        "station": "coding_desk",
        "name": "Computador (PC)",
        "icon": "💻",
        "min_required": 1,
        "w": 80,
        "h": 44,
        "seat_offset": (0, 24, "up"),
        "collab_offsets": [(-28, 22, "right"), (28, 22, "left"), (0, 44, "up")],
    },
    "bookshelf": {
        "type": "bookshelf",
        "station": "library",
        "name": "Mueble de Libros",
        "icon": "📚",
        "min_required": 1,
        "w": 64,
        "h": 50,
        "seat_offset": (0, 38, "up"),
        "collab_offsets": [(-26, 38, "right"), (26, 38, "left"), (0, 56, "up")],
    },
    "server_terminal": {
        "type": "server_terminal",
        "station": "server_lab",
        "name": "Servidor / Terminal",
        "icon": "⚡",
        "min_required": 1,
        "w": 68,
        "h": 54,
        "seat_offset": (0, 40, "up"),
        "collab_offsets": [(-26, 40, "right"), (26, 40, "left")],
    },
    "whiteboard": {
        "type": "whiteboard",
        "station": "strategy_board",
        "name": "Pizarra Estrategia",
        "icon": "💭",
        "min_required": 1,
        "w": 110,
        "h": 46,
        "seat_offset": (0, 38, "up"),
        "collab_offsets": [(-30, 38, "right"), (30, 38, "left")],
    },
    "orchestrator_core": {
        "type": "orchestrator_core",
        "station": "orchestrator_hub",
        "name": "Consola Orchestrator",
        "icon": "🎛️",
        "min_required": 1,
        "w": 78,
        "h": 48,
        "seat_offset": (0, 36, "up"),
        "collab_offsets": [(-28, 36, "right"), (28, 36, "left")],
    },
    "web_radar": {
        "type": "web_radar",
        "station": "web_station",
        "name": "Cabina Web / Radar",
        "icon": "🌐",
        "min_required": 1,
        "w": 68,
        "h": 44,
        "seat_offset": (0, 34, "up"),
        "collab_offsets": [(-26, 34, "right"), (26, 34, "left")],
    },
    "art_easel": {
        "type": "art_easel",
        "station": "art_studio",
        "name": "Mesa Estudio UI",
        "icon": "🎨",
        "min_required": 1,
        "w": 60,
        "h": 44,
        "seat_offset": (0, 34, "up"),
        "collab_offsets": [(-24, 34, "right"), (24, 34, "left")],
    },
    "coffee_sofa": {
        "type": "coffee_sofa",
        "station": "lounge",
        "name": "Sofá / Barra Café",
        "icon": "☕",
        "min_required": 1,
        "w": 88,
        "h": 40,
        "seat_offset": (0, 26, "up"),
        "collab_offsets": [(-28, 26, "right"), (28, 26, "left"), (-16, 44, "up"), (16, 44, "up")],
    },
}

DECORATION_CATALOG: Dict[str, Dict[str, Any]] = {
    "plant_monstera": {"type": "plant_monstera", "name": "Planta Monstera",   "icon": "🪴", "w": 26, "h": 32},
    "plant_cactus":   {"type": "plant_cactus",   "name": "Cactus Pixel",      "icon": "🌵", "w": 22, "h": 28},
    "arcade_machine": {"type": "arcade_machine", "name": "Máquina Arcade",    "icon": "🕹️", "w": 34, "h": 48},
    "water_cooler":   {"type": "water_cooler",   "name": "Dispensador Agua",  "icon": "🚰", "w": 24, "h": 38},
    "coffee_bar":     {"type": "coffee_bar",     "name": "Cafetera Espresso", "icon": "☕", "w": 46, "h": 32},
    "rug_persian":    {"type": "rug_persian",    "name": "Alfombra Roja",     "icon": "🛋️", "w": 84, "h": 48},
    "rug_cyber":      {"type": "rug_cyber",      "name": "Alfombra Cyber",    "icon": "💠", "w": 84, "h": 48},
    "floor_lamp":     {"type": "floor_lamp",     "name": "Lámpara de Pie",    "icon": "💡", "w": 20, "h": 40},
    "trophy":         {"type": "trophy",         "name": "Trofeo MediaHub",   "icon": "🏆", "w": 24, "h": 30},
}


def build_default_office_layout() -> Dict[str, Any]:
    """Construye el diseño de oficina por defecto con habitaciones, pisos, dispositivos y decoración."""
    return {
        "hallway_floor": "marble_slate",
        "show_room_walls": True,
        "room_floors": {
            "library": "walnut_wood",
            "strategy_board": "navy_carpet",
            "orchestrator_hub": "amber_tech",
            "web_station": "cyber_grid",
            "coding_desk": "emerald_tile",
            "server_lab": "metal_grate",
            "art_studio": "studio_purple",
            "lounge": "cafe_warm",
        },
        "devices": [
            # Biblioteca (2 muebles de libros por defecto)
            {"id": "dev-lib-1", "type": "bookshelf", "x": 86,  "y": 82},
            {"id": "dev-lib-2", "type": "bookshelf", "x": 188, "y": 82},
            # Estrategia (1 gran pizarra)
            {"id": "dev-str-1", "type": "whiteboard", "x": 394, "y": 82},
            # Orchestrator (1 consola central)
            {"id": "dev-orc-1", "type": "orchestrator_core", "x": 616, "y": 96},
            # Cabina Web (2 estaciones radar)
            {"id": "dev-web-1", "type": "web_radar", "x": 852, "y": 86},
            {"id": "dev-web-2", "type": "web_radar", "x": 948, "y": 86},
            # Sala de Computadores (4 computadores por defecto; el usuario puede dejar 1, 2 o agregar más)
            {"id": "dev-pc-1",  "type": "computer_desk", "x": 96,  "y": 392},
            {"id": "dev-pc-2",  "type": "computer_desk", "x": 274, "y": 392},
            {"id": "dev-pc-3",  "type": "computer_desk", "x": 96,  "y": 500},
            {"id": "dev-pc-4",  "type": "computer_desk", "x": 274, "y": 500},
            # Terminal Lab (2 racks de servidores/consola)
            {"id": "dev-srv-1", "type": "server_terminal", "x": 442, "y": 405},
            {"id": "dev-srv-2", "type": "server_terminal", "x": 534, "y": 405},
            # Estudio UI (1 mesa creativa)
            {"id": "dev-art-1", "type": "art_easel", "x": 686, "y": 415},
            # Cafetería & Lounge (2 zonas de descanso/sofá)
            {"id": "dev-lng-1", "type": "coffee_sofa", "x": 846, "y": 418},
            {"id": "dev-lng-2", "type": "coffee_sofa", "x": 948, "y": 512},
        ],
        "decorations": [
            {"id": "dec-1", "type": "plant_monstera", "x": 42,  "y": 232},
            {"id": "dec-2", "type": "coffee_bar",     "x": 845, "y": 362},
            {"id": "dec-3", "type": "water_cooler",   "x": 992, "y": 365},
            {"id": "dec-4", "type": "arcade_machine", "x": 992, "y": 438},
            {"id": "dec-5", "type": "plant_cactus",   "x": 342, "y": 364},
            {"id": "dec-6", "type": "trophy",         "x": 736, "y": 364},
        ],
    }


# =============================================================================
# GESTOR CENTRAL DE PERSONALIZACIÓN, POOL DE PERSONAJES Y CONTROL DE DEMANDA
# =============================================================================
class CustomizationManager:
    def __init__(self, storage_path: Optional[str] = None):
        if not storage_path:
            appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            data_dir = os.path.join(appdata, "MediaHub", "Pixelavity")
            os.makedirs(data_dir, exist_ok=True)
            storage_path = os.path.join(data_dir, "customization.json")
        self.storage_path = storage_path
        self.lock = threading.RLock()

        self.characters: List[Dict[str, Any]] = copy.deepcopy(DEFAULT_CHARACTERS)
        self.office: Dict[str, Any] = build_default_office_layout()

        # Asignaciones activas: agent_id -> character_id
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
            if isinstance(raw.get("office"), dict):
                default_off = build_default_office_layout()
                default_off.update(raw["office"])
                self.office = default_off
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
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            print(f"[CustomizationManager] Error guardando configuración: {e}")

    # -------------------------------------------------------------------------
    # GESTIÓN DE PERSONAJES Y ASIGNACIÓN ALEATORIA SIN REPETICIÓN
    # -------------------------------------------------------------------------
    def get_characters(self) -> List[Dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.characters)

    def save_character(self, char_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            cid = char_data.get("id") or f"char-{uuid.uuid4().hex[:8]}"
            char_data["id"] = cid
            replaced = False
            for idx, existing in enumerate(self.characters):
                if existing["id"] == cid:
                    self.characters[idx] = copy.deepcopy(char_data)
                    replaced = True
                    break
            if not replaced:
                self.characters.append(copy.deepcopy(char_data))
            self._save()
            return copy.deepcopy(char_data)

    def delete_character(self, char_id: str) -> Tuple[bool, str]:
        with self.lock:
            if len(self.characters) <= 1:
                return False, "Debe existir al menos 1 personaje en tu colección."
            self.characters = [c for c in self.characters if c["id"] != char_id]
            # Limpiar asignaciones de agentes que usaban este personaje para que tomen otro
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
        """
        Asigna personajes de forma aleatoria a los agentes activos SIN repetir personajes,
        a menos que todos los personajes ya estén en uso y haya más agentes que personajes
        (ej. 5 personajes y 6 agentes -> usa los 5 sin repetir + 1 repetido al azar).
        """
        with self.lock:
            if not self.characters:
                self.characters = copy.deepcopy(DEFAULT_CHARACTERS)

            char_by_id = {c["id"]: c for c in self.characters}
            active_set = set(active_agent_ids)

            # 1. Liberar personajes de agentes que ya no están activos
            for old_aid in list(self.agent_to_character.keys()):
                if old_aid not in active_set or self.agent_to_character[old_aid] not in char_by_id:
                    del self.agent_to_character[old_aid]

            # 2. Contar cuántas veces está siendo usado cada personaje actualmente
            usage_count: Dict[str, int] = {c["id"]: 0 for c in self.characters}
            for aid in active_agent_ids:
                cid = self.agent_to_character.get(aid)
                if cid and cid in usage_count:
                    usage_count[cid] += 1

            # 3. Para cada agente sin personaje asignado, elegir aleatoriamente entre los de menor uso
            #    (Si hay personajes con uso == 0, elige exclusivamente entre los no usados.
            #     Si todos tienen uso >= 1, elige entre los de uso == min_usage).
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
    # GESTIÓN DEL BACKGROUND / OFICINA Y REGLAS MÍNIMAS DE DISPOSITIVOS
    # -------------------------------------------------------------------------
    def get_office_layout(self) -> Dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.office)

    def validate_office_devices(self, devices: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Verifica las reglas mínimas de dispositivos interactivos:
        Debe haber mínimo 1 Computador, mínimo 1 Mueble de Libros, mínimo 1 Terminal,
        mínimo 1 Pizarra, mínimo 1 Consola Orchestrator, mínimo 1 Cabina Web,
        mínimo 1 Mesa UI y mínimo 1 Zona de Descanso/Café.
        """
        counts: Dict[str, int] = {}
        for d in devices:
            dtype = d.get("type", "")
            counts[dtype] = counts.get(dtype, 0) + 1

        for dtype, spec in DEVICE_CATALOG.items():
            min_req = spec.get("min_required", 1)
            if counts.get(dtype, 0) < min_req:
                return (
                    False,
                    f"⚠️ Regla de la oficina: Debe haber como mínimo {min_req} {spec['icon']} {spec['name']} "
                    f"para que los agentes puedan interactuar.",
                )
        return True, "Diseño válido."

    def update_office_layout(self, new_office: Dict[str, Any]) -> Tuple[bool, str]:
        with self.lock:
            devices = new_office.get("devices", self.office.get("devices", []))
            ok, msg = self.validate_office_devices(devices)
            if not ok:
                return False, msg
            self.office.update(copy.deepcopy(new_office))
            self._save()
            return True, "Oficina guardada correctamente."

    def add_device(self, device_type: str, x: int, y: int) -> Tuple[bool, Dict[str, Any]]:
        with self.lock:
            if device_type not in DEVICE_CATALOG:
                return False, {}
            new_dev = {
                "id": f"dev-{uuid.uuid4().hex[:7]}",
                "type": device_type,
                "x": int(x),
                "y": int(y),
            }
            self.office.setdefault("devices", []).append(new_dev)
            self._save()
            return True, copy.deepcopy(new_dev)

    def remove_device(self, device_id: str) -> Tuple[bool, str]:
        with self.lock:
            current_devs = self.office.get("devices", [])
            remaining = [d for d in current_devs if d.get("id") != device_id]
            ok, msg = self.validate_office_devices(remaining)
            if not ok:
                return False, msg
            self.office["devices"] = remaining
            self._save()
            return True, "Dispositivo eliminado."

    def move_item(self, item_id: str, x: int, y: int) -> bool:
        with self.lock:
            for d in self.office.get("devices", []):
                if d.get("id") == item_id:
                    d["x"] = int(max(36, min(1004, x)))
                    d["y"] = int(max(44, min(585, y)))
                    self._save()
                    return True
            for dec in self.office.get("decorations", []):
                if dec.get("id") == item_id:
                    dec["x"] = int(max(24, min(1016, x)))
                    dec["y"] = int(max(30, min(595, y)))
                    self._save()
                    return True
            return False

    def add_decoration(self, dec_type: str, x: int, y: int) -> Tuple[bool, Dict[str, Any]]:
        with self.lock:
            if dec_type not in DECORATION_CATALOG:
                return False, {}
            new_dec = {
                "id": f"dec-{uuid.uuid4().hex[:7]}",
                "type": dec_type,
                "x": int(x),
                "y": int(y),
            }
            self.office.setdefault("decorations", []).append(new_dec)
            self._save()
            return True, copy.deepcopy(new_dec)

    def remove_decoration(self, dec_id: str) -> bool:
        with self.lock:
            before = len(self.office.get("decorations", []))
            self.office["decorations"] = [d for d in self.office.get("decorations", []) if d.get("id") != dec_id]
            self._save()
            return len(self.office["decorations"]) < before

    def set_room_floor(self, room_id: str, material_id: str):
        with self.lock:
            if material_id not in FLOOR_MATERIALS:
                return
            if room_id == "hallway":
                self.office["hallway_floor"] = material_id
            else:
                self.office.setdefault("room_floors", {})[room_id] = material_id
            self._save()

    def set_show_room_walls(self, show_walls: bool):
        with self.lock:
            self.office["show_room_walls"] = bool(show_walls)
            self._save()

    def reset_office_to_default(self):
        with self.lock:
            self.office = build_default_office_layout()
            self._save()

    # -------------------------------------------------------------------------
    # CONTROL DE DEMANDA Y COLABORACIÓN / PAIR-PROGRAMMING EN DISPOSITIVOS
    # -------------------------------------------------------------------------
    def allocate_station_positions(self, agents_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Dado el listado de agentes activos y la estación que cada uno necesita:
        - Si hay suficientes dispositivos de esa estación (ej. 2 computadores y 2 agentes),
          cada agente usa su propio dispositivo (role="primary").
        - Si la demanda supera a los dispositivos disponibles (ej. 2 computadores y 3 agentes),
          1 agente usa un computador y los otros 2 comparten el otro computador:
          uno programa en el asiento principal (role="primary") y el otro se coloca a su lado
          (role="collaborator") mirándolo como si estuviera revisando o discutiendo con él.
        """
        with self.lock:
            devices = self.office.get("devices", [])
            devices_by_station: Dict[str, List[Dict[str, Any]]] = {}
            for dev in devices:
                spec = DEVICE_CATALOG.get(dev.get("type", ""))
                if spec:
                    st = spec["station"]
                    devices_by_station.setdefault(st, []).append(dev)

            # Agrupar agentes por estación destino
            agents_by_station: Dict[str, List[Dict[str, Any]]] = {}
            for ag in agents_list:
                st = ag.get("station", "lounge")
                agents_by_station.setdefault(st, []).append(ag)

            allocations: Dict[str, Dict[str, Any]] = {}

            for st, st_agents in agents_by_station.items():
                st_devices = devices_by_station.get(st, [])
                if not st_devices:
                    # Fallback seguro si no hubiera dispositivo
                    for idx, ag in enumerate(st_agents):
                        allocations[ag["id"]] = {
                            "device_id": None,
                            "x": 850 + (idx % 3) * 45,
                            "y": 450 + (idx // 3) * 55,
                            "face": "down",
                            "role": "primary",
                            "is_collaborating": False,
                            "partner_name": None,
                        }
                    continue

                # Ordenar agentes de forma determinista para que no salten de asiento entre ticks
                st_agents_sorted = sorted(st_agents, key=lambda a: a["id"])
                num_devs = len(st_devices)

                # Mapa de qué agentes quedaron asignados a cada dispositivo: dev_idx -> list of agents
                assigned_per_dev: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(num_devs)}
                for idx, ag in enumerate(st_agents_sorted):
                    # Determinar índice de dispositivo preferido
                    dev_idx = idx % num_devs
                    assigned_per_dev[dev_idx].append(ag)

                for dev_idx, dev_agents in assigned_per_dev.items():
                    dev = st_devices[dev_idx]
                    spec = DEVICE_CATALOG[dev["type"]]
                    dx, dy = dev["x"], dev["y"]
                    sox, soy, sface = spec["seat_offset"]
                    collab_offsets = spec["collab_offsets"]

                    has_collaborators = len(dev_agents) > 1
                    primary_agent = dev_agents[0] if dev_agents else None

                    for rank, ag in enumerate(dev_agents):
                        if rank == 0:
                            # Agente principal frente al computador / dispositivo
                            partner_names = [a.get("name", a["id"][:6]) for a in dev_agents[1:]]
                            allocations[ag["id"]] = {
                                "device_id": dev["id"],
                                "x": dx + sox,
                                "y": dy + soy,
                                "face": sface,
                                "role": "primary",
                                "is_collaborating": has_collaborators,
                                "partner_name": ", ".join(partner_names) if partner_names else None,
                            }
                        else:
                            # Agente colaborador al lado del compañero revisando / discutiendo
                            coff_x, coff_y, coff_face = collab_offsets[(rank - 1) % len(collab_offsets)]
                            allocations[ag["id"]] = {
                                "device_id": dev["id"],
                                "x": dx + coff_x,
                                "y": dy + coff_y,
                                "face": coff_face,
                                "role": "collaborator",
                                "is_collaborating": True,
                                "partner_name": primary_agent.get("name", primary_agent["id"][:6]) if primary_agent else None,
                            }

            return allocations
