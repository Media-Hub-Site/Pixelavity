# -*- coding: utf-8 -*-
"""
PixelAgents - Real-Time Antigravity Brain & Transcript Watcher
Monitorea en tiempo real ~/.gemini/antigravity/brain/<conv-id>/.system_generated/logs/transcript.jsonl
Detecta:
  - Múltiples chats abiertos simultáneamente (cada chat es un Agente Principal con su modelo)
  - Uso de Orchestrator / Subagentes (invoke_subagent, swarm, run_workflow, send_message)
  - Acciones específicas mapeadas a zonas de la oficina Pixel Art:
      * library          (Biblioteca: buscar librerías, leer archivos, grep, docs)
      * coding_desk      (Computador: programar, crear/editar código)
      * server_lab       (Laboratorio Terminal: ejecutar comandos, consola, tareas)
      * web_station      (Cabina Web: buscar en internet, browser agent, APIs)
      * orchestrator_hub (Mesa de Comando: invocar subagentes, swarm, workflows)
      * art_studio       (Estudio Creativo: UI, CSS, generación de imágenes)
      * strategy_board   (Pizarra: pensando, planificando pasos, analizando prompt)
      * lounge           (Cafetería / Sofá: en espera de usuario, tarea completada)
"""

import os
import re
import json
import time
import glob
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any


# Nombres amigables para los modelos de Gemini / Antigravity
MODEL_DISPLAY_NAMES = {
    "gemini-4-argon-high": "Gemini 4 Argon (High)",
    "gemini-4-argon": "Gemini 4 Argon",
    "gemini-4-neon-high": "Gemini 4 Neon (High)",
    "gemini-4-neon": "Gemini 4 Neon",
    "gemini-4-hydrogen-xhigh": "Gemini 4 Hydrogen (XHigh)",
    "gemini-4-hydrogen-high": "Gemini 4 Hydrogen (High)",
    "gemini-3.8-flash-high": "Gemini 3.8 Flash (High)",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "flash": "Gemini Flash",
    "flash_lite": "Gemini Flash Lite",
    "pro": "Gemini Pro",
    "inherit": "Gemini Sub-Agent",
}


def format_model_display_name(raw_name: str) -> str:
    if not raw_name:
        return "Gemini"
    if raw_name in MODEL_DISPLAY_NAMES:
        return MODEL_DISPLAY_NAMES[raw_name]
    # Formatear automáticamente slugs como "gemini-4-neon-high" -> "Gemini 4 Neon (High)"
    parts = raw_name.replace("_", "-").split("-")
    if len(parts) >= 2 and parts[0].lower() == "gemini":
        if parts[-1].lower() in ("high", "xhigh", "low", "lite"):
            tier = parts[-1].upper() if parts[-1].lower() == "xhigh" else parts[-1].capitalize()
            base = " ".join(p.capitalize() for p in parts[:-1])
            return f"{base} ({tier})"
        return " ".join(p.capitalize() for p in parts)
    return raw_name

# Paletas de personajes (sprites) asignadas de forma determinista por ID
AGENT_PALETTES = [
    {"id": "cyan_coder", "name": "Neo-Cyan", "suit": "#00e5ff", "hair": "#1a237e", "accent": "#80d8ff", "hat": "headphones"},
    {"id": "amber_architect", "name": "Amber-Lead", "suit": "#ffb300", "hair": "#3e2723", "accent": "#ffe57f", "hat": "visor"},
    {"id": "emerald_hacker", "name": "Emerald-Dev", "suit": "#00e676", "hair": "#1b5e20", "accent": "#b9f6ca", "hat": "cap"},
    {"id": "violet_scholar", "name": "Violet-Sage", "suit": "#d500f9", "hair": "#311b92", "accent": "#ea80fc", "hat": "glasses"},
    {"id": "crimson_ops", "name": "Crimson-Ops", "suit": "#ff1744", "hair": "#212121", "accent": "#ff8a80", "hat": "helmet"},
    {"id": "royalblue_pilot", "name": "Astra-Blue", "suit": "#2979ff", "hair": "#eceff1", "accent": "#82b1ff", "hat": "antenna"},
    {"id": "coral_artist", "name": "Coral-UX", "suit": "#ff6d00", "hair": "#4a148c", "accent": "#ffd180", "hat": "beret"},
    {"id": "mint_researcher", "name": "Mint-Scout", "suit": "#1de9b6", "hair": "#263238", "accent": "#a7ffeb", "hat": "goggles"},
]


