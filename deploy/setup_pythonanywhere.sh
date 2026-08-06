#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.10}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Arquivo .env criado. Preencha as variáveis antes de publicar."
fi

python manage.py migrate
python manage.py seed_cronogramas
python manage.py collectstatic --noinput
python manage.py check
python manage.py test

cat <<'EOF'

Preparação concluída.
Próximas ações manuais:
1. Edite o arquivo .env e informe a chave Gemini e o domínio.
2. Execute: source .venv/bin/activate && python manage.py createsuperuser
3. Configure a aplicação Web e o WSGI no PythonAnywhere.
4. Recarregue a aplicação.
EOF
