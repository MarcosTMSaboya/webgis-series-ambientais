"""Importa a coluna WaveHeight sem alterar a planilha de origem."""
import argparse
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

BASE = Path(__file__).resolve().parent
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def importar(origem, unidade="m"):
    with zipfile.ZipFile(origem) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(t.itertext()) for t in ET.fromstring(
                z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        linhas = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall("m:sheetData/m:row", NS)
        registros = []
        for linha in linhas:
            registro = {}
            for celula in linha:
                coluna = re.sub(r"\d", "", celula.attrib["r"])
                valor = celula.find("m:v", NS)
                texto = valor.text if valor is not None else "".join(celula.itertext())
                registro[coluna] = strings[int(texto)] if celula.get("t") == "s" else texto
            registros.append(registro)
    cabecalho = {v: k for k, v in registros[0].items()}
    pontos = json.loads((BASE / "Pontos_Clean.geojson").read_text(encoding="utf-8"))["features"]
    coordenadas = {p["properties"]["name"].strip().upper(): p["geometry"]["coordinates"][:2] for p in pontos}
    # Somente aliases com identificador explícito no nome do ponto.
    aliases = {
        "SGOM_A2": "A2 - Sebastião Gomes", "Arquipelago_A4": "A4 - Portinho Norte",
        "PA2-A8": "A8 - PA2", "PLES_A1": "A1 - Pedra de Leste",
        "Rodoraso_A5": "A5 - Rodoraso", "PAB3": "A3 - PAB3 (Validado 2026)",
        "PAB5": "PAB 5", "Esquecidos_Sul2_B6": "B6 (Validado 2026)",
        "Esquecidos_Norte_B2": "B2 100326 (Validado 2026)",
        "Esquecidos_Central_B3": "ES B3 (Validado 2026)",
        "Esquecidos_rodolito_B1": "B1 (Validado 2026)",
        "Esquecidos_Sul_B4": "B4 (Validado 2026)",
        "Buraca": "Buraca Rasa", "Arangueira": "Arenguera",
    }
    sitios = {}
    for registro in registros[1:]:
        def campo(nome):
            return registro.get(cabecalho[nome], "")
        sitio = campo("Sitio").strip()
        mes = f'{int(campo("Ano")):04d}-{int(campo("Mes")):02d}'
        valor = float(campo("WaveHeight")) if campo("WaveHeight") else None
        if valor is not None and not math.isfinite(valor):
            valor = None
        nome_ponto = aliases.get(sitio, sitio)
        item = sitios.setdefault(sitio, {"ponto_mapa": nome_ponto,
            "coordenadas": coordenadas.get(nome_ponto.upper()), "valores": {}})
        if mes in item["valores"]:
            raise ValueError(f"Registro duplicado: {sitio}, {mes}")
        item["valores"][mes] = valor
    resultado = {"fonte": Path(origem).name, "variavel": "WaveHeight", "unidade": unidade,
                 "coordenadas_fonte": "Pontos_Clean.geojson, associação por nome ou identificador explícito; latitude da planilha desconsiderada",
                 "sitios": sitios}
    destino = BASE / "Dados" / "waveheight.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meses = sorted({m for s in sitios.values() for m in s["valores"]})
    print(json.dumps({"registros": len(registros)-1, "sitios": len(sitios), "primeiro_mes": meses[0],
                      "ultimo_mes": meses[-1], "sem_coordenadas": [s for s, d in sitios.items() if d["coordenadas"] is None]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("planilha")
    parser.add_argument("--unidade", default="m")
    args = parser.parse_args()
    importar(args.planilha, args.unidade)
