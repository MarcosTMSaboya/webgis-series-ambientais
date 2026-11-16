# Índice de séries temporais

`series_cache.py` prepara uma matriz local por produto em `Dados/cache_series`.
As consultas leem somente o pixel solicitado, via memória mapeada, sem abrir
um NetCDF para cada mês a cada clique. Os arquivos de origem são preservados.
O índice contém todos os meses disponíveis; as consultas continuam aceitando
os filtros `inicio` e `fim`, com 2012–2025 como período padrão.

O índice usa os valores decodificados de cada arquivo, preserva valores ausentes
e seleciona o mesmo pixel mais próximo que xarray, incluindo o desempate pela
maior coordenada. As fontes são verificadas por caminho, tamanho e data de
modificação, com verificação a cada 30 segundos para evitar centenas de acessos
ao disco por clique. Se houver mudança, a API usa a leitura original até reconstruir
o índice. O catálogo de arquivos mantém o cache já existente na aplicação,
portanto reinicie a API após adicionar novos NetCDFs.

Para reconstruir o índice após atualizar os dados, pare a API (necessário para
substituir arquivos mapeados no Windows), execute e inicie novamente:

```powershell
.\.venv\Scripts\python.exe series_cache.py
```

O gráfico também consulta DHW e HotSpot como máximo diário de cada mês, pela
NOAA Coral Reef Watch, desde 2012. A primeira consulta de cada produto baixa
uma série diária de um único pixel; resultados recentes são mantidos em cache
no servidor. Cada gráfico oferece exportação do CSV mensal do sítio (incluindo
as sete variáveis) e do gráfico visível em PNG.

O mapa reaproveita as últimas 20 consultas completas da sessão e mostra quantas
das sete séries já terminaram de carregar. Se a consulta histórica CRW falhar,
o gráfico usa os meses já presentes no cache local e informa quantos pontos
estão disponíveis; a planilha completa fica desabilitada enquanto faltar dado.
Se não houver cache para o sítio, as séries locais ainda são exibidas e a falha
é identificada. Tente abrir novamente para repetir a consulta. Atualize a página
após modificar os dados para descartar esse cache do navegador.

Validação: `python -m unittest test_serie_crw_api.py test_coral_reef_watch.py test_series_cache.py test_waveheight.py`
e `node test_serie_temporal.cjs`.
