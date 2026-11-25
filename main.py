# -*- coding: utf-8 -*-
"""
Pixelavity - Visualizador 2D Pixel Art en Tiempo Real para Agentes de Antigravity (Gemini)
Parte del conglomerado MediaHub (https://github.com/Media-Hub-Site/Pixelavity).

Modos de uso:
  python main.py                -> Inicia la aplicación de escritorio nativa en PyQt6 (por defecto)
  python main.py --web          -> Inicia el servidor web local y lo abre en el navegador
  python main.py --server-only  -> Ejecuta solo el servidor HTTP/SSE en http://127.0.0.1:8765
"""

import os
import sys
import time
import argparse
import webbrowser

# Asegurar rutas de importación tanto en desarrollo como en PyInstaller
current_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", current_dir)
else:
    base_dir = current_dir

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)


def main():
    parser = argparse.ArgumentParser(description="Pixelavity - Antigravity Live Visualizer (MediaHub)")
    parser.add_argument("--brain-dir", type=str, default=None, help="Ruta a ~/.gemini/antigravity/brain")
    parser.add_argument("--web", action="store_true", help="Abrir modo web local en el navegador")
    parser.add_argument("--server-only", action="store_true", help="Ejecutar únicamente el servidor HTTP/SSE")
    parser.add_argument("--port", type=int, default=8765, help="Puerto local para modo web (default: 8765)")
    args = parser.parse_args()

    if args.web or args.server_only:
        from core.server import PixelAgentsServer

        web_dir = os.path.join(base_dir, "web")
        server = PixelAgentsServer(host="127.0.0.1", port=args.port, brain_dir=args.brain_dir, web_dir=web_dir)
        url = server.start()
        if args.web:
            webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            server.stop()
        return

    # Modo por defecto: App de Escritorio Nativa PyQt6
    from app_qt import run_desktop_app
    run_desktop_app(brain_dir=args.brain_dir)


if __name__ == "__main__":
    main()
