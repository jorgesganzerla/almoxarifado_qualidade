# Quality gates — fichas

Cada gate tem critério mensurável, risco controlado, momento, evidência, consequência e limitação,
conforme a ficha exigida no enunciado. Os gates são passos do job `Quality gates` no GitHub Actions e
rodam nesta ordem: Gate 1 → Gate 2 → Gate 5 → Gate 3 → Gate 4. O primeiro gate que falha interrompe
o job; o resumo e o artefato de evidências são publicados sempre (`if: always()`).

## Riscos de qualidade do sistema

| ID | Risco | Onde | Gate que controla |
|----|-------|------|-------------------|
| R1 | Código que não compila/empacota chega à `main` e ninguém consegue executar o sistema | todo o projeto | 1 |
| R2 | Retirada com quantidade negativa ou zero altera o estoque indevidamente (defeito real da versão original) | `RegrasEstoque.validarRetirada` | 3, 4 |
| R3 | Erro de fronteira: recusar retirar exatamente o estoque disponível, ou permitir retirar mais que o estoque | `RegrasEstoque.podeRetirar` | 3, 4 |
| R4 | Retirada parcial: estoque debitado sem registrar o histórico (ou o contrário) | `DatabaseConnection.retirarProduto` (transação) | 3 |
| R5 | Erro silencioso: falha no banco mostrada ao usuário como "nenhum resultado" | `DatabaseConnection` | 2 (regras de bloco vazio), 3 |
| R6 | Nova regra de negócio entra sem nenhum teste | `service` | 4 |
| R7 | Dependência com vulnerabilidade conhecida (ex.: driver JDBC) | `pom.xml` | 5 |
| R8 | Senha versionada no repositório (havia na versão original) | configuração | revisão + `.gitignore` + senha gerada/segredo do GitHub |

---

## Gate 1 — Build

| Campo | Registro |
|-------|----------|
| **Nome e critério** | `mvn -B clean package -DskipTests` termina com código de saída 0 e gera `target/almoxarifado.jar`. |
| **Justificativa** | R1. Se o projeto não compila, nenhuma outra verificação faz sentido e o sistema não pode ser entregue. É o feedback mais rápido do pipeline. |
| **Momento** | Primeiro gate, em todo push e pull request para `main`. |
| **Evidência** | Log do passo; `almoxarifado.jar` no artefato `evidencias-qualidade` (30 dias). |
| **Consequência** | **Bloqueia.** Os gates seguintes não executam. |
| **Limitação/exceção** | Compilar não garante comportamento correto (papel dos gates 3 e 4). Não há exceção: código que não compila nunca é aceito. |

## Gate 2 — Análise estática

| Campo | Registro |
|-------|----------|
| **Nome e critério** | `mvn checkstyle:check` com **zero violações** das regras de `config/checkstyle.xml` (todas com severidade `error`), em código de produção e de teste. |
| **Justificativa** | R5 e manutenibilidade. As regras foram escolhidas por esconderem defeitos, não por estilo: `EmptyCatchBlock` (erro engolido — foi assim que a versão original escondia falhas de banco), `printStackTrace` proibido (erro só no console), `MissingSwitchDefault`, `FallThrough`, `EqualsHashCode`, `NeedBraces`, `UnusedImports`, `HideUtilityClassConstructor`. Não usamos o conjunto completo do Google/Sun porque geraria centenas de alertas de formatação sem relação com risco. |
| **Momento** | Depois do build, em todo push e pull request. |
| **Evidência** | Log do passo (arquivo:linha de cada violação), `checkstyle-result.xml` no artefato e lista de violações no resumo da execução. |
| **Consequência** | **Bloqueia.** |
| **Limitação/exceção** | Checkstyle analisa padrões de código, não fluxo de dados: não encontra SQL injection, NullPointerException ou erro de lógica. Exceções pontuais devem ser discutidas no pull request e registradas com `// CHECKSTYLE:OFF` justificado (hoje não há nenhuma). Evolução possível: SpotBugs ou CodeQL. |

## Gate 3 — Testes automatizados

