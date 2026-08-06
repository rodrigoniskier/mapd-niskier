#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${HOME}/mapd-niskier"
VENV_DIR="${PROJECT_DIR}/.venv"

cd "$PROJECT_DIR"

PYTHON_BIN=""
for candidate in python3.10 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Nenhuma instalação compatível do Python foi encontrada."
  exit 1
fi

echo "Usando: $($PYTHON_BIN --version)"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Arquivo .env criado a partir de .env.example."
else
  echo "Arquivo .env já existe e não foi alterado."
fi

python manage.py migrate
python manage.py seed_cronogramas
python manage.py collectstatic --noinput
python manage.py check
python manage.py test

echo
echo "Preparação concluída. Agora preencha o .env, crie o superusuário e configure a aplicação Web no PythonAnywhere."
