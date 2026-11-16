import unittest
import numpy as np
from escalas import escala_raster
from app import raster_info


class EscalasTest(unittest.TestCase):
    def test_clorofila_logaritmica(self):
        escala = escala_raster("CHL", np.array([1.]))
        self.assertEqual((escala["minimo"], escala["maximo"]), (.01, 20))
        np.testing.assert_allclose(escala["marcas"][2], np.sqrt(.01*20))

    def test_percentis_ignoram_ausentes_e_escala_constante(self):
        escala = escala_raster("SST", np.array([0., 1., 2., 3., np.nan]))
        np.testing.assert_allclose([escala["minimo"], escala["maximo"]], np.percentile([0,1,2,3], [2,98]))
        constante = escala_raster("KD", np.array([2., 2.]))
        self.assertGreater(constante["maximo"], constante["minimo"])

    def test_cinco_rasters_fornecem_escala_e_gradiente(self):
        for produto in ("CHL", "SST", "PAR", "KD", "WAVEHEIGHT"):
            with self.subTest(produto=produto):
                escala = raster_info(produto, "2020-01")["escala"]
                self.assertEqual(len(escala["cores"]), 33)
                self.assertEqual(len(escala["marcas"]), 5)
                self.assertLess(escala["minimo"], escala["maximo"])


if __name__ == "__main__":
    unittest.main()
