import http.server
import socketserver
import urllib.parse
import json
import os
import secrets
import hashlib
from datetime import datetime

RESULTS_FILE = "results.json"
BOOKS_FILE = "books_data/books.json"
USERS_FILE = "books_data/users.json"
SESSIONS_FILE = "sessions.json"
PORT = 5000

class QuizHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/login.html'
        elif self.path == '/api/books':
            self.verify_auth_and_call(self.send_books_list)
        elif self.path.startswith('/api/quiz/'):
            book_id = self.path.split('/api/quiz/')[1]
            self.verify_auth_and_call(self.send_quiz_data, book_id)
        elif self.path.startswith('/api/status/'):
            book_id = self.path.split('/api/status/')[1]
            self.verify_auth_and_call(self.send_book_status, book_id)
        elif self.path == '/api/user':
            self.verify_auth_and_call(self.send_user_info)
        elif self.path == '/api/logout':
            self.logout_user()
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/login':
            self.handle_login()
        elif self.path == '/api/signup':
            self.handle_signup()
        elif self.path == '/api/log-result':
            self.verify_auth_and_call(self.log_result_authenticated)
        elif self.path == '/api/change-password':
            self.verify_auth_and_call(self.change_password)
        elif self.path == '/api/admin/users':
            self.verify_admin_and_call(self.get_all_users)
        elif self.path == '/api/admin/reset-password':
            self.verify_admin_and_call(self.admin_reset_password)
        elif self.path == '/api/admin/results':
            self.verify_admin_and_call(self.get_user_results)
        else:
            self.send_error(404)

    def verify_auth_and_call(self, method, *args):
        """Vérifier l'authentification avant d'appeler une méthode"""
        user = self.get_authenticated_user()
        if not user:
            self.send_error(401)
            return
        self.current_user = user
        return method(*args)

    def verify_admin_and_call(self, method, *args):
        """Vérifier que l'utilisateur est administrateur"""
        user = self.get_authenticated_user()
        if not user or not user.get('is_admin', False):
            self.send_error(403)
            return
        self.current_user = user
        return method(*args)

    def get_authenticated_user(self):
        """Récupérer l'utilisateur depuis le token session"""
        cookies = self.headers.get('Cookie', '')
        session_token = None
        for cookie in cookies.split(';'):
            if 'session_token=' in cookie:
                session_token = cookie.split('session_token=')[1].strip()
                break
        
        if not session_token:
            return None
        
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
                if session_token in sessions:
                    session = sessions[session_token]
                    created_time = datetime.fromisoformat(session['created_at'])
                    if (datetime.now() - created_time).total_seconds() < 86400:
                        return self.get_user_by_id(session['user_id'])
        
        return None

    def get_user_by_id(self, user_id):
        """Récupérer les infos d'un utilisateur"""
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
                if user_id in users:
                    user = users[user_id]
                    user['id'] = user_id
                    return user
        return None

    def handle_login(self):
        """Gérer la connexion"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)
            
            login = params.get('login', '')
            password = params.get('password', '')
            
            if not os.path.exists(USERS_FILE):
                self.send_json({"success": False, "message": "Identifiants invalides"}, 401)
                return
            
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            user_id = None
            for uid, user in users.items():
                if user['login'] == login:
                    user_id = uid
                    break
            
            if not user_id:
                self.send_json({"success": False, "message": "Identifiants invalides"}, 401)
                return
            
            user = users[user_id]
            hashed = hashlib.sha256(password.encode()).hexdigest()
            if hashed != user['password_hash']:
                self.send_json({"success": False, "message": "Identifiants invalides"}, 401)
                return
            
            session_token = secrets.token_urlsafe(32)
            if not os.path.exists(SESSIONS_FILE):
                sessions = {}
            else:
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            
            sessions[session_token] = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }
            
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Set-Cookie', f'session_token={session_token}; Path=/; HttpOnly; Max-Age=86400')
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "message": "Connexion réussie",
                "user": {
                    "id": user_id,
                    "login": user['login'],
                    "nom": user['nom'],
                    "prenom": user['prenom'],
                    "is_admin": user.get('is_admin', False)
                }
            }).encode())
        except Exception as e:
            self.send_json({"success": False, "message": str(e)}, 500)

    def handle_signup(self):
        """Gérer l'inscription"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)
            
            nom = params.get('nom', '').strip()
            prenom = params.get('prenom', '').strip()
            email = params.get('email', '').strip()
            login = params.get('login', '').strip()
            
            if not all([nom, prenom, email, login]):
                self.send_json({"success": False, "message": "Tous les champs sont requis"}, 400)
                return
            
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    users = json.load(f)
            else:
                users = {}
            
            for user in users.values():
                if user['login'] == login:
                    self.send_json({"success": False, "message": "Ce login existe déjà"}, 400)
                    return
                if user['email'] == email:
                    self.send_json({"success": False, "message": "Cet email est déjà utilisé"}, 400)
                    return
            
            user_id = hashlib.sha256(f"{login}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            temp_password = secrets.token_urlsafe(12)
            
            users[user_id] = {
                "login": login,
                "nom": nom,
                "prenom": prenom,
                "email": email,
                "password_hash": hashlib.sha256(temp_password.encode()).hexdigest(),
                "is_admin": False,
                "created_at": datetime.now().isoformat()
            }
            
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            
            self.send_registration_email(email, login, temp_password, prenom)
            
            self.send_json({
                "success": True,
                "message": f"Inscription réussie ! Un mot de passe temporaire a été envoyé à {email}"
            }, 201)
        except Exception as e:
            self.send_json({"success": False, "message": str(e)}, 500)

    def send_registration_email(self, email, login, password, prenom):
        """Envoyer un email avec le mot de passe temporaire"""
        try:
            print(f"\n📧 [EMAIL] Envoi à {email}")
            print(f"   Login: {login}")
            print(f"   Mot de passe temporaire: {password}")
            print(f"   Prénom: {prenom}")
        except Exception as e:
            print(f"Erreur lors de l'envoi d'email: {e}")

    def log_result_authenticated(self):
        """Enregistrer un résultat (version authentifiée)"""
        try:
            user = self.current_user
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            book_id = params.get('book_id', ['unknown'])[0]
            chapitre = params.get('chapitre', ['?'])[0]
            score = params.get('score', ['?'])[0]
            
            self.log_result(user['id'], book_id, chapitre, score)
            
            self.send_json({"status": "ok"})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def change_password(self):
        """Changer le mot de passe"""
        try:
            user = self.current_user
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)
            
            old_password = params.get('old_password', '')
            new_password = params.get('new_password', '')
            
            if not old_password or not new_password:
                self.send_json({"success": False, "message": "Ancien et nouveau mot de passe requis"}, 400)
                return
            
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            user_data = users[user['id']]
            
            old_hashed = hashlib.sha256(old_password.encode()).hexdigest()
            if old_hashed != user_data['password_hash']:
                self.send_json({"success": False, "message": "Ancien mot de passe incorrect"}, 401)
                return
            
            user_data['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
            
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            
            self.send_json({"success": True, "message": "Mot de passe changé avec succès"})
        except Exception as e:
            self.send_json({"success": False, "message": str(e)}, 500)

    def logout_user(self):
        """Déconnecter l'utilisateur"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Set-Cookie', 'session_token=; Path=/; Max-Age=0')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True}).encode())

    def send_books_list(self):
        """Envoie la liste des livres avec leur statut"""
        try:
            user = self.current_user
            with open(BOOKS_FILE, 'r', encoding='utf-8') as f:
                books_config = json.load(f)
            
            for book in books_config['books']:
                book_id = book['id']
                status = self.get_book_completion_status(user['id'], book_id)
                book['completed_chapters'] = status['completed_chapters']
                book['total_chapters'] = status['total_chapters']
                book['is_completed'] = status['is_completed']
                book['in_progress'] = status['in_progress']
            
            books_config['books'].sort(key=lambda x: (x['is_completed'], -x['completed_chapters']))
            
            self.send_json(books_config)
        except Exception as e:
            self.send_error(500, str(e))

    def send_quiz_data(self, book_id):
        """Envoie les données du quiz pour un livre"""
        try:
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
            
            quiz_file = book['quizFile']
            base_dir = os.path.dirname(os.path.abspath(__file__))
            quiz_path = os.path.join(base_dir, quiz_file)
            
            quiz_path = os.path.abspath(quiz_path)
            if not quiz_path.startswith(base_dir):
                self.send_error(403, "Accès refusé")
                return
            
            if not os.path.exists(quiz_path):
                self.send_error(404, "Quiz non trouvé")
                return
            
            with open(quiz_path, 'r', encoding='utf-8') as f:
                quiz_data = json.load(f)
            
            self.send_json(quiz_data)
        except Exception as e:
            self.send_error(500, str(e))

    def send_book_status(self, book_id):
        """Envoie le statut de complétion d'un livre"""
        try:
            user = self.current_user
            status = self.get_book_completion_status(user['id'], book_id)
            self.send_json(status)
        except Exception as e:
            self.send_error(500, str(e))

    def send_user_info(self):
        """Envoie les infos de l'utilisateur courant"""
        try:
            user = self.current_user
            self.send_json({
                "id": user['id'],
                "login": user['login'],
                "nom": user['nom'],
                "prenom": user['prenom'],
                "email": user['email'],
                "is_admin": user.get('is_admin', False)
            })
        except Exception as e:
            self.send_error(500, str(e))

    def get_all_users(self):
        """Obtenir tous les utilisateurs (admin)"""
        try:
            if not os.path.exists(USERS_FILE):
                self.send_json([])
                return
            
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            users_list = []
            for user_id, user in users.items():
                users_list.append({
                    "id": user_id,
                    "login": user['login'],
                    "nom": user['nom'],
                    "prenom": user['prenom'],
                    "email": user['email'],
                    "is_admin": user.get('is_admin', False),
                    "created_at": user.get('created_at', '')
                })
            
            self.send_json(users_list)
        except Exception as e:
            self.send_error(500, str(e))

    def admin_reset_password(self):
        """Réinitialiser le mot de passe d'un utilisateur (admin)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = json.loads(post_data)
            
            user_id = params.get('user_id', '')
            
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            if user_id not in users:
                self.send_json({"success": False, "message": "Utilisateur non trouvé"}, 404)
                return
            
            new_password = secrets.token_urlsafe(12)
            users[user_id]['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
            
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            
            self.send_json({
                "success": True,
                "message": f"Mot de passe réinitialisé",
                "new_password": new_password
            })
        except Exception as e:
            self.send_json({"success": False, "message": str(e)}, 500)

    def get_user_results(self):
        """Obtenir les résultats d'un utilisateur (admin)"""
        try:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            user_id = params.get('user_id', [''])[0]
            book_id = params.get('book_id', [''])[0]
            
            if not os.path.exists(RESULTS_FILE):
                self.send_json({})
                return
            
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                all_results = json.load(f)
            
            if user_id in all_results:
                if book_id:
                    book_results = {}
                    for chapter, result in all_results[user_id].items():
                        if chapter.startswith(book_id):
                            book_results[chapter] = result
                    self.send_json(book_results)
                else:
                    self.send_json(all_results[user_id])
            else:
                self.send_json({})
        except Exception as e:
            self.send_error(500, str(e))

    def log_result(self, user_id, book_id, chapter_title, score):
        """Enregistrer un résultat"""
        try:
            score_int = int(score)
        except:
            score_int = 0
        
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = {}
        
        if user_id not in results:
            results[user_id] = {}
        
        if book_id not in results[user_id]:
            results[user_id][book_id] = {}
        
        results[user_id][book_id][chapter_title] = {
            "score": score_int,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n[RÉSULTAT] Utilisateur: {user_id} | Livre: {book_id} | Chapitre: {chapter_title} | Score: {score_int}/5")

    def get_book_completion_status(self, user_id, book_id):
        """Retourne le statut de complétion d'un livre pour un utilisateur"""
        completed_chapters = []
        
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            if user_id in results and book_id in results[user_id]:
                for chapter_title, result in results[user_id][book_id].items():
                    if result['score'] > 3:
                        completed_chapters.append(chapter_title)
        
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
        
        is_completed = (len(completed_chapters) == total_chapters) and total_chapters > 0
        in_progress = len(completed_chapters) > 0 and not is_completed
        
        return {
            "completed_chapters": len(completed_chapters),
            "total_chapters": total_chapters,
            "is_completed": is_completed,
            "in_progress": in_progress,
            "chapters": completed_chapters
        }

    def send_json(self, data, status_code=200):
        """Envoyer une réponse JSON"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

print(f"Serveur lancé sur le port {PORT}")
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
    httpd.serve_forever()