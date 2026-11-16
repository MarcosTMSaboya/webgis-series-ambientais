"""Consultas pontuais de WaveHeight, sem interpolação espacial."""
from functools import lru_cache
import json
import math
from pathlib import Path
from fastapi import HTTPException

CAMINHO = Path(__file__).resolve().parent / "Dados" / "waveheight.json"


@lru_cache(maxsize=1)
def dados_waveheight():
    return json.loads(CAMINHO.read_text(encoding="utf-8"))


def meses_planilha():
    return sorted({mes for sitio in dados_waveheight()["sitios"].values() for mes in sitio["valores"]})


def distancia(lat, lon, coordenadas):
    x, y = coordenadas
    a, b = math.radians(lat), math.radians(y)
    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(x-lon)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def selecionar_sitio(lat, lon, sitio=None):
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(400, "Coordenadas inválidas.")
    sitios = dados_waveheight()["sitios"]
    if sitio is not None:
        if sitio not in sitios:
            raise HTTPException(404, "Sítio de WaveHeight não encontrado.")
        item = sitios[sitio]
        return sitio, item, distancia(lat, lon, item["coordenadas"]) if item["coordenadas"] else None
    candidatos = [(distancia(lat, lon, s["coordenadas"]), nome, s)
                  for nome, s in sitios.items() if s["coordenadas"] is not None]
    km, nome, item = min(candidatos, key=lambda candidato: candidato[0])
    return nome, item, km


def metadados(nome, item, km):
    fonte = dados_waveheight()
    coords = item["coordenadas"]
    return {"produto": "WAVEHEIGHT", "variavel": "WaveHeight", "descricao": "Altura de onda",
            "unidade": fonte["unidade"], "sitio": nome, "distancia_sitio_km": km,
            "sitio_utilizado": {"nome": nome, "latitude": coords[1], "longitude": coords[0]} if coords else {"nome": nome},
            "pixel_utilizado": None, "distancia_pixel_km": None,
            "arquivo": fonte["fonte"], "metodo": "Sítio mais próximo; sem interpolação"}


def valor_planilha(data, lat, lon, sitio=None):
    nome, item, km = selecionar_sitio(lat, lon, sitio)
    resposta = metadados(nome, item, km)
    resposta.update(data=data, valor=item["valores"].get(data))
    if data not in item["valores"]:
        resposta["erro"] = "Mês sem registro de WaveHeight para este sítio."
    return resposta


def serie_planilha(lat, lon, inicio, fim, sitio=None):
    nome, item, km = selecionar_sitio(lat, lon, sitio)
    serie = [{"data": mes, "valor": valor} for mes, valor in sorted(item["valores"].items()) if inicio <= mes <= fim]
    return {**metadados(nome, item, km), "inicio": inicio, "fim": fim,
            "coordenada_solicitada": {"latitude": lat, "longitude": lon},
            "quantidade_meses": len(serie), "serie": serie}


def catalogo_planilha():
    meses = meses_planilha()
    dados = dados_waveheight()
    return {"quantidade_meses": len(meses), "primeiro_mes": meses[0], "ultimo_mes": meses[-1],
            "quantidade_sitios": len(dados["sitios"]), "tipo": "sitios", "unidade": dados["unidade"],
            "sitios_sem_coordenadas": [nome for nome, s in dados["sitios"].items() if s["coordenadas"] is None],
            "variaveis": [{"nome": "WaveHeight", "descricao": "Altura de onda", "unidade": dados["unidade"]}]}


# A API passa a consultar a grade original para qualquer ponto do mapa.
# As funções *_planilha preservam a importação anterior para comparação.
from waveheight_grid import (meses_grid as meses_waveheight, valor_grid as valor_waveheight,
                             serie_grid as serie_waveheight, catalogo_grid as catalogo_waveheight)
