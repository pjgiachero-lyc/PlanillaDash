#!/usr/bin/env python3
"""
PlanillaDash — servidor local y online con Google Drive
"""
import os, json, threading, webbrowser, io, base64
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

PORT     = int(os.environ.get("PORT", 8765))
IS_LOCAL = os.environ.get("PORT") is None

FOLDER_ID      = "1EIaCbet09IcaYID2SH7VfKFhf-m81vdV"
PLANILLAS_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planillas")

# ── Google Drive client ──────────────────────────────────────────────────────
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    # Credenciales: variable de entorno en Railway, archivo local en PC
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


# ── HTTP Handler ─────────────────────────────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):

        # API: lista de archivos desde Drive
        if self.path == "/api/files":
            files = list_drive_files()
            result = []
            for f in files:
                result.append({
                    "name":     f["name"],
                    "id":       f["id"],
                    "size":     int(f.get("size", 0)),
                    "modified": f.get("modifiedTime", ""),
                })
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        # Descargar archivo por ID de Drive
        if self.path.startswith("/planillas/"):
            file_id = unquote(self.path[len("/planillas/"):])
            data = download_drive_file(file_id)
            if data:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", len(data))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
            return

        if self.path == "/":
            self.path = "/index.html"
        super().do_GET()

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
║        PlanillaDash - Corriendo      ║
╠══════════════════════════════════════╣
║  URL:  http://localhost:{PORT}          ║
║                                      ║
║  Los xlsx se leen desde Google Drive ║
║  Carpeta: planillas_dash             ║
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
