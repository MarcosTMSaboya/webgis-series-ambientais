const COMPARACAO_CONFIG = {
  CHL: {nome: "Clorofila-a", unidade: "mg/m³"}, SST: {nome: "SST", unidade: "°C"},
  PAR: {nome: "PAR", unidade: "mol/m²/dia"}, KD: {nome: "Kd 490", unidade: "m⁻¹"},
  WAVEHEIGHT: {nome: "Altura significativa de ondas", unidade: "m"},
  CRW_DHW: {nome: "DHW", unidade: "°C-semanas"}, CRW_HOTSPOT: {nome: "HotSpot", unidade: "°C"}
};
const CORES_COMPARACAO = ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#8c6500", "#563f9c", "#333333", "#00858a"];

function mesesComparacao(inicio, fim) {
  const meses = [];
  let [ano, mes] = inicio.split("-").map(Number);
  while (`${ano}-${String(mes).padStart(2, "0")}` <= fim) {
    meses.push(`${ano}-${String(mes).padStart(2, "0")}`);
    if (++mes > 12) { ano++; mes = 1; }
  }
  return meses;
}

function valoresComparacao(dados, meses) {
  const mapa = new Map(dados.serie.map(item => [item.data, item.valor]));
  return meses.map(mes => Number.isFinite(mapa.get(mes)) ? mapa.get(mes) : null);
}

async function filaComparacao(tarefas, executar, sinal, progresso) {
  let proxima = 0, concluidas = 0;
  const resultados = new Array(tarefas.length);
  await Promise.all(Array.from({length: Math.min(3, tarefas.length)}, async () => {
    while (!sinal.aborted && proxima < tarefas.length) {
      const indice = proxima++;
      try { resultados[indice] = {...tarefas[indice], dados: await executar(tarefas[indice])}; }
      catch (erro) { resultados[indice] = {...tarefas[indice], erro: erro.message}; }
      progresso(++concluidas, tarefas.length);
    }
  }));
  return resultados;
}

function csvComparacao(resultados, meses) {
  const linhas = [["ponto_id", "sitio", "latitude", "longitude", "produto", "mes", "valor", "unidade", "serie_parcial"]];
  for (const {ponto, produto, dados} of resultados) {
    if (!dados) continue;
    const valores = valoresComparacao(dados, meses);
    const parcial = Boolean(dados.incompleto || valores.includes(null));
    meses.forEach((mes, i) => linhas.push([ponto.id, ponto.nome, ponto.lat, ponto.lon, produto,
      mes, valores[i], dados.unidade || COMPARACAO_CONFIG[produto].unidade, parcial]));
  }
  return "\uFEFF" + linhas.map(linha => linha.map(v => `"${String(v ?? "").replaceAll('"', '""')}"`).join(";")).join("\r\n");
}

