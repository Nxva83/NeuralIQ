# 🎮 RiftIQ — AI-Powered Valorant Coaching

> Projet EIP Epitech 2025 — Intelligence Artificielle appliquée à l'esport compétitif

RiftIQ analyse tes parties Valorant avec du Machine Learning (K-Means clustering) et génère des heatmaps de tes zones de kills/morts, des statistiques détaillées et des conseils personnalisés, le tout dans un dashboard web avec design Valorant.

---

## 📋 Prérequis système

- **OS** : Ubuntu 20.04+ / WSL2 / Debian
- **Python** : 3.10+
- **Node.js** : 20.x+
- **npm** : 9.x+
- **Git** : 2.x+

---

## ⚙️ Installation

### Prerequisites

- Ubuntu 20.04+ / WSL2 / Debian
- Python 3.10+
- Node.js 20+
- Git
- Nvidia GPU (recommended for Ollama)

### 1. Clone the repository

```bash
git clone https://github.com/Nxva83/RiftIQ.git
cd RiftIQ
```

### 2. Installer Node.js 20 (si pas déjà installé)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Installe et utilise Node 20
nvm install 20
nvm use 20

# Vérifie
node --version   # doit afficher v20.x.x
npm --version    # doit afficher 9.x.x ou 10.x.x
```

### 3. Set up Python environment

```bash
# Installe python3-venv si nécessaire
sudo apt update
sudo apt install python3-venv python3-pip -y

# Crée le venv
python3 -m venv venv
source venv/bin/activate
pip install requests pandas numpy scikit-learn matplotlib pillow scipy \
            fastapi uvicorn python-multipart httpx opencv-python-headless \
            python-jose[cryptography] passlib[bcrypt]
