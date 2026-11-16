"""Acesso aos produtos diários e resumos mensais do NOAA Coral Reef Watch."""
import calendar
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import io
import math
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
from fastapi import HTTPException
from matplotlib import colormaps
from PIL import Image

from escalas import escala_raster


BASE_URL = "https://coastwatch.noaa.gov/erddap/griddap"
RESOLUCAO_GRAUS = 0.05
MARGEM_GRAUS = 0.25
CACHE_SEGUNDOS = 6 * 60 * 60

PRODUTOS_CRW = {
    "CRW_DHW": {
        "dataset": "noaacrwdhwDaily",
        "variavel": "degree_heating_week",
        "descricao": "Degree Heating Week",
    },
    "CRW_HOTSPOT": {
        "dataset": "noaacrwhotspotDaily",
        "variavel": "hotspot",
        "descricao": "Coral Bleaching HotSpot",
    },
}


@dataclass(frozen=True)
class GradeAtual:
    produto: str
    data: str
    latitudes: np.ndarray
    longitudes: np.ndarray
    valores: np.ndarray
    dias_amostrados: int = 1


_cache: dict[str, tuple[float, GradeAtual]] = {}
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _limites_consulta() -> tuple[float, float, float, float]:
    caminho = Path(__file__).resolve().parent / "Pontos_Clean.geojson"
    import json

    geojson = json.loads(caminho.read_text(encoding="utf-8"))
    coordenadas = [
        feature["geometry"]["coordinates"][:2]
        for feature in geojson["features"]
        if feature.get("geometry", {}).get("type") == "Point"
    ]
    if not coordenadas:
        raise RuntimeError("Pontos_Clean.geojson não contém pontos para recortar os dados CRW.")

    longitudes, latitudes = zip(*coordenadas)
    return (
        min(latitudes) - MARGEM_GRAUS,
        max(latitudes) + MARGEM_GRAUS,
        min(longitudes) - MARGEM_GRAUS,
        max(longitudes) + MARGEM_GRAUS,
    )


def _url_consulta(produto: str, data: str | None = None) -> str:
    config = PRODUTOS_CRW[produto]
    lat_min, lat_max, lon_min, lon_max = _limites_consulta()
    if data is None or data == "atual":
        intervalo = "[(last)]"
    else:
        if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", data):
            raise HTTPException(400, "A data CRW deve ser 'atual' ou estar no formato YYYY-MM.")
        ano, mes = (int(parte) for parte in data.split("-"))
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        inicio = f"{data}-01T00:00:00Z"
        fim = f"{data}-{ultimo_dia:02d}T23:59:59Z"
        intervalo = f"[({inicio}):({fim})]"
    expressao = (
        f"{config['variavel']}{intervalo}"
        f"[({lat_min:.3f}):({lat_max:.3f})]"
        f"[({lon_min:.3f}):({lon_max:.3f})]"
    )
    return (
        f"{BASE_URL}/{config['dataset']}.csvp?"
        f"{quote(expressao, safe='[]():.,-')}"
    )


def _meses_periodo(inicio: str, fim: str) -> list[str]:
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", inicio) or not re.fullmatch(
        r"20\d{2}-(0[1-9]|1[0-2])", fim
    ):
        raise HTTPException(400, "O período CRW deve usar o formato YYYY-MM.")
    if inicio > fim:
        raise HTTPException(400, "O início do período CRW deve ser anterior ao fim.")
    ano, mes = (int(parte) for parte in inicio.split("-"))
    ano_fim, mes_fim = (int(parte) for parte in fim.split("-"))
    meses = []
    while (ano, mes) <= (ano_fim, mes_fim):
        meses.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            ano += 1
            mes = 1
    return meses


