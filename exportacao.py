"""Exportação completa dos pontos e das seis séries em CSV/ZIP."""
import csv
from datetime import datetime, timezone
from io import TextIOWrapper
import json
from pathlib import Path
from threading import Lock, Thread
import uuid
import zipfile
import numpy as np
from fastapi import HTTPException
from indicadores import resumir_serie, linhas_indicadores, CABECALHO

BASE = Path(__file__).resolve().parent
PASTA = BASE / "Dados" / "exportacoes"
ESTADOS = {}
TRAVA = Lock()
PRODUTOS_EXPORTAR = ["CHL", "SST", "PAR", "KD", "WAVEHEIGHT", "CRW_DHW"]
COLUNAS = ["CHL_mg_m3", "SST_graus_C", "PAR_mol_m2_dia", "KD_m_1", "WAVEHEIGHT_m", "CRW_DHW_C_semanas"]
UNIDADES = {
    "CHL": "mg/m³",
    "SST": "°C",
    "PAR": "mol/m²/dia",
    "KD": "m⁻¹",
    "WAVEHEIGHT": "m",
    "CRW_DHW": "°C-semanas",
}
DHW_INICIO = "2012-01"


def _meses_entre(inicio, fim):
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


def _extrair_dhw(pontos, progresso=None):
    from coral_reef_watch import grade_atual
    from waveheight import distancia

    fim = datetime.now(timezone.utc).strftime("%Y-%m")
    meses = _meses_entre(DHW_INICIO, fim)
    latitudes = np.array([p["geometry"]["coordinates"][1] for p in pontos])
    longitudes = np.array([p["geometry"]["coordinates"][0] for p in pontos])
    valores = np.full((len(meses), len(pontos)), np.nan, dtype=float)
    pixels = None

    if progresso:
        progresso("dhw", 0, len(meses))
    for indice_mes, mes in enumerate(meses):
        try:
            grade = grade_atual("CRW_DHW", mes)
        except HTTPException as erro:
            if erro.status_code != 404:
                raise HTTPException(
                    erro.status_code, f"Falha ao consultar DHW para {mes}: {erro.detail}"
                ) from erro
        else:
            ys = np.abs(grade.latitudes[:, None] - latitudes[None, :]).argmin(axis=0)
            xs = np.abs(grade.longitudes[:, None] - longitudes[None, :]).argmin(axis=0)
            valores[indice_mes] = grade.valores[ys, xs]
            if pixels is None:
                pixels = [
                    {"latitude": float(grade.latitudes[y]), "longitude": float(grade.longitudes[x])}
                    for y, x in zip(ys, xs)
                ]
        if progresso:
            progresso("dhw", indice_mes + 1, len(meses))

    if pixels is None:
        raise RuntimeError("Não foi possível obter nenhum mês de DHW da NOAA desde 2012.")
    distancias = [
        distancia(lat, lon, [pixel["longitude"], pixel["latitude"]])
        for lat, lon, pixel in zip(latitudes, longitudes, pixels)
    ]
    return {
        "meses": meses,
        "valores": valores,
        "variavel": "degree_heating_week",
        "pixels": pixels,
        "distancias": distancias,
    }


def extrair_pontos(pontos, progresso=None, *, incluir_dhw=True, mes=None):
    from app import arquivos_produto
    from series_cache import CACHE, abrir_indice, assinatura
    from waveheight_grid import grade
    from waveheight import distancia
    lat = np.array([p["geometry"]["coordinates"][1] for p in pontos])
    lon = np.array([p["geometry"]["coordinates"][0] for p in pontos])
    extraidos = {}
    for produto in PRODUTOS_EXPORTAR[:-1]:
        if produto == "WAVEHEIGHT":
            g = grade()
            meta, cube = {"lat": g["lat"], "lon": g["lon"], "meses": g["meses"], "variavel": "swh"}, g["valores"]
        else:
            arquivo = CACHE / f"{produto}.json"
            if not arquivo.exists():
                raise RuntimeError("Prepare os índices executando python series_cache.py antes de exportar.")
            meta, cube = abrir_indice(produto, arquivo.stat().st_mtime_ns)
            if meta["fontes"] != assinatura(arquivos_produto(produto)):
                raise RuntimeError(f"Índice de {produto} desatualizado; reconstrua com series_cache.py.")
        ys, xs = [], []
        def vizinho(coords, v):
            c = np.asarray(coords)
            diferencas = abs(c-v)
            indices = np.flatnonzero(diferencas == diferencas.min())
            return int(indices[np.argmax(c[indices])])
        for y, x in zip(lat, lon):
            ys.append(vizinho(meta["lat"], y))
            xs.append(vizinho(meta["lon"], x))
        # Uma leitura vetorizada por produto evita milhares de acessos alternados ao disco.
        meses = meta["meses"]
        if mes is None:
            valores = np.asarray(cube[:, ys, xs]).copy()
        elif mes in meses:
            indice_mes = meses.index(mes)
            valores = np.asarray(cube[indice_mes:indice_mes+1, ys, xs]).copy()
            meses = [mes]
        else:
            valores = np.empty((0, len(pontos)))
            meses = []
        pixels = [{"latitude": float(meta["lat"][y]), "longitude": float(meta["lon"][x])} for y, x in zip(ys, xs)]
        distancias = [distancia(y, x, [p["longitude"], p["latitude"]]) for y, x, p in zip(lat, lon, pixels)]
        extraidos[produto] = {"meses": meses, "valores": valores, "variavel": meta["variavel"],
                              "pixels": pixels, "distancias": distancias}
    if incluir_dhw:
        extraidos["CRW_DHW"] = _extrair_dhw(pontos, progresso)
    return extraidos


