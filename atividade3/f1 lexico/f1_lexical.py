#!/usr/bin/env python3
"""F1 lexical por tokens - Atividade 3 (Vanna, versoes A e B).

Uso:
    python f1_lexical.py
    python f1_lexical.py --referencias referencias.csv --saidas saidas_brutas.csv --tau 0.5

Normalizacao: NFC + casefold. Tokens: sequencias \\w+ (palavras e numeros).
Intersecao: multiconjuntos (padrao) ou conjuntos (--modo conjuntos).

Entradas (CSV com ; ou ,):
    referencias.csv    -> colunas caso, referencia
    saidas_brutas.csv  -> colunas caso, versao, resposta

Saidas:
    tabela_f1.csv      -> abre direto no Excel/Sheets em portugues
    tabela_f1.md       -> tabela e resumo para colar no relatorio

Somente biblioteca padrao do Python 3.
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from fractions import Fraction
from pathlib import Path
from statistics import mean, median

CASOS = ["CT01", "CT02", "CT03", "CT04", "CT05", "CT06"]
VERSOES = ["A", "B"]


def tokenizar(texto):
    return re.findall(r"\w+", unicodedata.normalize("NFC", texto).casefold())


def calcular(resposta, referencia, modo="multiconjuntos"):
    """Retorna (Tc, Tr, Tg, P, R, F1). P, R e F1 sao fracoes exatas."""
    toks_resp = tokenizar(resposta)
    toks_ref = tokenizar(referencia)
    if modo == "conjuntos":
        toks_resp = sorted(set(toks_resp))
        toks_ref = sorted(set(toks_ref))
    tc = sum((Counter(toks_resp) & Counter(toks_ref)).values())
    tr, tg = len(toks_resp), len(toks_ref)
    if tc == 0:  # sem sobreposicao ou resposta vazia
        return tc, tr, tg, Fraction(0), Fraction(0), Fraction(0)
    p = Fraction(tc, tr)
    r = Fraction(tc, tg)
    return tc, tr, tg, p, r, 2 * p * r / (p + r)


def ler_csv(caminho, colunas):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        primeira = f.readline()
        f.seek(0)
        sep = ";" if primeira.count(";") >= primeira.count(",") else ","
        leitor = csv.DictReader(f, delimiter=sep)
        faltando = set(colunas) - set(leitor.fieldnames or [])
        if faltando:
            sys.exit(f"ERRO: {caminho} sem a(s) coluna(s): {sorted(faltando)}")
        return list(leitor)


def carregar_referencias(caminho):
    refs = {}
    for linha in ler_csv(caminho, ["caso", "referencia"]):
        caso = linha["caso"].strip().upper()
        if caso in refs:
            sys.exit(f"ERRO: referencia duplicada para {caso}")
        if not tokenizar(linha["referencia"] or ""):
            sys.exit(f"ERRO: referencia sem tokens em {caso}; corrija o caso.")
        refs[caso] = linha["referencia"]
    faltando = [c for c in CASOS if c not in refs]
    if faltando:
        sys.exit(f"ERRO: faltam referencias de {faltando}")
    return refs


def carregar_saidas(caminho):
    saidas = {}
    for linha in ler_csv(caminho, ["caso", "versao", "resposta"]):
        chave = (linha["caso"].strip().upper(), linha["versao"].strip().upper())
        if chave not in {(c, v) for c in CASOS for v in VERSOES}:
            sys.exit(f"ERRO: caso/versao invalido: {chave}")
        if chave in saidas:
            sys.exit(f"ERRO: saida duplicada para {chave}")
        saidas[chave] = linha["resposta"] or ""
    faltando = [k for k in ((c, v) for c in CASOS for v in VERSOES) if k not in saidas]
    if faltando:
        sys.exit(f"ERRO: faltam saidas de {faltando}. Registre a falha com resposta vazia.")
    return saidas


def br(valor, casas=4):
    return f"{float(valor):.{casas}f}".replace(".", ",")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--referencias", default="referencias.csv")
    ap.add_argument("--saidas", default="saidas_brutas.csv")
    ap.add_argument("--tau", type=Fraction, default=Fraction(1, 2))
    ap.add_argument("--modo", choices=["multiconjuntos", "conjuntos"], default="multiconjuntos")
    ap.add_argument("--destino", default=".")
    args = ap.parse_args()

    refs = carregar_referencias(args.referencias)
    saidas = carregar_saidas(args.saidas)

    linhas = []
    for versao in VERSOES:
        for caso in CASOS:
            resposta = saidas[(caso, versao)]
            tc, tr, tg, p, r, f1 = calcular(resposta, refs[caso], args.modo)
            linhas.append({
                "caso": caso, "versao": versao, "Tc": tc, "Tr": tr, "Tg": tg,
                "P": p, "R": r, "F1": f1,
                "sinal": "APROVA" if f1 >= args.tau else "REPROVA",
                "obs": "resposta vazia/falha: F1 = 0" if tr == 0 else "",
            })

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    cab = ["caso", "versao", "tokens_comuns", "tokens_resposta", "tokens_referencia",
           "P", "R", "F1", "sinal_automatico", "observacao"]

    def valores(l):
        return [l["caso"], l["versao"], l["Tc"], l["Tr"], l["Tg"],
                br(l["P"]), br(l["R"]), br(l["F1"]), l["sinal"], l["obs"]]

    with open(destino / "tabela_f1.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cab)
        w.writerows(valores(l) for l in linhas)

    resumo = []
    for versao in VERSOES:
        grupo = [l for l in linhas if l["versao"] == versao]
        f1s = [float(l["F1"]) for l in grupo]
        aprov = sum(l["sinal"] == "APROVA" for l in grupo)
        resumo.append([versao, br(mean(f1s)), br(median(f1s)), f"{aprov}/6"])

    with open(destino / "tabela_f1.md", "w", encoding="utf-8") as f:
        f.write(f"Parametros: NFC, casefold, tokens \\w+, {args.modo}, "
                f"tau = {br(args.tau, 2)} (aprova se F1 >= tau).\n\n")
        f.write("| " + " | ".join(cab) + " |\n|" + "---|" * len(cab) + "\n")
        for l in linhas:
            f.write("| " + " | ".join(str(v) for v in valores(l)) + " |\n")
        f.write("\n| versao | F1 medio | F1 mediano | aprovacao automatica |\n|---|---|---|---|\n")
        for r in resumo:
            f.write("| " + " | ".join(r) + " |\n")

    for l in linhas:
        print(f'{l["caso"]} {l["versao"]}  F1={br(l["F1"])}  {l["sinal"]}  {l["obs"]}')
    for r in resumo:
        print(f"Versao {r[0]}: F1 medio={r[1]} | mediana={r[2]} | automatico aprova {r[3]}")
    vazias = sum(1 for l in linhas if l["Tr"] == 0)
    if vazias:
        print(f"ATENCAO: {vazias} resposta(s) vazia(s), contadas como F1 = 0.")


if __name__ == "__main__":
    main()
