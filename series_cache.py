"""Índice local das séries NetCDF. Construção: python series_cache.py."""
import json
from pathlib import Path
from functools import lru_cache
from time import monotonic
import numpy as np

BASE = Path(__file__).resolve().parent
CACHE = BASE / "Dados" / "cache_series"
_verificacoes = {}


def assinatura(arquivos):
    fontes = []
    for item in arquivos:
        if item["mes"] is not None:
            estado = item["arquivo"].stat()
            fontes.append([str(item["arquivo"].relative_to(BASE)), estado.st_size, estado.st_mtime_ns])
    return fontes


@lru_cache(maxsize=4)
def abrir_indice(produto, versao):
    meta = json.loads((CACHE / f"{produto}.json").read_text(encoding="utf-8"))
    cube = np.load(CACHE / f"{produto}.npy", mmap_mode="r")
    return meta, cube


def serie_indexada(produto, arquivos, variavel, lat, lon, inicio, fim):
    """Retorna None quando o índice não existe ou as fontes foram atualizadas."""
    caminho = CACHE / f"{produto}.json"
    if not caminho.exists():
        return None
    versao = caminho.stat().st_mtime_ns
    meta, cube = abrir_indice(produto, versao)
    chave = (produto, versao)
    verificacao = _verificacoes.get(chave)
    if verificacao is None or monotonic() - verificacao[0] >= 30:
        verificacao = (monotonic(), meta["fontes"] == assinatura(arquivos))
        _verificacoes[chave] = verificacao
    if not verificacao[1] or meta["variavel"] != variavel:
        return None
    def vizinho(coordenadas, valor):
        # Mesmo desempate do xarray/pandas: maior coordenada.
        coords = np.asarray(coordenadas)
        dist = abs(coords - valor)
        candidatos = np.flatnonzero(dist == dist.min())
        return int(candidatos[np.argmax(coords[candidatos])])
    y, x = vizinho(meta["lat"], lat), vizinho(meta["lon"], lon)
    serie = []
    for i, mes in enumerate(meta["meses"]):
        if inicio <= mes <= fim:
            valor = float(cube[i, y, x])
            serie.append({"data": mes, "valor": valor if np.isfinite(valor) else None})
    return {"serie": serie, "pixel_utilizado": {"latitude": meta["lat"][y], "longitude": meta["lon"][x]} if serie else None}


def construir():
    from netCDF4 import Dataset
    from app import PRODUTOS, VARIAVEIS_PADRAO, arquivos_produto
    CACHE.mkdir(exist_ok=True)
    for produto in PRODUTOS:
        arquivos = [a for a in arquivos_produto(produto) if a["mes"] is not None]
        if not arquivos:
            continue
        destino = CACHE / f"{produto}.json"
        fontes = assinatura(arquivos)
        if destino.exists() and (CACHE / f"{produto}.npy").exists():
            meta = json.loads(destino.read_text(encoding="utf-8"))
            if meta["fontes"] == fontes and meta["variavel"] == VARIAVEIS_PADRAO[produto]:
                print(f"{produto}: índice atualizado", flush=True)
                continue
        temporario = CACHE / f"{produto}.tmp.npy"
        cube = None
        try:
            for i, item in enumerate(arquivos):
                with Dataset(item["arquivo"]) as ds:
                    nome_lat = next(n for n in ("lat", "latitude") if n in ds.variables)
                    nome_lon = next(n for n in ("lon", "longitude") if n in ds.variables)
                    lat, lon = np.asarray(ds[nome_lat][:]), np.asarray(ds[nome_lon][:])
                    var = ds[VARIAVEIS_PADRAO[produto]]
                    valores = np.ma.asarray(var[:]).astype(np.float64).filled(np.nan).squeeze()
                    dims = [d for d in var.dimensions if len(ds.dimensions[d]) > 1]
                    valores = np.transpose(valores, (dims.index(ds[nome_lat].dimensions[0]), dims.index(ds[nome_lon].dimensions[0])))
                    if cube is None:
                        lat_ref, lon_ref = lat.copy(), lon.copy()
                        cube = np.lib.format.open_memmap(temporario, mode="w+", dtype="float64",
                                                         shape=(len(arquivos), len(lat), len(lon)))
                    if not np.array_equal(lat_ref, lat) or not np.array_equal(lon_ref, lon):
                        raise ValueError(f"Grade diferente em {item['arquivo']}")
                    cube[i] = valores
                if (i+1) % 50 == 0:
                    print(f"{produto}: {i+1}/{len(arquivos)} meses", flush=True)
            cube.flush()
            del cube
            cube = None
            temporario.replace(CACHE / f"{produto}.npy")
            meta = {"variavel": VARIAVEIS_PADRAO[produto], "fontes": fontes,
                    "meses": [a["mes"] for a in arquivos], "lat": lat_ref.tolist(), "lon": lon_ref.tolist()}
            tmp_meta = destino.with_suffix(".tmp.json")
            tmp_meta.write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
            tmp_meta.replace(destino)
            print(f"{produto}: pronto ({len(arquivos)} meses)", flush=True)
        finally:
            if cube is not None:
                del cube


if __name__ == "__main__":
    construir()
