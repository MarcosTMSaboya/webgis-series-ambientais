"""Verificação integral de uma exportação real, sem reter o CSV descompactado."""
import csv
from io import TextIOWrapper
import json
from pathlib import Path
import zipfile
from app import consultar_serie
from coral_reef_watch import valor_no_ponto
from exportacao import gerar_zip, PRODUTOS_EXPORTAR, COLUNAS


def verificar(destino):
    meta = gerar_zip(destino, lambda etapa, i, total: print(
        f"{etapa}: {i}/{total}", flush=True) if i % 50 == 0 else None)
    contagem = 0
    ids = set()
    amostras = {}
    with zipfile.ZipFile(destino) as z:
        assert z.testzip() is None
        with TextIOWrapper(z.open("series_temporais.csv"), encoding="utf-8-sig", newline="") as texto:
            for r in csv.DictReader(texto, delimiter=";"):
                contagem += 1
                ids.add(int(r["ponto_id"]))
                if int(r["ponto_id"]) in (1, 191, 382) and r["mes"] in ("1940-01", "2020-01", "2026-05"):
                    amostras[(r["ponto_id"], r["mes"])] = r
        assert contagem == meta["linhas_series"], contagem
        assert len(ids) == meta["pontos"] == 382
        for r in amostras.values():
            for produto, coluna in zip(PRODUTOS_EXPORTAR, COLUNAS):
                if produto == "CRW_DHW":
                    resposta = valor_no_ponto(
                        produto, float(r["latitude"]), float(r["longitude"]), r["mes"])
                    esperado = resposta["valor"]
                else:
                    resposta = consultar_serie(
                        produto, float(r["latitude"]), float(r["longitude"]), r["mes"], r["mes"])
                    esperado = resposta["serie"][0]["valor"] if resposta["serie"] else None
                assert (float(r[coluna]) if r[coluna] else None) == esperado, (r["ponto_id"], r["mes"], produto)
        with TextIOWrapper(z.open("pixels_utilizados.csv"), encoding="utf-8-sig") as texto:
            assert sum(1 for _ in csv.DictReader(texto, delimiter=";")) == 382*len(PRODUTOS_EXPORTAR)
        assert len(json.loads(z.read("pontos.geojson"))["features"]) == 382
    print(json.dumps({"arquivo": str(destino), "linhas": contagem, "pontos": len(ids),
                      "tamanho_mb": round(Path(destino).stat().st_size/1e6, 2),
                      "amostras_conferidas": len(amostras)*len(PRODUTOS_EXPORTAR)}), flush=True)


if __name__ == "__main__":
    verificar(Path(__file__).resolve().parent / "Dados" / "exportacoes" / "series_completas_verificadas.zip")
