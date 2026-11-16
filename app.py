from pathlib import Path
from functools import lru_cache
from io import BytesIO
import re
import math
import numpy as np
import xarray as xr

from PIL import Image
from matplotlib import colormaps
from matplotlib.colors import LogNorm

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from waveheight import (catalogo_waveheight, meses_waveheight, valor_waveheight,
                        serie_waveheight)
from series_cache import serie_indexada
from waveheight_grid import raster_info_grid, raster_grid, pontos_grid, sitios_mapa
from coral_reef_watch import (
    PRODUTOS_CRW,
    informacao_raster as informacao_raster_crw,
    raster_png as raster_png_crw,
    serie_historica as serie_crw,
    valor_no_ponto as valor_crw,
)
from escalas import escala_raster

# ================================================================
# 1. CAMINHOS
# ================================================================

# api/app.py
# sobe um nível -> api
# sobe outro -> pasta principal do WebGIS
PASTA_PROJETO = Path(__file__).resolve().parent

PASTA_DADOS = PASTA_PROJETO / "dados"


PRODUTOS = {
      "CHL": PASTA_DADOS / "CHLO_04.26",
    "SST": PASTA_DADOS / "SST4_04.26",
    "PAR": PASTA_DADOS / "PAR",
    "KD": PASTA_DADOS / "KD490_04.26",
}

VARIAVEIS_PADRAO = {
    "CHL": "chlor_a",
    "SST": "sst4",
    "PAR": "par",
    "KD": "Kd_490",
}

# ================================================================
# 2. CRIAÇÃO DA API
# ================================================================

app = FastAPI(
    title="API WebGIS Abrolhos",
    version="0.1.0",
    description="Consulta de séries ambientais em arquivos NetCDF."
)


# Permite que o WebGIS do Live Preview consulte a API.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ================================================================
# 3. IDENTIFICAR MÊS PELO NOME DO ARQUIVO
# ================================================================

def descobrir_mes(caminho: Path):
    """
    Procura uma data como:

    20120101

    dentro do nome do arquivo e retorna:

    2012-01
    """

    resultado = re.search(
        r"(20\d{2})(0[1-9]|1[0-2])\d{2}",
        caminho.name
    )

    if resultado:
        ano = resultado.group(1)
        mes = resultado.group(2)

        return f"{ano}-{mes}"

    return None


# ================================================================
# 4. IDENTIFICAR LATITUDE E LONGITUDE
# ================================================================

def descobrir_coordenadas(ds):

    candidatos_lat = [
        "lat",
        "latitude",
        "Latitude"
    ]

    candidatos_lon = [
        "lon",
        "longitude",
        "Longitude"
    ]

    nome_lat = next(
        (
            nome
            for nome in candidatos_lat
            if nome in ds.coords
        ),
        None
    )

    nome_lon = next(
        (
            nome
            for nome in candidatos_lon
            if nome in ds.coords
        ),
        None
    )

    if nome_lat is None or nome_lon is None:
        raise ValueError(
            "Não foi possível identificar latitude e longitude."
        )

    return nome_lat, nome_lon


# ================================================================
# 5. DESCOBRIR VARIÁVEIS ESPACIAIS
# ================================================================

def descobrir_variaveis(ds):

    nome_lat, nome_lon = descobrir_coordenadas(ds)

    resultado = []

    for nome, variavel in ds.data_vars.items():

        if (
            nome_lat in variavel.dims
            and nome_lon in variavel.dims
            and np.issubdtype(variavel.dtype, np.number)
        ):

            resultado.append({
                "nome": nome,
                "descricao": variavel.attrs.get("long_name"),
                "unidade": variavel.attrs.get("units"),
                "dimensoes": list(variavel.dims),
                "shape": list(variavel.shape),
            })

    return resultado


# ================================================================
# 6. LISTAR ARQUIVOS DE UM PRODUTO
# ================================================================

@lru_cache(maxsize=None)
def arquivos_produto(produto: str):

    produto = produto.upper()

    if produto not in PRODUTOS:
        raise ValueError(
            f"Produto desconhecido: {produto}"
        )

    pasta = PRODUTOS[produto]

    if not pasta.exists():
        return []

    arquivos = sorted(
        pasta.rglob("*.nc")
    )

    return [
        {
            "arquivo": arquivo,
            "mes": descobrir_mes(arquivo)
        }
        for arquivo in arquivos
    ]


