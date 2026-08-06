#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/mapd-niskier}"
VENV_DIR="${VENV_DIR:-$HOME/.virtualenvs/mapd-niskier}"

cd "$PROJECT_DIR"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Virtualenv não encontrado em $VENV_DIR"
  echo "Crie-o com: mkvirtualenv mapd-niskier --python=/usr/local/bin/python3.13"
  exit 1
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_cronogramas
python manage.py preparar_plataforma
python manage.py collectstatic --noinput
python manage.py check
python manage.py test

echo "Atualização concluída. Recarregue a aplicação na aba Web do PythonAnywhere."
