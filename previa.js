// Aba de planilha: busca e paginação no servidor, carregada somente ao abrir.
function desenharPrevia(tabela, dados) {
  const cabecalho = tabela.querySelector("thead");
  const corpo = tabela.querySelector("tbody");
  cabecalho.replaceChildren();
  corpo.replaceChildren();
  const tr = document.createElement("tr");
  for (const coluna of dados.colunas) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = coluna;
    tr.appendChild(th);
  }
  cabecalho.appendChild(tr);
  for (const linha of dados.linhas) {
    const row = document.createElement("tr");
    for (const valor of linha) {
      const td = document.createElement("td");
      // Preserva precisão e zero; texto de atributos nunca é interpretado como HTML.
      td.textContent = valor === null || valor === undefined ? "—" : String(valor);
      if (valor === null || valor === undefined) td.className = "wg-valor-ausente";
      row.appendChild(td);
    }
    corpo.appendChild(row);
  }
}

let abrirPreviaDados;
let selecionarVisualizacao;
(() => {
  const porId = id => document.getElementById(id);
  const abaMapa = porId("aba-mapa");
  const abaPlanilha = porId("aba-planilha");
  const painel = porId("wg-previa");
  const estado = porId("previa-estado");
  const anterior = porId("previa-anterior");
  const proxima = porId("previa-proxima");
  const tabela = porId("previa-dados");
  let pagina = 1;
  let abriu = false;
  let requisicao = 0;
  let controle;
  let temporizador;

  async function carregar() {
    clearTimeout(temporizador);
    if (porId("previa-tabela").value === "series" && !porId("previa-ano").validity.valid) {
      porId("previa-ano").reportValidity();
      return;
    }
    const id = ++requisicao;
    controle?.abort();
    controle = new AbortController();
    estado.textContent = "Carregando prévia...";
    porId("previa-avisos").textContent = "";
    porId("previa-pagina").textContent = "";
    tabela.querySelector("thead").replaceChildren();
    tabela.querySelector("tbody").replaceChildren();
    porId("previa-grade").setAttribute("aria-busy", "true");
    anterior.disabled = proxima.disabled = true;
    const mes = porId("previa-tabela").value === "atributos"
      ? "2020-01" : `${porId("previa-ano").value}-${porId("previa-mes").value}`;
    const parametros = new URLSearchParams({mes,
      tabela: porId("previa-tabela").value, busca: porId("previa-busca").value,
      pagina, tamanho: porId("previa-tamanho").value});
    try {
      const resposta = await fetch(`/previa?${parametros}`, {signal: controle.signal});
      if (!resposta.ok) {
        const erro = await resposta.json().catch(() => ({}));
        throw new Error(typeof erro.detail === "string" ? erro.detail : `Erro HTTP ${resposta.status}`);
      }
      const dados = await resposta.json();
      if (id !== requisicao) return;
      pagina = dados.pagina;
      desenharPrevia(tabela, dados);
      tabela.querySelector("caption").textContent = dados.tabela === "series"
        ? `Séries mensais · ${dados.mes}` : "Atributos originais dos pontos";
      const inicio = dados.total ? (pagina-1)*dados.tamanho+1 : 0;
      estado.textContent = dados.total
        ? `Exibindo ${inicio}–${inicio+dados.linhas.length-1} de ${dados.total} pontos (${dados.total_pontos} no projeto).`
        : "Nenhum ponto encontrado para essa busca.";
      porId("previa-avisos").textContent = dados.avisos.join(" ");
      porId("previa-pagina").textContent = `Página ${pagina} de ${dados.paginas}`;
      anterior.disabled = pagina <= 1;
      proxima.disabled = pagina >= dados.paginas;
      porId("previa-grade").scrollTop = 0;
    } catch (erro) {
      if (id !== requisicao || erro.name === "AbortError") return;
      estado.textContent = `Não foi possível carregar a prévia: ${erro.message}. Use Atualizar prévia para tentar novamente.`;
    } finally {
      if (id === requisicao) porId("previa-grade").setAttribute("aria-busy", "false");
    }
  }

  function alternar(destino) {
    const planilha = destino === true || destino === "planilha";
    const graficos = destino === "graficos";
    painel.hidden = !planilha;
    porId("wg-area-app").hidden = planilha || graficos;
    porId("wg-graficos").hidden = !graficos;
    porId("aba-graficos").setAttribute("aria-selected", String(graficos));
    porId("aba-graficos").tabIndex = graficos ? 0 : -1;
    abaMapa.setAttribute("aria-selected", String(!planilha && !graficos));
    abaPlanilha.setAttribute("aria-selected", String(planilha));
    abaMapa.tabIndex = planilha || graficos ? -1 : 0;
    abaPlanilha.tabIndex = planilha ? 0 : -1;
    porId("wg-alternar-painel").hidden = planilha || graficos;
    if (planilha && !abriu) {
      abriu = true;
      if (typeof dataMensalSelecionada !== "undefined") {
        const [ano, mes] = dataMensalSelecionada.split("-");
        porId("previa-ano").value = ano;
        porId("previa-mes").value = mes;
      }
      carregar();
    }
    if (!planilha && !graficos && typeof mapa !== "undefined") requestAnimationFrame(() => mapa.invalidateSize());
  }
  selecionarVisualizacao = alternar;
  abrirPreviaDados = () => { alternar(true); abaPlanilha.focus(); };
  abaMapa.addEventListener("click", () => alternar(false));
  abaPlanilha.addEventListener("click", abrirPreviaDados);
  const abas = [abaMapa, abaPlanilha, porId("aba-graficos")];
  for (const aba of abas) {
    aba.addEventListener("keydown", evento => {
      if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(evento.key)) {
        evento.preventDefault();
        const indice = evento.key === "Home" ? 0 : evento.key === "End" ? abas.length-1
          : (abas.indexOf(aba) + (evento.key === "ArrowRight" ? 1 : abas.length-1)) % abas.length;
        abas[indice].click();
        abas[indice].focus();
      }
    });
  }
  porId("previa-filtros").addEventListener("submit", evento => { evento.preventDefault(); pagina = 1; carregar(); });
  for (const nome of ["previa-tabela", "previa-ano", "previa-mes", "previa-tamanho"]) {
    porId(nome).addEventListener("change", () => {
      pagina = 1;
      porId("previa-mes").disabled = porId("previa-tabela").value === "atributos";
      porId("previa-ano").disabled = porId("previa-tabela").value === "atributos";
      carregar();
    });
  }
  porId("previa-busca").addEventListener("input", () => {
    clearTimeout(temporizador);
    pagina = 1;
    temporizador = setTimeout(carregar, 300);
  });
  anterior.addEventListener("click", () => { pagina--; carregar(); });
  proxima.addEventListener("click", () => { pagina++; carregar(); });
  porId("previa-exportar").addEventListener("click", () =>
    exportarSeriesCompletas(porId("previa-exportar"), porId("previa-exportacao-estado")));
})();
