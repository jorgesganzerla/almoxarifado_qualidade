# Roteiro da demonstração (10–12 minutos)

O enunciado pede: acionamento do pipeline, uma execução aprovada, uma reprovação, as evidências
geradas e a correção. O professor pode perguntar a cada integrante individualmente, então os dois
falam e os dois precisam dominar todas as partes.

## Preparação (antes da aula)
- Execuções 1, 2 e 3 do `EXPERIMENTO.md` já feitas (são a garantia caso a rede falhe).
- Abas abertas: repositório, aba **Actions**, o pull request do experimento, o artefato baixado e
  descompactado (`site/jacoco/index.html`), `docs/QUALITY_GATES.md`.
- Uma branch pronta para a demonstração ao vivo, por exemplo `demo/import-sem-uso`, com a falha do
  Gate 2 (import não usado) — é a mais rápida (~1 min até reprovar).

## Roteiro

| Tempo | Quem | O que mostrar | O que dizer |
|-------|------|---------------|-------------|
| 0:00–1:30 | Int. 1 | README; sistema rodando (opcional, 20 s) | Finalidade, tecnologias, arquitetura em camadas (`ui` → `service`/`db`), funcionalidade estudada: **retirada de estoque**. |
| 1:30–3:00 | Int. 2 | `docs/QUALITY_GATES.md`, tabela de riscos | Riscos R1–R7 e qual gate controla cada um. Defeito real da versão original (retirada negativa aumentava o estoque) e senha fixa no código. |
| 3:00–4:30 | Int. 1 | `.github/workflows/ci.yml` | Gatilhos (push/PR/manual), ordem dos gates, Trivy com versão fixada, senha aleatória do MySQL descartável, `if: always()` nos relatórios, permissão somente leitura. |
| 4:30–6:00 | Int. 2 | **Ao vivo:** push da branch `demo/...` e abertura do pull request | Pipeline acionado automaticamente. Enquanto roda, mostrar a **execução 1 aprovada**: aba *Summary* com tabela dos gates, testes e cobertura por pacote; artefato `evidencias-qualidade`; relatório JaCoCo. |
| 6:00–8:00 | Int. 1 | **Execução 2 reprovada** (pull request do experimento) | Alteração `>=` → `>`; Gate 3 vermelho, teste `permiteRetirarExatamenteOEstoqueTotal`, mensagem `expected <true> but was <false>`; Gate 4 não executou; integração não rodou (Maven para no primeiro teste que falha); **merge bloqueado** no pull request. |
| 8:00–9:00 | Int. 2 | Resultado da demo ao vivo | Gate 2 vermelho com arquivo e linha da violação. Corrigir (remover o import), push, mostrar reexecução. |
| 9:00–10:00 | Int. 1 | **Execução 3 corrigida** | Commit de correção, todos os gates verdes, histórico preservado (as três execuções na aba Actions). Comparar tempos e resultados. |
| 10:00–11:30 | Int. 2 | — | Análise crítica: riscos não cobertos (UI, concorrência real, segurança de SQL além do PreparedStatement), verificações manuais, custo de manutenção, o que faltaria para CD e observabilidade. |
| 11:30–12:00 | ambos | — | Contribuição de cada um e encerramento. |

## Perguntas prováveis (preparar resposta curta)
- Por que 80% de linhas e 90% de ramos em `service`? E por que a UI fica fora?
- O que acontece se alguém desativar um teste com `@Disabled`?
- Por que o Trivy está fixado na versão 0.69.3? O que aconteceu com a tag `latest`?
- Onde está a senha do banco do pipeline? E se alguém fizer fork do repositório?
- Qual a diferença entre "ter testes automatizados" e "praticar QAOps"?
- O que é o `SELECT ... FOR UPDATE` e qual risco ele reduz?
- Quanto tempo o pipeline leva e onde está o gargalo (download de dependências, subida do MySQL)?

## Plano B (sem internet)
Prints das três execuções no relatório e o artefato já baixado. Localmente:
`mvn test` (reprova com a alteração `>`) e `mvn checkstyle:check` (reprova com o import).
