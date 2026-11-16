import unittest
from unittest.mock import patch

import app


class SerieCRWApiTest(unittest.TestCase):
    def test_api_encaminha_os_dois_produtos_crw_para_a_serie_historica(self):
        for produto in ("CRW_DHW", "CRW_HOTSPOT"):
            with self.subTest(produto=produto), patch.object(
                app, "serie_crw", return_value={"produto": produto}
            ) as serie:
                resposta = app.consultar_serie(
                    produto, -18.48, -38.48, "2012-01", "2025-12"
                )

            self.assertEqual(resposta, {"produto": produto})
            serie.assert_called_once_with(
                produto, -18.48, -38.48, "2012-01", "2025-12"
            )


if __name__ == "__main__":
    unittest.main()
