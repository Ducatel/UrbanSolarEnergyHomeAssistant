#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Installation de Home Assistant (peut prendre plusieurs minutes)..."
pip install --upgrade pip
pip install -r requirements_test.txt

mkdir -p config/custom_components
ln -sfn "$(pwd)/custom_components/urban_solar_energy" config/custom_components/urban_solar_energy

if [ ! -f config/configuration.yaml ]; then
  cat > config/configuration.yaml <<'EOF'
# Config minimale pour developper/tester l'integration urban_solar_energy en isolation
default_config:

logger:
  default: info
  logs:
    custom_components.urban_solar_energy: debug
EOF
fi

echo "Termine. Lance la tache VS Code 'Demarrer Home Assistant' (Ctrl+Shift+P > Run Task) ou: hass -c config --debug"
