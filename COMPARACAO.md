# Comparar pontos

A aba **Comparar pontos** permite buscar e selecionar até oito pontos, escolher
uma ou mais das sete variáveis e definir início e fim com ano digitável e mês.
Selecione **Gerar comparação** para consultar somente as séries escolhidas.

Há duas visualizações: séries mensais, com uma linha por ponto, e média dos
valores mensais do período, com uma barra por ponto. Cada variável recebe seu
próprio gráfico e unidade; a cor de um ponto é a mesma nos gráficos da comparação.
Os IDs distinguem nomes repetidos e correspondem aos IDs da planilha/exportação.
A busca não remove pontos já selecionados. Limpar seleção remove todos.

Meses são alinhados ao calendário inteiro solicitado; lacunas permanecem vazias,
sem interpolação. Zero é válido. Médias ignoram ausentes; não há ponderação por
dias. Cada gráfico informa quantos meses válidos existem por ponto. Médias com
coberturas distintas exigem cuidado na comparação. DHW e HotSpot usam máximos
diários mensais, portanto suas barras representam médias desses máximos mensais.
Pontos próximos podem compartilhar o mesmo pixel e produzir curvas iguais.

Os dados são carregados ao gerar, com até três consultas simultâneas. Há cache
de até 48 séries nesta aba por ponto, produto e período. Respostas explicitamente
incompletas não entram no cache. O intervalo por comparação é limitado a 30 anos.
Nova geração cancela as consultas anteriores e descarta resultados antigos.
Falhas de uma série não bloqueiam as outras e aparecem no gráfico correspondente.

Cada gráfico pode ser baixado como PNG. O CSV inclui somente as séries obtidas,
com IDs, coordenadas, produto, unidade, mês, valor e sinalização de série parcial.
Exporta o período escolhido, incluindo células vazias nas lacunas, em UTF-8 com
BOM e separador ponto e vírgula. Filtros alterados exigem nova geração; enquanto
isso os gráficos e downloads representam a comparação anterior, identificada
pelos títulos. A exportação integral na aba Planilha continua independente.

Validação: `node test_comparacao.cjs`, `node test_previa.cjs` e
`node --check comparacao.js`. Os testes verificam seleção persistente, alinhamento
mensal, zero/ausentes, médias, cache, CSV, cores consistentes e concorrência.
