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
import logging
import argparse
import tempfile
import traceback
import webbrowser

# Configuración segura de entorno antes de cargar PyQt6
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

# Asegurar rutas de importación tanto en desarrollo como en PyInstaller
current_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", current_dir)
else:
    base_dir = current_dir

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)


def get_log_path() -> str:
    """Devuelve la ruta de pixelavity.log en una carpeta con permisos de escritura."""
    candidates = []
    for env_key in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
        v = os.environ.get(env_key)
        if v:
            candidates.append(os.path.join(v, "MediaHub", "Pixelavity"))
    candidates.append(os.path.join(tempfile.gettempdir(), "MediaHub", "Pixelavity"))

    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, "pixelavity.log")
        except OSError:
            continue
    return os.path.join(tempfile.gettempdir(), "pixelavity.log")


def _setup_logging() -> str:
    log_path = get_log_path()
    try:
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            encoding="utf-8",
        )
    except Exception:
        pass
    logging.info("=== Iniciando Pixelavity (frozen=%s, base_dir=%s) ===", getattr(sys, "frozen", False), base_dir)
    return log_path


def _show_fatal_error(title: str, details: str, log_path: str):
    """Muestra un cuadro de error nativo (incluso si PyQt6 falló) y guarda el detalle en el log."""
    logging.error("%s\n%s", title, details)
    msg = (
        f"Pixelavity encontró un error inesperado al iniciar.\n\n"
        f"{details[:600]}\n\n"
        f"Se guardó el registro completo en:\n{log_path}"
    )
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, title, 0x10)
            return
        except Exception:
            pass
    print(f"[FATAL] {title}: {msg}", file=sys.stderr)


def main():
    log_path = _setup_logging()

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        tb_txt = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        _show_fatal_error("Pixelavity - Error de Ejecución", tb_txt, log_path)

    sys.excepthook = _excepthook

    try:
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
            logging.info("Modo servidor web iniciado en %s (brain=%s)", url, server.watcher.brain_dir)
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
    except Exception:
        _show_fatal_error("Pixelavity - No se pudo iniciar", traceback.format_exc(), log_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
