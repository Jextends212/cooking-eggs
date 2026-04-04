#!/bin/bash
# Menu interactivo para pausar/reanudar AWS resources
# Uso: bash aws_menu.sh

echo ""
echo "============================================================"
echo "  🛑 COKING EGGS - AWS RESOURCE CONTROL PANEL"
echo "============================================================"
echo ""
echo "Current Status:"
python quick_pause.py --status
echo ""
echo "============================================================"
echo "  OPCIONES"
echo "============================================================"
echo ""
echo "1️⃣  PAUSA RÁPIDA (RDS only)"
echo "   📊 Ahorra: ~\$15/mes"
echo "   ⏱️  Pausa: <2 minutos"
echo "   💾 Datos: PRESERVADOS"
echo "   🌐 Frontend: DISPONIBLE"
echo ""
echo "2️⃣  PAUSA COMPLETA (RDS + Lambda + CloudFront)"
echo "   📊 Ahorra: ~\$21/mes"
echo "   ⏱️  Pausa: <5 minutos"
echo "   💾 Datos: PRESERVADOS"
echo "   🌐 Frontend: NO DISPONIBLE"
echo ""
echo "3️⃣  REANUDAR (Reactiva todo)"
echo "   ⏱️  Reactivación: ~10-15 minutos"
echo ""
echo "4️⃣  VER DOCUMENTSACIÓN"
echo ""
echo "============================================================"
echo ""
read -p "Selecciona opción (1-4): " choice

case $choice in
  1)
    echo ""
    echo "⏸️  Quick pausing RDS database..."
    python quick_pause.py --pause
    ;;
  2)
    echo ""
    echo "🛑 Starting complete pause..."
    python pause_resources.py
    ;;
  3)
    echo ""
    echo "▶️  Resuming all resources..."
    python resume_resources.py
    ;;
  4)
    echo ""
    echo "📖 Cost Management Documentation:"
    echo "   - COST_MANAGEMENT.md"
    echo "   - PAUSE_RESUME_GUIDE.md"
    echo ""
    cat PAUSE_RESUME_GUIDE.md | less
    ;;
  *)
    echo "❌ Invalid option"
    exit 1
    ;;
esac

echo ""
echo "============================================================"
echo "Operación completada. ¿Necesitas algo más?"
echo "============================================================"