def _url_serie_ponto(produto: str, latitude: float, longitude: float, inicio: str, fim: str) -> str:
    config = PRODUTOS_CRW[produto]
    meses = _meses_periodo(inicio, fim)
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise HTTPException(400, "Latitude inválida para a série CRW.")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise HTTPException(400, "Longitude inválida para a série CRW.")

    primeiro_ano, primeiro_mes = (int(parte) for parte in meses[0].split("-"))
    ultimo_ano, ultimo_mes = (int(parte) for parte in meses[-1].split("-"))
    ultimo_dia = calendar.monthrange(ultimo_ano, ultimo_mes)[1]
    lat_indice = math.floor((89.975 - latitude) / RESOLUCAO_GRAUS + 0.5 - 1e-10)
    lon_indice = math.floor((longitude + 179.975) / RESOLUCAO_GRAUS + 0.5 - 1e-10)
    pixel_lat = 89.975 - lat_indice * RESOLUCAO_GRAUS
    pixel_lon = -179.975 + lon_indice * RESOLUCAO_GRAUS
    primeiro_dia = f"{primeiro_ano:04d}-{primeiro_mes:02d}-01T00:00:00Z"
    ultimo_dia_consulta = f"{ultimo_ano:04d}-{ultimo_mes:02d}-{ultimo_dia:02d}T23:59:59Z"
    expressao = (
        f"{config['variavel']}[({primeiro_dia}):({ultimo_dia_consulta})]"
        f"[({pixel_lat:.3f}):({pixel_lat:.3f})][({pixel_lon:.3f}):({pixel_lon:.3f})]"
    )
    return f"{BASE_URL}/{config['dataset']}.csvp?{quote(expressao, safe='[]():.,-')}"


def _baixar_csv(
    url: str, produto: str, periodo: str, timeout: int = 45, tentativas: int = 3
) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "text/csv",
            "User-Agent": "WebGIS-Abrolhos/1.0 (NOAA Coral Reef Watch data client)",
        },
    )
    for tentativa in range(tentativas):
        try:
            with urlopen(request, timeout=timeout) as resposta:
                conteudo = resposta.read(50_000_001)
            break
        except HTTPError as erro:
            if erro.code not in {502, 503, 504} or tentativa == tentativas - 1:
                raise HTTPException(
                    502, f"NOAA ERDDAP respondeu HTTP {erro.code} para {produto} ({periodo})."
                ) from erro
            time.sleep(2 ** tentativa)
        except URLError as erro:
            if tentativa == tentativas - 1:
                raise HTTPException(
                    502, f"Não foi possível acessar NOAA ERDDAP para {produto} ({periodo}): {erro.reason}"
                ) from erro
            time.sleep(2 ** tentativa)
        except TimeoutError as erro:
            if tentativa == tentativas - 1:
                raise HTTPException(
                    504, f"Tempo esgotado ao consultar NOAA ERDDAP para {produto} ({periodo})."
                ) from erro
            time.sleep(2 ** tentativa)
    if len(conteudo) > 50_000_000:
        raise HTTPException(502, f"A resposta NOAA para {produto} ({periodo}) excedeu 50 MB.")
    return conteudo


def _ler_grade(produto: str, data: str | None = None) -> GradeAtual:
    produto = produto.upper()
    if produto not in PRODUTOS_CRW:
        raise HTTPException(400, "Produto CRW deve ser CRW_DHW ou CRW_HOTSPOT.")
    periodo = f" ({data})" if data and data != "atual" else ""
    conteudo = _baixar_csv(_url_consulta(produto, data), produto, periodo or "atual")

    try:
        leitor = csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig")))
        linhas = list(leitor)
        if not linhas or not {"time (UTC)", "latitude (degrees_north)",
                              "longitude (degrees_east)"}.issubset(leitor.fieldnames or []):
            raise ValueError("A resposta não contém os campos esperados.")

        chave_valor = next(
            chave for chave in linhas[0]
            if chave.startswith(PRODUTOS_CRW[produto]["variavel"] + " ")
        )
        latitudes = np.array(
            sorted({float(linha["latitude (degrees_north)"]) for linha in linhas}, reverse=True),
            dtype=float,
        )
        longitudes = np.array(
            sorted({float(linha["longitude (degrees_east)"]) for linha in linhas}),
            dtype=float,
        )
        valores = np.full((len(latitudes), len(longitudes)), np.nan, dtype=float)
        indices_lat = {valor: indice for indice, valor in enumerate(latitudes)}
        indices_lon = {valor: indice for indice, valor in enumerate(longitudes)}
        dias = set()
        for linha in linhas:
            data_linha = linha["time (UTC)"][:10]
            if data is not None and data != "atual" and data_linha[:7] != data:
                continue
            dias.add(data_linha)
            valor = float(linha[chave_valor])
            indice_lat = indices_lat[float(linha["latitude (degrees_north)"])]
            indice_lon = indices_lon[float(linha["longitude (degrees_east)"])]
            if data is None or data == "atual":
                valores[indice_lat, indice_lon] = valor
            elif math.isfinite(valor):
                valores[indice_lat, indice_lon] = np.fmax(valores[indice_lat, indice_lon], valor)
        data_resultado = linhas[0]["time (UTC)"][:10] if data is None or data == "atual" else data
    except (UnicodeDecodeError, csv.Error, KeyError, StopIteration, ValueError) as erro:
        raise HTTPException(502, f"Resposta NOAA inválida para {produto}{periodo}: {erro}") from erro

    if not latitudes.size or not longitudes.size or not np.isfinite(valores).any():
        periodo = data_resultado if data_resultado else "atual"
        raise HTTPException(404, f"NOAA não retornou valores válidos de {produto} para {periodo} na região de Abrolhos.")
    return GradeAtual(produto, data_resultado, latitudes, longitudes, valores, len(dias))


