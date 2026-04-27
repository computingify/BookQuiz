"""
Module de gestion de la base de données SQLite pour les résultats de quiz.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_FILE = "quiz_results.db"


def get_db_path():
    """Retourne le chemin absolu vers la base de données."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_FILE)


@contextmanager
def get_connection():
    """Context manager pour les connexions à la base."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialise la base de données avec les tables nécessaires."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table des résultats de quiz
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                chapter_title TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Index pour optimiser les requêtes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_book_chapter 
            ON quiz_results(book_id, chapter_title)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_book_id 
            ON quiz_results(book_id)
        """)


def log_result(book_id, chapter_title, score):
    """Enregistre un résultat de quiz."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Supprimer l'ancien résultat pour ce chapitre
        cursor.execute("""
            DELETE FROM quiz_results 
            WHERE book_id = ? AND chapter_title = ?
        """, (book_id, chapter_title))
        
        # Insérer le nouveau résultat
        cursor.execute("""
            INSERT INTO quiz_results (book_id, chapter_title, score, timestamp)
            VALUES (?, ?, ?, ?)
        """, (book_id, chapter_title, score, datetime.now().isoformat()))


def get_book_results(book_id):
    """Retourne tous les résultats pour un livre."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chapter_title, score, timestamp 
            FROM quiz_results 
            WHERE book_id = ?
            ORDER BY timestamp DESC
        """, (book_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_completed_chapters(book_id, min_score=4):
    """Retourne la liste des chapitres complétés (score >= min_score)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT chapter_title 
            FROM quiz_results 
            WHERE book_id = ? AND score >= ?
        """, (book_id, min_score))
        return [row['chapter_title'] for row in cursor.fetchall()]


# Initialisation automatique
if __name__ != "__main__":
    init_db()