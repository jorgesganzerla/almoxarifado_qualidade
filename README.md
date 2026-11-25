# Sistema de Almoxarifado — DevOps/QAOps

Aplicação desktop (Java Swing + MySQL) para cadastrar produtos, registrar retiradas de estoque,
listar produtos e consultar relatórios. O sistema foi desenvolvido em uma disciplina anterior e,
neste trabalho, recebeu um **pipeline de CI no GitHub Actions com quality gates** que bloqueiam
alterações inadequadas antes que cheguem à branch `main`.

## Funcionalidades
- Cadastrar produto (nome, quantidade, especificação, empresa)
- **Retirar produto** (pessoa, setor, produto, quantidade) com controle transacional de estoque —
  funcionalidade escolhida para o estudo de qualidade
- Listar produtos e estoque atual
- Relatórios: por setor, por pessoa e por produto (busca parcial)

## Tecnologias
| Item | Ferramenta | Por quê |
|------|-----------|---------|
| Linguagem | Java 21 (LTS) | linguagem original do sistema |
| Build e dependências | Maven (`pom.xml`) | arquivo declarativo de dependências, padrão no ecossistema Java |
| Banco | MySQL 8 | banco original do sistema |
| Testes | JUnit 5 + Surefire (unitários) + Failsafe (integração) | separa testes rápidos dos que precisam de banco |
| Análise estática | Checkstyle | regras configuráveis e explicáveis, roda em segundos |
| Cobertura | JaCoCo | integra ao Maven e permite limites por pacote |
| Dependências | Trivy (imagem `aquasec/trivy:0.69.3`) | gratuito, lê o `pom.xml`, filtra por severidade, sem chave de API |
| CI | GitHub Actions | repositório da dupla está no GitHub; resumo e artefatos em cada execução |

## Arquitetura resumida
```
src/main/java/almoxarifado/
  ui/        Telas Swing (MainFrame, Cadastro, Retirada, Listar, Relatório)   -> chamam service e db
  service/   RegrasEstoque (regras de negócio), FormatadorListagem, FormatadorRelatorio
  db/        DbConfig (lê variáveis de ambiente), DatabaseConnection (JDBC), TesteConexao
  model/     Produto
src/test/java/  testes unitários (*Test) e de integração (*IT)
config/checkstyle.xml                regras de análise estática
database.sql                         esquema do banco (fonte única, usada também pelos testes)
.github/workflows/ci.yml             pipeline
ci/resumo_qualidade.py               gera o relatório dos gates em cada execução
docs/                                quality gates, experimento e roteiro da demonstração
```

## Instalação e execução local

### Pré-requisitos
- JDK 21 ou superior
- Maven 3.9+
- MySQL 8 (para executar o sistema e os testes de integração)

### Banco de dados (sem credenciais no código)
A conexão é lida de variáveis de ambiente (ou propriedades `-D` da JVM):

| Variável | Obrigatória | Padrão |
|----------|-------------|--------|
| `DB_URL` | não | `jdbc:mysql://localhost:3306/almoxarifado` |
| `DB_USER` | não | `root` |
| `DB_PASSWORD` | **sim** | — |

```bash
# Linux/macOS
export DB_PASSWORD='sua_senha'
# Windows (PowerShell)
$env:DB_PASSWORD = 'sua_senha'
```
Crie o esquema uma vez: `mysql -u root -p < database.sql`

### Build e execução
```bash
mvn -B clean package -DskipTests
java -jar target/almoxarifado.jar
```
Para testar apenas a conexão: `java -cp target/almoxarifado.jar almoxarifado.db.TesteConexao`

## Testes
```bash
mvn test              # 44 testes unitários (*Test): rápidos, NÃO precisam de banco
mvn verify            # unitários + 9 de integração (*IT): precisam de MySQL de TESTE
mvn checkstyle:check  # análise estática
mvn jacoco:check      # gate de cobertura (depois do verify)
```
Os testes de integração **apagam e recriam as tabelas**. Por segurança só rodam se `DB_URL` apontar
para um banco com `_test` no nome:
```bash
mysql -u root -p -e "CREATE DATABASE almoxarifado_test"
export DB_URL='jdbc:mysql://localhost:3306/almoxarifado_test?useSSL=false&allowPublicKeyRetrieval=true'
export DB_PASSWORD='sua_senha'
mvn verify
```
Relatório de cobertura: `target/site/jacoco/index.html`. Resumo igual ao do pipeline:
`python3 ci/resumo_qualidade.py`.

