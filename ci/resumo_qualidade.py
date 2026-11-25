#!/usr/bin/env python3
"""Gera o resumo em Markdown dos quality gates a partir dos relatórios do Maven.

Usado pelo pipeline do GitHub Actions (passo "Resumo dos quality gates"), que grava a
saída na aba Summary da execução ($GITHUB_STEP_SUMMARY).
Também pode ser executado localmente depois de um "mvn verify":
python3 ci/resumo_qualidade.py

Lê (quando existirem):
  target/surefire-reports/TEST-*.xml   testes unitários
  target/failsafe-reports/TEST-*.xml   testes de integração
  target/site/jacoco/jacoco.csv        cobertura
  target/checkstyle-result.xml         análise estática
O resultado de cada gate vem das variáveis de ambiente GATE_* definidas no workflow.
"""

import csv
import glob
import os
import xml.etree.ElementTree as ET

ICONES = {"success": "✅ aprovado", "failure": "❌ reprovado", "cancelled": "⚪ cancelado",
          "skipped": "⏭️ não executado", "": "⏭️ não executado"}

GATES = [
    ("1 - Build", "GATE_BUILD", "código compila e o jar é gerado"),
    ("2 - Análise estática", "GATE_ESTATICA", "nenhuma violação das regras de config/checkstyle.xml"),
    ("5 - Dependências", "GATE_DEPENDENCIAS", "nenhuma vulnerabilidade HIGH/CRITICAL nas dependências (Trivy)"),
    ("3 - Testes", "GATE_TESTES", "100% dos testes unitários e de integração passam"),
    ("4 - Cobertura", "GATE_COBERTURA", "linhas ≥ 80% (model, service, db) e ramos de service ≥ 90%"),
]


def status_do_gate(variavel):
    """Resultado do passo do gate (success/failure/skipped); vazio = não executado."""
    return os.environ.get(variavel, "").strip()


def ler_testes(pasta):
    """Soma os resultados dos arquivos TEST-*.xml e coleta os testes que falharam."""
    total = falhas = erros = ignorados = 0
    tempo = 0.0
    quebrados = []
    for arquivo in sorted(glob.glob(os.path.join(pasta, "TEST-*.xml"))):
        try:
            raiz = ET.parse(arquivo).getroot()
        except ET.ParseError:
            continue
        total += int(raiz.get("tests", 0))
        falhas += int(raiz.get("failures", 0))
        erros += int(raiz.get("errors", 0))
        ignorados += int(raiz.get("skipped", 0))
        tempo += float(raiz.get("time", 0) or 0)
        for caso in raiz.iter("testcase"):
            problema = caso.find("failure")
            if problema is None:
                problema = caso.find("error")
            if problema is not None:
                classe = caso.get("classname", "").split(".")[-1]
                mensagem = (problema.get("message") or problema.get("type") or "").strip()
                quebrados.append((f"{classe}.{caso.get('name')}", mensagem.splitlines()[0][:150] if mensagem else ""))
    if total == 0:
        return None
    return {"total": total, "falhas": falhas, "erros": erros, "ignorados": ignorados,
            "tempo": tempo, "quebrados": quebrados}


def ler_cobertura(caminho):
    """Calcula cobertura de linhas e ramos por pacote a partir do jacoco.csv."""
    if not os.path.exists(caminho):
        return None
    pacotes = {}
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            p = pacotes.setdefault(linha["PACKAGE"], [0, 0, 0, 0])
            p[0] += int(linha["LINE_COVERED"])
            p[1] += int(linha["LINE_MISSED"])
            p[2] += int(linha["BRANCH_COVERED"])
            p[3] += int(linha["BRANCH_MISSED"])
    return pacotes


def pct(coberto, perdido):
    total = coberto + perdido
    return "—" if total == 0 else f"{100.0 * coberto / total:.1f}%"


def ler_checkstyle(caminho):
    if not os.path.exists(caminho):
        return None
    violacoes = []
    for arquivo in ET.parse(caminho).getroot().iter("file"):
        nome = arquivo.get("name", "")
        nome = nome[nome.find("src/"):] if "src/" in nome else os.path.basename(nome)
        for erro in arquivo.iter("error"):
            violacoes.append(f"{nome}:{erro.get('line')} — {erro.get('message')}")
    return violacoes


def main():
    linhas = ["## Resultado dos Quality Gates", "",
              "| Gate | Critério de aprovação | Resultado |", "|------|-----------------------|-----------|"]
    for nome, variavel, criterio in GATES:
        status = status_do_gate(variavel)
        linhas.append(f"| {nome} | {criterio} | {ICONES.get(status, status)} |")
    linhas.append("")

    linhas.append("### Testes")
    for rotulo, pasta in (("Unitários (surefire)", "target/surefire-reports"),
                          ("Integração (failsafe)", "target/failsafe-reports")):
        r = ler_testes(pasta)
        if r is None:
            linhas.append(f"- **{rotulo}:** não executados")
            continue
        aprovados = r["total"] - r["falhas"] - r["erros"] - r["ignorados"]
        linhas.append(f"- **{rotulo}:** {aprovados}/{r['total']} aprovados, {r['falhas']} falhas, "
                      f"{r['erros']} erros, {r['ignorados']} ignorados ({r['tempo']:.1f}s)")
        for teste, mensagem in r["quebrados"]:
            linhas.append(f"  - ❌ `{teste}` — {mensagem}")
    linhas.append("")

    cobertura = ler_cobertura("target/site/jacoco/jacoco.csv")
    linhas.append("### Cobertura (JaCoCo)")
    if cobertura is None:
        linhas.append("Relatório de cobertura não gerado.")
    else:
        linhas += ["| Pacote | Linhas | Ramos |", "|--------|--------|-------|"]
        soma = [0, 0, 0, 0]
        for pacote in sorted(cobertura):
            c = cobertura[pacote]
            soma = [a + b for a, b in zip(soma, c)]
            linhas.append(f"| `{pacote}` | {pct(c[0], c[1])} | {pct(c[2], c[3])} |")
        linhas.append(f"| **Total** | **{pct(soma[0], soma[1])}** | **{pct(soma[2], soma[3])}** |")
    linhas.append("")

    violacoes = ler_checkstyle("target/checkstyle-result.xml")
    linhas.append("### Análise estática (Checkstyle)")
    if violacoes is None:
        linhas.append("Análise não executada.")
    elif not violacoes:
        linhas.append("Nenhuma violação encontrada.")
    else:
        linhas.append(f"{len(violacoes)} violação(ões):")
        linhas += [f"- `{v}`" for v in violacoes[:20]]
    linhas.append("")
    linhas.append("Relatórios completos no artefato **evidencias-qualidade** desta execução.")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
