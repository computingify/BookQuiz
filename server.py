import http.server
import socketserver
import urllib.parse
import json
import os
from datetime import datetime

import database

BOOKS_FILE = "books_data/books.json"
PORT = 6000

class QuizHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/home.html'
        elif self.path == '/api/books':
            self.send_books_list()
        elif self.path.startswith('/api/quiz/'):
            book_id = self.path.split('/api/quiz/')[1]
            self.send_quiz_data(book_id)
        elif self.path.startswith('/api/status/'):
            book_id = self.path.split('/api/status/')[1]
            self.send_book_status(book_id)
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        if self.path == '/home.html':
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/log-result':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            book_id = params.get('book_id', ['unknown'])[0]
            chapitre = params.get('chapitre', ['?'])[0]
            score = params.get('score', ['?'])[0]
            
            self.log_result(book_id, chapitre, score)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

    def send_books_list(self):
        """Envoie la liste des livres avec leur statut"""
        try:
            with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
                books_config = json.load(f)
            
            # Enrichir avec les infos de progression
            for book in books_config['books']:
                book_id = book['id']
                status = self.get_book_completion_status(book_id)
                book['completed_chapters'] = status['completed_chapters']
                book['total_chapters'] = status['total_chapters']
                book['is_completed'] = status['is_completed']
                book['in_progress'] = status['in_progress']
            
            # Trier : en cours d'abord, puis terminés
            books_config['books'].sort(key=lambda x: (x['is_completed'], -x['completed_chapters']))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(books_config).encode())
        except Exception as e:
            self.send_error(500, str(e))

    def send_quiz_data(self, book_id):
        """Envoie les données du quiz pour un livre"""
        try:
            # Charger la config du livre
            with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
                books_config = json.load(f)
            
            book = None
            for b in books_config['books']:
                if b['id'] == book_id:
                    book = b
                    break
            
            if not book:
                self.send_error(404, "Livre non trouvé")
                return
            
            # Charger le fichier quiz
            quiz_file = book['quizFile']
            
            # Résoudre le chemin de manière sécurisée
            base_dir = os.path.dirname(os.path.abspath(__file__))
            quiz_path = os.path.join(base_dir, quiz_file)
            
            # Vérifier que le chemin reste dans le répertoire de base
            quiz_path = os.path.abspath(quiz_path)
            if not quiz_path.startswith(base_dir):
                self.send_error(403, "Accès refusé")
                return
            
            if not os.path.exists(quiz_path):
                self.send_error(404, "Quiz non trouvé")
                return
            
            with open(quiz_path, 'r', encoding='utf-8') as f:
                quiz_data = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(quiz_data).encode())
        except Exception as e:
            self.send_error(500, str(e))

    def send_book_status(self, book_id):
        """Envoie le statut de complétion d'un livre"""
        try:
            status = self.get_book_completion_status(book_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        except Exception as e:
            self.send_error(500, str(e))

    def log_result(self, book_id, chapter_title, score):
        """Enregistre le résultat d'un quiz"""
        try:
            score_int = int(score)
        except:
            score_int = 0
        
        # Enregistrer dans SQLite
        database.log_result(book_id, chapter_title, score_int)
        
        print(f"\n[RÉSULTAT] Livre: {book_id} | Chapitre: {chapter_title} | Score: {score_int}/5")

    def get_book_completion_status(self, book_id):
        """Retourne le statut de complétion d'un livre"""
        # Récupérer les chapitres complétés depuis SQLite
        completed_chapters = database.get_completed_chapters(book_id, min_score=4)
        
        # Charger le nombre total de chapitres
        total_chapters = 0
        try:
            with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
                books_config = json.load(f)
            for book in books_config['books']:
                if book['id'] == book_id:
                    total_chapters = book['chapters']
                    break
        except:
            pass
        
        is_completed = (len(completed_chapters) >= total_chapters) and total_chapters > 0
        in_progress = len(completed_chapters) > 0 and not is_completed
        
        return {
            "completed_chapters": len(completed_chapters),
            "total_chapters": total_chapters,
            "is_completed": is_completed,
            "in_progress": in_progress,
            "chapters": completed_chapters
        }


# Initialiser la base de données au démarrage
database.init_db()

print(f"Serveur lancé sur le port {PORT}")
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
    httpd.serve_forever()