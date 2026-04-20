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