def gerar_zip(destino, progresso=None):
    from waveheight_grid import sitios_mapa
    pontos = sitios_mapa()
    destino = Path(destino)
    destino.parent.mkdir(exist_ok=True, parents=True)
    fontes, intervalos, pixels = {}, {}, []
    total_linhas = 0
    extraidos = extrair_pontos(pontos, progresso)
    if progresso:
        progresso("pontos", 0, len(pontos))
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        with z.open("series_temporais.csv", "w", force_zip64=True) as raw:
            with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as texto:
                writer = csv.writer(texto, delimiter=";")
                writer.writerow(["ponto_id", "sitio", "latitude", "longitude", "mes", *COLUNAS])
                for i, ponto in enumerate(pontos, 1):
                    lon, lat = ponto["geometry"]["coordinates"][:2]
                    nome = ponto["properties"]["name"]
                    valores, meses = [], set()
                    for produto in PRODUTOS_EXPORTAR:
                        resposta = extraidos[produto]
                        serie = {mes: float(v) if np.isfinite(v) else None
                                 for mes, v in zip(resposta["meses"], resposta["valores"][:, i-1])}
                        valores.append(serie)
                        meses.update(serie)
                        intervalo = sorted(serie)
                        intervalos[produto] = {"inicio": intervalo[0] if intervalo else None,
                                               "fim": intervalo[-1] if intervalo else None, "meses": len(serie)}
                        fontes[produto] = resposta["variavel"]
                        pixel = resposta["pixels"][i-1]
                        pixels.append([i, nome, produto, pixel["latitude"], pixel["longitude"], resposta["distancias"][i-1]])
                    for mes in sorted(meses):
                        writer.writerow([i, nome, lat, lon, mes, *[serie.get(mes) for serie in valores]])
                        total_linhas += 1
                    if progresso:
                        progresso("pontos", i, len(pontos))
        with z.open("pixels_utilizados.csv", "w") as raw:
            with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as texto:
                writer = csv.writer(texto, delimiter=";")
                writer.writerow(["ponto_id", "sitio", "produto", "pixel_latitude", "pixel_longitude", "distancia_km"])
                writer.writerows(pixels)
        geojson = {"type": "FeatureCollection", "features": [
            {**p, "properties": {**p["properties"], "export_ponto_id": i}} for i, p in enumerate(pontos, 1)]}
        z.writestr("pontos.geojson", json.dumps(geojson, ensure_ascii=False))
        with z.open("indicadores.csv", "w") as raw:
            with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as texto:
                writer = csv.writer(texto, delimiter=";")
                writer.writerow(["ponto_id", "sitio", "latitude", "longitude", *CABECALHO])
                for i, ponto in enumerate(pontos):
                    lon, lat = ponto["geometry"]["coordinates"][:2]
                    for produto, dados in extraidos.items():
                        serie = [{"data": mes, "valor": float(v)} for mes, v in
                                 zip(dados["meses"], dados["valores"][:, i])]
                        resumo = resumir_serie(produto, serie, UNIDADES.get(produto))
                        for linha in linhas_indicadores(produto, resumo):
                            writer.writerow([i+1, ponto["properties"]["name"], lat, lon, *linha])
        with z.open("resumos_anuais.csv", "w") as raw:
            with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as texto:
                writer = csv.writer(texto, delimiter=";")
                writer.writerow(["ponto_id", "sitio", "produto", "ano", "media", "maximo",
                                 "unidade", "meses_validos", "ano_completo"])
                for i, ponto in enumerate(pontos):
                    for produto, dados in extraidos.items():
                        resumo = resumir_serie(produto, [
                            {"data": mes, "valor": float(v)} for mes, v in
                            zip(dados["meses"], dados["valores"][:, i])])
                        for ano in resumo["anuais"]:
                            writer.writerow([i+1, ponto["properties"]["name"], produto, ano["ano"],
                                             ano["media"], ano["maximo"], UNIDADES.get(produto),
                                             ano["meses_validos"], ano["completo"]])
        atributos = sorted({chave for p in pontos for chave in p["properties"]})
        with z.open("atributos_pontos.csv", "w") as raw:
            with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as texto:
                writer = csv.writer(texto, delimiter=";")
                writer.writerow(["ponto_id", "latitude", "longitude", *atributos])
                for i, ponto in enumerate(pontos, 1):
                    lon, lat = ponto["geometry"]["coordinates"][:2]
                    writer.writerow([i, lat, lon, *[ponto["properties"].get(c) for c in atributos]])
        meta = {"gerado_em_utc": datetime.now(timezone.utc).isoformat(), "pontos": len(pontos),
                "linhas_series": total_linhas, "periodos": intervalos, "variaveis": fontes,
                "colunas_valores": dict(zip(PRODUTOS_EXPORTAR, COLUNAS)),
                "unidades": UNIDADES,
                "indicadores": {
                    "base": "Valores mensais válidos de cada produto; períodos próprios, sem imputação",
                    "sd": "Populacional (ddof=0)", "cv": "SD / abs(média); SST em Celsius depende da escala",
                    "momentos": "Assimetria e excesso de curtose populacionais, sem correção de viés",
                    "dhw": "Contagens de meses com máximo diário mensal > 4 e > 8; não são eventos nem dias",
                    "anuais": "Média dos máximos anuais de DHW usa somente anos com 12 meses válidos",
                    "atributos": "Atributos originais; ele é elevação GPS, time é registro GPS, não profundidade nem data de levantamento ecológico"},
                "metodo": "Pixel mais próximo por parâmetro; sem interpolação temporal ou espacial",
                "ausentes": "Célula vazia: sem dado ou fora do período disponível; zero é preservado"}
        z.writestr("metadados.json", json.dumps(meta, ensure_ascii=False, indent=2))
        z.writestr("LEIA-ME.txt", "Séries completas de todos os pontos e parâmetros, sem o recorte do gráfico.\n"
                   "CSV UTF-8 com BOM, separador ponto e vírgula e decimal ponto.\n"
                   "Uma linha por ponto e mês; valores ausentes ficam vazios. Zero é um valor válido.\n"
                   "CHL: mg/m³; SST: °C; PAR: mol/m²/dia; KD: m⁻¹; WAVEHEIGHT: m; "
                   "CRW_DHW: °C-semanas (máximo diário mensal desde 2012-01).\n"
                   "pixels_utilizados.csv informa o pixel e a distância para cada parâmetro e ponto.\n"
                   "pontos.geojson preserva os atributos originais; export_ponto_id relaciona os arquivos.\n"
                   "indicadores.csv: resumos mensais com período e cobertura; resumos_anuais.csv: médias e máximos por ano.\n"
                   "atributos_pontos.csv: atributos originais; elevação e horário GPS não representam profundidade ou data de levantamento ecológico.\n"
                   "DHW: contagens de meses acima dos limiares, não eventos independentes ou dias.\n"
                   "Consulte metadados.json para os períodos efetivamente disponíveis.\n")
    return meta


