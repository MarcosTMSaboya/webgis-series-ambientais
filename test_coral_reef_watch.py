import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import numpy as np
from PIL import Image
from fastapi import HTTPException
from urllib.error import HTTPError

import coral_reef_watch as crw
from coral_reef_watch import GradeAtual
from escalas import escala_raster


class CoralReefWatchTest(unittest.TestCase):
    def tearDown(self):
        crw.limpar_cache()

    def test_consulta_usa_dataset_diario_e_recorte_local(self):
        url = crw._url_consulta("CRW_DHW")
        self.assertIn("noaacrwdhwDaily.csvp", url)
        self.assertIn("degree_heating_week[(last)]", url)
        self.assertIn("(-20.448)", url)

    def test_consulta_mensal_limita_periodo_e_grade(self):
        url = crw._url_consulta("CRW_HOTSPOT", "2020-02")
        self.assertIn("noaacrwhotspotDaily.csvp", url)
        self.assertIn("hotspot[(2020-02-01T00:00:00Z):(2020-02-29T23:59:59Z)]", url)
        self.assertIn("[(-20.448):(-17.034)]", url)

    def test_url_da_serie_crw_consulta_um_pixel_para_o_periodo_todo(self):
        url = crw._url_serie_ponto("CRW_DHW", -18.48, -38.48, "2012-01", "2020-02")
        query = unquote(urlsplit(url).query)

        self.assertIn("noaacrwdhwDaily.csvp", url)
        self.assertIn("degree_heating_week[(2012-01-01T00:00:00Z):(2020-02-29T23:59:59Z)]", query)
        self.assertIn("[(-18.475):(-18.475)][(-38.475):(-38.475)]", query)

    def test_serie_historica_agrega_maximo_diario_e_preserva_meses_vazios(self):
        conteudo = (
            "time (UTC),latitude (degrees_north),longitude (degrees_east),"
            "degree_heating_week (degree_Celsius_weeks)\n"
            "2020-01-01T12:00:00Z,-18.475,-38.475,2\n"
            "2020-01-15T12:00:00Z,-18.475,-38.475,8\n"
            "2020-02-01T12:00:00Z,-18.475,-38.475,NaN\n"
            "2020-03-01T12:00:00Z,-18.475,-38.475,4\n"
        ).encode()
        crw._serie_historica_cache.cache_clear()
        with patch.object(crw, "_baixar_csv", return_value=conteudo) as baixar:
            resposta = crw.serie_historica("CRW_DHW", -18.48, -38.48, "2020-01", "2020-03")

        self.assertEqual([item["valor"] for item in resposta["serie"]], [8.0, None, 4.0])
        self.assertEqual(resposta["dias_amostrados"], 3)
        self.assertEqual(resposta["pixel_utilizado"], {"latitude": -18.475, "longitude": -38.475})
        self.assertEqual(resposta["resumo"], "máximo diário de cada mês")
        baixar.assert_called_once()
        crw._serie_historica_cache.cache_clear()

    def test_serie_historica_usa_cache_local_mas_marca_a_resposta_incompleta(self):
        grade = GradeAtual(
            "CRW_DHW",
            "2020-01",
            np.array([-18.475, -18.525]),
            np.array([-38.475, -38.525]),
            np.array([[8.0, 4.0], [1.0, 2.0]]),
            31,
        )
        crw._serie_historica_cache.cache_clear()
        with patch.object(
            crw, "_baixar_csv", side_effect=HTTPException(504, "NOAA timeout")
        ), patch.object(
            crw, "_carregar_cache_mensal", side_effect=[grade, None]
        ):
            resposta = crw.serie_historica("CRW_DHW", -18.48, -38.48, "2020-01", "2020-02")

        self.assertTrue(resposta["incompleto"])
        self.assertEqual(resposta["meses_em_cache"], 1)
        self.assertEqual(resposta["erro"], "NOAA timeout")
        self.assertEqual([item["valor"] for item in resposta["serie"]], [8.0, None])
        crw._serie_historica_cache.cache_clear()

    def test_serie_historica_rejeita_periodo_invertido(self):
        with self.assertRaises(HTTPException) as contexto:
            crw.serie_historica("CRW_HOTSPOT", -18, -38, "2021-01", "2020-12")

        self.assertEqual(contexto.exception.status_code, 400)

    def test_escala_dhw_marca_limiares_noaa(self):
        escala = escala_raster("CRW_DHW", np.array([0.0, 4.0, 8.0]))
        self.assertEqual(escala["marcas"], [0, 4, 8, 12, 16, 20])
        self.assertEqual((escala["minimo"], escala["maximo"]), (0.0, 20.0))

    def test_grade_atual_faz_cache_e_valor_mais_proximo(self):
        grade = GradeAtual(
            "CRW_DHW",
            "2026-11-03",
            np.array([-18.475, -18.525]),
            np.array([-38.475, -38.525]),
            np.array([[0.0, 4.0], [8.0, np.nan]]),
        )
        with patch.object(crw, "_ler_grade", return_value=grade) as carregar:
            resposta = crw.valor_no_ponto("CRW_DHW", -18.48, -38.48)
            info = crw.informacao_raster("CRW_DHW")

        self.assertEqual(resposta["valor"], 0.0)
        self.assertEqual(resposta["data"], "2026-11-03")
        self.assertEqual(info["celulas_com_estresse"], 2)
        carregar.assert_called_once_with("CRW_DHW")

    def test_agregacao_mensal_usa_maximo_e_ignora_dia_do_mes_seguinte(self):
        conteudo = (
            "time (UTC),latitude (degrees_north),longitude (degrees_east),"
            "degree_heating_week (degree_Celsius_weeks)\n"
            "2020-01-01T12:00:00Z,-18.475,-38.475,2\n"
            "2020-01-15T12:00:00Z,-18.475,-38.475,8\n"
            "2020-02-01T12:00:00Z,-18.475,-38.475,20\n"
        ).encode()
        with patch.object(crw, "urlopen", return_value=BytesIO(conteudo)):
            grade = crw._ler_grade("CRW_DHW", "2020-01")

        self.assertEqual(grade.data, "2020-01")
        self.assertEqual(grade.dias_amostrados, 2)
        self.assertEqual(grade.valores[0, 0], 8.0)

    def test_consulta_mensal_tenta_novamente_em_erro_502_transitorio(self):
        conteudo = (
            "time (UTC),latitude (degrees_north),longitude (degrees_east),"
            "degree_heating_week (degree_Celsius_weeks)\n"
            "2020-01-01T12:00:00Z,-18.475,-38.475,8\n"
        ).encode()
        erro = HTTPError("https://noaa.invalid", 502, "Bad Gateway", {}, BytesIO(b"temporary"))
        with patch.object(crw, "urlopen", side_effect=[erro, BytesIO(conteudo)]) as consultar, \
                patch.object(crw.time, "sleep") as esperar:
            grade = crw._ler_grade("CRW_DHW", "2020-01")

        self.assertEqual(grade.valores[0, 0], 8.0)
        self.assertEqual(consultar.call_count, 2)
        esperar.assert_called_once_with(1)

    def test_erro_noaa_informa_o_mes_consultado(self):
        erro = HTTPError("https://noaa.invalid", 502, "Bad Gateway", {}, BytesIO(b"temporary"))
        with patch.object(crw, "urlopen", side_effect=[erro, erro, erro]), \
                patch.object(crw.time, "sleep"):
            with self.assertRaises(HTTPException) as contexto:
                crw._ler_grade("CRW_DHW", "2020-01")

        self.assertIn("HTTP 502", contexto.exception.detail)
        self.assertIn("2020-01", contexto.exception.detail)

    def test_resumo_mensal_e_persistido_em_cache_local(self):
        grade = GradeAtual(
            "CRW_DHW",
            "2020-01",
            np.array([-18.475]),
            np.array([-38.475]),
            np.array([[8.0]]),
            31,
        )
        with TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "CRW_DHW_2020-01.npz"
            with patch.object(crw, "_arquivo_cache_mensal", return_value=caminho), \
                    patch.object(crw, "_ler_grade", return_value=grade) as carregar:
                primeira = crw.grade_atual("CRW_DHW", "2020-01")
                crw.limpar_cache()
                segunda = crw.grade_atual("CRW_DHW", "2020-01")

        self.assertEqual(primeira.valores[0, 0], segunda.valores[0, 0])
        self.assertEqual(segunda.dias_amostrados, 31)
        carregar.assert_called_once_with("CRW_DHW", "2020-01")

    def test_raster_png_transparente_em_celulas_sem_estresse(self):
        grade = GradeAtual(
            "CRW_HOTSPOT",
            "2026-11-03",
            np.array([-18.475, -18.525]),
            np.array([-38.475, -38.525]),
            np.array([[-1.0, 1.0], [3.0, np.nan]]),
        )
        with patch.object(crw, "_ler_grade", return_value=grade):
            imagem = Image.open(BytesIO(crw.raster_png("CRW_HOTSPOT"))).convert("RGBA")

        self.assertEqual(imagem.size, (2, 2))
        self.assertEqual(imagem.getpixel((0, 0))[3], 0)
        self.assertEqual(imagem.getpixel((1, 0))[3], 255)
        self.assertEqual(imagem.getpixel((1, 1))[3], 0)


if __name__ == "__main__":
    unittest.main()
