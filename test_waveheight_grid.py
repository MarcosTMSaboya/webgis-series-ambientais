import unittest
from io import BytesIO
import numpy as np
import xarray as xr
from PIL import Image
from fastapi import HTTPException
from waveheight_grid import (FONTE, grade, sitios_mapa, valor_grid, serie_grid,
                             pontos_grid, raster_grid, raster_info_grid)


class WaveHeightGridTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with xr.open_dataset(FONTE, engine="netcdf4") as ds:
            cls.original = ds.swh.load()

    def test_historico_de_todos_os_382_pontos_igual_ao_original(self):
        pontos = sitios_mapa()
        self.assertEqual(len(pontos), 382)
        for ponto in pontos:
            lon, lat = ponto["geometry"]["coordinates"][:2]
            with self.subTest(sitio=ponto["properties"]["name"]):
                esperado = self.original.sel(latitude=lat, longitude=lon, method="nearest")
                resposta = serie_grid(lat, lon, "1940-01", "2025-06")
                self.assertEqual(resposta["quantidade_meses"], 1026)
                np.testing.assert_equal(np.array([r["valor"] if r["valor"] is not None else np.nan for r in resposta["serie"]]), esperado.values)
                self.assertEqual(resposta["pixel_utilizado"], {"latitude": float(esperado.latitude), "longitude": float(esperado.longitude)})
                self.assertTrue(np.isfinite(esperado.values).any())

    def test_camada_pontual_inclui_todos_os_sitios(self):
        dados = pontos_grid("2020-01")
        self.assertEqual(len(dados["features"]), 382)
        self.assertTrue(all(f["properties"]["valor"] is not None for f in dados["features"]))

    def test_coordenada_fora_da_cobertura_nao_extrapola(self):
        with self.assertRaises(HTTPException) as contexto:
            valor_grid("2020-01", 0, 0)
        self.assertEqual(contexto.exception.status_code, 404)

    def test_mes_sem_registro(self):
        self.assertIsNone(valor_grid("2026-01", -18, -39)["valor"])
        self.assertEqual(serie_grid(-18, -39, "2025-01", "2025-12")["quantidade_meses"], 6)

    def test_consulta_por_nome_do_ponto(self):
        p = sitios_mapa()[0]
        lon, lat = p["geometry"]["coordinates"][:2]
        por_nome = valor_grid("2020-01", 0, 0, p["properties"]["name"])
        self.assertEqual(por_nome["valor"], valor_grid("2020-01", lat, lon)["valor"])

    def test_raster_e_limites(self):
        with Image.open(BytesIO(raster_grid("2020-01"))) as imagem:
            self.assertEqual(imagem.size, (29, 25))
            self.assertEqual(imagem.mode, "RGBA")
        self.assertAlmostEqual(raster_info_grid("2020-01")["bounds"]["norte"], -13.72)
        self.assertEqual(grade()["unidade"], "m")


if __name__ == "__main__":
    unittest.main()
