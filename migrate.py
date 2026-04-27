#!/usr/bin/env python3
"""
Script de migration des données results.json vers SQLite.
"""
import json
import os
import sys

# Ajouter le répertoire parent au path pour importer database
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database

RESULTS_FILE = "results.json"


def migrate_results():
    """Migre les résultats JSON vers SQLite."""
    if not os.path.exists(RESULTS_FILE):
        print("Aucun fichier results.json à migrer.")
        return
    
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    total_migrated = 0
    for book_id, chapters in results.items():
        for chapter_title, data in chapters.items():
            score = data.get('score', 0)
            database.log_result(book_id, chapter_title, score)
            total_migrated += 1
            print(f"  ✓ Migré: {book_id} - {chapter_title} (score: {score})")
    
    print(f"\nMigration terminée: {total_migrated} résultats migrés.")
    
    # Sauvegarder l'ancien fichier
    backup_file = f"{RESULTS_FILE}.backup"
    os.rename(RESULTS_FILE, backup_file)
    print(f"Ancien fichier sauvegardé: {backup_file}")


if __name__ == "__main__":
    print("=== Migration vers SQLite ===\n")
    migrate_results()
    print("\n=== Terminé ===")