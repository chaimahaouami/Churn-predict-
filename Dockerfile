# Image officielle Python 3.10 (version slim)
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier les fichiers requirements.txt, app.py et randomForest.pkl dans le conteneur
COPY requirements.txt .
COPY app.py .
COPY randomForest.pkl .

# Mettre à jour pip
RUN pip install --upgrade pip

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port 5000 (port par défaut Flask)
EXPOSE 5000

# Commande pour lancer ton app Flask
CMD ["python", "app.py"]