@lru_cache(maxsize=128)
def _serie_historica_cache(produto: str, latitude: float, longitude: float, inicio: str, fim: str) -> dict:
    meses = _meses_periodo(inicio, fim)
    conteudo = _baixar_csv(
        _url_serie_ponto(produto, latitude, longitude, inicio, fim),
        produto,
        f"{inicio} a {fim}",
        timeout=15,
        tentativas=2,
    )
    try:
        leitor = csv.DictReader(io.StringIO(conteudo.decode("utf-8-sig")))
        if not {"time (UTC)", "latitude (degrees_north)", "longitude (degrees_east)"}.issubset(
            leitor.fieldnames or []
        ):
            raise ValueError("A resposta não contém os campos esperados.")
        linhas = list(leitor)
        if not linhas:
            raise ValueError("A resposta não contém observações.")
        chave_valor = next(
            chave for chave in linhas[0]
            if chave.startswith(PRODUTOS_CRW[produto]["variavel"] + " ")
        )
        valores_por_mes: dict[str, float] = {}
        dias_por_mes: dict[str, set[str]] = {}
        pixel_latitude = float(linhas[0]["latitude (degrees_north)"])
        pixel_longitude = float(linhas[0]["longitude (degrees_east)"])
        for linha in linhas:
            data_linha = linha["time (UTC)"]
            mes = data_linha[:7]
            if mes not in meses:
                continue
            valor = float(linha[chave_valor])
            if math.isfinite(valor):
                valores_por_mes[mes] = (
                    max(valores_por_mes[mes], valor) if mes in valores_por_mes else valor
                )
                dias_por_mes.setdefault(mes, set()).add(data_linha[:10])
    except (UnicodeDecodeError, csv.Error, KeyError, StopIteration, ValueError) as erro:
        raise HTTPException(502, f"Resposta NOAA inválida para {produto} ({inicio} a {fim}): {erro}") from erro

    lat1, lat2 = math.radians(latitude), math.radians(pixel_latitude)
    dlat = lat2 - lat1
    dlon = math.radians(pixel_longitude - longitude)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distancia = 6371 * 2 * math.asin(min(1, math.sqrt(a)))
    config = PRODUTOS_CRW[produto]
    return {
        "produto": produto,
        "variavel": config["variavel"],
        "descricao": config["descricao"],
        "inicio": inicio,
        "fim": fim,
        "coordenada_solicitada": {"latitude": latitude, "longitude": longitude},
        "pixel_utilizado": {"latitude": pixel_latitude, "longitude": pixel_longitude},
        "distancia_pixel_km": distancia,
        "unidade": "°C-semanas" if produto == "CRW_DHW" else "°C",
        "resumo": "máximo diário de cada mês",
        "dias_amostrados": sum(len(dias) for dias in dias_por_mes.values()),
        "quantidade_meses": len(meses),
        "serie": [{"data": mes, "valor": valores_por_mes.get(mes)} for mes in meses],
        "fonte": "NOAA Coral Reef Watch, Daily Global 5km v3.1",
    }