# ================================================================
# 7. ESCOLHER VARIÁVEL
# ================================================================

def escolher_variavel(ds, variavel_solicitada=None):

    if variavel_solicitada:

        if variavel_solicitada not in ds.data_vars:
            raise ValueError(
                f"A variável '{variavel_solicitada}' "
                "não existe neste NetCDF."
            )

        return variavel_solicitada

    candidatas = descobrir_variaveis(ds)

    if len(candidatas) == 0:
        raise ValueError(
            "Nenhuma variável espacial foi encontrada."
        )

    if len(candidatas) == 1:
        return candidatas[0]["nome"]

    nomes = [
        item["nome"]
        for item in candidatas
    ]

    raise ValueError(
        "Há mais de uma variável espacial disponível. "
        f"Informe uma delas usando ?var=. Opções: {nomes}"
    )


# ================================================================
# 8. LOCALIZAR ARQUIVO DE UM MÊS
# ================================================================

def encontrar_arquivo(produto: str, mes: str):

    arquivos = arquivos_produto(produto)

    encontrados = [
        item
        for item in arquivos
        if item["mes"] == mes
    ]

    if len(encontrados) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Não encontrei {produto} para {mes}."
        )

    if len(encontrados) > 1:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Existe mais de um arquivo de "
                f"{produto} para {mes}."
            )
        )

    return encontrados[0]["arquivo"]


# ================================================================
# 9. ROTA INICIAL
# ================================================================

@app.get("/")
def inicio():

    return {
        "api": "WebGIS Abrolhos",
        "status": "online",
        "produtos": [*PRODUTOS, "WAVEHEIGHT", *PRODUTOS_CRW]
    }


# ================================================================
# 10. CATÁLOGO
# ================================================================

@app.get("/catalogo")
def catalogo():

    resposta = {}

    for produto in PRODUTOS:

        arquivos = arquivos_produto(produto)

        meses = sorted({
            item["mes"]
            for item in arquivos
            if item["mes"] is not None
        })

        info = {
            "quantidade_arquivos": len(arquivos),

            "quantidade_meses": len(meses),

            "primeiro_mes":
                meses[0]
                if meses
                else None,

            "ultimo_mes":
                meses[-1]
                if meses
                else None,

            "variaveis": []
        }

        # Inspeciona somente o primeiro arquivo,
        # porque não precisamos abrir os 168 NetCDFs
        # só para descobrir a estrutura.

        if arquivos:

            primeiro = arquivos[0]["arquivo"]

            try:

                with xr.open_dataset(
                    primeiro,
                    engine="netcdf4"
                ) as ds:

                    info["variaveis"] = (
                        descobrir_variaveis(ds)
                    )

            except Exception as erro:

                info["erro"] = str(erro)

        resposta[produto] = info

    resposta["WAVEHEIGHT"] = catalogo_waveheight()
    resposta["CRW_DHW"] = {
        "tipo": "máximo diário mensal",
        "inicio": "2012-01",
        "fonte": "NOAA Coral Reef Watch Daily Global 5km v3.1",
        "variaveis": [{"nome": "degree_heating_week", "descricao": "Degree Heating Week", "unidade": "°C-semanas"}],
    }
    resposta["CRW_HOTSPOT"] = {
        "tipo": "máximo diário mensal",
        "inicio": "2012-01",
        "fonte": "NOAA Coral Reef Watch Daily Global 5km v3.1",
        "variaveis": [{"nome": "hotspot", "descricao": "Coral Bleaching HotSpot", "unidade": "°C"}],
    }
    return resposta


# ================================================================
# 11. MESES DISPONÍVEIS
# ================================================================

@app.get("/meses")
def listar_meses(produto: str):

    produto = produto.upper()

    if produto == "WAVEHEIGHT":
        meses = meses_waveheight()
        return {"produto": produto, "quantidade": len(meses), "meses": meses}

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR ou KD."
        )

    arquivos = arquivos_produto(produto)

    meses = sorted({
        item["mes"]
        for item in arquivos
        if item["mes"] is not None
    })

    return {
        "produto": produto,
        "quantidade": len(meses),
        "meses": meses
    }

# ================================================================
# DISTÂNCIA ENTRE O PONTO E O CENTRO DO PIXEL
# ================================================================

def distancia_haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
):
    raio_terra_km = 6371.0088

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(
        lat2 - lat1
    )

    delta_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_phi / 2) ** 2
        +
        math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return raio_terra_km * c

