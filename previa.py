"""Prévia paginada da exportação, sem downloads nem geração de ZIP."""
import math

import numpy as np
from fastapi import HTTPException

from exportacao import COLUNAS, PRODUTOS_EXPORTAR, extrair_pontos
from waveheight_grid import sitios_mapa


def consultar_previa(mes, tabela="series", busca="", pagina=1, tamanho=25):
    pontos = sitios_mapa()
    # IDs são sempre os da exportação integral, mesmo após filtrar/paginar.
    encontrados = [(i, p) for i, p in enumerate(pontos, 1)
                   if busca.casefold().strip() in str(p["properties"].get("name", "")).casefold()]
    paginas = max(1, math.ceil(len(encontrados)/tamanho))
    pagina = min(pagina, paginas)
    amostra = encontrados[(pagina-1)*tamanho:pagina*tamanho]
    avisos = []
    linhas = []
    if tabela == "atributos":
        atributos = sorted({k for p in pontos for k in p["properties"]})
        colunas = ["ponto_id", "latitude", "longitude", *atributos]
        for identificador, ponto in amostra:
            lon, lat = ponto["geometry"]["coordinates"][:2]
            linhas.append([identificador, lat, lon, *[ponto["properties"].get(k) for k in atributos]])
        avisos.append("Elevação e registro GPS não representam profundidade ou data de levantamento ecológico.")
    else:
        colunas = ["ponto_id", "sitio", "latitude", "longitude", "mes", *COLUNAS]
        if amostra:
            try:
                dados = extrair_pontos([p for _, p in amostra], incluir_dhw=False, mes=mes)
            except RuntimeError as erro:
                raise HTTPException(409, str(erro)) from erro
            # Mesma grade mensal e seleção espacial da exportação, somente se já estiver em disco.
            from coral_reef_watch import _carregar_cache_mensal
            try:
                grade = _carregar_cache_mensal("CRW_DHW", mes)
            except (OSError, ValueError):
                grade = None
            if grade is None:
                avisos.append("DHW indisponível no cache local deste mês. A exportação completa tentará obtê-lo na NOAA.")
            for j, (identificador, ponto) in enumerate(amostra):
                lon, lat = ponto["geometry"]["coordinates"][:2]
                valores = []
                for produto in PRODUTOS_EXPORTAR[:-1]:
                    d = dados[produto]
                    v = float(d["valores"][0, j]) if d["meses"] else float("nan")
                    valores.append(v if math.isfinite(v) else None)
                dhw = None
                if grade is not None:
                    y = int(np.abs(grade.latitudes-lat).argmin())
                    x = int(np.abs(grade.longitudes-lon).argmin())
                    v = float(grade.valores[y, x])
                    dhw = v if math.isfinite(v) else None
                linhas.append([identificador, ponto["properties"].get("name"), lat, lon, mes, *valores, dhw])
        avisos.append("Valores ausentes aparecem como —; zero é preservado. DHW é o máximo diário de cada mês.")
    return {"tabela": tabela, "mes": mes, "colunas": colunas, "linhas": linhas,
            "pagina": pagina, "paginas": paginas, "tamanho": tamanho,
            "total": len(encontrados), "total_pontos": len(pontos), "avisos": avisos,
            "escopo_exportacao": "Todos os pontos e todo o período disponível; os filtros da prévia não restringem o ZIP."}
