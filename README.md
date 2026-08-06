# MAPD Niskier — Plataforma de Estudos

Plataforma Django para revisão, avaliação formativa personalizada e tutoria por IA em **Mecanismos de Agressão, Patológicos e de Defesa 2**.

## Entrega funcional

### Área do aluno

- primeiro acesso com **RGM + nome + turma + senha**;
- vínculo permanente do RGM com a turma;
- código de ingresso opcional por turma;
- login posterior com RGM e senha;
- temas liberados conforme o cronograma da turma;
- revisão em carrossel com até três telas;
- avaliação personalizada com **9 objetivas + 1 discursiva**;
- seleção adaptativa por histórico e dificuldade;
- salvamento automático das respostas;
- chat lateral com pistas graduais, sem revelar diretamente o gabarito;
- Plantão Niskier 24h com fontes e URLs auditáveis;
- resultado, feedback individual, comprovante em PDF e validação por QR Code;
- interface responsiva, modo escuro e PWA.

### Área do professor

- visão geral por turma, tema e aluno;
- médias, conclusões, tentativas em revisão e gráficos;
- gestão de temas, cronogramas, alunos, slides, questões e fontes;
- geração de pacote com Gemini: 3 telas, 15 objetivas e 2 discursivas;
- aprovação individual ou em lote e publicação controlada;
- correção discursiva preliminar por IA com sinalização para revisão docente;
- edição de notas com histórico obrigatório de auditoria;
- relatórios filtráveis, CSV e PDF;
- painel avançado do Django Admin.

### IA e auditoria

- modelo principal configurável por `.env`;
- modelo de fallback;
- respostas estruturadas por Pydantic;
- contexto de URL para fontes aprovadas;
- Pesquisa Google opcional no Plantão para aprofundamento;
- armazenamento de título, URL e resumo das fontes usadas;
- respostas determinísticas de contingência quando a API estiver indisponível.

## Atualização definitiva no PythonAnywhere

No Bash:

```bash
cd ~/mapd-niskier
rm -f core/migrations/0002_alter_usuario_options.py
git reset --hard HEAD
git pull origin main

workon mapd-niskier
bash deploy/update_pythonanywhere.sh
```

O script executa:

```text
instalação/atualização das dependências
migrações
carga dos cronogramas A, B e C
configuração inicial e fonte principal
collectstatic
check
testes automatizados
```

Depois, na aba **Web**, clique em **Reload**.

## Configuração do `.env`

```env
DJANGO_SECRET_KEY=uma-chave-longa-e-aleatoria
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=mapdniskier.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://mapdniskier.pythonanywhere.com

GEMINI_API_KEY=SUA_CHAVE
GEMINI_MODEL=gemini-3.6-flash
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=70
GEMINI_ENABLE_SEARCH=True
```

Nunca envie o arquivo `.env` ao GitHub.

## WSGI no PythonAnywhere

```python
import os
import sys

path = "/home/mapdniskier/mapd-niskier"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mapd_niskier.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Virtualenv:

```text
/home/mapdniskier/.virtualenvs/mapd-niskier
```

Static files:

```text
URL: /static/
Directory: /home/mapdniskier/mapd-niskier/staticfiles
```

## Acessos

- aplicação: `https://mapdniskier.pythonanywhere.com/`
- professor: o login redireciona automaticamente para `/professor/`;
- administração avançada: `/admin/`;
- primeiro acesso do aluno: `/primeiro-acesso/`.

O formulário aceita o username administrativo sem alterar maiúsculas/minúsculas e aceita o RGM normalizado dos alunos.

## Primeira preparação do conteúdo

1. Acesse **Fontes e auditoria** e confira a fonte principal.
2. Importe o texto público, quando possível, ou mantenha o contexto por URL.
3. Abra cada tema e clique em **Gerar pacote completo com Gemini**.
4. Revise amostras, edite o necessário e aprove as questões.
5. Publique o pacote.

Para gerar rascunhos pelo Bash:

```bash
workon mapd-niskier
cd ~/mapd-niskier
python manage.py gerar_todos_pacotes --substituir
```

A geração em lote pode consumir cota da API. O fluxo pelo painel permite revisar um tema por vez.

## Segurança e LGPD

- senhas armazenadas pelo mecanismo de hash do Django;
- chave Gemini usada somente no servidor;
- separação de permissões entre aluno e professor;
- aluno não altera a própria turma;
- acesso a temas limitado à turma vinculada;
- logs acadêmicos usam o RGM apenas quando necessário;
- notas alteradas ficam registradas com professor, data e justificativa;
- respostas externas da IA mantêm fontes para auditoria;
- o documento emitido é um **comprovante de atividade formativa**, não um certificado institucional oficial.

## Identidade visual

O repositório inclui uma marca tipográfica própria “MAPD Niskier — Medicina • UNIPÊ”. Ela não substitui o arquivo oficial de identidade visual da instituição. Um arquivo oficial autorizado pode substituir `static/img/logo.svg` sem alterar os templates.

## Testes

```bash
python manage.py check
python manage.py test
```

Os testes cobrem cadastro e vínculo de turma, código de ingresso, isolamento entre turmas, montagem 9+1, conclusão sem API, dashboard docente e edição de tema.

## Autoria

Desenvolvido para o **Prof. Rodrigo Niskier Ferreira Barbosa**. Repositório privado.
