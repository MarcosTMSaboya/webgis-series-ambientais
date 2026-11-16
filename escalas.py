"""Limites e cores usados tanto pelo raster quanto pela legenda."""
import numpy as np
from matplotlib import colormaps
from fastapi import HTTPException

CONFIG = {
    "CHL": ("Clorofila-a", "mg/m³"), "SST": ("Temperatura superficial", "°C"),
    "PAR": ("Radiação fotossintética", "mol/m²/dia"), "KD": ("Kd 490", "m⁻¹"),
    "WAVEHEIGHT": ("Altura significativa de ondas", "m"),
    "CRW_DHW": ("DHW — estresse térmico acumulado", "°C-semanas"),
    "CRW_HOTSPOT": ("HotSpot — estresse térmico diário", "°C")}


def escala_raster(produto, matriz):
    if produto == "CHL":
        minimo, maximo, mapa, tipo = .01, 20., "turbo", "logaritmica"
    elif produto == "WAVEHEIGHT":
        minimo, maximo, mapa, tipo = 0., 3., "viridis", "linear"
    elif produto == "CRW_DHW":
        minimo, maximo, mapa, tipo = 0., 20., "YlOrRd", "linear"
    elif produto == "CRW_HOTSPOT":
        minimo, maximo, mapa, tipo = 0., 5., "YlOrRd", "linear"
    else:
        validos = matriz[np.isfinite(matriz)]
        if not validos.size:
            raise HTTPException(404, "Mês sem valores válidos.")
        minimo, maximo = (float(v) for v in np.percentile(validos, [2, 98]))
        if maximo <= minimo:
            maximo = minimo + max(abs(minimo)*.01, .000001)
        mapa, tipo = "viridis", "linear"
    if tipo == "logaritmica":
        valores = np.geomspace(minimo, maximo, 5)
    elif produto == "CRW_DHW":
        valores = np.array([0., 4., 8., 12., 16., 20.])
    elif produto == "CRW_HOTSPOT":
        valores = np.array([0., 1., 2.5, 3.75, 5.])
    else:
        valores = np.linspace(minimo, maximo, 5)
    cores = ["#%02x%02x%02x" % tuple(int(c*255) for c in colormaps[mapa](t)[:3]) for t in np.linspace(0, 1, 33)]
    return {"produto": produto, "nome": CONFIG[produto][0], "unidade": CONFIG[produto][1],
            "minimo": minimo, "maximo": maximo, "tipo": tipo, "cores": cores, "marcas": valores.tolist(),
            "limites": "limites de referência NOAA CRW" if produto.startswith("CRW_") else
            "fixos" if produto in ("CHL", "WAVEHEIGHT") else "percentis 2–98 do mês"}