def _serie_historica_disco(
    produto: str,
    latitude: float,
    longitude: float,
    inicio: str,
    fim: str,
    erro_noaa: HTTPException,
) -> dict | None:
    meses = _meses_periodo(inicio, fim)
    valores_por_mes: dict[str, float] = {}
    pixel_latitude = None
    pixel_longitude = None
    dias_amostrados = 0

    for mes in meses:
        grade = _carregar_cache_mensal(produto, mes)
        if grade is None:
            continue
        i = int(np.argmin(np.abs(grade.latitudes - latitude)))
        j = int(np.argmin(np.abs(grade.longitudes - longitude)))
        if pixel_latitude is None:
            pixel_latitude = float(grade.latitudes[i])
            pixel_longitude = float(grade.longitudes[j])
        valor = float(grade.valores[i, j])
        if math.isfinite(valor):
            valores_por_mes[mes] = valor
            dias_amostrados += grade.dias_amostrados

    if not valores_por_mes or pixel_latitude is None or pixel_longitude is None:
        return None

    lat1, lat2 = math.radians(latitude), math.radians(pixel_latitude)
    dlat = lat2 - lat1
    dlon = math.radians(pixel_longitude - longitude)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distancia = 6371 * 2 * math.asin(min(1, math.sqrt(a)))
    config = PRODUTOS_CRW[produto]
    return {
        "produto": produto,
        "variavel": config["variavel"],
        "descricao": config["descricao"],
        "inicio": inicio,
        "fim": fim,
        "coordenada_solicitada": {"latitude": latitude, "longitude": longitude},
        "pixel_utilizado": {"latitude": pixel_latitude, "longitude": pixel_longitude},
        "distancia_pixel_km": distancia,
        "unidade": "°C-semanas" if produto == "CRW_DHW" else "°C",
        "resumo": "máximo diário de cada mês",
        "dias_amostrados": dias_amostrados,
        "quantidade_meses": len(meses),
        "meses_em_cache": len(valores_por_mes),
        "incompleto": True,
        "erro": erro_noaa.detail,
        "serie": [{"data": mes, "valor": valores_por_mes.get(mes)} for mes in meses],
        "fonte": "NOAA Coral Reef Watch, Daily Global 5km v3.1; cache local parcial",
    }


def serie_historica(
    produto: str, latitude: float, longitude: float, inicio: str = "2012-01", fim: str = "2025-12"
) -> dict:
    produto = produto.upper()
    if produto not in PRODUTOS_CRW:
        raise HTTPException(400, "Produto CRW deve ser CRW_DHW ou CRW_HOTSPOT.")
    try:
        return _serie_historica_cache(produto, latitude, longitude, inicio, fim)
    except HTTPException as erro:
        if erro.status_code not in {502, 504}:
            raise
        serie_cache = _serie_historica_disco(
            produto, latitude, longitude, inicio, fim, erro
        )
        if serie_cache is not None:
            return serie_cache
        raise


def _arquivo_cache_mensal(produto: str, data: str) -> Path:
    pasta = Path(__file__).resolve().parent / "Dados" / "CRW" / "mensal"
    return pasta / f"{produto}_{data}.npz"


def _carregar_cache_mensal(produto: str, data: str) -> GradeAtual | None:
    caminho = _arquivo_cache_mensal(produto, data)
    if not caminho.exists():
        return None
    mes_atual_utc = datetime.now(timezone.utc).strftime("%Y-%m")
    if data == mes_atual_utc and time.time() - caminho.stat().st_mtime >= CACHE_SEGUNDOS:
        return None
    with np.load(caminho, allow_pickle=False) as arquivo:
        if str(arquivo["produto"].item()) != produto or str(arquivo["data"].item()) != data:
            raise ValueError(f"Metadados inválidos no cache NOAA: {caminho}")
        return GradeAtual(
            produto,
            data,
            arquivo["latitudes"],
            arquivo["longitudes"],
            arquivo["valores"],
            int(arquivo["dias_amostrados"].item()),
        )


def _salvar_cache_mensal(grade: GradeAtual) -> None:
    caminho = _arquivo_cache_mensal(grade.produto, grade.data)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".npz.tmp")
    with temporario.open("wb") as arquivo:
        np.savez_compressed(
            arquivo,
            produto=np.array(grade.produto),
            data=np.array(grade.data),
            dias_amostrados=np.array(grade.dias_amostrados),
            latitudes=grade.latitudes,
            longitudes=grade.longitudes,
            valores=grade.valores,
        )
    temporario.replace(caminho)


