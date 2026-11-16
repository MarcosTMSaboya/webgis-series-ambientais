import unittest
from unittest.mock import patch
import numpy as np
import xarray as xr
from app import PRODUTOS, VARIAVEIS_PADRAO, arquivos_produto
from series_cache import serie_indexada, _verificacoes


class SeriesCacheTest(unittest.TestCase):
    def test_valores_e_pixel_iguais_ao_netcdf(self):
        for produto in PRODUTOS:
            arquivos = arquivos_produto(produto)
            for item in (arquivos[0], arquivos[len(arquivos)//2], arquivos[-1]):
                with self.subTest(produto=produto, mes=item["mes"]):
                    with xr.open_dataset(item["arquivo"], engine="netcdf4", mask_and_scale=True) as ds:
                        original = ds[VARIAVEIS_PADRAO[produto]].sel(lat=-18.0, lon=-39.0, method="nearest").squeeze(drop=True)
                        indice = serie_indexada(produto, arquivos, VARIAVEIS_PADRAO[produto], -18, -39, item["mes"], item["mes"])
                        self.assertIsNotNone(indice)
                        self.assertEqual(len(indice["serie"]), 1)
                        esperado = float(original.values)
                        self.assertEqual(indice["serie"][0]["valor"], esperado if np.isfinite(esperado) else None)
                        self.assertEqual(indice["pixel_utilizado"], {"latitude": float(original.lat), "longitude": float(original.lon)})

    def test_fontes_alteradas_nao_usam_cache_antigo(self):
        with patch.dict(_verificacoes, {}, clear=True), patch("series_cache.assinatura", return_value=[]):
            self.assertIsNone(serie_indexada("CHL", arquivos_produto("CHL"), "chlor_a", -18, -39, "2020-01", "2020-12"))

    def test_periodo_vazio(self):
        indice = serie_indexada("CHL", arquivos_produto("CHL"), "chlor_a", -18, -39, "1900-01", "1900-12")
        self.assertEqual(indice, {"serie": [], "pixel_utilizado": None})


if __name__ == "__main__":
    unittest.main()
