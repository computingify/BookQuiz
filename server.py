import http.server
import socketserver
import urllib.parse
import json
import os
from datetime import datetime

LOG_FILE = "resultats_quiz.txt"
PORT = 5000

class QuizHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/get-status':
            success_chapters = self.get_successful_chapters()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(success_chapters).encode())
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/log-result':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            chapitre = params.get('chapitre', ['?'])[0]
            score = params.get('score', ['?'])[0]
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] Chapitre : {chapitre} | Score : {score}/5"
            
            print(f"\n[RÉCEPTION] {log_entry}")
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            
            self.send_response(200)
            self.end_headers()

    def get_successful_chapters(self):
        """Lit le fichier de log et renvoie la liste des chapitres réussis (>3)"""
        status = {}
        if not os.path.exists(LOG_FILE):
            return []

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    # Extraction simple : Chapitre : Nom du Chapitre | Score : X/5
                    parts = line.split('|')
                    chap_name = parts[0].split('Chapitre : ')[1].strip()
                    score_val = int(parts[1].split('Score : ')[1].split('/')[0])
                    # Le dictionnaire écrase avec la ligne la plus récente (grâce à l'ordre du fichier)
                    status[chap_name] = score_val
                except:
                    continue
        
        # On ne garde que les noms des chapitres où le score > 3
        return [name for name, score in status.items() if score > 3]

print(f"Serveur lancé sur le port {PORT}")
with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
    httpd.serve_forever()