def grade_atual(produto: str, data: str | None = None) -> GradeAtual:
    produto = produto.upper()
    if produto not in PRODUTOS_CRW:
        raise HTTPException(400, "Produto CRW deve ser CRW_DHW ou CRW_HOTSPOT.")

    mensal = data is not None and data != "atual"
    chave_cache = f"{produto}:{data}" if mensal else produto
    agora = time.monotonic()
    entrada = _cache.get(chave_cache)
    if entrada and agora - entrada[0] < CACHE_SEGUNDOS:
        return entrada[1]

    with _lock:
        agora = time.monotonic()
        entrada = _cache.get(chave_cache)
        if entrada and agora - entrada[0] < CACHE_SEGUNDOS:
            return entrada[1]
        if mensal:
            grade = _carregar_cache_mensal(produto, data)
            if grade is None:
                grade = _ler_grade(produto, data)
                _salvar_cache_mensal(grade)
        else:
            grade = _ler_grade(produto)
        _cache[chave_cache] = (time.monotonic(), grade)
        return grade


def limpar_cache() -> None:
    with _lock:
        _cache.clear()


def informacao_raster(produto: str, data: str | None = None) -> dict:
    grade = grade_atual(produto, data)
    passo_lat = float(np.median(np.abs(np.diff(grade.latitudes)))) if len(grade.latitudes) > 1 else RESOLUCAO_GRAUS
    passo_lon = float(np.median(np.abs(np.diff(grade.longitudes)))) if len(grade.longitudes) > 1 else RESOLUCAO_GRAUS
    limiar = 1.0 if produto == "CRW_HOTSPOT" else 0.0
    celulas_com_estresse = int(np.count_nonzero(grade.valores >= limiar)) if produto == "CRW_HOTSPOT" else int(np.count_nonzero(grade.valores > limiar))
    return {
        "produto": produto,
        "data": grade.data,
        "fonte": "NOAA Coral Reef Watch, Daily Global 5km v3.1",
        "dias_amostrados": grade.dias_amostrados,
        "escala": escala_raster(produto, grade.valores),
        "celulas_com_estresse": celulas_com_estresse,
        "limiar_visualizacao": limiar,
        "bounds": {
            "sul": float(np.min(grade.latitudes) - passo_lat / 2),
            "norte": float(np.max(grade.latitudes) + passo_lat / 2),
            "oeste": float(np.min(grade.longitudes) - passo_lon / 2),
            "leste": float(np.max(grade.longitudes) + passo_lon / 2),
        },
    }


def raster_png(produto: str, data: str | None = None) -> bytes:
    grade = grade_atual(produto, data)
    escala = escala_raster(produto, grade.valores)
    valido = np.isfinite(grade.valores)
    if produto == "CRW_DHW":
        valido &= grade.valores > 0
    else:
        valido &= grade.valores >= 1.0
    valores_cor = np.where(valido, grade.valores, escala["minimo"])
    normalizado = np.clip(
        (valores_cor - escala["minimo"]) / (escala["maximo"] - escala["minimo"]),
        0,
        1,
    )
    nome_mapa = "YlOrRd"
    cores = (colormaps[nome_mapa](normalizado) * 255).astype(np.uint8)
    cores[..., 3] = np.where(valido, 255, 0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(cores, mode="RGBA").save(buffer, format="PNG")
    return buffer.getvalue()


def valor_no_ponto(produto: str, latitude: float, longitude: float, data: str | None = None) -> dict:
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise HTTPException(400, "Coordenadas inválidas para a consulta CRW.")
    grade = grade_atual(produto, data)
    i = int(np.argmin(np.abs(grade.latitudes - latitude)))
    j = int(np.argmin(np.abs(grade.longitudes - longitude)))
    valor = float(grade.valores[i, j])
    pixel_lat = float(grade.latitudes[i])
    pixel_lon = float(grade.longitudes[j])
    lat1, lat2 = math.radians(latitude), math.radians(pixel_lat)
    dlat = lat2 - lat1
    dlon = math.radians(pixel_lon - longitude)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distancia = 6371 * 2 * math.asin(min(1, math.sqrt(a)))
    config = PRODUTOS_CRW[produto]
    return {
        "produto": produto,
        "variavel": config["variavel"],
        "descricao": config["descricao"],
        "data": grade.data,
        "valor": valor if math.isfinite(valor) else None,
        "unidade": "°C-semanas" if produto == "CRW_DHW" else "°C",
        "pixel_utilizado": {"latitude": pixel_lat, "longitude": pixel_lon},
        "distancia_pixel_km": distancia,
        "resolucao_graus": RESOLUCAO_GRAUS,
        "fonte": "NOAA Coral Reef Watch, Daily Global 5km v3.1",
        "dias_amostrados": grade.dias_amostrados,
        "resumo": "máximo diário do mês" if data and data != "atual" else "valor diário mais recente",
    }
