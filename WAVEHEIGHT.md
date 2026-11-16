# WaveHeight no WebGIS

A fonte ativa é `Dados/WAVEHEIGHT/waveheight.nc`, cópia do arquivo
`data_stream-wamd_stepType-avgua.nc` indicado pelo usuário. A variável `swh`
representa a altura significativa combinada de ondas de vento e swell, em metros.
São 1.026 registros mensais, de janeiro/1940 a junho/2025, numa grade de 25 × 29
células com espaçamento de 0,5° (~55 km na direção norte-sul).

Todos os 382 pontos de `Pontos_Clean.geojson` são consultados pelas suas próprias
coordenadas. O valor vem do pixel mais próximo da grade original, sem interpolação,
e a interface informa o centro do pixel e a distância ao ponto. Pontos próximos
podem compartilhar o mesmo pixel e o mesmo valor. Valores ausentes não viram zero.
Coordenadas fora da cobertura são rejeitadas. Meses posteriores a junho/2025 não
são extrapolados. A série do gráfico mantém o período 2012–2025; a API permite
consultar todo o histórico desde 1940.

O NetCDF é carregado uma vez em memória (~3 MB decodificado) e fechado, preservando
o carregamento rápido das séries. Reinicie a API após substituir esse arquivo.
A camada ambiental usa o raster original, com escala de cores de 0–3 m.

Rotas:

- `/catalogo` e `/meses?produto=WAVEHEIGHT`
- `/valor?produto=WAVEHEIGHT&data=2020-01&lat=-18&lon=-39`
- `/serie?produto=WAVEHEIGHT&lat=-18&lon=-39&inicio=1940-01&fim=2025-06`
- `/raster-info?produto=WAVEHEIGHT&data=2020-01`
- `/raster?produto=WAVEHEIGHT&data=2020-01`
- `/waveheight/sitios` (todos os pontos do mapa)
- `/waveheight/pontos?data=2020-01` (GeoJSON com valor e pixel de cada ponto)

`/valor` e `/serie` aceitam também `sitio=NOME_EXATO_DO_PONTO`. Os identificadores
da planilha que já tinham coordenadas associadas continuam sendo aceitos.
Identificadores sem coordenadas cadastradas, como RHS60 e Tim1 da planilha antiga,
precisam de uma posição ou do nome correto no mapa. Isso não impede a consulta
por coordenadas de nenhum dos 382 pontos atuais.

A planilha e `Dados/waveheight.json` foram preservados como fonte anterior.
As funções `*_planilha` em `waveheight.py` permitem comparar a importação antiga;
o mapa e a API utilizam o NetCDF.

Validação: `python -m unittest test_waveheight_grid.py test_waveheight.py test_series_cache.py`
e `node --check mapa.js`. O teste da grade compara os 1.026 meses de cada um dos
382 pontos com a seleção direta no NetCDF original.
