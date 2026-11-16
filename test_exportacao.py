import csv
from io import TextIOWrapper
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from fastapi import HTTPException

import exportacao
from coral_reef_watch import GradeAtual


class ExportacaoTest(unittest.TestCase):
    def test_meses_entre_inclui_limites_e_virada_de_ano(self):
        self.assertEqual(
            exportacao._meses_entre("2020-11", "2021-02"),
            ["2020-11", "2020-12", "2021-01", "2021-02"],
        )

    def test_extrair_dhw_preserva_meses_sem_dados(self):
        pontos = [
            {"geometry": {"coordinates": [-38.0, -18.0]}},
            {"geometry": {"coordinates": [-39.0, -19.0]}},
        ]
        grade = GradeAtual(
            "CRW_DHW",
            "2020-02",
            np.array([-18.0, -19.0]),
            np.array([-38.0, -39.0]),
            np.array([[4.0, 8.0], [12.0, 16.0]]),
        )
        progresso = []
        with patch("exportacao._meses_entre", return_value=["2020-01", "2020-02"]), \
                patch("coral_reef_watch.grade_atual",
                      side_effect=[HTTPException(404, "sem dados"), grade]):
            resposta = exportacao._extrair_dhw(
                pontos, lambda etapa, concluido, total: progresso.append((etapa, concluido, total)))

        self.assertEqual(resposta["meses"], ["2020-01", "2020-02"])
        np.testing.assert_array_equal(resposta["valores"][0], [np.nan, np.nan])
        np.testing.assert_array_equal(resposta["valores"][1], [4.0, 16.0])
        self.assertEqual(resposta["variavel"], "degree_heating_week")
        self.assertEqual(resposta["pixels"][1], {"latitude": -19.0, "longitude": -39.0})
        self.assertEqual(progresso[-1], ("dhw", 2, 2))

    def test_extrair_dhw_identifica_mes_com_falha_noaa(self):
        pontos = [{"geometry": {"coordinates": [-38.0, -18.0]}}]
        with patch("exportacao._meses_entre", return_value=["2020-01"]), \
                patch("coral_reef_watch.grade_atual",
                      side_effect=HTTPException(502, "NOAA ERDDAP respondeu HTTP 502")):
            with self.assertRaises(HTTPException) as contexto:
                exportacao._extrair_dhw(pontos)

        self.assertEqual(contexto.exception.status_code, 502)
        self.assertIn("2020-01", contexto.exception.detail)
        self.assertIn("HTTP 502", contexto.exception.detail)

    def test_zip_exporta_coluna_dhw_unidade_e_periodo(self):
        ponto = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-38.0, -18.0]},
            "properties": {"name": "Ponto A"},
        }
        extraidos = {}
        for produto in exportacao.PRODUTOS_EXPORTAR:
            extraidos[produto] = {
                "meses": ["2020-01"],
                "valores": np.array([[7.5]]),
                "variavel": "degree_heating_week" if produto == "CRW_DHW" else produto.lower(),
                "pixels": [{"latitude": -18.0, "longitude": -38.0}],
                "distancias": [0.0],
            }

        with TemporaryDirectory() as diretorio:
            destino = Path(diretorio) / "export.zip"
            with patch("waveheight_grid.sitios_mapa", return_value=[ponto]), \
                    patch("exportacao.extrair_pontos", return_value=extraidos):
                meta = exportacao.gerar_zip(destino)

            with zipfile.ZipFile(destino) as arquivo:
                with TextIOWrapper(
                    arquivo.open("series_temporais.csv"), encoding="utf-8-sig", newline=""
                ) as texto:
                    linhas = list(csv.DictReader(texto, delimiter=";"))
                metadados = json.loads(arquivo.read("metadados.json"))
                leia_me = arquivo.read("LEIA-ME.txt").decode("utf-8")
                with TextIOWrapper(arquivo.open("indicadores.csv"), encoding="utf-8-sig") as texto:
                    indicadores = list(csv.DictReader(texto, delimiter=";"))
                with TextIOWrapper(arquivo.open("atributos_pontos.csv"), encoding="utf-8-sig") as texto:
                    atributos = list(csv.DictReader(texto, delimiter=";"))
                with TextIOWrapper(arquivo.open("resumos_anuais.csv"), encoding="utf-8-sig") as texto:
                    anuais = list(csv.DictReader(texto, delimiter=";"))

        self.assertEqual(linhas[0]["CRW_DHW_C_semanas"], "7.5")
        self.assertIn("CRW_DHW", exportacao.PRODUTOS_EXPORTAR)
        self.assertEqual(meta["periodos"]["CRW_DHW"]["inicio"], "2020-01")
        self.assertEqual(metadados["unidades"]["CRW_DHW"], "°C-semanas")
        self.assertEqual(metadados["colunas_valores"]["CRW_DHW"], "CRW_DHW_C_semanas")
        self.assertIn("máximo diário mensal", leia_me)
        media_chl = next(r for r in indicadores if r["produto"] == "CHL" and r["indicador"] == "media")
        self.assertEqual(media_chl["valor"], "7.5")
        self.assertEqual(media_chl["ponto_id"], "1")
        self.assertEqual(atributos[0]["name"], "Ponto A")
        self.assertEqual(anuais[0]["ano_completo"], "False")


if __name__ == "__main__":
    unittest.main()
