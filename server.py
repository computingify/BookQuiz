import http.server
import socketserver
import urllib.parse
import json
import os
import sqlite3
from datetime import datetime

# Configuration
DB_FILE = "quiz_database.db"
BOOKS_FILE = "books_data/books.json"
PORT = 5042

def init_db():
    """Initialise la base de données SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            book_id TEXT,
            chapter_title TEXT,
            score INTEGER,
            timestamp DATETIME,
            UNIQUE(username, book_id, chapter_title)
        )
    ''')
    conn.commit()
    conn.close()

class QuizHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        path = parsed_url.path

        if path == '/':
            self.path = '/home.html'
        elif path == '/api/books':
            username = query_params.get('user', ['Guest'])[0]
            self.send_books_list(username)
            return
        elif path.startswith('/api/quiz/'):
            book_id = path.split('/api/quiz/')[1]
            self.send_quiz_data(book_id)
            return
        elif path.startswith('/api/status/'):
            book_id = path.split('/api/status/')[1]
            username = query_params.get('user', ['Guest'])[0]
            self.send_book_status(book_id, username)
            return
        
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/log-result':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            user = params.get('username', ['Guest'])[0]
            book_id = params.get('book_id', ['unknown'])[0]
            chapitre = params.get('chapitre', ['?'])[0]
            score = params.get('score', ['0'])[0]
            
            self.save_result(user, book_id, chapitre, score)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

    def save_result(self, user, book_id, chapter_title, score):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO results (username, book_id, chapter_title, score, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (user, book_id, chapter_title, int(score), now))
        conn.commit()
        conn.close()
        print(f"[SQL] Result saved: {user} | {book_id} | {score}/5")

    def get_progression(self, book_id, username):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT chapter_title FROM results WHERE username = ? AND book_id = ? AND score > 3', (username, book_id))
        completed = [row[0] for row in cursor.fetchall()]
        conn.close()
        return completed

    def send_books_list(self, username):
        try:
            with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for book in data['books']:
                completed = self.get_progression(book['id'], username)
                book['completed_chapters'] = len(completed)
                book['total_chapters'] = book['chapters']
                book['is_completed'] = len(completed) >= book['chapters']
                book['in_progress'] = 0 < len(completed) < book['chapters']
                book['completed_list'] = completed

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        except Exception as e:
            self.send_error(500, str(e))

    def send_quiz_data(self, book_id):
        with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
            books = json.load(f)['books']
        book = next((b for b in books if b['id'] == book_id), None)
        if book:
            with open(book['quizFile'], 'r', encoding='utf-8') as f:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(f.read().encode())

    def send_book_status(self, book_id, username):
        completed = self.get_progression(book_id, username)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"chapters": completed}).encode())

if __name__ == "__main__":
    init_db()
    print(f"Serveur lancé sur http://localhost:{PORT}")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
        httpd.serve_forever()