# ================================================================
# 12. CONSULTA DE VALOR
# ================================================================

@app.get("/valor")
def consultar_valor(
    produto: str,
    data: str,
    lat: float,
    lon: float,
    var: str | None = Query(default=None),
    sitio: str | None = None
):

    produto = produto.upper()

    if produto == "WAVEHEIGHT":
        return valor_waveheight(data, lat, lon, sitio)

    # ------------------------------------------------------------
    # VALIDA O PRODUTO
    # ------------------------------------------------------------

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR ou KD."
        )

    # ------------------------------------------------------------
    # VALIDA A DATA
    # ------------------------------------------------------------

    if not re.fullmatch(
        r"20\d{2}-(0[1-9]|1[0-2])",
        data
    ):
        raise HTTPException(
            status_code=400,
            detail="Use a data no formato YYYY-MM."
        )

    # ------------------------------------------------------------
    # LOCALIZA O ARQUIVO DO MÊS
    # ------------------------------------------------------------

    arquivo = encontrar_arquivo(
        produto,
        data
    )

    try:

        # --------------------------------------------------------
        # ABRE O NETCDF
        # --------------------------------------------------------

        with xr.open_dataset(
            arquivo,
            engine="netcdf4",
            mask_and_scale=True
        ) as ds:

            nome_lat, nome_lon = (
                descobrir_coordenadas(ds)
            )

            # ----------------------------------------------------
            # ESCOLHE A VARIÁVEL
            # ----------------------------------------------------

            if var is not None:
                nome_variavel = escolher_variavel(
                    ds,
                    var
                )

            else:
                nome_variavel = VARIAVEIS_PADRAO[
                    produto
                ]

            if nome_variavel not in ds.data_vars:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"A variável '{nome_variavel}' "
                        f"não existe no arquivo {arquivo.name}."
                    )
                )

            da = ds[
                nome_variavel
            ]

            # ----------------------------------------------------
            # LIMITES GEOGRÁFICOS
            # ----------------------------------------------------

            lat_min = float(
                ds[nome_lat].min()
            )

            lat_max = float(
                ds[nome_lat].max()
            )

            lon_min = float(
                ds[nome_lon].min()
            )

            lon_max = float(
                ds[nome_lon].max()
            )

            # ----------------------------------------------------
            # VERIFICA SE O CLIQUE ESTÁ DENTRO DA GRADE
            # ----------------------------------------------------

            if not (
                lat_min <= lat <= lat_max
                and
                lon_min <= lon <= lon_max
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A coordenada está fora "
                        "da área coberta pelo raster."
                    )
                )

            # ----------------------------------------------------
            # SELECIONA O CENTRO DE PIXEL MAIS PRÓXIMO
            # ----------------------------------------------------

            pixel = da.sel(
                {
                    nome_lat: lat,
                    nome_lon: lon
                },
                method="nearest"
            )

            pixel = pixel.squeeze(
                drop=True
            )

            if pixel.size != 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A consulta ainda possui "
                        "dimensões adicionais."
                    )
                )

            # ----------------------------------------------------
            # VALOR E COORDENADAS DO PIXEL
            # ----------------------------------------------------

            valor = float(
                pixel.values
            )

            pixel_lat = float(
                pixel[nome_lat].values
            )

            pixel_lon = float(
                pixel[nome_lon].values
            )

            # ----------------------------------------------------
            # DISTÂNCIA ENTRE O CLIQUE E O CENTRO DO PIXEL
            # ----------------------------------------------------

            distancia_pixel_km = (
                distancia_haversine_km(
                    lat,
                    lon,
                    pixel_lat,
                    pixel_lon
                )
            )

            # ----------------------------------------------------
            # TRATA NODATA / NAN
            # ----------------------------------------------------

            if np.isfinite(valor):
                valor_resposta = valor

            else:
                valor_resposta = None

            # ----------------------------------------------------
            # RESPOSTA DA API
            # ----------------------------------------------------

            return {
                "produto": produto,

                "data": data,

                "variavel": nome_variavel,

                "descricao":
                    da.attrs.get("long_name"),

                "unidade":
                    da.attrs.get("units"),

                "coordenada_solicitada": {
                    "latitude": lat,
                    "longitude": lon
                },

                "pixel_utilizado": {
                    "latitude": pixel_lat,
                    "longitude": pixel_lon
                },

                "distancia_pixel_km":
                    distancia_pixel_km,

                "valor":
                    valor_resposta,

                "arquivo":
                    arquivo.name
            }

    except HTTPException:
        raise

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=str(erro)
        )
    # ------------------------------------------------------------
    # VALIDA O PRODUTO
    # ------------------------------------------------------------

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR ou KD."
        )

    # ------------------------------------------------------------
    # VALIDA A DATA
    # ------------------------------------------------------------

    if not re.fullmatch(
        r"20\d{2}-(0[1-9]|1[0-2])",
        data
    ):
        raise HTTPException(
            status_code=400,
            detail="Use a data no formato YYYY-MM."
        )

    # ------------------------------------------------------------
    # LOCALIZA O NETCDF DO MÊS
    # ------------------------------------------------------------

    arquivo = encontrar_arquivo(
        produto,
        data
    )

    try:

        # --------------------------------------------------------
        # ABRE O NETCDF
        # --------------------------------------------------------

        with xr.open_dataset(
            arquivo,
            engine="netcdf4",
            mask_and_scale=True
        ) as ds:

            # Descobre os nomes das coordenadas.
            nome_lat, nome_lon = descobrir_coordenadas(ds)

            # ----------------------------------------------------
            # ESCOLHE A VARIÁVEL
            # ----------------------------------------------------

            # Se o usuário informou ?var=, usa essa variável.
            if var is not None:
                nome_variavel = escolher_variavel(
                    ds,
                    var
                )

            # Caso contrário, usa a variável científica padrão
            # correspondente ao produto.
            else:
                nome_variavel = VARIAVEIS_PADRAO[
                    produto
                ]

            # Confere se a variável realmente existe.
            if nome_variavel not in ds.data_vars:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"A variável '{nome_variavel}' "
                        f"não existe no arquivo {arquivo.name}."
                    )
                )

            da = ds[nome_variavel]

            # ----------------------------------------------------
            # EXTENSÃO GEOGRÁFICA DO RASTER
            # ----------------------------------------------------

            lat_min = float(
                ds[nome_lat].min()
            )

            lat_max = float(
                ds[nome_lat].max()
            )

            lon_min = float(
                ds[nome_lon].min()
            )

            lon_max = float(
                ds[nome_lon].max()
            )

            # ----------------------------------------------------
            # VERIFICA SE O PONTO ESTÁ DENTRO DO RASTER
            # ----------------------------------------------------

            if not (
                lat_min <= lat <= lat_max
                and
                lon_min <= lon <= lon_max
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A coordenada está fora "
                        "da área coberta pelo raster."
                    )
                )

            # ----------------------------------------------------
            # PROCURA O PIXEL MAIS PRÓXIMO
            # ----------------------------------------------------

            pixel = da.sel(
                {
                    nome_lat: lat,
                    nome_lon: lon
                },
                method="nearest"
            )

            pixel = pixel.squeeze(
                drop=True
            )

            # Depois de selecionar lat/lon,
            # esperamos encontrar somente um valor.
            if pixel.size != 1:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A consulta ainda possui "
                        "dimensões adicionais."
                    )
                )

            # ----------------------------------------------------
            # VALOR DO PIXEL
            # ----------------------------------------------------

            valor = float(
                pixel.values
            )

            pixel_lat = float(
                pixel[nome_lat].values
            )

            pixel_lon = float(
                pixel[nome_lon].values
            )

            if np.isfinite(valor):
                valor_resposta = valor
            else:
                valor_resposta = None

            # ----------------------------------------------------
            # RESPOSTA DA API
            # ----------------------------------------------------

            return {
                "produto": produto,

                "data": data,

                "variavel": nome_variavel,

                "descricao":
                    da.attrs.get("long_name"),

                "unidade":
                    da.attrs.get("units"),

                "coordenada_solicitada": {
                    "latitude": lat,
                    "longitude": lon
                },

                "pixel_utilizado": {
                    "latitude": pixel_lat,
                    "longitude": pixel_lon
                },

                "valor": valor_resposta,

                "arquivo": arquivo.name
            }

    except HTTPException:
        raise

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=str(erro)
        )

    # ================================================================
