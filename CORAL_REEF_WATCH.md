# NOAA Coral Reef Watch no WebGIS

O WebGIS integra DHW (Degree Heating Week) e HotSpot do NOAA Coral Reef Watch,
versão 3.1, pela API ERDDAP pública do NOAA. A cobertura histórica dos produtos
diários começa em 1985; a interface do projeto oferece resumos mensais desde
2012, para alinhar ao período principal das outras variáveis.

O valor de cada mês é o **máximo diário da grade em cada célula**. Portanto,
estas são agregações calculadas pelo WebGIS, não produtos mensais originais do
CRW. O máximo de DHW representa o maior estresse térmico acumulado (janela
móvel de 12 semanas) atingido no mês; o máximo de HotSpot representa o pico
diário de estresse instantâneo naquele mês. A agregação não deve ser
interpretada como média mensal nem como uma observação de campo.

Somente a região ao redor dos pontos do mapa é consultada, preservando a grade
nativa de 0,05° (aproximadamente 5 km). O servidor busca um mês por produto na
primeira solicitação e guarda o resumo em `Dados/CRW/mensal`; os meses
históricos já armazenados não precisam ser baixados de novo. O mês corrente é
atualizado quando o cache tem mais de seis horas. O servidor que executa
`app.py` precisa ter acesso à internet.

Ao selecionar DHW ou HotSpot, escolha o ano e o mês nos controles ambientais
para exibir o raster desse período, como nas demais variáveis. Meses ainda não
armazenados podem demorar mais na primeira consulta; depois ficam em cache
local.

Na visualização do raster, DHW igual a zero e HotSpot abaixo de 1 °C ficam
transparentes para não encobrir o mapa-base onde não há estresse térmico no
limiar visualizado. As consultas pontuais ainda mostram o máximo numérico
mensal, inclusive zero ou HotSpot negativo. A escala DHW marca 0, 4, 8, 12, 16
e 20 °C-semanas; HotSpot usa 0–5 °C. A data e a quantidade de dias retornados
pela fonte aparecem na interface. Se o provedor não retornar um mês, a API
mostra o erro em vez de tratar o período como um raster válido.

Fontes oficiais:

- [Produtos diários globais de 5 km do NOAA CRW](https://coralreefwatch.noaa.gov/product/5km/index.php)
- [DHW no ERDDAP do NOAA](https://coastwatch.noaa.gov/erddap/griddap/noaacrwdhwDaily)
- [HotSpot no ERDDAP do NOAA](https://coastwatch.noaa.gov/erddap/griddap/noaacrwhotspotDaily)

Ao reutilizar os dados, creditar NOAA Coral Reef Watch e citar o produto/dataset
de acordo com as [recomendações de citação do programa](https://coralreefwatch.noaa.gov/satellite/docs/recommendations_crw_citation.php).
