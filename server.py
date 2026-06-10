#!/usr/bin/env python3
"""
PlanillaDash — servidor local y online con Google Drive
"""
import os, json, threading, webbrowser, io
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

PORT = int(os.environ.get("PORT", 8765))
IS_LOCAL = os.environ.get("PORT") is None

FOLDER_ID = "1EIaCbet09IcaYID2SH7VfKFhf-m81vdV"

# Archivo donde se persisten las reglas de categorización
CATEGORIAS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "categorias.json")

# ── Google Drive client ──────────────────────────────────────────────────────
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        info = json.loads(creds_json)
    else:
        creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
        with open(creds_path) as f:
            info = json.load(f)

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

def list_drive_files():
    try:
        svc = get_drive_service()
        res = svc.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false and (mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='application/vnd.ms-excel')",
            fields="files(id,name,size,modifiedTime)",
            orderBy="name"
        ).execute()
        return res.get("files", [])
    except Exception as e:
        print("Error listando Drive:", e)
        return []

def download_drive_file(file_id):
    try:
        svc = get_drive_service()
        req = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        from googleapiclient.http import MediaIoBaseDownload
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()
    except Exception as e:
        print("Error descargando:", e)
        return None

# ── Categorías helpers ───────────────────────────────────────────────────────
def load_categorias():
    """Lee el JSON de reglas del disco. Devuelve lista vacía si no existe."""
    try:
        with open(CATEGORIAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_categorias(data):
    """Escribe la lista de reglas al disco."""
    with open(CATEGORIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── HTTP Handler ─────────────────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # ── Listar archivos de Drive ──
        if self.path == "/api/files":
            files = list_drive_files()
            result = [
                {"name": f["name"], "id": f["id"],
                 "size": int(f.get("size", 0)), "modified": f.get("modifiedTime", "")}
                for f in files
            ]
            self._json_response(result)
            return

        # ── Obtener reglas de categorización ──
        if self.path == "/api/categorias":
            self._json_response(load_categorias())
            return

        # ── Descargar archivo de Drive ──
        if self.path.startswith("/planillas/"):
            file_id = unquote(self.path[len("/planillas/"):])
            data = download_drive_file(file_id)
            if data:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", len(data))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        # Redirigir / → index.html y rutas sin extensión
        if self.path == "/":
            self.path = "/index.html"
        elif self.path in ("/ventas", "/gastos", "/categorizador"):
            self.path = self.path + ".html"

        super().do_GET()

    def do_POST(self):
        # ── Guardar reglas de categorización ──
        if self.path == "/api/categorias":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                if not isinstance(data, list):
                    raise ValueError("Expected a JSON array")
                save_categorias(data)
                self._json_response({"ok": True, "saved": len(data)})
            except Exception as e:
                print("Error guardando categorías:", e)
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if IS_LOCAL:
        def abrir_browser():
            import time; time.sleep(1.2)
            webbrowser.open(f"http://localhost:{PORT}")
        threading.Thread(target=abrir_browser, daemon=True).start()
        print(f"""
╔══════════════════════════════════════╗
║  PlanillaDash - Corriendo            ║
╠══════════════════════════════════════╣
║  URL: http://localhost:{PORT}           ║
║                                      ║
║  Los xlsx se leen desde Google Drive ║
║  Categorías: categorias.json         ║
║                                      ║
║  Cerrá esta ventana para apagar.     ║
╚══════════════════════════════════════╝
""")
    else:
        print(f"PlanillaDash corriendo en puerto {PORT}")

    try:
        HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nServidor apagado.")