## Pipeline de CI (`.github/workflows/ci.yml`)
Acionado a cada **push** e **pull request** para `main` (e manualmente pela aba *Actions*).
Não é preciso configurar nada: o MySQL do pipeline é descartável e recebe uma senha aleatória,
mascarada nos logs, a cada execução. Se o segredo `DB_PASSWORD` existir em
*Settings → Secrets and variables → Actions*, ele é usado no lugar.

```
push/PR ─► dependências ─► Gate 1 ─► Gate 2 ────► Gate 5 ───────► Gate 3 ─► Gate 4 ─► resumo + artefato
           (JDK, cache)    Build     Checkstyle   Dependências    Testes    Cobertura  (sempre)
                                                  (Trivy)         + MySQL
```

| Gate | Comando | Reprova quando | Evidência |
|------|---------|----------------|-----------|
| 1 Build | `mvn package -DskipTests` | o código não compila ou não empacota | log do passo, `almoxarifado.jar` |
| 2 Análise estática | `mvn checkstyle:check` | qualquer violação de `config/checkstyle.xml` | log, `checkstyle-result.xml` |
| 5 Dependências | `trivy fs --severity HIGH,CRITICAL --exit-code 1` | alguma dependência tem vulnerabilidade alta ou crítica | log, `trivy-dependencias.txt` |
| 3 Testes | `mvn verify` | qualquer teste unitário ou de integração falha | `surefire-reports`, `failsafe-reports` |
| 4 Cobertura | `mvn jacoco:check` | linhas < 80% (model, service, db) **ou** ramos de `service` < 90% | `site/jacoco/` |

O job para no primeiro gate que falha; os seguintes aparecem como "não executado". Mesmo assim,
o resumo (aba *Summary* da execução) e o artefato **evidencias-qualidade** são sempre publicados,
com o resultado de cada gate, os testes que quebraram, a cobertura por pacote e as violações.
A justificativa e a ficha completa de cada gate estão em [`docs/QUALITY_GATES.md`](docs/QUALITY_GATES.md).

### Para que o bloqueio seja efetivo
Em *Settings → Branches → Add branch protection rule* (`main`): marcar **Require a pull request
before merging** e **Require status checks to pass before merging**, selecionando o check
`Quality gates`. Assim um pull request reprovado não pode ser integrado.

## Experimento e demonstração
- Roteiro do experimento aprovado → reprovado → corrigido: [`docs/EXPERIMENTO.md`](docs/EXPERIMENTO.md)
- Roteiro da apresentação (10–12 min): [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md)

## Segurança
- Nenhuma senha, token ou chave no código; configuração via variáveis de ambiente.
- `.gitignore` bloqueia `.env`, `target/`, `.class` e `.jar`.
- A senha do banco de teste é gerada a cada execução (ou vem de um segredo do GitHub) e é mascarada nos logs.
- O pipeline roda com permissão somente de leitura (`permissions: contents: read`).
- A imagem do Trivy é fixada na versão 0.69.3: as versões 0.69.4–0.69.6 e a tag `latest` foram
  comprometidas em março/2026 (CVE-2026-33634). Usar tag fixa é o próprio controle de risco aqui.

## Melhorias feitas sobre a versão original
- Projeto convertido para Maven; `.class`, `.jar`, `.bat` com caminhos fixos e o código antigo da
  raiz removidos do Git.
- Credenciais fora do código (a versão original tinha a senha do MySQL fixa em `DatabaseConnection`).
- Regras de negócio extraídas das telas para `service/`, permitindo testes sem interface gráfica.
- **Defeito corrigido:** retirada ou cadastro com quantidade negativa era aceito (retirada negativa
  *aumentava* o estoque).
- **Defeito corrigido:** campo "Código" ficava vazio na tela de retirada se o usuário não trocasse
  o produto selecionado.
- Falhas de banco deixaram de ser silenciosas (antes retornavam lista vazia).
- Retirada usa `SELECT ... FOR UPDATE` para evitar estoque negativo em retiradas simultâneas.
- Classe `Retirada` (sem uso) e contador estático de `Produto` removidos.

## Limitações conhecidas
- A interface Swing não é testada automaticamente (exige ambiente gráfico); é verificada manualmente.
- O gate de dependências depende das bases públicas do Trivy; uma vulnerabilidade ainda não
  publicada não é detectada. Não há atualização automática de dependências (equivalente ao
  Dependabot/Renovate).
- Não há etapa de implantação (CD) nem observabilidade: o sistema é desktop e o pipeline termina no
  artefato `almoxarifado.jar`.
