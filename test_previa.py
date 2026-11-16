import unittest
from unittest.mock import patch

import numpy as np

from coral_reef_watch import GradeAtual
from previa import consultar_previa
from exportacao import PRODUTOS_EXPORTAR, COLUNAS


def pontos_teste():
    return [{"properties": {"name": nome, "ele": 0},
             "geometry": {"coordinates": [-38., -18.]}}
            for nome in ["Primeiro", "Alvo A", "Alvo B"]]


class PreviaTest(unittest.TestCase):
    def test_filtro_paginacao_e_ids_originais_sem_carregar_series(self):
        with patch("previa.sitios_mapa", return_value=pontos_teste()), \
                patch("previa.extrair_pontos") as extrair:
            r = consultar_previa("2020-01", "atributos", "ALVO", 2, 1)
        extrair.assert_not_called()
        self.assertEqual(r["total"], 2)
        self.assertEqual(r["total_pontos"], 3)
        self.assertEqual(r["linhas"][0][0], 3)
        self.assertEqual(r["linhas"][0][r["colunas"].index("ele")], 0)

    def test_series_preservam_colunas_da_exportacao_zeros_e_ausentes(self):
        dados = {p: {"meses": ["2020-01"], "valores": np.array([[0., np.nan]])}
                 for p in PRODUTOS_EXPORTAR[:-1]}
        dados["SST"]["meses"] = []
        grade = GradeAtual("CRW_DHW", "2020-01", np.array([-18.]),
                           np.array([-38.]), np.array([[8.5]]))
        with patch("previa.sitios_mapa", return_value=pontos_teste()), \
                patch("previa.extrair_pontos", return_value=dados) as extrair, \
                patch("coral_reef_watch._carregar_cache_mensal", return_value=grade), \
                patch("coral_reef_watch.grade_atual") as remoto:
            r = consultar_previa("2020-01", "series", "alvo", 1, 25)
        remoto.assert_not_called()
        self.assertEqual(extrair.call_args.kwargs, {"incluir_dhw": False, "mes": "2020-01"})
        self.assertEqual(r["colunas"][5:], COLUNAS)
        self.assertEqual(r["linhas"][0][0], 2)
        self.assertEqual(r["linhas"][0][5], 0)
        self.assertIsNone(r["linhas"][0][6])
        self.assertIsNone(r["linhas"][1][5])
        self.assertEqual(r["linhas"][0][-1], 8.5)

    def test_sem_resultados_nao_abre_dados_e_pagina_e_limitada(self):
        with patch("previa.sitios_mapa", return_value=pontos_teste()), \
                patch("previa.extrair_pontos") as extrair:
            r = consultar_previa("2020-01", "series", "inexistente", 100, 25)
        extrair.assert_not_called()
        self.assertEqual(r["pagina"], 1)
        self.assertEqual(r["linhas"], [])

    def test_dhw_ausente_nao_dispara_download(self):
        dados = {p: {"meses": [], "valores": np.empty((0, 1))}
                 for p in PRODUTOS_EXPORTAR[:-1]}
        with patch("previa.sitios_mapa", return_value=pontos_teste()), \
                patch("previa.extrair_pontos", return_value=dados), \
                patch("coral_reef_watch._carregar_cache_mensal", return_value=None), \
                patch("coral_reef_watch.grade_atual") as remoto:
            r = consultar_previa("2020-01", tamanho=1)
        remoto.assert_not_called()
        self.assertIsNone(r["linhas"][0][-1])
        self.assertIn("cache local", r["avisos"][0])


if __name__ == "__main__":
    unittest.main()
