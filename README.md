# 👾 PixelAgents — Antigravity Live Visualizer

**PixelAgents** es una aplicación web y ventana gráfica interactiva en **2D Pixel Art** inspirada en *Pixel Agents*, diseñada específicamente para visualizar en tiempo real a los agentes de **Antigravity (Gemini)** mientras trabajan, piensan, buscan librerías, programan, usan la terminal o despliegan subagentes mediante **Orchestrator**.

---

## ✨ Características Principales

- 🧠 **Conexión en Tiempo Real con Antigravity Brain**:
  Lee y monitorea en vivo `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`.
- 💬 **Soporte Multi-Chat Simultáneo**:
  Si tienes varios chats abiertos en Antigravity (incluso con distintos modelos como *Gemini 4 Argon*, *Gemini 3.8 Flash*, etc.), cada conversación aparece como su propio personaje en la oficina con su etiqueta de modelo y color.
- 🎛️ **Visualización de Orchestrator y Subagentes**:
  Cuando un agente principal invoca subagentes (`invoke_subagent`, `research`, `browser`, `self`, `image-generator`), el agente principal se dirige al **Núcleo Orchestrator**, proyecta enlaces holográficos hacia el **Spawn Pad**, y los subagentes aparecen y caminan hacia sus estaciones asignadas.
- 🚶 **Caminata con Pathfinding por Salas y Pasillos**:
  Los personajes caminan físicamente entre las 8 salas a través del corredor central y las puertas según la herramienta que estén ejecutando:
  1. 📚 **Biblioteca & Librerías**: Cuando busca librerías, explora documentación o lee archivos (`read_file`, `grep_search`, `find_by_name`, `search_marketplace`).
  2. 💻 **Sala de Computadores**: Cuando programa, crea o edita archivos (`write_file`, `edit_file`). Los monitores duales se encienden con código en movimiento.
  3. ⚡ **Laboratorio Terminal**: Cuando ejecuta comandos de consola o tests (`run_command`, `manage_task`).
  4. 💭 **Pizarra de Estrategia**: Cuando analiza un prompt del usuario o actualiza el plan (`thinking`, `update_steps`, `update_focus`).
  5. 🎛️ **Núcleo Orchestrator**: Cuando coordina y despliega subagentes.
  6. 🌐 **Cabina Web & Radar**: Cuando realiza búsquedas en internet o usa el agente navegador (`search_web`, `browser`).
  7. 🎨 **Estudio Creativo**: Cuando diseña interfaces o genera imágenes.
  8. ☕ **Cafetería & Descanso**: Cuando termina su turno y espera la siguiente instrucción del usuario.

---

## 🚀 Cómo Ejecutar

### 1. App de Escritorio 100% Nativa en PyQt6 (Recomendado — Sin navegador web)
```bash
python app_qt.py
```
*Incluye modo **"📌 Fijar Encima"** para mantenerla flotando sobre Antigravity o VS Code y renderizado directo con `QPainter` a 60 FPS.*

### 2. Ventana Gráfica Web / Navegador
```bash
python main.py
# o en modo ventana web dedicada / navegador:
python main.py --app-window
python main.py --browser
```

En modo web, el servidor también queda disponible en `http://127.0.0.1:8765`.
