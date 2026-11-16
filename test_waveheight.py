import unittest
from fastapi import HTTPException
from waveheight import dados_waveheight, meses_planilha as meses_waveheight, valor_planilha as valor_waveheight, serie_planilha as serie_waveheight


class WaveHeightTest(unittest.TestCase):
    def test_importacao_completa(self):
        sitios = dados_waveheight()["sitios"]
        self.assertEqual(len(sitios), 64)
        self.assertEqual(sum(len(s["valores"]) for s in sitios.values()), 65664)
        self.assertEqual(meses_waveheight()[0], "1940-01")
        self.assertEqual(meses_waveheight()[-1], "2025-06")
        self.assertEqual(dados_waveheight()["unidade"], "m")
        self.assertEqual(sum(s["coordenadas"] is not None for s in sitios.values()), 62)
        self.assertEqual(sitios["Buraca"]["ponto_mapa"], "Buraca Rasa")
        self.assertEqual(sitios["Arangueira"]["ponto_mapa"], "Arenguera")

    def test_valor_original_e_associacao_espacial(self):
        sitio = dados_waveheight()["sitios"]["RHC30"]
        lon, lat = sitio["coordenadas"]
        resposta = valor_waveheight("1940-01", lat, lon)
        self.assertEqual(resposta["sitio"], "RHC30")
        self.assertAlmostEqual(resposta["valor"], 1.519694328308105)
        self.assertAlmostEqual(resposta["distancia_sitio_km"], 0)
        self.assertIsNone(resposta["pixel_utilizado"])
        self.assertNotEqual(lat, lon)

    def test_mes_ausente_nao_vira_zero(self):
        resposta = valor_waveheight("2026-03", -18, -39)
        self.assertIsNone(resposta["valor"])
        self.assertIn("erro", resposta)

    def test_serie_recortada_sem_extrapolacao(self):
        resposta = serie_waveheight(-18, -39, "2025-01", "2025-12", "RHC30")
        self.assertEqual(resposta["quantidade_meses"], 6)
        self.assertEqual(resposta["serie"][-1]["data"], "2025-06")

    def test_sitio_sem_coordenadas_preservado(self):
        resposta = valor_waveheight("1940-01", -18, -39, "RHS60")
        self.assertIsNotNone(resposta["valor"])
        self.assertIsNone(resposta["distancia_sitio_km"])

    def test_coordenadas_invalidas(self):
        with self.assertRaises(HTTPException):
            valor_waveheight("2020-01", 91, -39)


if __name__ == "__main__":
    unittest.main()
