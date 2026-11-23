# KG Matériaux

Knowledge graph de matériaux aéronautiques (Neo4j Aura) avec une interface web PHP :
terminal Cypher en lecture seule et assistant IA (Ollama) qui traduit des questions en français en requêtes Cypher.

## Installation
1. Placer le dossier dans `C:\wamp64\www\` et lancer WAMP.
2. Copier `.env.example` en `.env` et renseigner `NEO4J_PASSWORD`.
3. (Optionnel) Lancer Ollama avec le modèle `qwen2.5-coder:1.5b` pour l'assistant IA.
4. Ouvrir http://localhost/kg-materiaux/

## Fichiers
- `index.php` : interface web
- `query.php` : exécution des requêtes Cypher (lecture seule)
- `ai.php` : assistant IA (Ollama → Cypher)
- `config.php` : connexion à Neo4j Aura via la Query API HTTPS (port 443)
- `test.py` : création du graphe (`pip install neo4j`, puis `python test.py`)
