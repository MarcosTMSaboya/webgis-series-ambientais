# Controles e exportação

A aba **Planilha de dados**, no cabeçalho, abre uma prévia somente para leitura.
Também pode ser aberta por **Conferir planilha antes de exportar** no painel
Dados ambientais. A prévia tem busca pelo nome do ponto, páginas de 25, 50 ou
100 linhas, campos separados de ano (digitável) e mês e duas planilhas:
séries mensais e atributos originais.
Os IDs e as colunas de valores são os mesmos da exportação integral.

As consultas começam somente ao abrir a aba. `/previa` lê um mês dos índices
locais e os pontos da página atual. DHW usa somente o cache mensal já disponível,
com aviso quando faltar. Não há download NOAA nem geração de ZIP ao visualizar.
Valores ausentes aparecem como `—`; zero e a precisão dos valores são preservados.
Os atributos GPS não são interpretados como dados de profundidade ou amostragem.

O botão **Exportar todos os pontos (ZIP com CSVs)** inicia a exportação completa
existente. Busca, mês e paginação da prévia não restringem o arquivo exportado;
a exportação ainda inclui todos os pontos e todos os meses disponíveis.

API da prévia: `GET /previa?mes=2020-01&tabela=series&pagina=1&tamanho=25&busca=`.
`tabela` aceita `series` e `atributos`; `tamanho` é limitado a 100. Não há escrita
nos dados de origem. A aba de mapa preserva seus filtros e posição ao alternar.

Validação da prévia: `python -m unittest test_previa.py test_exportacao.py`
e `node test_previa.cjs`. Inclui paginação com IDs estáveis, ausência de downloads,
valores zero/ausentes, carregamento sob demanda e descarte de respostas antigas.

Todos os painéis (mapas de fundo, filtros, grupos/cores, dados ambientais,
escalas e gráfico) podem ser minimizados/restaurados pela barra superior.
`A−` e `A+` diminuem/aumentam a caixa; o canto inferior direito permite
redimensionar livremente. O conteúdo rola dentro da caixa. Arraste pela barra
para reposicionar o painel. O gráfico acompanha o tamanho disponível.

O painel Escalas de cores mostra uma barra para cada parâmetro, com unidades,
marcas e o mês selecionado. O parâmetro ativo é destacado. A clorofila usa
escala logarítmica fixa de 0,01–20 mg/m³ (turbo). WaveHeight usa 0–3 m (viridis).
SST, PAR e KD usam os percentis 2–98 do mês (viridis), exatamente como os rasters.
Meses sem dados são sinalizados. Os limites vêm da mesma função usada no raster.

No painel Dados ambientais, Exportar séries de todos os pontos inicia a geração
em segundo plano. O mapa continua disponível e a interface mostra o progresso
da consulta mensal de DHW e, depois, da escrita dos pontos. Ao terminar, o ZIP
é baixado e permanece um link para repetir o download.

A exportação inclui todo o período disponível, sem os filtros do gráfico,
da camada, do mês ou dos pontos visíveis. Inclui 382 pontos e seis parâmetros,
cobrindo a união dos períodos disponíveis. O DHW mensal da NOAA é incluído
desde janeiro/2012 e corresponde ao máximo diário de cada mês, em °C-semanas.
Campos vazios representam ausência de dado; valores zero são preservados.
O arquivo ZIP contém:

- `series_temporais.csv`: uma linha por ponto/mês e as seis variáveis; `CRW_DHW_C_semanas` contém DHW.
- `pixels_utilizados.csv`: pixel e distância para cada ponto/parâmetro.
- `pontos.geojson`: coordenadas e atributos originais, com `export_ponto_id`.
- `metadados.json`: períodos, colunas, unidades e método por parâmetro.
- `LEIA-ME.txt`: formato, unidades e resumo mensal do DHW.

CSV em UTF-8 com BOM, separador ponto e vírgula, decimal ponto e precisão original.
Os índices dos quatro produtos MODIS devem estar atualizados (`series_cache.py`).
WaveHeight usa a grade NetCDF carregada em memória; DHW consulta as grades
mensais da NOAA e as mantém em `Dados/CRW/mensal` para reutilização. A extração
é vetorizada por produto, para evitar alternar centenas de acessos ao disco por ponto.

API: `POST /exportacoes`, `GET /exportacoes/{id}` e
`GET /exportacoes/{id}/arquivo`. O progresso fica em memória até reiniciar a API;
os ZIPs ficam em `Dados/exportacoes`. Não são iniciados dois trabalhos simultâneos.

Validação: `node test_paineis.cjs`, `node --check mapa.js`,
`python -m unittest test_exportacao.py test_escalas.py test_waveheight_grid.py test_waveheight.py test_series_cache.py`
e `python verificar_exportacao.py`. A verificação completa confere a integridade
do ZIP, todas as linhas e IDs, os 2.292 registros de pixels e até 54 valores de amostra.
