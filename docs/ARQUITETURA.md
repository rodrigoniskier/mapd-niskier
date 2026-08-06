# Arquitetura do MAPD Niskier

## Perfis

- **Aluno:** cadastro inicial por RGM, nome, turma e senha; revisão, avaliação, tutoria, resultado e feedback.
- **Professor:** métricas por aluno, turma e tema; geração e publicação de pacotes; edição completa pelo Django Admin.

## Fluxo de conteúdo

1. Fontes aprovadas são armazenadas em `FonteConhecimento`.
2. O professor gera um pacote por tema com o Gemini.
3. Slides e questões entram como rascunho.
4. O professor revisa e publica.
5. Cada tentativa sorteia 9 objetivas e 1 discursiva aprovadas.

## Avaliação

- Objetivas: 0,8 ponto cada, totalizando 7,2.
- Discursiva: até 2,8 pontos.
- Total: 10,0 pontos.
- Ajustes docentes geram registro em `AuditoriaNota`.

## IA Niskier

- Plantão geral por tema.
- Tutor lateral durante a avaliação.
- Resposta socrática, sem entrega direta da alternativa.
- Citações limitadas às fontes previamente aprovadas e armazenadas.

## Segurança

- Chave Gemini apenas no servidor.
- Senhas gerenciadas pelo Django.
- Controle de acesso por perfil.
- Proteção CSRF e cookies seguros em produção.
