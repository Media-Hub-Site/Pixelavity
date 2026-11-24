# -*- coding: utf-8 -*-
"""
PixelAgents - Visualizador 2D Pixel Art en Tiempo Real para Agentes de Antigravity (Gemini)
Integrado en el ecosistema MediaHub.

Modos de uso:
  python main.py                -> Inicia el watcher + servidor y abre ventana gráfica nativa
  python main.py --browser      -> Inicia el servidor y lo abre en el navegador web
  python main.py --server-only  -> Ejecuta solo el servidor web en http://127.0.0.1:8765
"""

import os
import sys
import time
import argparse
import webbrowser
import subprocess

# Asegurar rutas de importación tanto en desarrollo como en PyInstaller
current_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", current_dir)
else:
    base_dir = current_dir

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from core.server import PixelAgentsServer


def launch_chrome_or_edge_app_window(url: str) -> bool:
    """Intenta abrir una ventana gráfica dedicada (--app) usando Edge o Chrome."""
    if sys.platform != "win32":
        return False

    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if os.path.isfile(exe):
            try:
                subprocess.Popen([exe, f"--app={url}", "--window-size=1340,830"])
                return True
            except Exception:
                continue
    return False


def main():
    parser = argparse.ArgumentParser(description="PixelAgents - Antigravity Live Visualizer")
    parser.add_argument("--port", type=int, default=8765, help="Puerto local (default: 8765)")
    parser.add_argument("--brain-dir", type=str, default=None, help="Ruta a ~/.gemini/antigravity/brain")
    parser.add_argument("--browser", action="store_true", help="Abrir en el navegador por defecto")
    parser.add_argument("--app-window", action="store_true", help="Abrir en ventana gráfica independiente (--app)")
    parser.add_argument("--server-only", action="store_true", help="Ejecutar únicamente el servidor HTTP/SSE")
    args = parser.parse_args()

    web_dir = os.path.join(base_dir, "web")
    server = PixelAgentsServer(host="127.0.0.1", port=args.port, brain_dir=args.brain_dir, web_dir=web_dir)
    url = server.start()

    print("=" * 68)
    print(" 👾 PIXEL AGENTS // ANTIGRAVITY LIVE VISUALIZER")
    print("=" * 68)
    print(f" 🌐 Servidor Web Activo : {url}")
    print(f" 🧠 Monitoreando Brain  : {server.watcher.brain_dir}")
    print("=" * 68)

    if args.server_only:
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            server.stop()
        return

    if args.browser:
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            server.stop()
        return

    if args.app_window:
        if not launch_chrome_or_edge_app_window(url):
            webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            server.stop()
        return

    # Intentar abrir con pywebview (ventana nativa de escritorio)
    try:
        import webview
        window = webview.create_window(
            title="PixelAgents // Antigravity Live Visualizer",
            url=url,
            width=1360,
            height=840,
            min_size=(1024, 680),
            background_color="#0b0e17",
        )
        webview.start()
        server.stop()
        return
    except Exception as e:
        print(f"[Info] pywebview no disponible o falló al iniciar ({e}), abriendo ventana gráfica web...")
        if not launch_chrome_or_edge_app_window(url):
            webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            server.stop()


if __name__ == "__main__":
    main()
