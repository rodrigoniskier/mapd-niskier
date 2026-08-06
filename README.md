# MAPD Niskier — Plataforma de Estudos

Plataforma Django para revisão, avaliação formativa e tutoria por IA em **Mecanismos de Agressão, Patológicos e de Defesa 2**.

## Estado do projeto

MVP funcional com:

- cadastro no primeiro acesso por **RGM + nome + turma + senha**;
- login posterior por **RGM + senha**;
- dashboards separados para aluno e professor;
- cronogramas das turmas A, B e C de 2026/2;
- revisão rápida em até 3 telas;
- avaliação com 9 questões objetivas e 1 discursiva;
- tutoria lateral “IA Niskier” sem entrega direta da resposta;
- Plantão Niskier 24h;
- correção, nota, feedback e comprovante imprimível;
- integração opcional com a API Gemini;
- Django Admin para editar turmas, temas, questões, notas e fontes.

## Instalação rápida no PythonAnywhere

No Bash:

```bash
git clone https://github.com/rodrigoniskier/mapd-niskier.git
cd mapd-niskier

python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
```

Preencha, no mínimo:

```env
DJANGO_SECRET_KEY=uma-chave-longa-e-secreta
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=SEU_USUARIO.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://SEU_USUARIO.pythonanywhere.com
GEMINI_API_KEY=SUA_CHAVE
```

Prepare o banco:

```bash
python manage.py migrate
python manage.py seed_cronogramas
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

No painel **Web** do PythonAnywhere:

1. Crie uma nova aplicação manual.
2. Selecione Python 3.10.
3. Informe o caminho do virtualenv: `/home/SEU_USUARIO/mapd-niskier/.venv`.
4. Configure o arquivo WSGI:

```python
import os
import sys

path = "/home/SEU_USUARIO/mapd-niskier"
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mapd_niskier.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

5. Em **Static files**, configure:
   - URL: `/static/`
   - Directory: `/home/SEU_USUARIO/mapd-niskier/staticfiles`
6. Recarregue a aplicação.

## Fluxo inicial recomendado

1. Entre em `/admin/` com o superusuário.
2. Confirme os cronogramas e temas.
3. No dashboard do professor, clique em **Gerar pacote com IA** para cada tema.
4. Revise as questões no Django Admin.
5. Publique o pacote para liberar aos alunos.

Sem `GEMINI_API_KEY`, a plataforma continua funcionando para cadastro, cronogramas, edição manual e avaliações já cadastradas.

## Atualização futura

Depois do primeiro clone:

```bash
cd ~/mapd-niskier
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

## Fonte principal

A base indicada no projeto é:

- https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/

O comando abaixo importa texto público de uma URL para a base auditável:

```bash
python manage.py importar_fonte_url "https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/"
```

A importação automática deve ser conferida pelo professor, especialmente quando a página usar carregamento dinâmico.

## Segurança

- Nunca envie `.env` ao GitHub.
- A chave Gemini é usada apenas no servidor.
- Senhas são armazenadas pelo mecanismo seguro do Django.
- Alunos são identificados pelo RGM.
- Alterações de nota ficam registradas no banco.
- O comprovante é uma evidência de realização da atividade, não um certificado institucional oficial.

## Licença e autoria

Código privado. Desenvolvido por **Prof. Rodrigo Niskier Ferreira Barbosa**.
