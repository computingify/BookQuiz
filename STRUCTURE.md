# Structure du projet Quiz

## 📁 Organisation des fichiers

### Dossier racine
- `server.py` - Serveur Python
- `home.html` - Page d'accueil (bibliothèque)
- `quiz.html` - Page de quiz
- `books.json` - Configuration des livres
- `results.json` - Résultats des quiz (généré automatiquement)
- `README.md` - Ce fichier

### Dossier `books_data/`
Contient tous les données spécifiques aux livres (modifiables par l'utilisateur)

```
books_data/
├── le-secret-du-gladiateur/
│   ├── quiz.json           # Questions et réponses du quiz
│   ├── cover.svg           # Image de couverture (300x400px)
│   └── cover.png           # Alternative PNG (optionnel)
├── mon-autre-livre/
│   ├── quiz.json
│   ├── cover.svg
│   └── ...
```

## 🚀 Ajouter un nouveau livre

### Étape 1 : Créer le dossier du livre
```bash
mkdir books_data/mon-nouveau-livre
```

### Étape 2 : Créer le fichier quiz
Créez `books_data/mon-nouveau-livre/quiz.json` avec le format suivant :

```json
{
  "id": "mon-nouveau-livre",
  "title": "Titre du Livre",
  "chapters": [
    {
      "id": 1,
      "title": "Chapitre 1 : Titre",
      "questions": [
        {
          "q": "Question 1 ?",
          "options": ["Réponse A", "Réponse B", "Réponse C"],
          "r": 0,
          "ex": "Explication de la bonne réponse"
        },
        // ... 4 autres questions
      ]
    }
    // ... autres chapitres
  ]
}
```

**Format requis :**
- Chaque chapitre doit avoir exactement **5 questions**
- `r` est l'index de la bonne réponse (0, 1 ou 2)
- `ex` est l'explication affichée après le quiz

### Étape 3 : Créer la couverture
Créez `books_data/mon-nouveau-livre/cover.svg` (ou `.png`)

**Format recommandé :**
- Dimensions : 300x400 pixels
- Format : SVG (natif web) ou PNG
- Style : À votre convenance

### Étape 4 : Ajouter le livre à `books.json`

```json
{
  "books": [
    {
      "id": "mon-nouveau-livre",
      "title": "Titre du Livre",
      "author": "Nom de l'Auteur",
      "description": "Description courte du livre",
      "cover": "books_data/mon-nouveau-livre/cover.svg",
      "chapters": 12,
      "quizFile": "books_data/mon-nouveau-livre/quiz.json"
    }
  ]
}
```

## 📊 Format des résultats

Le fichier `results.json` est généré automatiquement et contient :

```json
{
  "mon-nouveau-livre": {
    "Chapitre 1 : Titre": {
      "score": 4,
      "timestamp": "2026-04-21T09:47:22"
    }
  }
}
```

## 🎯 Génération avec IA

Pour générer les quiz avec IA, utilisez ce prompt :

> Générer un fichier JSON au format suivant pour le livre "[TITRE]". Le JSON doit contenir [N] chapitres avec 5 questions chacun. Chaque question doit avoir 3 options, une bonne réponse (index 0-2), et une explication.

## 🔧 Points techniques

- Le serveur cherche les fichiers quiz dans les chemins relatifs définis dans `books.json`
- Les résultats sont stockés par ID de livre pour gérer plusieurs livres simultanément
- Les coches vertes (✅) apparaissent pour les chapitres avec score > 3/5
- Le quiz s'ouvre automatiquement sur le premier chapitre non complété
