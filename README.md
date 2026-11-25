# 👾 Pixelavity — Antigravity Live Visualizer (MediaHub Edition)

**Pixelavity** es una aplicación de escritorio nativa en **2D Pixel Art** perteneciente al conglomerado **MediaHub**, diseñada para observar en tiempo real a los agentes de **Antigravity (Gemini)** mientras trabajan, piensan, consultan librerías, programan, ejecutan comandos en la terminal o despliegan subagentes mediante **Orchestrator**.

---

## ✨ Características Principales

- 🖥️ **App de Escritorio Nativa (PyQt6 + QPainter a 60 FPS)**:
  Modo espectador limpio, sin pestañas de navegador, con botón **`📌 Fijar Encima`** para mantener la oficina visible mientras trabajas en Antigravity o VS Code.
- 🧠 **Telemetría Real de Antigravity Brain**:
  Monitorea en vivo `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`.
- 💬 **Soporte Multi-Chat Simultáneo**:
  Cada chat abierto en Antigravity aparece como un personaje independiente con su modelo y paleta visual.
- 🎛️ **Orchestrator y Subagentes**:
  Visualiza enlaces holográficos en vivo entre el agente principal y los subagentes desplegados desde el **Spawn Pad**.
- 🏢 **8 Salas Interactivas con Iluminación Dinámica**:
  1. 📚 **Biblioteca**: Búsqueda de librerías, lectura de archivos y documentación (`read_file`, `grep_search`, `find_by_name`, `search_marketplace`).
  2. 💭 **Estrategia**: Análisis de prompts y planificación (`thinking`, `update_steps`, `update_focus`).
  3. 🎛️ **Orchestrator**: Despliegue y coordinación multi-agente (`invoke_subagent`, `swarm`, `run_workflow`).
  4. 🌐 **Cabina Web**: Búsquedas en internet y agente navegador (`search_web`, `browser`).
  5. 💻 **Computadores**: Escritura y edición de código (`write_file`, `edit_file`) con monitores que se iluminan con código en vivo.
  6. ⚡ **Terminal Lab**: Comandos de consola y pruebas (`run_command`, `manage_task`).
  7. 🎨 **Estudio UI**: Diseño visual y generación de imágenes.
  8. ☕ **Cafetería & Lounge**: Descanso en espera del siguiente mensaje del usuario.

---

## 🚀 Uso en Desarrollo

```bash
pip install -r requirements.txt
python main.py
```

## 📦 Compilar Ejecutable (.exe)

```bash
pip install pyinstaller
pyinstaller Pixelavity.spec
```

El ejecutable standalone se genera en `dist/Pixelavity/Pixelavity.exe`.
Al publicar un tag `v*` en GitHub (`Media-Hub-Site/Pixelavity`), GitHub Actions genera y publica automáticamente `Pixelavity.zip` y `Pixelavity-Setup.exe` compatibles con **MediaHub Launcher**.