# CONSULTA CONJUNTA DAS VARIÁVEIS AMBIENTAIS
# ================================================================

@app.get("/ambiente")
def consultar_ambiente(
    data: str,
    lat: float,
    lon: float
):

    produtos = [
        "CHL",
        "SST",
        "PAR",
        "KD"
    ]

    resultados = {}


    for produto in produtos:

        try:

            resposta = consultar_valor(
                produto=produto,
                data=data,
                lat=lat,
                lon=lon,
                var=None
            )

            resultados[produto] = {
    "variavel": resposta["variavel"],
    "descricao": resposta["descricao"],
    "valor": resposta["valor"],
    "unidade": resposta["unidade"],
    "pixel_utilizado": resposta["pixel_utilizado"],
    "distancia_pixel_km": resposta["distancia_pixel_km"],
    "arquivo": resposta["arquivo"]
}


        except HTTPException as erro:

            resultados[produto] = {
                "valor": None,
                "erro": erro.detail
            }


    try:
        resultados["WAVEHEIGHT"] = valor_waveheight(data, lat, lon)
    except HTTPException as erro:
        resultados["WAVEHEIGHT"] = {"valor": None, "erro": erro.detail}

    for produto in PRODUTOS_CRW:
        try:
            resultados[produto] = valor_crw(produto, lat, lon, data)
        except HTTPException as erro:
            resultados[produto] = {"valor": None, "erro": erro.detail}

    return {
        "data": data,

        "coordenada_solicitada": {
            "latitude": lat,
            "longitude": lon
        },

        "resultados": resultados
    }