```

### 4. Install Ollama + AI models

```bash
pip install requests pandas numpy scikit-learn matplotlib pillow scipy fastapi uvicorn python-multipart
```

### 5. Installer les dépendances du dashboard React

```bash
cd dashboard
npm install
npm install recharts@2.12.7 --legacy-peer-deps
cd ..
```

---

## 🔑 API Keys

### Riot Games API Key
1. Va sur [developer.riotgames.com](https://developer.riotgames.com)
2. Connecte-toi avec ton compte Riot
3. Génère une **Development API Key** (valable 24h)
4. Exporte-la :

```bash
export RIOT_API_KEY="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Henrik Dev API Key
1. Rejoins le Discord Henrik : [discord.gg/X3GaVkX2YN](https://discord.gg/X3GaVkX2YN)
2. Va sur [api.henrikdev.xyz/dashboard](https://api.henrikdev.xyz/dashboard)
3. Génère une **Basic Key** (gratuite, instantanée)
4. Exporte-la :

```bash
export HENRIK_API_KEY="HDEV-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

> ⚠️ **Pour rendre les clés permanentes** (pas besoin de les réexporter à chaque terminal) :
> ```bash
> echo 'export RIOT_API_KEY="RGAPI-ta-clé"' >> ~/.bashrc
> echo 'export HENRIK_API_KEY="HDEV-ta-clé"' >> ~/.bashrc
> source ~/.bashrc
> ```

---

## 📁 Structure du projet

```
RiftIQ/
├── riot_pipeline.py      # Collecte les données de matchs via API
├── analyze.py            # Analyse statistique des données
├── heatmap.py            # Module IA K-Means — génère les heatmaps
├── api.py                # API FastAPI — sert les données au dashboard
├── data/                 # Données JSON générées (gitignore)
├── output/               # Heatmaps PNG générées (gitignore)
├── dashboard/            # Dashboard React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── pages/
│   │       ├── Overview.jsx
│   │       ├── Matches.jsx
│   │       ├── Heatmaps.jsx
│   │       └── Report.jsx
│   └── package.json
├── venv/                 # Environnement Python (gitignore)
├── .gitignore
└── README.md
```

---

## 🎯 Utilisation

### Étape 1 — Récupérer tes données de match

```bash
source venv/bin/activate

# Lance le pipeline (remplace par ton Riot ID et tag)
python riot_pipeline.py --name "TonPseudo" --tag "EUW" --matches 20

# Options disponibles :
#   --name     Ton Riot ID (obligatoire)
#   --tag      Ton tag Riot (obligatoire)
#   --region   Région : euw (défaut), na, kr
#   --matches  Nombre de matchs à analyser (max 20 avec clé dev)
```

### Step 2 — Generate heatmaps

```bash
python heatmap.py --name "TonPseudo" --tag "EUW" --matches 20

# Les images PNG sont générées dans output/
# Pour les ouvrir (WSL) :
explorer.exe output/
```

### Step 3 — Launch the platform

```bash
python analyze.py --name "TonPseudo" --tag "EUW"
```

### Étape 4 — Lancer le dashboard

**Terminal 1 — API Python :**
```bash
source venv/bin/activate
uvicorn api:app --reload --port 8000

# Terminal 2 — Dashboard
cd dashboard && npm run dev
```

**Ouvre dans ton navigateur :** [http://localhost:5173](http://localhost:5173)

> Si le port 5173 est occupé, Vite utilisera 5174. Vérifie l'URL dans le terminal.

---

## 🔧 Lancement rapide (tout en une fois)

Crée un fichier `start.sh` à la racine :

```bash
cat > start.sh << 'EOF'
#!/bin/bash
echo "🎮 Démarrage RiftIQ..."

# Active le venv
source venv/bin/activate

# Lance l'API en arrière-plan
uvicorn api:app --port 8000 &
API_PID=$!
echo "✅ API lancée (PID $API_PID)"

# Lance le dashboard
cd dashboard
npm run dev &
DASH_PID=$!
echo "✅ Dashboard lancé (PID $DASH_PID)"

echo ""
echo "🌐 Dashboard : http://localhost:5173"
echo "📡 API       : http://localhost:8000"
echo ""
echo "Pour arrêter : Ctrl+C ou kill $API_PID $DASH_PID"

wait
EOF

chmod +x start.sh
```

Ensuite :
```bash
./start.sh
```

---

## 🗺️ Maps supportées

| Map | Paramètres | Statut |
|-----|-----------|--------|
| Ascent | ✅ | Supportée |
| Bind | ✅ | Supportée |
| Split | ✅ | Supportée |
| Haven | ✅ | Supportée |
| Fracture | ✅ | Supportée |
| Pearl | ✅ | Supportée |
| Icebox | ✅ | Supportée |
| Breeze | ✅ | Supportée |
| Lotus | ✅ | Supportée |
| Sunset | ✅ | Supportée |
| Abyss | ✅ | Supportée |
| Corrode | ✅ | Supportée |

---

## 🧠 Architecture technique

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Riot API      │────▶│  riot_pipeline   │────▶│   data/*.json   │
│  Henrik API     │     │   (Python)       │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                        ┌──────────────────┐              │
                        │   heatmap.py     │◀─────────────┘
                        │  K-Means + KDE   │
                        │  scikit-learn    │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  output/*.png    │
                        │  (heatmaps)      │
                        └────────┬─────────┘
                                 │
┌─────────────────┐     ┌────────▼─────────┐
│  Dashboard      │◀────│   api.py         │
│  React + Vite   │     │   FastAPI        │
│  localhost:5173 │     │   localhost:8000 │
└─────────────────┘     └──────────────────┘
```

---

## ❗ Dépannage

### `RIOT_API_KEY` expire toutes les 24h
Les clés de développement Riot expirent. Régénère-en une sur [developer.riotgames.com](https://developer.riotgames.com) et réexporte-la.

### Erreur CORS sur le dashboard
Vite démarre parfois sur le port 5174 au lieu de 5173. Dans `api.py`, assure-toi d'avoir :
```python
allow_origins=["*"],
```

### `npm install` échoue avec peer deps
```bash
npm install --legacy-peer-deps
```

### Recharts ne s'installe pas
```bash
npm install recharts@2.12.7 --legacy-peer-deps
```

### Rate limit Henrik (429)
Le pipeline attend automatiquement 12 secondes. Si ça persiste, attends 1 minute et relance.

### Aucun match récupéré
- Vérifie que `HENRIK_API_KEY` est bien exportée
- Vérifie que le pseudo et le tag sont exacts (sensible à la casse)
- Assure-toi d'avoir joué des parties compétitives récemment

---

## 📊 Fonctionnalités

### Pipeline de données
- Connexion à la Riot API officielle pour le PUUID
- Récupération des matchs via Henrik Dev API
- Parsing et structuration des données (KDA, HS%, ACS, économie, positions)
- Sauvegarde en JSON pour traitement offline

### Module IA — K-Means Clustering
- Détection automatique du K optimal (méthode du coude)
- KDE gaussien pour visualiser la densité
- Masquage des zones hors-map via canal alpha
- Coloration par niveau de danger (vert → rouge)
- Labels anti-overlap avec flèches

### Dashboard React
- **Overview** : KPIs, évolution KDA, profil radar, agents, winrate par map
- **Matches** : Historique complet coloré WIN/LOSS
- **Heatmaps** : Grille de toutes les maps, zoom plein écran au clic
- **Rapport** : Analyse textuelle colorée avec conseils

---

## 🔮 Roadmap EIP

- [x] Pipeline données Riot + Henrik
- [x] Module K-Means heatmap
- [x] API FastAPI
- [x] Dashboard React
- [ ] Module LLM — conseils en langage naturel (GPT/Mistral)
- [ ] Authentification multi-joueurs
- [ ] Scoring économique (2ème module IA)
- [ ] Déploiement production (Docker + VPS)
- [ ] Application mobile

---

## ⚖️ Mentions légales

Ce projet utilise les APIs Riot Games et Henrik Dev.  
Il n'est pas approuvé par Riot Games et ne reflète pas leurs opinions.  
Riot Games, VALORANT et tous les éléments associés sont des marques déposées de Riot Games, Inc.

---

## 👥 Équipe EIP Epitech 2025

**RiftIQ** — Coaching IA pour joueurs compétitifs Valorant

---

*Made with ❤️ at Epitech*