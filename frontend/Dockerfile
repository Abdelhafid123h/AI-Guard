FROM node:18-alpine

# Définir le répertoire de travail
WORKDIR /app

# Copier package.json et package-lock.json
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier le reste des fichiers
COPY . .

# Exposer le port
EXPOSE 3000

# Variables d'environnement
ENV REACT_APP_API_URL=http://localhost:8000

# Commande de démarrage
CMD ["npm", "start"]