# ================================================================
# INFORMAÇÕES ESPACIAIS DO RASTER
# ================================================================

@app.get("/raster-info")
def raster_info(
    produto: str,
    data: str
):

    produto = produto.upper()

    if produto in PRODUTOS_CRW:
        return informacao_raster_crw(produto, data)

    if produto == "WAVEHEIGHT":
        return raster_info_grid(data)

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR ou KD."
        )

    arquivo = encontrar_arquivo(
        produto,
        data
    )

    with xr.open_dataset(
        arquivo,
        engine="netcdf4",
        mask_and_scale=True
    ) as ds:

        nome_lat, nome_lon = descobrir_coordenadas(ds)

        latitudes = np.asarray(
            ds[nome_lat].values,
            dtype=float
        )

        longitudes = np.asarray(
            ds[nome_lon].values,
            dtype=float
        )

        passo_lat = abs(
            float(
                np.nanmedian(
                    np.diff(latitudes)
                )
            )
        )

        passo_lon = abs(
            float(
                np.nanmedian(
                    np.diff(longitudes)
                )
            )
        )

        return {
            "produto": produto,
            "data": data,
            "escala": escala_raster(produto, np.asarray(ds[VARIAVEIS_PADRAO[produto]].values, dtype=float)),

            "bounds": {
                "sul": float(
                    np.nanmin(latitudes)
                    - passo_lat / 2
                ),

                "norte": float(
                    np.nanmax(latitudes)
                    + passo_lat / 2
                ),

                "oeste": float(
                    np.nanmin(longitudes)
                    - passo_lon / 2
                ),

                "leste": float(
                    np.nanmax(longitudes)
                    + passo_lon / 2
                )
            }
        }


# ================================================================
# RASTER PNG
# ================================================================