def clean_arg_string(val: Any) -> str:
    """Limpia comillas escapadas de los argumentos JSON de transcript.jsonl."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        s = s[1:-1]
    s = s.replace('\\"', '"').replace('\\\\', '\\')
    return s


def extract_user_prompt_title(raw_content: str) -> str:
    """Extrae el texto limpio de <USER_REQUEST>...</USER_REQUEST>."""
    if not raw_content:
        return "Sesión Antigravity"
    m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw_content, re.DOTALL)
    text = m.group(1).strip() if m else raw_content.strip()
    # Tomar la primera línea significativa
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first = lines[0] if lines else "Consulta de usuario"
    return first[:55] + ("..." if len(first) > 55 else "")


def classify_tool_to_station(tool_name: str, args: Dict[str, Any]) -> Dict[str, str]:
    """
    Traduce una llamada de herramienta de Antigravity en una estación física
    dentro del mundo Pixel Art, junto con su etiqueta de acción y detalle.
    """
    t = (tool_name or "").lower()

    # 1. BIBLIOTECA (Búsqueda de librerías, lectura de archivos, documentación, grep)
    if t in ("read_file", "view_file_outline", "view_code_item", "list_dir", "find_by_name", "grep_search", "search_marketplace"):
        path_arg = clean_arg_string(args.get("Path") or args.get("DirectoryPath") or args.get("SearchPath") or "")
        query_arg = clean_arg_string(args.get("Query") or args.get("Pattern") or args.get("queries") or "")
        basename = os.path.basename(path_arg.replace("\\", "/")) if path_arg else ""

        if t == "search_marketplace":
            detail = f"Buscando plugins/librerías: {query_arg[:28]}" if query_arg else "Explorando catálogo de librerías"
            badge = "📚 Buscando Librerías"
        elif t in ("grep_search", "find_by_name"):
            detail = f"Investigando: {query_arg[:26] or basename or 'archivos'}"
            badge = "🔍 Investigando en Biblioteca"
        else:
            detail = f"Leyendo: {basename or 'documentación'}"
            badge = f"📖 Leyendo {basename[:18]}" if basename else "📖 Consultando Archivos"

        return {
            "station": "library",
            "activity": "reading",
            "badge": badge,
            "detail": detail,
            "icon": "📚",
        }

    # 2. ESTACIÓN DE PROGRAMACIÓN / COMPUTADOR (Escribir y editar código)
    if t in ("write_file", "edit_file", "replace_file_content", "multi_replace_file_content"):
        path_arg = clean_arg_string(args.get("Path") or args.get("TargetFile") or "")
        basename = os.path.basename(path_arg.replace("\\", "/")) if path_arg else "código"
        ext = os.path.splitext(basename)[1].lower()

        # Si es arte/UI puro y queremos variedad, o computador de programación:
        return {
            "station": "coding_desk",
            "activity": "coding",
            "badge": f"💻 Programando {basename[:18]}",
            "detail": f"Escribiendo código en {basename}",
            "icon": "💻",
        }

    # 3. LABORATORIO DE SERVIDORES / TERMINAL (Comandos, tests, paquetes)
    if t in ("run_command", "manage_task", "send_command_input", "schedule"):
        summary = clean_arg_string(args.get("toolSummary") or "")
        cmd = clean_arg_string(args.get("CommandLine") or "")
        cmd_lower = cmd.lower()

        # Si el comando en terminal está instalando o buscando librerías (pip, npm, cargo, etc.),
        # podemos mostrar el detalle claro o mandarlo a Biblioteca si es búsqueda de paquetes
        if any(k in cmd_lower for k in ("pip search", "npm search", "pip index", "import ")):
            return {
                "station": "library",
                "activity": "reading",
                "badge": f"📚 Librerías: {(summary or cmd)[:20]}",
                "detail": summary or cmd[:42],
                "icon": "📚",
            }

        label = summary or (cmd[:24] + "..." if len(cmd) > 24 else cmd) or "Ejecutando terminal"
        return {
            "station": "server_lab",
            "activity": "terminal",
            "badge": f"⚡ Terminal: {label[:22]}",
            "detail": f"Consola: {cmd[:48] or label}",
            "icon": "⚡",
        }

    # 4. CABINA WEB / RADAR (Web search, browser, red)
    if t in ("search_web", "read_url_content", "open_browser_url", "list_plugin_accounts"):
        q = clean_arg_string(args.get("query") or args.get("Url") or "Web")
        return {
            "station": "web_station",
            "activity": "browsing",
            "badge": f"🌐 Web: {q[:20]}",
            "detail": f"Consultando en la red: {q[:40]}",
            "icon": "🌐",
        }

    # 5. MESA DE COMANDO ORCHESTRATOR (Subagentes, Swarm, Workflows)
    if t in ("invoke_subagent", "manage_subagents", "send_message", "define_subagent", "swarm", "run_workflow"):
        role = clean_arg_string(args.get("Role") or args.get("name") or args.get("TypeName") or "Subagente")
        return {
            "station": "orchestrator_hub",
            "activity": "orchestrating",
            "badge": f"🎛️ Orchestrator: {role[:18]}",
            "detail": f"Coordinando agente: {role}",
            "icon": "🎛️",
        }

    # 6. ESTUDIO CREATIVO (Imágenes, diseño)
    if "image" in t or "canvas" in t or "ui" in t:
        return {
            "station": "art_studio",
            "activity": "designing",
            "badge": "🎨 Diseñando Arte/UI",
            "detail": f"Herramienta creativa: {tool_name}",
            "icon": "🎨",
        }

    # 7. PIZARRA DE ESTRATEGIA (Planificación, pasos, foco)
    if t in ("update_steps", "update_focus", "ask_question"):
        focus_txt = clean_arg_string(args.get("focus") or "Actualizando plan de trabajo")
        return {
            "station": "strategy_board",
            "activity": "planning",
            "badge": f"📋 Plan: {focus_txt[:20]}",
            "detail": focus_txt,
            "icon": "📋",
        }

    # Por defecto: Computador
    return {
        "station": "coding_desk",
        "activity": "coding",
        "badge": f"🔧 {tool_name[:20]}",
        "detail": f"Ejecutando {tool_name}",
        "icon": "🔧",
    }


def default_station_for_subagent_type(sub_type: str) -> str:
    """Estación preferida inicial según el tipo de subagente de Antigravity."""
    st = (sub_type or "").lower()
    if st == "research":
        return "library"
    if st == "browser":
        return "web_station"
    if st == "image-generator":
        return "art_studio"
    return "coding_desk"


class AntigravityBrainWatcher:
    """
    Observador en tiempo real del directorio brain de Antigravity.
    Mantiene el estado de todos los agentes (chats principales y subagentes de orchestrator)
    y un buffer circular de eventos para animar el desplazamiento paso a paso en el frontend.
    """

    def __init__(self, brain_dir: Optional[str] = None):
        if not brain_dir:
            brain_dir = os.environ.get(
                "ANTIGRAVITY_BRAIN_DIR",
                os.path.expanduser("~/.gemini/antigravity/brain"),
            )
        self.brain_dir = os.path.abspath(brain_dir)
        self.lock = threading.RLock()

        # Mapa de agentes activos/conocidos: agent_id -> dict
        self.agents: Dict[str, Dict[str, Any]] = {}
        # Estado de lectura incremental por archivo transcript.jsonl
        self.file_cursors: Dict[str, int] = {}
        self.file_mtimes: Dict[str, float] = {}

        # Relaciones Padre (Orchestrator) -> Hijos (Subagentes)
        # Guardamos subagentes pendientes cuando invoke_subagent ocurre antes de leer el GENERIC response
        self.pending_subagent_meta: Dict[str, List[Dict[str, str]]] = {}
        self.parent_by_child: Dict[str, str] = {}
        self.subagent_meta_by_id: Dict[str, Dict[str, str]] = {}

        # Agentes de simulación / demo creados por el usuario en la interfaz
        self.simulated_agents: Dict[str, Dict[str, Any]] = {}

        # Cola global de eventos con ID incremental para el motor de animación
        self.event_seq: int = 1
        self.events: List[Dict[str, Any]] = []
        self.max_events: int = 250

        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia el hilo de monitoreo continuo."""
        if self._running:
            return
        self._running = True
        # Escaneo inicial
        self.scan_once(initial=True)
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name="BrainWatcher")
        self._thread.start()

    def stop(self):
        self._running = False

    def _watch_loop(self):
        while self._running:
            try:
                self.scan_once(initial=False)
                self._tick_simulated_agents()
            except Exception as e:
                print(f"[BrainWatcher] Error en ciclo: {e}")
            time.sleep(0.75)

    def _palette_for_id(self, agent_id: str, index_hint: int = 0) -> Dict[str, str]:
        h = sum(ord(c) for c in agent_id) + index_hint
        return AGENT_PALETTES[h % len(AGENT_PALETTES)]

    def _emit_event(self, agent_id: str, station: str, activity: str, badge: str, detail: str, icon: str = "✨"):
        """Registra un evento de movimiento/acción para que el cliente anime la caminata."""
        ev = {
            "id": self.event_seq,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "agent_id": agent_id,
            "agent_name": self.agents.get(agent_id, {}).get("name")
                          or self.simulated_agents.get(agent_id, {}).get("name")
                          or agent_id[:8],
            "station": station,
            "activity": activity,
            "badge": badge,
            "detail": detail,
            "icon": icon,
        }
        self.event_seq += 1
        self.events.append(ev)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def scan_once(self, initial: bool = False):
        """Escanea las carpetas de conversación en brain/ y procesa nuevas líneas JSONL."""
        if not os.path.isdir(self.brain_dir):
            return

        now = time.time()
        candidates = []

        try:
            with os.scandir(self.brain_dir) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    conv_id = entry.name
                    transcript_path = os.path.join(
                        entry.path, ".system_generated", "logs", "transcript.jsonl"
                    )
                    if not os.path.isfile(transcript_path):
                        continue
                    try:
                        mtime = os.path.getmtime(transcript_path)
                    except OSError:
                        continue
                    candidates.append((mtime, conv_id, transcript_path))
        except OSError:
            return

        # Ordenar por más reciente primero
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Monitoreamos hasta las 8 conversaciones más recientes (o cualquiera modificada en las últimas 6 horas)
        selected = []
        for idx, (mtime, conv_id, tpath) in enumerate(candidates):
            age_hours = (now - mtime) / 3600.0
            if idx < 6 or age_hours <= 6.0 or conv_id in self.agents or conv_id in self.parent_by_child:
                selected.append((mtime, conv_id, tpath))

        # Procesar en orden cronológico para que los padres registren subagentes antes de leer al hijo
        selected.sort(key=lambda x: x[0])

        with self.lock:
            for mtime, conv_id, tpath in selected:
                prev_mtime = self.file_mtimes.get(conv_id, 0)
                if mtime > prev_mtime or conv_id not in self.file_cursors:
                    self._process_transcript_file(conv_id, tpath, mtime, initial=initial)
                    self.file_mtimes[conv_id] = mtime

            # Verificar tiempos de inactividad: si un agente lleva > 45s sin nuevos pasos y su último paso fue DONE
            for conv_id, ag in list(self.agents.items()):
                idle_secs = now - ag.get("last_updated", now)
                ag["idle_seconds"] = int(idle_secs)
                ag["is_live"] = idle_secs < 900  # Activo en los últimos 15 minutos

                # Si terminó su turno (waiting_user) y ya pasó tiempo, su estación de reposo es lounge
                if ag.get("turn_complete", False) and ag.get("station") != "lounge" and idle_secs > 12:
                    ag["station"] = "lounge"
                    ag["activity"] = "idle"
                    ag["badge"] = "☕ En descanso (Listo)"
                    ag["detail"] = "Esperando siguiente consulta del usuario"
                    if not initial:
                        self._emit_event(
                            conv_id, "lounge", "idle",
                            "☕ Descansando en Cafetería",
                            "Turno completado, esperando nuevo prompt", "☕"
                        )

    def _ensure_agent_entry(self, conv_id: str, mtime: float) -> Dict[str, Any]:
        if conv_id not in self.agents:
            idx = len(self.agents)
            palette = self._palette_for_id(conv_id, idx)
            parent_id = self.parent_by_child.get(conv_id)
            sub_meta = self.subagent_meta_by_id.get(conv_id, {})

            is_sub = bool(parent_id or sub_meta)
            role_title = sub_meta.get("role") or (f"Sub-Agente #{idx + 1}" if is_sub else f"Chat #{idx + 1}")
            sub_type = sub_meta.get("type_name", "self" if is_sub else "main")

            self.agents[conv_id] = {
                "id": conv_id,
                "short_id": conv_id[:8],
                "name": role_title,
                "chat_title": "Sesión Antigravity",
                "model": sub_meta.get("model", "Gemini"),
                "model_raw": sub_meta.get("model", "gemini"),
                "is_subagent": is_sub,
                "subagent_type": sub_type,
                "parent_id": parent_id,
                "children_ids": [],
                "palette": palette,
                "station": default_station_for_subagent_type(sub_type) if is_sub else "lounge",
                "activity": "idle",
                "badge": "☕ En espera",
                "detail": "Sesión iniciada",
                "icon": "🤖",
                "step_count": 0,
                "tool_History": [],
                "turn_complete": True,
                "last_updated": mtime,
                "idle_seconds": int(max(0, time.time() - mtime)),
                "is_live": (time.time() - mtime) < 900,
                "is_simulated": False,
            }
            if parent_id and parent_id in self.agents:
                if conv_id not in self.agents[parent_id]["children_ids"]:
                    self.agents[parent_id]["children_ids"].append(conv_id)

        return self.agents[conv_id]

    def _process_transcript_file(self, conv_id: str, tpath: str, mtime: float, initial: bool = False):
        ag = self._ensure_agent_entry(conv_id, mtime)
        cursor = self.file_cursors.get(conv_id, 0)

        try:
            with open(tpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            return

        if cursor >= len(lines):
            return

        new_lines = lines[cursor:]
        self.file_cursors[conv_id] = len(lines)

        # Si es la carga inicial y el archivo tiene muchas líneas, igual procesamos todas para reconstruir
        # metadatos (modelo, título, subagentes), pero solo emitimos eventos de animación para las últimas 4 líneas
        emit_threshold = max(0, len(new_lines) - 4) if initial else 0

        for idx, raw_line in enumerate(new_lines):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                step = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            should_emit = (idx >= emit_threshold) and (not initial or (time.time() - mtime) < 900)
            self._apply_step_to_agent(ag, step, mtime, should_emit=should_emit)

    def _apply_step_to_agent(self, ag: Dict[str, Any], step: Dict[str, Any], mtime: float, should_emit: bool):
        conv_id = ag["id"]
        step_type = step.get("type", "")
        source = step.get("source", "")
        content = step.get("content", "") or ""
        model_raw = step.get("model")

        ag["step_count"] = max(ag["step_count"], int(step.get("step_index", 0)) + 1)
        ag["last_updated"] = mtime if mtime else time.time()

        # Actualizar modelo si viene en el step
        if model_raw:
            ag["model_raw"] = model_raw
            ag["model"] = format_model_display_name(model_raw)
            # Si es un agente principal sin nombre personalizado, usar el nombre del modelo + ID corto
            if not ag["is_subagent"]:
                short_model = (
                    ag["model"]
                    .replace("Gemini ", "G")
                    .replace(" (High)", "+")
                    .replace(" (XHigh)", "++")
                )
                ag["name"] = f"{short_model} [{ag['short_id'][:4]}]"

        # Detectar cambio de modelo en USER_INPUT (<USER_SETTINGS_CHANGE>)
        if "<USER_SETTINGS_CHANGE>" in content:
            m_mod = re.search(r"Model Selection` from .*? to ([^.\n]+)", content)
            if m_mod:
                human_model = m_mod.group(1).strip()
                ag["model"] = human_model
                if not ag["is_subagent"]:
                    short_model = human_model.replace("Gemini ", "G").replace(" (High)", "+")
                    ag["name"] = f"{short_model} [{ag['short_id'][:4]}]"

        # 1. Detectar si este transcript pertenece a un SUBAGENTE (step 0 SYSTEM_MESSAGE con sender=<uuid>)
        if step.get("step_index") == 0 and source == "SYSTEM" and "sender=" in content:
            m_sender = re.search(r"sender=([0-9a-fA-F-]{36})", content)
            if m_sender:
                parent_id = m_sender.group(1)
                ag["is_subagent"] = True
                ag["parent_id"] = parent_id
                self.parent_by_child[conv_id] = parent_id
                if parent_id in self.agents:
                    if conv_id not in self.agents[parent_id]["children_ids"]:
                        self.agents[parent_id]["children_ids"].append(conv_id)

                # Extraer tarea del subagente
                m_body = re.search(r"content=(.*?)</SYSTEM_MESSAGE>", content, re.DOTALL)
                if m_body:
                    task_line = m_body.group(1).strip().splitlines()[0][:55]
                    ag["chat_title"] = task_line

        # 2. Paso de entrada de usuario (USER_INPUT) -> El agente despierta y va a la Pizarra a pensar
        if step_type == "USER_INPUT":
            prompt_title = extract_user_prompt_title(content)
            if prompt_title:
                ag["chat_title"] = prompt_title
            ag["turn_complete"] = False
            ag["station"] = "strategy_board"
            ag["activity"] = "thinking"
            ag["badge"] = "💭 Analizando consulta..."
            ag["detail"] = f"Prompt: {prompt_title}"
            ag["icon"] = "💭"
            if should_emit:
                self._emit_event(
                    conv_id, "strategy_board", "thinking",
                    "💭 Analizando Prompt",
                    f"Nueva consulta: {prompt_title}", "💭"
                )
            return

        # 3. Respuesta del Planificador / Modelo (PLANNER_RESPONSE)
        if step_type == "PLANNER_RESPONSE":
            tool_calls = step.get("tool_calls") or []
            thinking = step.get("thinking") or ""

            # Si tiene pensamiento y herramientas, primero pasa por estrategia o directo a las herramientas
            if tool_calls:
                ag["turn_complete"] = False
                for tc in tool_calls:
                    t_name = tc.get("name", "")
                    t_args = tc.get("args") or {}

                    # Si invoca un subagente (Orchestrator!)
                    if t_name == "invoke_subagent":
                        role = clean_arg_string(t_args.get("Role") or "Subagente")
                        type_name = clean_arg_string(t_args.get("TypeName") or "research")
                        sub_model = clean_arg_string(t_args.get("Model") or "inherit")
                        self.pending_subagent_meta.setdefault(conv_id, []).append({
                            "role": role,
                            "type_name": type_name,
                            "model": MODEL_DISPLAY_NAMES.get(sub_model, sub_model),
                        })

                    mapped = classify_tool_to_station(t_name, t_args)
                    ag["station"] = mapped["station"]
                    ag["activity"] = mapped["activity"]
                    ag["badge"] = mapped["badge"]
                    ag["detail"] = mapped["detail"]
                    ag["icon"] = mapped["icon"]

                    # Guardar historial reciente de herramientas del agente
                    ag["tool_History"].append({
                        "tool": t_name,
                        "badge": mapped["badge"],
                        "station": mapped["station"],
                        "time": time.strftime("%H:%M:%S"),
                    })
                    if len(ag["tool_History"]) > 8:
                        ag["tool_History"] = ag["tool_History"][-8:]

                    if should_emit:
                        self._emit_event(
                            conv_id,
                            mapped["station"],
                            mapped["activity"],
                            mapped["badge"],
                            mapped["detail"],
                            mapped["icon"],
                        )
            else:
                # Respuesta final al usuario sin más herramientas -> Turno completado
                ag["turn_complete"] = True
                if thinking and should_emit:
                    self._emit_event(
                        conv_id, "strategy_board", "thinking",
                        "💡 Preparando respuesta",
                        "Sintetizando respuesta final", "💡"
                    )
                ag["station"] = "lounge"
                ag["activity"] = "idle"
                ag["badge"] = "✅ Respuesta entregada"
                ag["detail"] = "Esperando siguiente mensaje en el chat"
                ag["icon"] = "✅"
                if should_emit:
                    self._emit_event(
                        conv_id, "lounge", "idle",
                        "✅ Respuesta Lista",
                        "Descansando en la cafetería", "☕"
                    )
            return

        # 4. Resultado de herramienta (GENERIC) -> Detectar creación de subagentes por conversationId
        if step_type == "GENERIC" and "Created the following subagent:" in content:
            m_sub = re.search(r'"conversationId"\s*:\s*"([0-9a-fA-F-]{36})"', content)
            if m_sub:
                sub_id = m_sub.group(1)
                self.parent_by_child[sub_id] = conv_id
                if sub_id not in ag["children_ids"]:
                    ag["children_ids"].append(sub_id)

                pending_list = self.pending_subagent_meta.get(conv_id, [])
                meta = pending_list.pop(0) if pending_list else {
                    "role": f"Subagente {sub_id[:4]}",
                    "type_name": "research",
                    "model": ag["model"],
                }
                self.subagent_meta_by_id[sub_id] = meta

                # Si el subagente ya había sido creado en self.agents, actualizar sus datos
                if sub_id in self.agents:
                    sub_ag = self.agents[sub_id]
                    sub_ag["is_subagent"] = True
                    sub_ag["parent_id"] = conv_id
                    sub_ag["name"] = meta["role"]
                    sub_ag["subagent_type"] = meta["type_name"]
                    sub_ag["model"] = meta["model"]

    # =========================================================================
    # MODO SIMULACIÓN INTERACTIVA / DEMO (Para probar Orchestrator, Biblioteca, etc.)
    # =========================================================================
    def trigger_simulation(self, action_type: str) -> Dict[str, Any]:
        """
        Permite al usuario disparar situaciones en vivo desde la interfaz gráfica
        (ej. "Nuevo Chat", "Desplegar Orchestrator", "Buscar Librerías", "Programar", "Terminal")
        para ver cómo caminan e interactúan los agentes en cualquier momento.
        """
        with self.lock:
            now = time.time()

            if action_type == "clear_sim":
                self.simulated_agents.clear()
                self._emit_event("system", "lounge", "idle", "🧹 Simulación reiniciada", "Mostrando solo agentes reales de Antigravity", "🧹")
                return {"ok": True, "message": "Agentes simulados eliminados"}

            if action_type == "spawn_chat":
                sim_idx = len([a for a in self.simulated_agents.values() if not a["is_subagent"]]) + 1
                sim_id = f"sim-chat-{int(now * 1000) % 100000}"
                models = ["Gemini 4 Argon (High)", "Gemini 3.8 Flash (High)", "Gemini 2.5 Pro"]
                chosen_model = models[(sim_idx - 1) % len(models)]
                palette = self._palette_for_id(sim_id, sim_idx + 2)

                tasks = [
                    ("library", "reading", "📚 Buscando Librerías Python", "Explorando documentación de FastAPI y Pygame", "📚"),
                    ("coding_desk", "coding", "💻 Programando app.py", "Implementando arquitectura modular en MediaHub", "💻"),
                    ("server_lab", "terminal", "⚡ Ejecutando pytest", "Verificando suite de pruebas unitarias", "⚡"),
                    ("web_station", "browsing", "🌐 Consultando API Docs", "Buscando referencias técnicas en la web", "🌐"),
                ]
                st, act, badge, detail, icon = tasks[(sim_idx - 1) % len(tasks)]

                self.simulated_agents[sim_id] = {
                    "id": sim_id,
                    "short_id": f"CHAT-{sim_idx}",
                    "name": f"Chat #{sim_idx} ({chosen_model.split()[1]})",
                    "chat_title": f"Consulta simultánea #{sim_idx}: {detail}",
                    "model": chosen_model,
                    "model_raw": chosen_model.lower(),
                    "is_subagent": False,
                    "subagent_type": "main",
                    "parent_id": None,
                    "children_ids": [],
                    "palette": palette,
                    "station": st,
                    "activity": act,
                    "badge": badge,
                    "detail": detail,
                    "icon": icon,
                    "step_count": 3,
                    "tool_History": [{"tool": act, "badge": badge, "station": st, "time": time.strftime("%H:%M:%S")}],
                    "turn_complete": False,
                    "last_updated": now,
                    "idle_seconds": 0,
                    "is_live": True,
                    "is_simulated": True,
                    "sim_cycle_step": sim_idx,
                }
                self._emit_event(sim_id, st, act, badge, detail, icon)
                return {"ok": True, "agent_id": sim_id}

            if action_type == "spawn_orchestrator":
                # Buscar un agente principal o crear un Orchestrator Lead
                orch_id = "sim-orchestrator-lead"
                if orch_id not in self.simulated_agents:
                    self.simulated_agents[orch_id] = {
                        "id": orch_id,
                        "short_id": "ORCH-01",
                        "name": "Orchestrator Prime",
                        "chat_title": "Orquestación Multi-Agente Full-Stack",
                        "model": "Gemini 4 Argon (High)",
                        "model_raw": "gemini-4-argon-high",
                        "is_subagent": False,
                        "subagent_type": "main",
                        "parent_id": None,
                        "children_ids": [],
                        "palette": AGENT_PALETTES[1],  # Amber Lead
                        "station": "orchestrator_hub",
                        "activity": "orchestrating",
                        "badge": "🎛️ Dirigiendo 3 Subagentes",
                        "detail": "Coordinando equipo: Biblioteca, Código y Web",
                        "icon": "🎛️",
                        "step_count": 12,
                        "tool_History": [],
                        "turn_complete": False,
                        "last_updated": now,
                        "idle_seconds": 0,
                        "is_live": True,
                        "is_simulated": True,
                        "sim_cycle_step": 0,
                    }
                else:
                    self.simulated_agents[orch_id]["station"] = "orchestrator_hub"
                    self.simulated_agents[orch_id]["activity"] = "orchestrating"
                    self.simulated_agents[orch_id]["badge"] = "🎛️ Dirigiendo Subagentes"
                    self.simulated_agents[orch_id]["last_updated"] = now

                self._emit_event(
                    orch_id, "orchestrator_hub", "orchestrating",
                    "🎛️ Orchestrator Activo",
                    "Desplegando escuadrón de subagentes especializados", "🎛️"
                )

                # Crear 3 subagentes especializados que salen a distintas estaciones
                squad = [
                    ("sub-lib", "Research Agent", "research", "Gemini 3.8 Flash", "library", "reading", "📚 Buscando Librerías", "Investigando paquetes en la Biblioteca", "📚", 7),
                    ("sub-code", "Code Builder", "self", "Gemini 4 Argon", "coding_desk", "coding", "💻 Programando Módulo", "Escribiendo componentes en Computador #2", "💻", 2),
                    ("sub-web", "Browser Scout", "browser", "Gemini 3.8 Flash", "web_station", "browsing", "🌐 Verificando UI Web", "Inspeccionando DOM en Cabina Web", "🌐", 5),
                ]
                for s_key, s_name, s_type, s_model, s_st, s_act, s_badge, s_det, s_icon, pal_idx in squad:
                    if s_key not in self.simulated_agents[orch_id]["children_ids"]:
                        self.simulated_agents[orch_id]["children_ids"].append(s_key)
                    self.simulated_agents[s_key] = {
                        "id": s_key,
                        "short_id": s_key.upper(),
                        "name": s_name,
                        "chat_title": f"Subagente de Orchestrator: {s_det}",
                        "model": s_model,
                        "model_raw": s_model.lower(),
                        "is_subagent": True,
                        "subagent_type": s_type,
                        "parent_id": orch_id,
                        "children_ids": [],
                        "palette": AGENT_PALETTES[pal_idx % len(AGENT_PALETTES)],
                        "station": s_st,
                        "activity": s_act,
                        "badge": s_badge,
                        "detail": s_det,
                        "icon": s_icon,
                        "step_count": 5,
                        "tool_History": [{"tool": s_type, "badge": s_badge, "station": s_st, "time": time.strftime("%H:%M:%S")}],
                        "turn_complete": False,
                        "last_updated": now,
                        "idle_seconds": 0,
                        "is_live": True,
                        "is_simulated": True,
                        "sim_cycle_step": pal_idx,
                    }
                    self._emit_event(s_key, s_st, s_act, s_badge, s_det, s_icon)

                return {"ok": True, "orchestrator_id": orch_id}

            # Enviar a todos los agentes activos o al agente principal a una estación específica para demostración
            station_demos = {
                "go_library": ("library", "reading", "📚 Buscando Librerías", "Consultando estantería de paquetes y docs", "📚"),
                "go_coding": ("coding_desk", "coding", "💻 Programando en PC", "Escribiendo código fuente a máxima velocidad", "💻"),
                "go_terminal": ("server_lab", "terminal", "⚡ Ejecutando Terminal", "Corriendo scripts y compilación en servidores", "⚡"),
                "go_strategy": ("strategy_board", "thinking", "💭 Planificando Arquitectura", "Diseñando diagrama de pasos en la pizarra", "💭"),
                "go_art": ("art_studio", "designing", "🎨 Creando Pixel Art & UI", "Diseñando sprites e interfaz gráfica", "🎨"),
                "go_lounge": ("lounge", "idle", "☕ Tomando Café", "Descansando en el sofá tras completar tarea", "☕"),
            }
            if action_type in station_demos:
                st, act, badge, detail, icon = station_demos[action_type]
                # Aplicar al agente más reciente (o crear uno si no hay)
                target = None
                if self.simulated_agents:
                    target = list(self.simulated_agents.values())[-1]
                elif self.agents:
                    # Ordenar por last_updated
                    most_recent = sorted(self.agents.values(), key=lambda x: x["last_updated"], reverse=True)[0]
                    target = most_recent

                if target:
                    target["station"] = st
                    target["activity"] = act
                    target["badge"] = badge
                    target["detail"] = detail
                    target["icon"] = icon
                    target["last_updated"] = now
                    target["turn_complete"] = (st == "lounge")
                    self._emit_event(target["id"], st, act, badge, detail, icon)
                return {"ok": True}

            return {"ok": False, "message": f"Acción desconocida: {action_type}"}

    def _tick_simulated_agents(self):
        """Hace que los agentes simulados cambien autónomamente de estación cada ~9 segundos para dar vida."""
        with self.lock:
            if not self.simulated_agents:
                return
            now = time.time()
            cycle_stations = [
                ("library", "reading", "📚 Consultando Librerías", "Revisando documentación técnica en la biblioteca", "📚"),
                ("strategy_board", "thinking", "💭 Analizando Solución", "Evaluando estructura en la pizarra táctica", "💭"),
                ("coding_desk", "coding", "💻 Programando Módulo", "Implementando lógica en la estación de trabajo", "💻"),
                ("server_lab", "terminal", "⚡ Ejecutando Tests", "Validando build en el rack de servidores", "⚡"),
                ("web_station", "browsing", "🌐 Verificando Endpoint", "Probando respuesta en la cabina web", "🌐"),
                ("art_studio", "designing", "🎨 Ajustando Interfaz", "Puliendo detalles visuales en el estudio", "🎨"),
                ("lounge", "idle", "☕ Pausa de Café", "Recargando energía en la cafetería", "☕"),
            ]
            for sim_id, ag in self.simulated_agents.items():
                # Si es el Orchestrator Prime y tiene hijos activos, permanece en orchestrator_hub o alterna con strategy_board
                if sim_id == "sim-orchestrator-lead":
                    continue
                if now - ag.get("last_updated", 0) >= 8.5:
                    step_idx = (ag.get("sim_cycle_step", 0) + 1) % len(cycle_stations)
                    ag["sim_cycle_step"] = step_idx
                    st, act, badge, det, icon = cycle_stations[step_idx]
                    ag["station"] = st
                    ag["activity"] = act
                    ag["badge"] = badge
                    ag["detail"] = det
                    ag["icon"] = icon
                    ag["last_updated"] = now
                    self._emit_event(sim_id, st, act, badge, det, icon)

    def get_snapshot(self, since_event_id: int = 0) -> Dict[str, Any]:
        """Devuelve el estado completo de agentes y los eventos nuevos desde since_event_id."""
        with self.lock:
            all_agents = list(self.agents.values()) + list(self.simulated_agents.values())
            # Ordenar: primero agentes en vivo / simulados, luego por última actualización
            all_agents.sort(
                key=lambda a: (
                    1 if (a.get("is_live") or a.get("is_simulated")) else 0,
                    a.get("last_updated", 0),
                ),
                reverse=True,
            )

            new_events = [e for e in self.events if e["id"] > since_event_id]

            return {
                "timestamp": time.time(),
                "brain_dir": self.brain_dir,
                "latest_event_id": self.event_seq - 1,
                "agents": all_agents,
                "events": new_events,
                "recent_log": self.events[-20:][::-1],
            }
