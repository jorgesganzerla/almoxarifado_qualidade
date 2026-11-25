# Roteiro do experimento: aprovado → reprovado → corrigido

O enunciado exige, no histórico do GitHub Actions, uma execução **aprovada**, uma **reprovada por
alteração controlada** e uma **nova aprovada após a correção**. Tudo deve ser feito em commits e
pull requests reais, com os dois integrantes participando (sugestão de divisão entre parênteses).

> Antes de começar: configure a proteção da branch `main` (README, seção "Para que o bloqueio
> seja efetivo"). Assim a reprovação também aparece como **merge bloqueado** no pull request, a
> evidência mais forte de que o gate impede o avanço da alteração.

## Execução 1 — Aprovada (linha de base) — *Integrante 1*
1. Faça o push da `main` com o pipeline (não é preciso criar segredo).
2. Na aba **Actions**, abra a execução e confirme os 5 gates verdes.
3. Registre na tabela de evidências: link, commit, duração, testes e cobertura (aba *Summary*) e
   baixe o artefato `evidencias-qualidade`.

## Execução 2 — Reprovada (falha controlada no Gate 3) — *Integrante 2*
1. Crie a branch: `git switch -c experimento/erro-fronteira`
2. Em `src/main/java/almoxarifado/service/RegrasEstoque.java`, método `podeRetirar`, troque
   ```java
   return quantidadeSolicitada > 0 && estoqueAtual >= quantidadeSolicitada;
   ```
   por
   ```java
   return quantidadeSolicitada > 0 && estoqueAtual > quantidadeSolicitada;
   ```
   Erro de fronteira realista (`>=` → `>`): o sistema passa a recusar a retirada de **todo** o
   estoque restante (ex.: há 5 grampeadores e alguém pede 5). Compila, passa no Checkstyle e só é
   detectado por teste.
3. `git commit -am "experimento: altera regra de fronteira da retirada (falha controlada)"`,
   `git push -u origin experimento/erro-fronteira` e abra um **pull request** para `main`.
4. **Resultado esperado** (validado localmente):
   - Gate 1 ✅, Gate 2 ✅, Gate 5 ✅, **Gate 3 ❌**, Gate 4 ⏭️ não executado.
   - Teste que falha: `RegrasEstoqueTest$PodeRetirar.permiteRetirarExatamenteOEstoqueTotal`
     com `expected: <true> but was: <false>` → **43/44** unitários aprovados.
   - Os 9 testes de integração **não executam**: o Maven para na fase `test` quando um unitário
     falha. (Se o teste unitário não existisse, o de integração `retiradaDoEstoqueTotalEhPermitida`
     pegaria o mesmo defeito, um nível acima.)
   - No pull request, o check `Quality gates` fica vermelho e o merge aparece bloqueado.
5. Registre: link da execução vermelha, print do passo que falhou, trecho do log com o teste
   quebrado e print do pull request bloqueado.

## Execução 3 — Aprovada após correção — *Integrante 1*
1. Na mesma branch, volte para `estoqueAtual >= quantidadeSolicitada`.
2. `git commit -am "fix: permite retirar exatamente o estoque disponível"` e `git push`.
3. O pull request é reexecutado automaticamente: todos os gates verdes, 44/44 + 9/9 testes.
4. Registre link e commit da correção. Faça o **merge** do pull request (o histórico das três
   execuções fica preservado na aba Actions e no pull request).

## Variações opcionais (mostram outros gates reprovando)
Todas foram validadas localmente. Use uma por pull request, com o mesmo ciclo falha → correção.

| Falha proposital | Gate que reprova | Evidência esperada |
|------------------|------------------|--------------------|
| Adicionar `import java.util.Date;` sem uso em `FormatadorRelatorio.java` | **2 – Análise estática** | `FormatadorRelatorio.java:3 — Unused import - java.util.Date.` |
| Erro de sintaxe (ex.: apagar um `;`) em qualquer `.java` | **1 – Build** | erro de compilação no log; os demais gates não executam |
| Nova regra de negócio **sem teste** (abaixo) | **4 – Cobertura** | ramos de `service` caem de 100% para 85% (< 90%); todos os testes passam |

### Variação "nova regra sem teste" (Gate 4)
Mostra que testes verdes não bastam: o gate de cobertura detecta código novo não verificado.
Adicione em `RegrasEstoque` (antes de `estaVazio`):
```java
    /** Indica se o produto precisa de reposição (estoque no mínimo ou abaixo dele). */
    public static boolean precisaRepor(int estoqueAtual, int estoqueMinimo) {
        if (estoqueMinimo <= 0) {
            return false;
        }
        if (estoqueAtual < 0) {
            throw new IllegalArgumentException("Estoque não pode ser negativo!");
        }
        return estoqueAtual <= estoqueMinimo;
    }
```
Resultado esperado: gates 1–3 ✅, **Gate 4 ❌** (`almoxarifado.service` ramos 34/40 = 85%).
Correção: adicionar os testes em `RegrasEstoqueTest`:
```java
    @Nested
    @DisplayName("precisaRepor")
    class PrecisaRepor {

        @Test
        void avisaQuandoEstoqueAtingeOMinimo() {
            assertTrue(RegrasEstoque.precisaRepor(5, 5));
        }

        @Test
        void naoAvisaQuandoEstoqueAcimaDoMinimo() {
            assertFalse(RegrasEstoque.precisaRepor(6, 5));
        }

        @Test
        void semMinimoDefinidoNuncaAvisa() {
            assertFalse(RegrasEstoque.precisaRepor(0, 0));
        }

        @Test
        void rejeitaEstoqueNegativo() {
            assertThrows(IllegalArgumentException.class, () -> RegrasEstoque.precisaRepor(-1, 5));
        }
    }
```
Com eles, `service` volta a 100% de ramos e o pipeline fica verde (48 unitários).

## Tabela de evidências (preencher e levar para o relatório)

| Execução | Branch/PR | Commit | Autor | Link da execução | Duração | Gate que falhou | Testes | Cobertura (linhas / ramos service) |
|----------|-----------|--------|-------|------------------|---------|-----------------|--------|-----------------------------------|
| 1 Aprovada | `main` | | | | | — | 44/44 + 9/9 | |
| 2 Reprovada | PR # | | | | | Gate 3 | 43/44 + 0/9 | — |
| 3 Corrigida | PR # | | | | | — | 44/44 + 9/9 | |

## Para a defesa oral
Cada integrante deve saber explicar: o que é cada gate e por que o limite escolhido; por que a UI
fica fora da cobertura; por que os testes de integração não rodaram na execução 2; o que o
`FOR UPDATE` resolve; por que os testes de integração só rodam em banco `_test`; e como a senha
do banco do pipeline é gerada sem ficar no repositório.
