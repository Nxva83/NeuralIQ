#!/bin/bash
source venv/bin/activate
echo "🔄 Rafraîchissement des données..."
python riot_pipeline.py --name "TuOrdinateur" --tag "6969" --matches 20
python heatmap.py --name "TuOrdinateur" --tag "6969" --matches 20
python analyze.py --name "TuOrdinateur" --tag "6969"
echo "✅ Données mises à jour !"