(() => {
  const el = id => document.getElementById(id);
  const estado = el("cmp-estado");
  const selecionados = new Set();
  const cache = new Map();
  let pontos = [], carregandoPontos = false, controle, geracao = 0;
  let graficos = [], resultadoAtual = [], mesesAtuais = [];
  const variaveis = [];

  for (const [produto, config] of Object.entries(COMPARACAO_CONFIG)) {
    const label = document.createElement("label");
    const caixa = document.createElement("input");
    caixa.type = "checkbox";
    caixa.value = produto;
    caixa.checked = ["CHL", "SST"].includes(produto);
    variaveis.push(caixa);
    label.append(caixa, document.createTextNode(` ${config.nome} (${config.unidade})`));
    el("cmp-variaveis").appendChild(label);
  }
  const nomesMeses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  for (const limite of ["inicio", "fim"]) {
    nomesMeses.forEach((nome, i) => {
      const opcao = document.createElement("option");
      opcao.value = String(i+1).padStart(2, "0");
      opcao.textContent = nome;
      el(`cmp-mes-${limite}`).appendChild(opcao);
    });
    el(`cmp-mes-${limite}`).value = limite === "inicio" ? "01" : "12";
  }

  function resumoSelecao() {
    const nomes = pontos.filter(p => selecionados.has(p.id)).map(p => `${p.nome} (#${p.id})`);
    el("cmp-selecao").textContent = nomes.length ? `${nomes.length}/8 selecionados: ${nomes.join("; ")}` : "Nenhum ponto selecionado";
  }
  function listarPontos() {
    const busca = el("cmp-busca").value.trim().toLocaleLowerCase("pt-BR");
    el("cmp-pontos").replaceChildren();
    const encontrados = pontos.filter(p => p.nome.toLocaleLowerCase("pt-BR").includes(busca));
    for (const ponto of encontrados) {
      const label = document.createElement("label");
      const caixa = document.createElement("input");
      caixa.type = "checkbox";
      caixa.checked = selecionados.has(ponto.id);
      caixa.addEventListener("change", () => {
        if (caixa.checked && selecionados.size >= 8) {
          caixa.checked = false;
          estado.textContent = "Selecione até 8 pontos por comparação. Remova um ponto para incluir outro.";
          return;
        }
        if (caixa.checked) selecionados.add(ponto.id); else selecionados.delete(ponto.id);
        resumoSelecao();
      });
      label.append(caixa, document.createTextNode(` ${ponto.nome} (#${ponto.id})`));
      el("cmp-pontos").appendChild(label);
    }
    if (!encontrados.length) el("cmp-pontos").textContent = "Nenhum ponto encontrado.";
  }
  async function carregarPontos() {
    if (pontos.length || carregandoPontos) return;
    carregandoPontos = true;
    estado.textContent = "Carregando lista de pontos...";
    el("cmp-recarregar").hidden = true;
    try {
      const resposta = await fetch("/Pontos_Clean.geojson");
      if (!resposta.ok) throw new Error(`Erro HTTP ${resposta.status}`);
      const dados = await resposta.json();
      pontos = dados.features.map((p, i) => ({id: i+1, nome: p.properties.name || "Sem nome",
        lat: p.geometry.coordinates[1], lon: p.geometry.coordinates[0]}));
      listarPontos();
      estado.textContent = `${pontos.length} pontos disponíveis. Selecione ao menos dois para comparar e clique em Gerar comparação.`;
    } catch (erro) {
      estado.textContent = `Não foi possível carregar os pontos: ${erro.message}`;
      el("cmp-recarregar").hidden = false;
    } finally { carregandoPontos = false; }
  }
  el("aba-graficos").addEventListener("click", () => {
    selecionarVisualizacao("graficos");
    carregarPontos();
    requestAnimationFrame(() => graficos.forEach(g => g.resize()));
  });
  el("cmp-recarregar").addEventListener("click", carregarPontos);
  el("cmp-busca").addEventListener("input", listarPontos);
  el("cmp-limpar").addEventListener("click", () => { selecionados.clear(); listarPontos(); resumoSelecao(); });
  el("cmp-form").addEventListener("change", () => {
    if (resultadoAtual.length) estado.textContent = "Filtros alterados. Clique em Gerar comparação para atualizar. Os gráficos e downloads atuais mantêm a comparação anterior.";
  });

  function baixar(conteudo, nome) {
    const link = document.createElement("a");
    const url = typeof conteudo === "string" ? conteudo : URL.createObjectURL(conteudo);
    link.href = url;
    link.download = nome;
    link.click();
    if (typeof conteudo !== "string") setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function desenhar(resultados, meses, produtos, tipo) {
    for (const produto of produtos) {
      const config = COMPARACAO_CONFIG[produto];
      const series = resultados.filter(r => r.produto === produto && r.dados);
      const card = document.createElement("article");
      card.className = "wg-comparacao-card";
      const titulo = document.createElement("h3");
      titulo.textContent = `${config.nome} (${config.unidade}) · ${meses[0]} a ${meses.at(-1)}`;
      card.appendChild(titulo);
      const resumo = document.createElement("p");
      const validas = series.filter(r => valoresComparacao(r.dados, meses).some(v => v !== null));
      resumo.textContent = series.map(r => {
        const valores = valoresComparacao(r.dados, meses);
        return `${r.ponto.nome} (#${r.ponto.id}): ${valores.filter(v => v !== null).length}/${meses.length} meses válidos${r.dados.incompleto || valores.includes(null) ? " (parcial)" : ""}`;
      }).join(" · ") || "Não foi possível obter séries desta variável.";
      card.appendChild(resumo);
      const falhas = resultados.filter(r => r.produto === produto && r.erro);
      if (falhas.length) {
        const aviso = document.createElement("p");
        aviso.className = "wg-comparacao-erro";
        aviso.textContent = falhas.map(r => `${r.ponto.nome} (#${r.ponto.id}): ${r.erro}`).join(" · ");
        card.appendChild(aviso);
      }
      el("cmp-graficos").appendChild(card);
      if (validas.length) {
        const area = document.createElement("div");
        area.className = "wg-comparacao-canvas";
        const canvas = document.createElement("canvas");
        canvas.setAttribute("role", "img");
        canvas.setAttribute("aria-label", titulo.textContent);
        area.appendChild(canvas);
        card.appendChild(area);
        const datasets = tipo === "linha" ? validas.map(r => ({
          label: `${r.ponto.nome} (#${r.ponto.id})`, data: valoresComparacao(r.dados, meses),
          borderColor: CORES_COMPARACAO[r.cor], backgroundColor: CORES_COMPARACAO[r.cor],
          borderDash: r.cor >= 4 ? [6, 3] : [], borderWidth: 2, pointRadius: meses.length > 48 ? 0 : 2,
          spanGaps: false, tension: 0
        })) : [{label: `Média dos valores mensais (${config.unidade})`,
          data: validas.map(r => { const vs = valoresComparacao(r.dados, meses).filter(v => v !== null); return vs.reduce((a,b) => a+b, 0)/vs.length; }),
          backgroundColor: validas.map(r => CORES_COMPARACAO[r.cor])}];
        const grafico = new Chart(canvas, {type: tipo === "linha" ? "line" : "bar",
          data: {labels: tipo === "linha" ? meses : validas.map(r => `${r.ponto.nome} (#${r.ponto.id})`), datasets},
          options: {responsive: true, maintainAspectRatio: false, animation: false,
            interaction: {mode: "index", intersect: false},
            plugins: {legend: {display: tipo === "linha"}, title: {display: true, text: `${config.nome} · ${meses[0]} a ${meses.at(-1)}`}},
            scales: {x: {ticks: {maxTicksLimit: 15}}, y: {title: {display: true, text: config.unidade}, beginAtZero: tipo !== "linha"}}}});
        graficos.push(grafico);
        const png = document.createElement("button");
        png.type = "button";
        png.textContent = "Baixar gráfico PNG";
        png.addEventListener("click", () => baixar(grafico.toBase64Image("image/png", 1), `comparacao_${produto}_${meses[0]}_${meses.at(-1)}.png`));
        card.appendChild(png);
      }
    }
  }

  el("cmp-form").addEventListener("submit", async evento => {
    evento.preventDefault();
    const pontosAtivos = pontos.filter(p => selecionados.has(p.id));
    const produtos = variaveis.filter(c => c.checked).map(c => c.value);
    const inicio = `${el("cmp-ano-inicio").value}-${el("cmp-mes-inicio").value}`;
    const fim = `${el("cmp-ano-fim").value}-${el("cmp-mes-fim").value}`;
    if (!pontosAtivos.length || !produtos.length) { estado.textContent = "Selecione ao menos um ponto e uma variável. Para comparar locais, selecione dois ou mais pontos."; return; }
    if (!/^20\d{2}-(0[1-9]|1[0-2])$/.test(inicio) || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(fim) || inicio > fim) {
      estado.textContent = "Confira o período: a data inicial deve ser anterior ou igual à final."; return;
    }
    const meses = mesesComparacao(inicio, fim);
    if (meses.length > 360) { estado.textContent = "Use até 30 anos por comparação para manter as consultas leves."; return; }
    if (typeof Chart === "undefined") { estado.textContent = "A biblioteca de gráficos não carregou. Atualize a página e tente novamente."; return; }
    const id = ++geracao;
    controle?.abort();
    controle = new AbortController();
    const sinal = controle.signal;
    const tipo = el("cmp-tipo").value;
    graficos.forEach(g => g.destroy()); graficos = [];
    el("cmp-graficos").replaceChildren();
    resultadoAtual = []; el("cmp-csv").disabled = true;
    const tarefas = pontosAtivos.flatMap((ponto, cor) => produtos.map(produto => ({ponto, produto, cor})));
    estado.textContent = `Carregando 0/${tarefas.length} séries...`;
    const resultados = await filaComparacao(tarefas, async ({ponto, produto}) => {
      const chave = `${ponto.id}:${produto}:${inicio}:${fim}`;
      if (cache.has(chave)) return cache.get(chave);
      const parametros = new URLSearchParams({produto, lat: ponto.lat, lon: ponto.lon, inicio, fim});
      const resposta = await fetch(`/serie?${parametros}`, {signal: sinal});
      if (!resposta.ok) {
        const erro = await resposta.json().catch(() => ({}));
        throw new Error(typeof erro.detail === "string" ? erro.detail : `Erro HTTP ${resposta.status}`);
      }
      const dados = await resposta.json();
      if (!dados.incompleto) {
        cache.set(chave, dados);
        if (cache.size > 48) cache.delete(cache.keys().next().value);
      }
      return dados;
    }, sinal, (n, total) => { if (id === geracao) estado.textContent = `Carregando ${n}/${total} séries...`; });
    if (id !== geracao) return;
    resultadoAtual = resultados;
    mesesAtuais = meses;
    try {
      desenhar(resultados, meses, produtos, tipo);
      const falhas = resultados.filter(r => r.erro).length;
      estado.textContent = `${inicio} a ${fim} · ${pontosAtivos.length} pontos · ${produtos.length} variáveis · ${resultados.length-falhas}/${resultados.length} séries obtidas${falhas ? "; falhas identificadas nos gráficos; o CSV inclui somente as séries obtidas" : ""}. Pontos próximos podem compartilhar o mesmo pixel e apresentar curvas iguais.`;
      el("cmp-csv").disabled = !resultados.some(r => r.dados && valoresComparacao(r.dados, meses).some(v => v !== null));
    } catch (erro) { estado.textContent = `Falha ao desenhar os gráficos: ${erro.message}`; }
  });
  el("cmp-csv").addEventListener("click", () => {
    baixar(new Blob([csvComparacao(resultadoAtual, mesesAtuais)], {type: "text/csv;charset=utf-8"}),
      `comparacao_pontos_${mesesAtuais[0]}_${mesesAtuais.at(-1)}.csv`);
  });
})();