@app.get("/raster")
def gerar_raster(
    produto: str,
    data: str
):

    produto = produto.upper()

    if produto in PRODUTOS_CRW:
        return Response(
            content=raster_png_crw(produto, data),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=21600"},
        )

    if produto == "WAVEHEIGHT":
        return Response(content=raster_grid(data), media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR ou KD."
        )

    arquivo = encontrar_arquivo(
        produto,
        data
    )

    with xr.open_dataset(
        arquivo,
        engine="netcdf4",
        mask_and_scale=True
    ) as ds:

        nome_lat, nome_lon = descobrir_coordenadas(ds)

        nome_variavel = VARIAVEIS_PADRAO[
            produto
        ]

        da = ds[
            nome_variavel
        ]

        matriz = np.asarray(
            da.values,
            dtype=float
        )

        if matriz.ndim != 2:
            raise HTTPException(
                status_code=400,
                detail="O raster precisa possuir duas dimensões."
            )

        latitudes = np.asarray(
            ds[nome_lat].values,
            dtype=float
        )

        longitudes = np.asarray(
            ds[nome_lon].values,
            dtype=float
        )

        # Norte deve ficar no topo da imagem.
        if latitudes[0] < latitudes[-1]:
            matriz = np.flipud(
                matriz
            )

        # Oeste deve ficar à esquerda.
        if longitudes[0] > longitudes[-1]:
            matriz = np.fliplr(
                matriz
            )


        # --------------------------------------------------------
        # CLOROFILA
        # --------------------------------------------------------

        if produto == "CHL":

            valido = (
                np.isfinite(matriz)
                & (matriz > 0)
            )

            escala = escala_raster(produto, matriz)
            minimo, maximo = escala["minimo"], escala["maximo"]

            normalizador = LogNorm(
                vmin=minimo,
                vmax=maximo,
                clip=True
            )

            matriz_cor = np.where(
                valido,
                matriz,
                minimo
            )

            cores = colormaps[
                "turbo"
            ](
                normalizador(
                    matriz_cor
                )
            )


        # --------------------------------------------------------
        # OUTROS PRODUTOS
        # --------------------------------------------------------

        else:

            valido = np.isfinite(
                matriz
            )

            valores_validos = matriz[
                valido
            ]

            if valores_validos.size == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Raster sem valores válidos."
                )

            escala = escala_raster(produto, matriz)
            minimo, maximo = escala["minimo"], escala["maximo"]

            matriz_normalizada = (
                matriz - minimo
            ) / (
                maximo - minimo
            )

            matriz_normalizada = np.clip(
                matriz_normalizada,
                0,
                1
            )

            cores = colormaps[
                "viridis"
            ](
                matriz_normalizada
            )


        # NoData transparente.
        cores[..., 3] = np.where(
            valido,
            1.0,
            0.0
        )

        rgba = (
            cores * 255
        ).astype(
            np.uint8
        )

        imagem = Image.fromarray(
            rgba,
            mode="RGBA"
        )

        buffer = BytesIO()

        imagem.save(
            buffer,
            format="PNG"
        )

        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600"
            }
        )

    # ================================================================
# SÉRIE TEMPORAL
# ================================================================

@app.get("/serie")
def consultar_serie(
    produto: str,
    lat: float,
    lon: float,
    inicio: str = "2012-01",
    fim: str = "2025-12",
    sitio: str | None = None
):
    from indicadores import resumir_serie
    resposta = _consultar_serie(produto, lat, lon, inicio, fim, sitio)
    if "serie" in resposta:
        resposta = {**resposta, "indicadores": resumir_serie(
            produto.upper(), resposta["serie"], resposta.get("unidade"),
            resposta.get("incompleto", False))}
    return resposta


def _consultar_serie(
    produto: str,
    lat: float,
    lon: float,
    inicio: str = "2012-01",
    fim: str = "2025-12",
    sitio: str | None = None
):

    produto = produto.upper()

    if produto == "WAVEHEIGHT":
        return serie_waveheight(lat, lon, inicio, fim, sitio)

    if produto in PRODUTOS_CRW:
        return serie_crw(produto, lat, lon, inicio, fim)

    if produto not in PRODUTOS:
        raise HTTPException(
            status_code=400,
            detail="Produto deve ser CHL, SST, PAR, KD, WAVEHEIGHT, CRW_DHW ou CRW_HOTSPOT."
        )

    arquivos = arquivos_produto(
        produto
    )

    # Mantém somente o período solicitado.
    arquivos_periodo = [
        item
        for item in arquivos
        if (
            item["mes"] is not None
            and inicio <= item["mes"] <= fim
        )
    ]

    nome_variavel = VARIAVEIS_PADRAO[
        produto
    ]

    indice = serie_indexada(produto, arquivos, nome_variavel, lat, lon, inicio, fim)
    if indice is not None:
        pixel = indice["pixel_utilizado"]
        return {
            "produto": produto, "variavel": nome_variavel, "inicio": inicio, "fim": fim,
            "coordenada_solicitada": {"latitude": lat, "longitude": lon},
            "pixel_utilizado": pixel,
            "distancia_pixel_km": distancia_haversine_km(lat, lon, pixel["latitude"], pixel["longitude"]) if pixel else None,
            "quantidade_meses": len(indice["serie"]), "serie": indice["serie"]
        }

    serie = []

    pixel_referencia = None
    distancia_pixel_km = None


    for item in arquivos_periodo:

        arquivo = item["arquivo"]
        mes = item["mes"]

        try:

            with xr.open_dataset(
                arquivo,
                engine="netcdf4",
                mask_and_scale=True
            ) as ds:

                nome_lat, nome_lon = (
                    descobrir_coordenadas(ds)
                )

                da = ds[
                    nome_variavel
                ]

                pixel = da.sel(
                    {
                        nome_lat: lat,
                        nome_lon: lon
                    },
                    method="nearest"
                )

                pixel = pixel.squeeze(
                    drop=True
                )

                valor = float(
                    pixel.values
                )

                pixel_lat = float(
                    pixel[nome_lat].values
                )

                pixel_lon = float(
                    pixel[nome_lon].values
                )

                # Guarda o centro do pixel usado.
                if pixel_referencia is None:

                    pixel_referencia = {
                        "latitude": pixel_lat,
                        "longitude": pixel_lon
                    }

                    distancia_pixel_km = (
                        distancia_haversine_km(
                            lat,
                            lon,
                            pixel_lat,
                            pixel_lon
                        )
                    )

                if np.isfinite(valor):
                    valor_final = valor
                else:
                    valor_final = None

                serie.append({
                    "data": mes,
                    "valor": valor_final
                })

        except Exception as erro:

            serie.append({
                "data": mes,
                "valor": None,
                "erro": str(erro)
            })


    return {
        "produto": produto,
        "variavel": nome_variavel,

        "inicio": inicio,
        "fim": fim,

        "coordenada_solicitada": {
            "latitude": lat,
            "longitude": lon
        },

        "pixel_utilizado":
            pixel_referencia,

        "distancia_pixel_km":
            distancia_pixel_km,

        "quantidade_meses":
            len(serie),

        "serie":
            serie
    }