| Campo | Registro |
|-------|----------|
| **Nome e critério** | `mvn verify`: **100%** dos 44 testes unitários (Surefire) e dos 9 testes de integração (Failsafe, contra um MySQL 8 descartável) aprovados. |
| **Justificativa** | R2, R3, R4. Os testes cobrem as regras críticas com casos positivos e negativos, inclusive valores de fronteira (estoque = pedido, quantidade 0, negativa, texto com 100 e 101 caracteres) e o comportamento transacional da retirada no banco. Basta um teste falhar para indicar regressão em comportamento crítico; por isso o critério é 100%, não um percentual. |
| **Momento** | Depois dos gates 2 e 5. Um MySQL 8 é criado num contêiner descartável, com senha gerada na execução e mascarada no log. Surefire roda os unitários; se passarem, Failsafe roda os de integração. |
| **Evidência** | Resumo da execução (aba *Summary*) com aprovados, falhas e o nome e a mensagem de cada teste que falhou; `surefire-reports/` e `failsafe-reports/` no artefato. |
| **Consequência** | **Bloqueia.** Se um teste unitário falhar, os de integração nem são executados (feedback mais rápido). |
| **Limitação/exceção** | A interface Swing não tem teste automatizado (exige ambiente gráfico; verificada manualmente). Não há teste de carga nem de concorrência real para o `FOR UPDATE`. O gate não impede que alguém desative um teste com `@Disabled` (conta como "ignorado", não como falha); por isso o relatório mostra os ignorados e isso deve ser verificado na revisão do pull request. Teste instável (flaky) deve ser corrigido, nunca desativado silenciosamente. |

## Gate 4 — Cobertura

| Campo | Registro |
|-------|----------|
| **Nome e critério** | `mvn jacoco:check` com duas regras: **(a)** cobertura de **linhas ≥ 80%** no conjunto `model` + `service` + `db`; **(b)** cobertura de **ramos ≥ 90%** no pacote `almoxarifado.service`. |
| **Justificativa** | R6. (a) 80% é alcançável sem testar código trivial e deixa margem para os blocos `catch` de erro de banco, difíceis de provocar com MySQL real (estimativa atual: cerca de 90%). (b) `service` concentra as regras de estoque; ali cada `if` é uma decisão de negócio, por isso medimos **ramos**, não linhas, com limite mais alto (atual: 100%). A pasta `ui` e o utilitário `TesteConexao` ficam fora da medição porque não são testáveis sem interface gráfica/banco interativo. |
| **Momento** | Último gate, usando o `target/jacoco.exec` gerado pelo Gate 3 (unitários + integração no mesmo arquivo). |
| **Evidência** | Relatório HTML/CSV/XML em `site/jacoco/` no artefato; tabela de linhas e ramos por pacote no resumo da execução. |
| **Consequência** | **Bloqueia.** |
| **Limitação/exceção** | Cobertura mede o que foi **executado**, não o que foi **verificado**: um teste sem asserção também cobre linhas. Por isso o gate complementa (e não substitui) a revisão dos testes. Alterar limites exige justificativa no pull request. |

## Gate 5 — Dependências vulneráveis

| Campo | Registro |
|-------|----------|
| **Nome e critério** | `trivy fs --scanners vuln --severity HIGH,CRITICAL --exit-code 1`: **nenhuma** dependência do `pom.xml` (diretas e transitivas) com vulnerabilidade conhecida de severidade **alta ou crítica**. |
| **Justificativa** | R7. O sistema usa um driver JDBC que lida com credenciais e rede; uma vulnerabilidade alta nele afeta diretamente a confidencialidade dos dados. Bloquear apenas "crítica" deixaria passar falhas de alto impacto; bloquear "média" geraria ruído e bloqueios por falhas sem caminho de exploração em um sistema desktop interno. Escolhemos o Trivy por ser gratuito, não exigir chave de API, filtrar por severidade e rodar em todo push (o Dependency Review do GitHub só roda em pull request). |
| **Momento** | Depois da análise estática e antes dos testes, em todo push e pull request. |
| **Evidência** | Tabela de vulnerabilidades no log do passo e em `trivy-dependencias.txt` no artefato. |
| **Consequência** | **Bloqueia e exige revisão**: atualizar a dependência para versão corrigida ou, se não houver, registrar a análise de risco no pull request. |
| **Limitação/exceção** | Só detecta vulnerabilidades já publicadas nas bases que o Trivy consulta. Uma vulnerabilidade nova em dependência existente pode reprovar um pipeline sem que o código tenha mudado (o que é desejável, mas pode surpreender). O próprio scanner é uma dependência da cadeia de suprimentos: a imagem fica fixada em `aquasec/trivy:0.69.3`, porque as versões 0.69.4–0.69.6 e a tag `latest` foram comprometidas em março/2026 (CVE-2026-33634). |

---

## Como o bloqueio é garantido
Um gate vermelho marca a execução como falha. Com a proteção da branch `main` configurada
(*Require a pull request before merging* + *Require status checks to pass* com o check
`Quality gates`), o botão de merge do pull request fica bloqueado até a correção.
