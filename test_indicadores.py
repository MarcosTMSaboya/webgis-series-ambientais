import json
import unittest
from unittest.mock import patch

from indicadores import resumir_serie


class IndicadoresTest(unittest.TestCase):
    def resumo(self, produto, valores):
        return resumir_serie(produto, [
            {"data": f"2020-{i:02}", "valor": v} for i, v in enumerate(valores, 1)])

    def test_momentos_cobertura_zero_e_ausentes(self):
        r = self.resumo("CHL", [0, 1, None, float("nan"), 2, 3])
        m = {v["codigo"]: v["valor"] for v in r["metricas"]}
        self.assertEqual(r["meses_validos"], 4)
        self.assertEqual(r["meses_esperados"], 6)
        self.assertTrue(r["incompleto"])
        self.assertEqual(m["media"], 1.5)
        self.assertAlmostEqual(m["sd"], 1.25**0.5)
        self.assertAlmostEqual(m["cv"], 1.25**0.5/1.5)
        self.assertAlmostEqual(m["assimetria"], 0)
        self.assertAlmostEqual(m["curtose"], -1.36)
        json.dumps(r, allow_nan=False)

    def test_constante_vazia_e_lacuna_no_calendario(self):
        r = self.resumo("SST", [0]*4)
        m = {v["codigo"]: v["valor"] for v in r["metricas"]}
        self.assertEqual(m["sd"], 0)
        for codigo in ("cv", "assimetria", "curtose"):
            self.assertIsNone(m[codigo])
        self.assertEqual(self.resumo("CHL", [None])["metricas"], [])
        r = resumir_serie("CHL", [{"data": "2020-01", "valor": 2},
                                   {"data": "2020-03", "valor": 4}])
        self.assertEqual(r["meses_esperados"], 3)
        self.assertTrue(r["incompleto"])

    def test_dhw_limiares_estritos_e_anos_incompletos(self):
        serie = [{"data": f"2020-{i:02}", "valor": v}
                 for i, v in enumerate([0, 4, 8, 9]+[0]*8, 1)]
        serie.append({"data": "2021-01", "valor": 20})
        r = resumir_serie("CRW_DHW", serie)
        m = {v["codigo"]: v["valor"] for v in r["metricas"]}
        self.assertEqual(m["meses_gt_4"], 3)
        self.assertEqual(m["meses_gt_8"], 2)
        self.assertEqual(m["maximo"], 20)
        self.assertEqual(m["media_maximos_anuais"], 9)
        self.assertEqual(m["anos_completos"], 1)
        self.assertFalse(r["anuais"][1]["completo"])

    def test_api_reaproveita_serie_e_preserva_sinalizacao_parcial(self):
        import app
        fonte = {"produto": "CHL", "serie": [{"data": "2020-01", "valor": 2}],
                 "incompleto": True}
        with patch.object(app, "_consultar_serie", return_value=fonte) as consulta:
            r = app.consultar_serie("CHL", -18, -38)
        consulta.assert_called_once()
        self.assertTrue(r["indicadores"]["incompleto"])
        self.assertNotIn("indicadores", fonte)


if __name__ == "__main__":
    unittest.main()