# ================================================================
# SERVIR WEBGIS
# ================================================================

app.mount(
    "/static",
    StaticFiles(directory="."),
    name="static"
)


@app.get("/mapa")
def abrir_webgis():

    return RedirectResponse("/static/index.html?v=rede-local-20")


# Compatibilidade com páginas antigas abertas em /mapa e com seus assets relativos.
@app.get("/estilo.css", include_in_schema=False)
def servir_estilo():
    return FileResponse(PASTA_PROJETO / "estilo.css", media_type="text/css")


@app.get("/mapa.js", include_in_schema=False)
def servir_javascript():
    return FileResponse(PASTA_PROJETO / "mapa.js", media_type="application/javascript")


@app.get("/Pontos_Clean.geojson", include_in_schema=False)
def servir_pontos():
    return FileResponse(PASTA_PROJETO / "Pontos_Clean.geojson", media_type="application/geo+json")

@app.get("/waveheight/sitios")
def listar_sitios_waveheight():
    return {f["properties"]["name"]: {"coordenadas": f["geometry"]["coordinates"][:2]}
            for f in sitios_mapa()}


@app.get("/waveheight/pontos")
def pontos_waveheight(data: str):
    return pontos_grid(data)


@app.get("/escalas")
def listar_escalas(data: str):
    resposta = {}
    if data == "atual":
        for produto in PRODUTOS_CRW:
            resposta[produto] = escala_raster(produto, np.array([0.0]))
        return {"data": "NOAA CRW · dados diários", "escalas": resposta}

    for produto in [*PRODUTOS, "WAVEHEIGHT"]:
        try:
            resposta[produto] = raster_info(produto, data)["escala"]
        except HTTPException as erro:
            resposta[produto] = {"erro": erro.detail}
    for produto in PRODUTOS_CRW:
        resposta[produto] = escala_raster(produto, np.array([0.0]))
    return {"data": data, "escalas": resposta}


@app.post("/exportacoes")
def criar_exportacao():
    from exportacao import iniciar_exportacao
    return iniciar_exportacao()


@app.get("/previa")
def previa_exportacao(
    mes: str = Query(pattern=r"^20\d{2}-(0[1-9]|1[0-2])$"),
    tabela: str = Query(default="series", pattern=r"^(series|atributos)$"),
    busca: str = Query(default="", max_length=150),
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=25, ge=1, le=100),
):
    from previa import consultar_previa
    return consultar_previa(mes, tabela, busca, pagina, tamanho)


@app.get("/exportacoes/{identificador}")
def consultar_exportacao(identificador: str):
    from exportacao import estado_exportacao
    return estado_exportacao(identificador)


@app.get("/exportacoes/{identificador}/arquivo")
def baixar_exportacao(identificador: str):
    from exportacao import arquivo_exportacao
    return FileResponse(arquivo_exportacao(identificador), media_type="application/zip",
                        filename="series_completas_todos_pontos.zip")
