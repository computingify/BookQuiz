import http.server
import socketserver
import urllib.parse
from datetime import datetime

LOG_FILE = "resultats_quiz.txt"
PORT = 5000

class QuizHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # Cette partie intercepte les résultats envoyés par le site
        if self.path == '/log-result':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            chapitre = params.get('chapitre', ['?'])[0]
            score = params.get('score', ['?'])[0]
            score_text = params.get('scoretext', ['?'])[0]
            
            # Création du timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] Chapitre : {chapitre} | Score : {score}/5  | Result : {score_text}"
            
            # 1. Affichage dans la console
            print(f"\n[RÉCEPTION] {log_entry}")
            
            # 2. Écriture dans le fichier (mode 'a' pour append/ajouter à la fin)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            
            self.send_response(200)
            self.end_headers()

print(f"Serveur lancé sur le port {PORT}")
print(f"Les résultats seront enregistrés dans : {LOG_FILE}")
with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
    httpd.serve_forever()
