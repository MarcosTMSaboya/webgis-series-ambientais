"""Altura significativa de ondas: consulta à grade original do NetCDF."""
from functools import lru_cache
from io import BytesIO
import json
import math
from pathlib import Path
import re
import numpy as np
import xarray as xr
from fastapi import HTTPException
from escalas import escala_raster

BASE = Path(__file__).resolve().parent
FONTE = BASE / "Dados" / "WAVEHEIGHT" / "waveheight.nc"


@lru_cache(maxsize=1)
def grade():
    # Arquivo pequeno (~3 MB decodificado): ler uma vez e fechar o NetCDF.
    with xr.open_dataset(FONTE, engine="netcdf4", mask_and_scale=True) as ds:
        meses = np.datetime_as_string(ds.valid_time.values, unit="M").tolist()
        if len(set(meses)) != len(meses):
            raise ValueError("WaveHeight precisa ter exatamente um registro por mês.")
        return {"meses": meses, "lat": ds.latitude.values.copy(), "lon": ds.longitude.values.copy(),
                "valores": ds.swh.transpose("valid_time", "latitude", "longitude").values.copy(),
                "unidade": ds.swh.attrs["units"], "descricao": ds.swh.attrs["long_name"]}


@lru_cache(maxsize=1)
def sitios_mapa():
    return json.loads((BASE / "Pontos_Clean.geojson").read_text(encoding="utf-8"))["features"]


def meses_grid():
    return grade()["meses"]


def validar_mes(mes):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", mes):
        raise HTTPException(400, "Data deve usar o formato AAAA-MM.")


def limites():
    g = grade()
    return {"sul": float(g["lat"].min() - .25), "norte": float(g["lat"].max() + .25),
            "oeste": float(g["lon"].min() - .25), "leste": float(g["lon"].max() + .25)}


def pixel(lat, lon, sitio=None):
    if sitio is not None:
        encontrados = [f for f in sitios_mapa() if f["properties"]["name"].casefold() == sitio.casefold()]
        if not encontrados:
            # Compatibilidade com identificadores da planilha já associados ao mapa.
            legado = json.loads((BASE / "Dados" / "waveheight.json").read_text(encoding="utf-8"))["sitios"].get(sitio)
            if not legado or legado["coordenadas"] is None:
                raise HTTPException(404, "Sítio sem coordenadas cadastradas. Consulte pelo nome do ponto no mapa.")
            lon, lat = legado["coordenadas"]
        else:
            lon, lat = encontrados[0]["geometry"]["coordinates"][:2]
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(400, "Coordenadas inválidas.")
    b = limites()
    if not b["sul"] <= lat <= b["norte"] or not b["oeste"] <= lon <= b["leste"]:
        raise HTTPException(404, "Coordenada fora da cobertura do NetCDF de WaveHeight.")
    g = grade()
    def vizinho(coords, valor):
        diferenca = abs(coords - valor)
        candidatos = np.flatnonzero(diferenca == diferenca.min())
        return int(candidatos[np.argmax(coords[candidatos])])
    y, x = vizinho(g["lat"], lat), vizinho(g["lon"], lon)
    py, px = float(g["lat"][y]), float(g["lon"][x])
    a, b = math.radians(lat), math.radians(py)
    h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(px-lon)/2)**2
    km = 6371 * 2 * math.asin(min(1, math.sqrt(h)))
    return y, x, {"produto": "WAVEHEIGHT", "variavel": "swh", "descricao": "Altura significativa de ondas (vento e swell)",
        "unidade": g["unidade"], "arquivo": FONTE.name, "fonte_tipo": "netcdf", "resolucao_graus": .5,
        "pixel_utilizado": {"latitude": py, "longitude": px}, "distancia_pixel_km": km,
        "coordenada_solicitada": {"latitude": lat, "longitude": lon},
        "metodo": "Pixel mais próximo da grade original; sem interpolação"}


def valor_grid(data, lat, lon, sitio=None):
    validar_mes(data)
    y, x, meta = pixel(lat, lon, sitio)
    g = grade()
    if data not in g["meses"]:
        return {**meta, "data": data, "valor": None, "erro": "Mês sem registro de WaveHeight no NetCDF."}
    valor = float(g["valores"][g["meses"].index(data), y, x])
    return {**meta, "data": data, "valor": valor if np.isfinite(valor) else None}


def serie_grid(lat, lon, inicio, fim, sitio=None):
    validar_mes(inicio)
    validar_mes(fim)
    if inicio > fim:
        raise HTTPException(400, "Início deve ser anterior ou igual ao fim.")
    y, x, meta = pixel(lat, lon, sitio)
    serie = [{"data": mes, "valor": float(v) if np.isfinite(v) else None}
             for mes, v in zip(grade()["meses"], grade()["valores"][:, y, x]) if inicio <= mes <= fim]
    return {**meta, "inicio": inicio, "fim": fim, "quantidade_meses": len(serie), "serie": serie}


def catalogo_grid():
    g = grade()
    return {"tipo": "grade", "quantidade_arquivos": 1, "quantidade_meses": len(g["meses"]),
        "primeiro_mes": g["meses"][0], "ultimo_mes": g["meses"][-1], "unidade": g["unidade"],
        "resolucao_graus": .5, "quantidade_pontos_mapa": len(sitios_mapa()), "bounds": limites(),
        "variaveis": [{"nome": "swh", "descricao": g["descricao"], "unidade": g["unidade"]}]}


def pontos_grid(data):
    validar_mes(data)
    features = []
    for f in sitios_mapa():
        lon, lat = f["geometry"]["coordinates"][:2]
        try:
            resposta = valor_grid(data, lat, lon)
        except HTTPException as erro:
            resposta = {"valor": None, "erro": erro.detail}
        features.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "sitio": f["properties"]["name"], "data": data, "unidade": grade()["unidade"], **resposta}})
    return {"type": "FeatureCollection", "features": features}


def raster_info_grid(data):
    validar_mes(data)
    if data not in meses_grid():
        raise HTTPException(404, "Mês sem registro de WaveHeight no NetCDF.")
    return {"produto": "WAVEHEIGHT", "data": data, "bounds": limites(), "unidade": grade()["unidade"],
            "resolucao_graus": .5, "minimo": 0, "maximo": 3,
            "escala": escala_raster("WAVEHEIGHT", grade()["valores"][meses_grid().index(data)])}


@lru_cache(maxsize=24)
def raster_grid(data):
    from matplotlib import colormaps
    from PIL import Image
    raster_info_grid(data)
    g = grade()
    matriz = g["valores"][g["meses"].index(data)]
    if g["lat"][0] < g["lat"][-1]:
        matriz = np.flipud(matriz)
    if g["lon"][0] > g["lon"][-1]:
        matriz = np.fliplr(matriz)
    valido = np.isfinite(matriz)
    rgba = colormaps["viridis"](np.clip(np.nan_to_num(matriz) / 3, 0, 1))
    rgba[..., 3] = valido.astype(float)
    imagem = Image.fromarray((rgba*255).astype(np.uint8))
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()