def iniciar_exportacao():
    with TRAVA:
        for identificador, estado in ESTADOS.items():
            if estado["status"] == "processando":
                return {"id": identificador, **estado}
        identificador = uuid.uuid4().hex
        ESTADOS[identificador] = {"status": "processando", "etapa": "dhw", "concluidos": 0, "total": 0}
    def executar():
        try:
            def progresso(etapa, i, total):
                with TRAVA:
                    ESTADOS[identificador].update(etapa=etapa, concluidos=i, total=total)
            meta = gerar_zip(PASTA / f"{identificador}.zip", progresso)
            with TRAVA:
                ESTADOS[identificador].update(status="pronto", linhas=meta["linhas_series"])
        except Exception as erro:
            with TRAVA:
                ESTADOS[identificador].update(status="erro", erro=str(erro))
    Thread(target=executar, daemon=True).start()
    return {"id": identificador, **ESTADOS[identificador]}


def estado_exportacao(identificador):
    with TRAVA:
        if identificador not in ESTADOS:
            raise HTTPException(404, "Exportação não encontrada. Gere novamente.")
        return {"id": identificador, **ESTADOS[identificador]}


def arquivo_exportacao(identificador):
    estado = estado_exportacao(identificador)
    if estado["status"] != "pronto":
        raise HTTPException(409, "A exportação ainda não está pronta.")
    return PASTA / f"{identificador}.zip"
