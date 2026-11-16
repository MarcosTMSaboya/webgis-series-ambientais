# Indicadores por ponto

Abra uma série temporal e expanda **Indicadores do ponto e cobertura dos dados**.
O botão **Baixar indicadores CSV** exporta os resumos do ponto consultado,
inclusive resumos parciais explicitamente identificados. Produtos que falharam
não aparecem no arquivo. Os indicadores usam o período da consulta `/serie`
(por padrão 2012-01 a 2025-12); cada produto informa seu intervalo disponível.

Os cálculos percorrem apenas a série mensal já obtida. Não baixam novas fontes,
não abrem rasters adicionais e não criam camadas no mapa. O cache de séries do
navegador também reaproveita os indicadores. A API acrescenta `indicadores` à
resposta de `/serie`, preservando os campos anteriores.

- Média, mínimo, máximo e desvio padrão populacional dos valores mensais válidos.
- CHL e SST: CV = SD / abs(média), assimetria e excesso de curtose pelos momentos
  populacionais, sem correção de viés. Assimetria exige 3 valores, curtose exige 4;
  ambos ficam ausentes em séries constantes. CV é ausente quando a média é zero.
  CV de SST em Celsius depende da escala e exige cuidado na comparação.
- DHW: máximo do período, número de meses com máximo diário mensal estritamente
  maior que 4 e que 8 e média dos máximos anuais apenas dos anos com 12 meses
  válidos. Um mesmo episódio pode atravessar vários meses: essas contagens não
  representam eventos independentes ou número de dias.
- Anos com menos de 12 meses têm médias e máximos parciais na exportação anual.
- Lacunas, NaN e infinitos são ignorados; zero é preservado. Cobertura conta os
  meses entre a primeira e a última data da série, incluindo lacunas intermediárias.
  A sinalização de falha parcial da fonte é preservada. Um mês válido não garante
  cobertura diária completa dentro daquele mês.

O ZIP geral acrescenta `indicadores.csv`, `resumos_anuais.csv` e
`atributos_pontos.csv`, com o mesmo `ponto_id` dos arquivos existentes. Usa todo
o período de cada produto, que pode diferir do período do painel. Metadados
registram as convenções e unidades. Nenhuma consulta adicional às fontes é feita
para os novos CSVs. Os arquivos de exportações antigas não são alterados.

Os popups mostram atributos disponíveis: elevação GPS, registro GPS, descrição
e, se existentes nas propriedades, profundidade, habitat, manejo e método.
`ele` não é interpretado como profundidade, nem `time` como data de amostragem
ecológica. Os pontos atuais não fornecem esses atributos ecológicos. Latitude,
longitude e todas as propriedades originais são preservadas no CSV e GeoJSON.

Esses resumos não reproduzem automaticamente os indicadores do artigo:
períodos, frequência e produto de SST precisam coincidir. MMM, conectividade,
pressões humanas e outras variáveis que exigem novas fontes não foram calculadas.

Validação: `python -m unittest test_indicadores.py test_exportacao.py
test_serie_crw_api.py` e `node test_indicadores.cjs`.
