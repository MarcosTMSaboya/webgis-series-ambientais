"use strict";

// ================================================================
// 1. CONFIGURAÇÕES
// ================================================================

const CONFIG = {
  arquivo: "./Pontos_Clean.geojson",
  raioPontos: 6,

  limiteNorteMeio: -18.255282,
  limiteMeioSul: -19.522466
};

const SETORES = ["Norte", "Meio", "Sul"];


// ================================================================
// 2. ORDEM DOS GRUPOS
// ================================================================

const ORDEM_GRUPOS = [
  "PAB1",
  "PAB2",
  "PAB3",
  "PAB4",
  "PAB5",
  "RHC",
  "RHS",
  "RH",
  "CANAL",
  "GRASS",
  "ALGA / ALGAS",
  "TIM",
  "PA",
  "PC",
  "RES",
  "LAM",
  "C",
  "D",
  "Q associados a D",
  "EXTRA",
  "TALUDE",
  "EXP",
  "A",
  "B",
  "PLES",
  "SGOM",
  "Outros"
];


// ================================================================
// 3. PALETAS
// ================================================================

const PALETAS = {
  Norte: [
    "#8B0000",
    "#A4161A",
    "#BA181B",
    "#D62828",
    "#E63946",
    "#C1121F",
    "#E5383B",
    "#F25C54",
    "#D94841",
    "#E76F51",
    "#F28482",
    "#E85D04",
    "#F48C06",
    "#FAA307",
    "#FF7F11",
    "#FF9505",
    "#CC5803",
    "#E36414",
    "#F77F00",
    "#F4A261",
    "#E76F51",
    "#D97706",
    "#C2410C",
    "#EA580C",
    "#FB923C",
    "#FDBA74",
    "#9A3412"
  ],

  Meio: [
    "#FFE08A",
    "#FFD166",
    "#E9C46A",
    "#DDB55A",
    "#D4A373",
    "#C9A227",
    "#B8860B",
    "#A67C00",
    "#DDA15E",
    "#C9975B",
    "#BC8A5F",
    "#B08968",
    "#A98467",
    "#9C755F",
    "#A47148",
    "#99582A",
    "#8C5E35",
    "#7F5539",
    "#6F4E37",
    "#A68A64",
    "#92734E",
    "#806044",
    "#76533C",
    "#68452F",
    "#5C4033",
    "#4A3428",
    "#3F2D20"
  ],

  Sul: [
    "#0077B6",
    "#168AAD",
    "#1A759F",
    "#2A6F97",
    "#468FAF",
    "#4361EE",
    "#3F37C9",
    "#3943B7",
    "#5E60CE",
    "#6A63D8",
    "#7570E0",
    "#6930C3",
    "#7244C8",
    "#7B2CBF",
    "#8E44CC",
    "#9855D4",
    "#9D4EDD",
    "#A855F7",
    "#B060E8",
    "#7209B7",
    "#6A00A8",
    "#5A189A",
    "#4C1D95",
    "#4338CA",
    "#581C87",
    "#6B21A8",
    "#312E81"
  ]
};

const CONTORNOS = {
  Norte: "#641414",
  Meio: "#5C4522",
  Sul: "#27245E"
};


// ================================================================
// 4. REGRAS DE CLASSIFICAÇÃO
// ================================================================

const REGRAS_GRUPOS = [
  ["Q associados a D", /^Q\d+\s*\(D\d+\)$/],
  ["EXP", /^EXP\b/],
  ["PAB", /\bPAB\s*\d+\b/],
  ["RHC", /^RHC\s*\d+\b/],
  ["RHS", /^RHS\s*\d+\b/],
  ["RH", /^RH\s*\d+\b/],
  ["TIM", /\bTIM\s*\d+\b/],
  ["PA", /\bPA\s*\d+\b/],
  ["CANAL", /^CANAL\s*\d+\b/],
  ["GRASS", /^GRASS\s*\d+\b/],
  ["ALGA / ALGAS", /^ALGAS?\s*\d+\b/],
  ["RES", /^RES\s*\d+\b/],
  ["PC", /^PC\s*\d+\b/],
  ["LAM", /^LAM\s*\d+\b/],
  ["EXTRA", /^EXTRA\s*\d+/],
  ["TALUDE", /^TALUDE\s*\d+\b/],
  ["PLES", /\bPLES\b/],
  ["SGOM", /\bSGOM\b/],
  ["C", /^C\d+/],
  ["D", /^D\d+/],
  ["A", /^A\d+/],
  ["B", /^(?:ES\s+)?B\d+/]
];


// ================================================================
// 5. CLASSIFICAÇÃO POR NOME
// ================================================================

function classificarNome(nomeOriginal) {
  const nome = String(nomeOriginal ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toUpperCase();

  const regra = REGRAS_GRUPOS.find(
    (item) => item[1].test(nome)
  );

  const familia = regra ? regra[0] : "Outros";

  let grupo = familia;
  let anoReferencia = null;

  if (familia === "PAB") {
    const resultado =
      nome.match(/\bPAB\s*(\d+)\b/);

    if (resultado) {
      grupo = `PAB${resultado[1]}`;
    }

    if (nome === "PAB225") {
      grupo = "PAB2";
      anoReferencia = 2025;
    }
  }

  return {
    familia,
    grupo,
    anoReferencia
  };
}


// ================================================================
// 6. SETORES
// ================================================================

function classificarSetor(latitude) {
  if (latitude >= CONFIG.limiteNorteMeio) {
    return "Norte";
  }

  if (latitude >= CONFIG.limiteMeioSul) {
    return "Meio";
  }

  return "Sul";
}


// ================================================================
// 7. COR
// ================================================================

function obterCor(grupo, setor) {
  const indice =
    ORDEM_GRUPOS.indexOf(grupo);

  const indiceCor =
    indice >= 0
      ? indice
      : ORDEM_GRUPOS.length - 1;

  return PALETAS[setor][indiceCor];
}


// ================================================================
// 8. PREPARAR GEOJSON
// ================================================================

function prepararDados(dados) {
  if (
    dados?.type !== "FeatureCollection" ||
    !Array.isArray(dados.features)
  ) {
    throw new Error(
      "O arquivo precisa conter uma FeatureCollection GeoJSON."
    );
  }

  return {
    ...dados,

    features: dados.features.map(
      (feicao) => {

        const [longitude, latitude] =
          feicao.geometry.coordinates;

        const atributos =
          feicao.properties ?? {};

        const classificacao =
          classificarNome(
            atributos.name
          );

        const setor =
          classificarSetor(
            latitude
          );

        return {
          ...feicao,

          properties: {
            ...atributos,

            wg_familia:
              classificacao.familia,

            wg_grupo:
              classificacao.grupo,

            wg_setor:
              setor,

            wg_ano_ref:
              classificacao.anoReferencia,

            wg_cor:
              obterCor(
                classificacao.grupo,
                setor
              )
          }
        };
      }
    )
  };
}


// ================================================================
// 9. MAPA
// ================================================================

const mapa = L.map(
  "mapa",
  {
    zoomSnap: 0.5
  }
).setView(
  [-18.7, -38.8],
  7
);

const secoesPainel = {};

function criarPainelControle() {
  const painel = L.DomUtil.create("div", "wg-dashboard");
  painel.id = "wg-painel-controle";
  const cabecalho = document.createElement("div");
  cabecalho.className = "wg-dashboard-cabecalho";

  const titulo = document.createElement("strong");
  titulo.textContent = "Painel de controle";

  const conteudo = document.createElement("div");
  conteudo.className = "wg-dashboard-conteudo";

  const definicoesSecoes = [
    ["mapas", "Mapas de fundo", true],
    ["ambiente", "Dados ambientais", true],
    ["setores", "Setores", false],
    ["escalas", "Escalas de cores", false],
    ["grupos", "Grupos e cores", false]
  ];

  for (const [id, nome, aberta] of definicoesSecoes) {
    const secao = document.createElement("details");
    secao.className = "wg-dashboard-secao";
    secao.open = aberta;

    const resumo = document.createElement("summary");
    resumo.textContent = nome;

    const corpo = document.createElement("div");
    corpo.className = "wg-dashboard-secao-conteudo";

    secao.append(resumo, corpo);
    conteudo.appendChild(secao);
    secoesPainel[id] = corpo;
  }

  cabecalho.appendChild(titulo);
  painel.append(cabecalho, conteudo);

  return painel;
}

const painelControle = criarPainelControle();
document.getElementById("wg-painel-lateral").appendChild(painelControle);

const botaoPainelApp = document.getElementById("wg-alternar-painel");
botaoPainelApp.addEventListener("click", () => {
  const visivel = document.getElementById("wg-painel-lateral").classList.toggle("wg-painel-visivel");
  botaoPainelApp.setAttribute("aria-expanded", String(visivel));
  setTimeout(() => mapa.invalidateSize(), 200);
});

function adicionarControleAoPainel(controle, secao) {
  const conteudo = secoesPainel[secao];
  const elemento = controle.getContainer();
  if (!conteudo || !elemento) {
    throw new Error(`Não foi possível adicionar controle à seção "${secao}".`);
  }
  elemento.classList.add("wg-controle-integrado");
  conteudo.appendChild(elemento);
}


// ================================================================
// 10. BASEMAPS
// ================================================================

const osm = L.tileLayer(
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  {
    maxZoom: 19,
    attribution:
      "&copy; OpenStreetMap contributors"
  }
);

const satelite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 19,
    attribution:
      "Esri, Maxar, Earthstar Geographics"
  }
);

const oceanos = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 16,
    attribution:
      "Esri, GEBCO, NOAA"
  }
);

const oceanLabels = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 16,
    attribution:
      "Esri, GEBCO, NOAA"
  }
);

const gebco = L.tileLayer.wms(
  "https://wms.gebco.net/mapserv?",
  {
    layers: "GEBCO_LATEST",
    format: "image/png",
    transparent: false,
    version: "1.3.0",
    attribution: "GEBCO"
  }
);

satelite.addTo(mapa);

// ================================================================
// CONTROLE DE BASEMAPS
// ================================================================

const mapasBase = {
  "Satélite": satelite,
  "Oceanos": oceanos,
  "GEBCO — Batimetria": gebco,
  "OpenStreetMap": osm
};

const camadasReferencia = {
  "Rótulos oceânicos": oceanLabels
};


const controleBasemaps =
  L.control.layers(
    mapasBase,
    camadasReferencia,
    {
      collapsed: false,
      position: "topleft"
    }
  );


controleBasemaps.addTo(
  mapa
);

adicionarControleAoPainel(controleBasemaps, "mapas");

// ================================================================
// 11. CONTROLES ARRASTÁVEIS
// ================================================================

function tornarControleArrastavel(
  controle,
  titulo
) {
  const painel =
    controle.getContainer();

  const mapaContainer =
    mapa.getContainer();

  if (!painel) {
    return;
  }

  if (painel.classList.contains("wg-painel")) return;
  painel.classList.add("wg-painel");
  painel.style.minWidth = "180px";
  Object.assign(painel.style, {display: "flex", flexDirection: "column", overflow: "hidden", resize: "both", boxSizing: "border-box"});
  const conteudo = document.createElement("div");
  conteudo.className = "conteudo-painel";
  Object.assign(conteudo.style, {overflow: "auto", flex: "1 1 auto", minHeight: "0", minWidth: "0"});
  while (painel.firstChild) conteudo.appendChild(painel.firstChild);
  painel.appendChild(conteudo);

  const barra =
    document.createElement("div");

  barra.textContent =
    `☰ ${titulo}`;

  barra.className =
    "barra-arraste";

  Object.assign(
    barra.style,
    {
      background: "#374151",
      color: "#ffffff",
      padding: "6px 10px",
      marginBottom: "6px",
      cursor: "grab",
      fontWeight: "bold",
      fontSize: "12px",
      borderRadius: "4px",
      userSelect: "none",
      display: "flex", alignItems: "center", gap: "8px", flexShrink: "0"
    }
  );

  painel.prepend(
    barra
  );

  const acoes = document.createElement("span");
  acoes.className = "acoes-painel";
  Object.assign(acoes.style, {display: "inline-flex", gap: "3px", marginLeft: "auto"});
  const botao = (texto, descricao, acao) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = texto;
    b.title = descricao;
    b.setAttribute("aria-label", `${descricao}: ${titulo}`);
    b.addEventListener("mousedown", e => e.stopPropagation());
    b.addEventListener("click", e => {e.stopPropagation(); acao(b);});
    acoes.appendChild(b);
    return b;
  };
  let tamanhoAnterior = null;
  botao("−", "Minimizar ou restaurar", b => {
    const minimo = painel.classList.toggle("wg-minimizado");
    if (minimo) {
      tamanhoAnterior = {height: painel.style.height, minHeight: painel.style.minHeight, width: painel.style.width};
      conteudo.dataset.displayAnterior = conteudo.style.display || "";
      conteudo.style.display = "none";
      painel.style.resize = "none";
      painel.style.height = "auto";
      painel.style.width = "auto";
      painel.style.minHeight = "0";
    } else {
      Object.assign(painel.style, tamanhoAnterior || {});
      conteudo.style.display = conteudo.dataset.displayAnterior || "";
      painel.style.resize = "both";
    }
    b.textContent = minimo ? "▢" : "−";
    b.setAttribute("aria-expanded", String(!minimo));
  });
  const dimensionar = fator => {
    if (painel.classList.contains("wg-minimizado")) return;
    const r = painel.getBoundingClientRect();
    painel.style.maxHeight = `${mapaContainer.clientHeight*.9}px`;
    painel.style.width = `${Math.min(mapaContainer.clientWidth*.94, Math.max(180, r.width*fator))}px`;
    painel.style.height = `${Math.min(mapaContainer.clientHeight*.9, Math.max(110, r.height*fator))}px`;
  };
  botao("A−", "Diminuir caixa", () => dimensionar(.85));
  botao("A+", "Aumentar caixa", () => dimensionar(1.18));
  const fechar = painel.querySelector("#fechar-serie");
  if (fechar) {
    fechar.style.position = "static";
    fechar.setAttribute("aria-label", "Fechar série temporal");
    fechar.addEventListener("mousedown", e => e.stopPropagation());
    acoes.appendChild(fechar);
  }
  barra.appendChild(acoes);
  new ResizeObserver(() => {
    if (painel.id === "painel-serie-temporal" && typeof graficoSerieTemporal !== "undefined" && graficoSerieTemporal) graficoSerieTemporal.resize();
  }).observe(conteudo);

  let arrastando = false;
  let offsetX = 0;
  let offsetY = 0;

  barra.addEventListener(
    "mousedown",
    function (evento) {

      evento.preventDefault();
      evento.stopPropagation();

      const mapaRect =
        mapaContainer.getBoundingClientRect();

      const painelRect =
        painel.getBoundingClientRect();

      const esquerda =
        painelRect.left -
        mapaRect.left;

      const topo =
        painelRect.top -
        mapaRect.top;

      mapaContainer.appendChild(
        painel
      );

      Object.assign(
        painel.style,
        {
          position: "absolute",
          transform: "none",
          left: `${esquerda}px`,
          top: `${topo}px`,
          right: "auto",
          bottom: "auto",
          margin: "0",
          zIndex: "2000"
        }
      );

      offsetX =
        evento.clientX -
        painelRect.left;

      offsetY =
        evento.clientY -
        painelRect.top;

      arrastando = true;

      barra.style.cursor =
        "grabbing";
    }
  );

  document.addEventListener(
    "mousemove",
    function (evento) {

      if (!arrastando) {
        return;
      }

      const mapaRect =
        mapaContainer.getBoundingClientRect();

      let x =
        evento.clientX -
        mapaRect.left -
        offsetX;

      let y =
        evento.clientY -
        mapaRect.top -
        offsetY;

      const maxX =
        mapaContainer.clientWidth -
        painel.offsetWidth;

      const maxY =
        mapaContainer.clientHeight -
        painel.offsetHeight;

      x = Math.max(
        0,
        Math.min(
          x,
          maxX
        )
      );

      y = Math.max(
        0,
        Math.min(
          y,
          maxY
        )
      );

      painel.style.left =
        `${x}px`;

      painel.style.top =
        `${y}px`;
    }
  );

  document.addEventListener(
    "mouseup",
    function () {

      if (!arrastando) {
        return;
      }

      arrastando = false;

      barra.style.cursor =
        "grab";
    }
  );

  L.DomEvent.disableClickPropagation(
    painel
  );

  L.DomEvent.disableScrollPropagation(
    painel
  );
}

// ================================================================
// 13. ESCALA
// ================================================================

L.control.scale({
  imperial: false
}).addTo(mapa);

async function exportarSeriesCompletas(botao, estado) {
  botao.disabled = true;
  estado.textContent = "Preparando exportação completa...";
  try {
    const inicio = await fetch("/exportacoes", {method: "POST"});
    if (!inicio.ok) throw new Error(`Erro HTTP ${inicio.status}`);
    const tarefa = await inicio.json();
    while (true) {
      const resposta = await fetch(`/exportacoes/${tarefa.id}`);
      if (!resposta.ok) throw new Error(`Erro HTTP ${resposta.status}`);
      const atual = await resposta.json();
      if (atual.status === "erro") throw new Error(atual.erro);
      if (atual.status === "pronto") {
        estado.textContent = `Pronto: ${atual.total} pontos e ${atual.linhas.toLocaleString("pt-BR")} linhas mensais.`;
        const link = document.createElement("a");
        link.href = `/exportacoes/${tarefa.id}/arquivo`;
        link.textContent = "Baixar ZIP completo";
        link.download = "series_completas_todos_pontos.zip";
        estado.appendChild(link);
        link.click();
        break;
      }
      estado.textContent = atual.etapa === "dhw"
        ? `Obtendo DHW mensal: ${atual.concluidos}/${atual.total} meses... Você pode continuar usando o mapa.`
        : `Exportando: ${atual.concluidos}/${atual.total} pontos... Você pode continuar usando o mapa.`;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  } catch (erro) {
    estado.textContent = `Falha na exportação: ${erro.message} — meses DHW já baixados ficam em cache; se a falha foi NOAA, tente novamente.`;
  } finally {
    botao.disabled = false;
  }
}


// ================================================================
// 14. ESTADO AMBIENTAL GLOBAL
// ================================================================

let dataAmbientalSelecionada =
  "2020-01";

let dataMensalSelecionada =
  dataAmbientalSelecionada;

let produtoRasterSelecionado =
  "CHL";

let rasterAmbientalVisivel =
  true;

let opacidadeRasterAmbiental =
  0.65;


// ================================================================
// 15. RASTER AMBIENTAL
// ================================================================

if (
  !mapa.getPane(
    "rasterAmbientalPane"
  )
) {
  mapa.createPane(
    "rasterAmbientalPane"
  );

  mapa.getPane(
    "rasterAmbientalPane"
  ).style.zIndex = 250;

  mapa.getPane(
    "rasterAmbientalPane"
  ).style.pointerEvents = "none";
}

let camadaRasterAmbiental = null;

let requisicaoRasterAtual = 0;
const cacheInfoRasterAmbiental = new Map();

async function obterInfoRasterAmbiental(produto, data) {
  const chave = `${produto}:${data}`;
  let entrada = cacheInfoRasterAmbiental.get(chave);

  if (entrada && Date.now() - entrada.criadoEm >= 6 * 60 * 60 * 1000) {
    cacheInfoRasterAmbiental.delete(chave);
    entrada = null;
  }

  if (!entrada) {
    const requisicao = fetch(
      "/raster-info" +
      `?produto=${encodeURIComponent(produto)}` +
      `&data=${encodeURIComponent(data)}`
    ).then(async resposta => {
      if (!resposta.ok) {
        const erroApi = await resposta.json().catch(() => ({}));
        throw new Error(
          erroApi.detail || `Erro ao obter limites: HTTP ${resposta.status}`
        );
      }
      return resposta.json();
    }).catch(erro => {
      if (cacheInfoRasterAmbiental.get(chave)?.requisicao === requisicao) {
        cacheInfoRasterAmbiental.delete(chave);
      }
      throw erro;
    });

    entrada = {requisicao, criadoEm: Date.now()};
    cacheInfoRasterAmbiental.set(chave, entrada);
  }

  return entrada.requisicao;
}


// ================================================================
// CARREGAR RASTER SEM PISCAR
// ================================================================

async function mostrarRasterAmbiental(
  produto,
  data
) {

  const idRequisicao =
    ++requisicaoRasterAtual;

  try {
    const info = await obterInfoRasterAmbiental(produto, data);

    if (
      idRequisicao !==
      requisicaoRasterAtual
    ) {
      return false;
    }

    if (produto.startsWith("CRW_")) {
      const periodo = document.querySelector(".wg-periodo-ambiental");
      if (periodo) {
        const statusEstresse = info.celulas_com_estresse === 0
          ? " · sem células acima do limiar de estresse no recorte"
          : ` · ${info.celulas_com_estresse} células com estresse`;
        periodo.textContent = `${info.escala.nome} · ${info.data} · máximo diário mensal, NOAA CRW 5 km (${info.dias_amostrados} dias)${statusEstresse}`;
      }
    }

    const bounds = [
      [
        info.bounds.sul,
        info.bounds.oeste
      ],
      [
        info.bounds.norte,
        info.bounds.leste
      ]
    ];

    const urlRaster =
      "/raster" +
      `?produto=${encodeURIComponent(produto)}` +
      `&data=${encodeURIComponent(data)}`;

    const novaCamada =
      L.imageOverlay(
        urlRaster,
        bounds,
        {
          opacity:
            opacidadeRasterAmbiental,

          pane:
            "rasterAmbientalPane"
        }
      );

    return await new Promise((resolve) => {
      novaCamada.once("load", function () {
        if (idRequisicao !== requisicaoRasterAtual) {
          if (mapa.hasLayer(novaCamada)) {
            mapa.removeLayer(novaCamada);
          }
          resolve(false);
          return;
        }

        const camadaAnterior = camadaRasterAmbiental;
        camadaRasterAmbiental = novaCamada;

        if (
          camadaAnterior &&
          camadaAnterior !== novaCamada &&
          mapa.hasLayer(camadaAnterior)
        ) {
          mapa.removeLayer(camadaAnterior);
        }

        console.log(`Raster carregado: ${produto} ${data}`);
        resolve(true);
      });

      novaCamada.once("error", function () {
        console.error(`Falha ao carregar raster ${produto} ${data}`);

        if (mapa.hasLayer(novaCamada)) {
          mapa.removeLayer(novaCamada);
        }
        if (idRequisicao === requisicaoRasterAtual) {
          const periodo = document.querySelector(".wg-periodo-ambiental");
          if (periodo) periodo.textContent = `Falha ao carregar raster ${produto} ${data}.`;
        }
        resolve(false);
      });

      novaCamada.addTo(mapa);
    });

  } catch (erro) {
    if (idRequisicao === requisicaoRasterAtual && camadaRasterAmbiental) {
      mapa.removeLayer(camadaRasterAmbiental);
      camadaRasterAmbiental = null;
    }
    if (idRequisicao === requisicaoRasterAtual) {
      const periodo = document.querySelector(".wg-periodo-ambiental");
      if (periodo) periodo.textContent = `Falha ao carregar ${produto}: ${erro.message}`;
    }
    console.error(
      "Erro ao carregar raster:",
      erro
    );
    return false;
  }
}


// ================================================================
// 16. FORMATAR VALORES AMBIENTAIS
// ================================================================

function formatarValorAmbiental(
  produto,
  valor
) {

  if (
    valor === null ||
    valor === undefined
  ) {
    return "Sem dado";
  }

  switch (produto) {

    case "CHL":
      return `${valor.toFixed(3)} mg/m³`;

    case "SST":
      return `${valor.toFixed(2)} °C`;

    case "PAR":
      return `${valor.toFixed(2)} mol/m²/dia`;

    case "KD":
      return `${valor.toFixed(4)} m⁻¹`;

    case "WAVEHEIGHT":
      return `${valor.toFixed(3)} ${unidadeWaveHeight || "(unidade a confirmar)"}`;

    case "CRW_DHW":
      return `${valor.toFixed(2)} °C-semanas`;

    case "CRW_HOTSPOT":
      return `${valor.toFixed(2)} °C`;

    default:
      return String(valor);
  }
}


// ================================================================
// 17. POPUP AMBIENTAL
// ================================================================
let graficoSerieTemporal = null;
const cacheSeriesTemporais = new Map();
let requisicaoSerieAtual = 0;
let unidadeWaveHeight = null;
let dadosSeriesTemporaisAtuais = [];
let coordenadaSerieAtual = null;

const CONFIG_SERIE_TEMPORAL = {
  CHL: {
    nome: "Clorofila-a",
    cor: "#16a34a",
    eixo: "yCHL",
    unidade: "mg/m³"
  },

  SST: {
    nome: "SST",
    cor: "#dc2626",
    eixo: "ySST",
    unidade: "°C"
  },

  PAR: {
    nome: "PAR",
    cor: "#d97706",
    eixo: "yPAR",
    unidade: "mol/m²/dia"
  },

  KD: {
    nome: "Kd 490",
    cor: "#2563eb",
    eixo: "yKD",
    unidade: "m⁻¹"
  },
  WAVEHEIGHT: {
    nome: "Altura significativa de ondas",
    cor: "#0891b2",
    eixo: "yWAVEHEIGHT",
    unidade: ""
  },
  CRW_DHW: {
    nome: "DHW",
    cor: "#7c3aed",
    eixo: "yCRW_DHW",
    unidade: "°C-semanas"
  },
  CRW_HOTSPOT: {
    nome: "HotSpot",
    cor: "#db2777",
    eixo: "yCRW_HOTSPOT",
    unidade: "°C"
  }
};

function nomeArquivoSerie(lat, lon) {
  const coordenadas = `${lat.toFixed(5)}_${lon.toFixed(5)}`
    .replaceAll("-", "m")
    .replaceAll(".", "_");
  return `serie_temporal_${coordenadas}`;
}

function exportarSerieCSV(respostas, lat, lon) {
  const datas = [...new Set(respostas.flatMap(dados => dados.serie.map(item => item.data)))].sort();
  const valoresPorProduto = new Map(
    respostas.map(dados => [
      dados.produto,
      new Map(dados.serie.map(item => [item.data, item.valor]))
    ])
  );
  const produtos = ["CHL", "SST", "PAR", "KD", "WAVEHEIGHT", "CRW_DHW", "CRW_HOTSPOT"];
  const cabecalho = [
    "mes",
    ...produtos.map(produto => {
      const config = CONFIG_SERIE_TEMPORAL[produto];
      const dados = respostas.find(item => item.produto === produto);
      const unidade = dados?.unidade || config.unidade;
      return unidade ? `${config.nome} (${unidade})` : config.nome;
    })
  ];
  const escapar = valor => `"${String(valor ?? "").replaceAll('"', '""')}"`;
  const linhas = [cabecalho, ...datas.map(data => [
    data,
    ...produtos.map(produto => valoresPorProduto.get(produto)?.get(data))
  ])].map(linha => linha.map(escapar).join(";"));
  const arquivo = new Blob(["\uFEFF", linhas.join("\r\n")], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(arquivo);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nomeArquivoSerie(lat, lon)}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}


function exportarIndicadoresCSV(respostas, lat, lon) {
  const linhas = [["latitude", "longitude", "produto", "indicador", "descricao", "valor", "unidade",
    "inicio", "fim", "meses_validos", "meses_esperados", "incompleto"]];
  for (const dados of respostas) {
    const r = dados.indicadores;
    if (!r) continue;
    for (const m of r.metricas) linhas.push([lat, lon, dados.produto, m.codigo, m.nome, m.valor,
      m.unidade, r.inicio, r.fim, r.meses_validos, r.meses_esperados, r.incompleto]);
  }
  const csv = linhas.map(linha => linha.map(v => `"${String(v ?? "").replaceAll('"', '""')}"`).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], {type: "text/csv;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${nomeArquivoSerie(lat, lon)}_indicadores.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function mostrarIndicadores(container, respostas) {
  container.replaceChildren();
  const nota = document.createElement("p");
  nota.textContent = "Resumos dos meses disponíveis no período consultado, sem preencher lacunas. DHW: meses acima do limiar, não eventos ou dias. CV de SST em °C depende da escala. SD e momentos populacionais; curtose é excesso (normal = 0).";
  container.appendChild(nota);
  for (const dados of respostas) {
    const r = dados.indicadores;
    if (!r) continue;
    const titulo = document.createElement("strong");
    titulo.textContent = `${CONFIG_SERIE_TEMPORAL[dados.produto]?.nome || dados.produto}: ${r.inicio || "—"} a ${r.fim || "—"} · ${r.meses_validos}/${r.meses_esperados} meses válidos${r.incompleto ? " · PARCIAL" : ""}`;
    container.appendChild(titulo);
    const tabela = document.createElement("table");
    const cabecalho = tabela.insertRow();
    for (const nome of ["Indicador", "Valor", "Unidade"]) {
      const th = document.createElement("th");
      th.textContent = nome;
      cabecalho.appendChild(th);
    }
    for (const m of r.metricas) {
      const tr = tabela.insertRow();
      for (const v of [m.nome, m.valor == null ? "Indisponível" : m.valor.toLocaleString("pt-BR", {maximumSignificantDigits: 6}), m.unidade]) {
        tr.insertCell().textContent = v;
      }
    }
    container.appendChild(tabela);
  }
}

async function abrirSerieTemporal(
  lat,
  lon
) {
  const idSerie = ++requisicaoSerieAtual;

  const produtos = [
    "CHL",
    "SST",
    "PAR",
    "KD",
    "WAVEHEIGHT",
    "CRW_DHW",
    "CRW_HOTSPOT"
  ];

  let painel =
    document.getElementById(
      "painel-serie-temporal"
    );


  // ============================================================
  // CRIA A JANELA
  // ============================================================

  if (!painel) {

    painel =
      document.createElement("div");

    painel.id =
      "painel-serie-temporal";

    Object.assign(
      painel.style,
      {
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: "translate(-50%, -50%)",

        width: "850px",
        maxWidth: "94%",

        height: "500px",
        maxHeight: "90%",

        background: "white",

        padding: "15px",

        borderRadius: "8px",

        boxShadow:
          "0 4px 20px rgba(0,0,0,0.35)",

        zIndex: "5000",

        boxSizing: "border-box"
      }
    );


    painel.innerHTML = `

      <button
        id="fechar-serie"
        style="
          position:absolute;
          right:12px;
          top:10px;
          cursor:pointer;
        "
      >
        ✕
      </button>


      <h3
        id="titulo-serie"
        style="margin-top:0;"
      >
        Série temporal ambiental
      </h3>


      <small
        id="info-serie"
        style="
          display:block;
          margin-bottom:10px;
        "
      >
      </small>


      <details class="wg-indicadores">
        <summary>Indicadores do ponto e cobertura dos dados</summary>
        <button id="exportar-indicadores-csv" type="button" disabled>Baixar indicadores CSV</button>
        <div id="indicadores-serie"></div>
      </details>

      <div
        id="controles-serie"
        style="
          display:flex;
          flex-wrap:wrap;
          gap:14px;
          margin-bottom:10px;
          font-size:13px;
        "
      >

        <label>
          <input
            type="checkbox"
            id="serie-todas"
            checked
          >
          Todas
        </label>


        <label>
          <input
            type="checkbox"
            class="serie-variavel"
            data-produto="CHL"
            checked
          >
          Clorofila-a
        </label>


        <label>
          <input
            type="checkbox"
            class="serie-variavel"
            data-produto="SST"
            checked
          >
          SST
        </label>


        <label>
          <input
            type="checkbox"
            class="serie-variavel"
            data-produto="PAR"
            checked
          >
          PAR
        </label>


        <label>
          <input
            type="checkbox"
            class="serie-variavel"
            data-produto="KD"
            checked
          >
          Kd 490
        </label>

        <label>
          <input type="checkbox" class="serie-variavel" data-produto="WAVEHEIGHT" checked>
          WaveHeight
        </label>

        <label>
          <input type="checkbox" class="serie-variavel" data-produto="CRW_DHW" checked>
          DHW
        </label>

        <label>
          <input type="checkbox" class="serie-variavel" data-produto="CRW_HOTSPOT" checked>
          HotSpot
        </label>

      </div>

      <div style="display:flex; gap:8px; margin:0 0 8px;">
        <button id="exportar-serie-png" type="button" disabled>Exportar gráfico PNG</button>
        <button id="exportar-serie-csv" type="button" disabled>Exportar planilha CSV</button>
      </div>

      <div
        style="
          width:100%;
          height:370px;
        "
      >
        <canvas id="grafico-serie"></canvas>
      </div>
    `;


    mapa
      .getContainer()
      .appendChild(
        painel
      );

    tornarControleArrastavel({getContainer: () => painel}, "Série temporal");
    const tituloSerie = painel.querySelector("#titulo-serie");
    if (tituloSerie) tituloSerie.style.display = "none";
    painel.querySelector("canvas").parentElement.classList.add("wg-area-grafico");
    painel.querySelector("#exportar-indicadores-csv").addEventListener("click", () => {
      exportarIndicadoresCSV(dadosSeriesTemporaisAtuais, coordenadaSerieAtual.latitude, coordenadaSerieAtual.longitude);
    });
    painel.querySelector("#exportar-serie-png").addEventListener("click", () => {
      if (!graficoSerieTemporal) return;
      try {
        const link = document.createElement("a");
        link.href = graficoSerieTemporal.toBase64Image("image/png", 1);
        link.download = `${nomeArquivoSerie(coordenadaSerieAtual.latitude, coordenadaSerieAtual.longitude)}.png`;
        link.click();
      } catch (erro) {
        document.getElementById("info-serie").textContent = `Falha ao exportar PNG: ${erro.message}`;
      }
    });
    painel.querySelector("#exportar-serie-csv").addEventListener("click", () => {
      if (dadosSeriesTemporaisAtuais.length) {
        try {
          exportarSerieCSV(dadosSeriesTemporaisAtuais, coordenadaSerieAtual.latitude, coordenadaSerieAtual.longitude);
        } catch (erro) {
          document.getElementById("info-serie").textContent = `Falha ao exportar CSV: ${erro.message}`;
        }
      }
    });


    // ----------------------------------------------------------
    // FECHAR
    // ----------------------------------------------------------

    document
      .getElementById(
        "fechar-serie"
      )
      .addEventListener(
        "click",
        function () {

          painel.style.display =
            "none";
        }
      );


    // ----------------------------------------------------------
    // CHECKBOX "TODAS"
    // ----------------------------------------------------------

    const checkboxTodas =
      document.getElementById(
        "serie-todas"
      );


    checkboxTodas.addEventListener(
      "change",
      function () {

        const caixas =
          document.querySelectorAll(
            ".serie-variavel"
          );


        caixas.forEach(
          caixa => {

            if (caixa.disabled) {
              return;
            }

            caixa.checked =
              checkboxTodas.checked;


            if (
              graficoSerieTemporal
            ) {

              const produto =
                caixa.dataset.produto;


              const dataset =
                graficoSerieTemporal
                  .data
                  .datasets
                  .find(
                    item =>
                      item.produto ===
                      produto
                  );


              if (dataset) {

                dataset.hidden =
                  !caixa.checked;


                const eixo =
                  CONFIG_SERIE_TEMPORAL[
                    produto
                  ].eixo;


                graficoSerieTemporal
                  .options
                  .scales[
                    eixo
                  ].display =
                    caixa.checked;
              }
            }
          }
        );


        if (
          graficoSerieTemporal
        ) {

          graficoSerieTemporal.update();
        }
      }
    );


    // ----------------------------------------------------------
    // CHECKBOXES INDIVIDUAIS
    // ----------------------------------------------------------

    document
      .querySelectorAll(
        ".serie-variavel"
      )
      .forEach(
        caixa => {

          caixa.addEventListener(
            "change",
            function () {

              if (
                !graficoSerieTemporal
              ) {
                return;
              }


              const produto =
                caixa.dataset.produto;


              const dataset =
                graficoSerieTemporal
                  .data
                  .datasets
                  .find(
                    item =>
                      item.produto ===
                      produto
                  );


              if (dataset) {

                dataset.hidden =
                  !caixa.checked;


                const eixo =
                  CONFIG_SERIE_TEMPORAL[
                    produto
                  ].eixo;


                graficoSerieTemporal
                  .options
                  .scales[
                    eixo
                  ].display =
                    caixa.checked;
              }


              const caixas =
                [
                  ...document.querySelectorAll(
                    ".serie-variavel"
                  )
                ];


              const todasMarcadas =
                caixas.every(
                  item =>
                    item.checked
                );


              const algumaMarcada =
                caixas.some(
                  item =>
                    item.checked
                );


              checkboxTodas.checked =
                todasMarcadas;


              checkboxTodas.indeterminate =
                algumaMarcada &&
                !todasMarcadas;


              graficoSerieTemporal.update();
            }
          );
        }
      );
  }


  painel.style.display =
    "flex";


  const info =
    document.getElementById(
      "info-serie"
    );


  info.textContent =
    "Carregando séries ambientais e NOAA CRW...";
  painel.querySelector("#exportar-serie-png").disabled = true;
  painel.querySelector("#exportar-serie-csv").disabled = true;
  painel.querySelector("#exportar-indicadores-csv").disabled = true;
  painel.querySelector("#indicadores-serie").textContent = "Carregando indicadores...";
  for (const produto of ["CRW_DHW", "CRW_HOTSPOT"]) {
    const caixa = painel.querySelector(`.serie-variavel[data-produto="${produto}"]`);
    if (caixa && caixa.disabled) {
      caixa.disabled = false;
      caixa.checked = true;
    }
  }


  try {

    if (
      typeof Chart === "undefined"
    ) {

      throw new Error(
        "Chart.js não foi carregado."
      );
    }


    // ============================================================
    // BAIXA AS 4 SÉRIES AO MESMO TEMPO
    // ============================================================

    const chaveSerie = `v3:${lat},${lon}`;
    let concluidas = 0;
    const resultados = cacheSeriesTemporais.get(chaveSerie) ||
      await Promise.allSettled(

        produtos.map(
          async produto => {

            const url =
              "/serie" +
              `?produto=${produto}` +
              `&lat=${lat}` +
              `&lon=${lon}`;


            const resposta =
              await fetch(
                url
              );


            if (!resposta.ok) {

              throw new Error(
                `${produto}: erro ${resposta.status}`
              );
            }


            const dados = await resposta.json();
            concluidas++;
            if (idSerie === requisicaoSerieAtual) {
              info.textContent = `Carregando séries: ${concluidas}/${produtos.length} concluídas...`;
            }
            return dados;
          }
        )
      );

    if (idSerie !== requisicaoSerieAtual) return;
    const falhaPrincipal = resultados.find(
      (resultado, indice) => resultado.status === "rejected" && !produtos[indice].startsWith("CRW_")
    );
    if (falhaPrincipal) throw falhaPrincipal.reason;
    const respostas = resultados
      .filter(resultado => resultado.status === "fulfilled")
      .map(resultado => resultado.value);
    const falhasCRW = resultados
      .map((resultado, indice) => ({resultado, produto: produtos[indice]}))
      .filter(item => item.resultado.status === "rejected");
    const seriesIncompletas = respostas.filter(dados => dados.incompleto);
    if (!falhasCRW.length && !seriesIncompletas.length) {
      cacheSeriesTemporais.set(chaveSerie, resultados);
      if (cacheSeriesTemporais.size > 20) cacheSeriesTemporais.delete(cacheSeriesTemporais.keys().next().value);
    }
    dadosSeriesTemporaisAtuais = respostas;
    coordenadaSerieAtual = {latitude: lat, longitude: lon};
    mostrarIndicadores(painel.querySelector("#indicadores-serie"), respostas);
    painel.querySelector("#exportar-indicadores-csv").disabled = !respostas.some(d => d.indicadores?.metricas.length);
    for (const produto of produtos) {
      const caixa = painel.querySelector(`.serie-variavel[data-produto="${produto}"]`);
      if (caixa) {
        caixa.disabled = falhasCRW.some(item => item.produto === produto);
        if (caixa.disabled) caixa.checked = false;
      }
    }
    const caixasSerie = [...painel.querySelectorAll(".serie-variavel")];
    const checkboxTodas = painel.querySelector("#serie-todas");
    checkboxTodas.checked = caixasSerie.every(caixa => caixa.checked);
    checkboxTodas.indeterminate = caixasSerie.some(caixa => caixa.checked) && !checkboxTodas.checked;


    // ============================================================
    // DATAS
    // ============================================================

    const onda = respostas.find(dados => dados.produto === "WAVEHEIGHT");
    unidadeWaveHeight = onda.unidade;

    const datas =
      [
        ...new Set(
          respostas.flatMap(
            dados =>
              dados.serie.map(
                item => item.data
              )
          )
        )
      ].sort();


    // ============================================================
    // DATASETS
    // ============================================================

    const datasets =
      respostas.map(
        dados => {

          const produto =
            dados.produto;


          const config =
            CONFIG_SERIE_TEMPORAL[
              produto
            ];


          const valoresPorData =
            new Map(
              dados.serie.map(
                item => [
                  item.data,
                  item.valor
                ]
              )
            );


          const valores =
            datas.map(
              data =>
                valoresPorData.has(
                  data
                )
                  ? valoresPorData.get(
                      data
                    )
                  : null
            );


          return {

            produto:
              produto,

            label:
              config.nome,

            data:
              valores,

            borderColor:
              config.cor,

            backgroundColor:
              config.cor,

            yAxisID:
              config.eixo,

            borderWidth:
              2,

            pointRadius:
              0,

            pointHoverRadius:
              4,

            tension:
              0.15,

            spanGaps:
              true,

            hidden:
              false
          };
        }
      );


    // ============================================================
    // DESTROI O GRÁFICO ANTERIOR
    // ============================================================

    if (
      graficoSerieTemporal
    ) {

      graficoSerieTemporal.destroy();

      graficoSerieTemporal =
        null;
    }


    const canvas =
      document.getElementById(
        "grafico-serie"
      );


    // ============================================================
    // CRIA O GRÁFICO
    // ============================================================

    graficoSerieTemporal =
      new Chart(
        canvas,
        {

          type: "line",

          plugins: [{
            id: "fundo-branco-exportacao",
            beforeDraw: grafico => {
              const contexto = grafico.canvas.getContext("2d");
              contexto.save();
              contexto.globalCompositeOperation = "destination-over";
              contexto.fillStyle = "#ffffff";
              contexto.fillRect(0, 0, grafico.width, grafico.height);
              contexto.restore();
            }
          }],

          data: {

            labels:
              datas,

            datasets:
              datasets
          },


          options: {

            responsive:
              true,

            maintainAspectRatio:
              false,


            interaction: {

              mode:
                "index",

              intersect:
                false
            },


            plugins: {

              legend: {

                display:
                  true
              },


              tooltip: {

                callbacks: {

                  label:
                    function (
                      contexto
                    ) {

                      const produto =
                        contexto.dataset.produto;


                      const valor =
                        contexto.parsed.y;


                      if (
                        valor === null
                      ) {

                        return (
                          `${contexto.dataset.label}: Sem dado`
                        );
                      }


                      return (
                        `${contexto.dataset.label}: ` +
                        formatarValorAmbiental(
                          produto,
                          valor
                        )
                      );
                    }
                }
              }
            },


            scales: {

              x: {

                ticks: {

                  maxTicksLimit:
                    14
                },

                title: {

                  display:
                    true,

                  text:
                    "Data"
                }
              },


              yCHL: {

                type:
                  "linear",

                position:
                  "left",

                display:
                  true,

                title: {

                  display:
                    true,

                  text:
                    "CHL (mg/m³)",

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .CHL.cor
                },

                ticks: {

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .CHL.cor
                },

                grid: {

                  drawOnChartArea:
                    true
                }
              },


              ySST: {

                type:
                  "linear",

                position:
                  "right",

                display:
                  true,

                title: {

                  display:
                    true,

                  text:
                    "SST (°C)",

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .SST.cor
                },

                ticks: {

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .SST.cor
                },

                grid: {

                  drawOnChartArea:
                    false
                }
              },


              yPAR: {

                type:
                  "linear",

                position:
                  "left",

                display:
                  true,

                title: {

                  display:
                    true,

                  text:
                    "PAR",

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .PAR.cor
                },

                ticks: {

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .PAR.cor
                },

                grid: {

                  drawOnChartArea:
                    false
                }
              },


              yWAVEHEIGHT: {
                type: "linear", position: "left", display: true,
                title: {display: true, text: `WaveHeight ${unidadeWaveHeight ? `(${unidadeWaveHeight})` : "(unidade a confirmar)"}`, color: "#0891b2"},
                ticks: {color: "#0891b2"}, grid: {drawOnChartArea: false}
              },
              yCRW_DHW: {
                type: "linear", position: "left", display: true, offset: true,
                title: {display: true, text: "DHW (°C-semanas)", color: CONFIG_SERIE_TEMPORAL.CRW_DHW.cor},
                ticks: {color: CONFIG_SERIE_TEMPORAL.CRW_DHW.cor}, grid: {drawOnChartArea: false}
              },
              yCRW_HOTSPOT: {
                type: "linear", position: "right", display: true, offset: true,
                title: {display: true, text: "HotSpot (°C)", color: CONFIG_SERIE_TEMPORAL.CRW_HOTSPOT.cor},
                ticks: {color: CONFIG_SERIE_TEMPORAL.CRW_HOTSPOT.cor}, grid: {drawOnChartArea: false}
              },
              yKD: {

                type:
                  "linear",

                position:
                  "right",

                display:
                  true,

                title: {

                  display:
                    true,

                  text:
                    "Kd 490 (m⁻¹)",

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .KD.cor
                },

                ticks: {

                  color:
                    CONFIG_SERIE_TEMPORAL
                      .KD.cor
                },

                grid: {

                  drawOnChartArea:
                    false
                }
              }
            }
          }
        }
      );
    painel.querySelector("#exportar-serie-png").disabled = false;
    painel.querySelector("#exportar-serie-csv").disabled = falhasCRW.length > 0 || seriesIncompletas.length > 0;


    // ============================================================
    // INFORMAÇÃO DO PIXEL
    // ============================================================

    const referencia =
      respostas[0];


    info.textContent =
      "Pixel: " +
      `${referencia.pixel_utilizado.latitude.toFixed(5)}, ` +
      `${referencia.pixel_utilizado.longitude.toFixed(5)} | ` +
      `Distância: ` +
      `${referencia.distancia_pixel_km.toFixed(2)} km`;

    if (onda.pixel_utilizado) {
      info.textContent += ` | WaveHeight: pixel ${onda.pixel_utilizado.latitude.toFixed(3)}, ${onda.pixel_utilizado.longitude.toFixed(3)}; distância ${onda.distancia_pixel_km.toFixed(2)} km; grade de 0,5°. Dados até 2025-06.`;
    }
    if (falhasCRW.length) {
      info.textContent += ` | ${falhasCRW.map(item => `${item.produto}: ${item.resultado.reason.message}`).join(" | ")} | CSV completo indisponível até carregar DHW e HotSpot.`;
    }
    if (seriesIncompletas.length) {
      info.textContent += ` | ${seriesIncompletas.map(dados => `${dados.produto}: NOAA indisponível; ${dados.meses_em_cache}/${dados.quantidade_meses} meses no cache`).join(" | ")} | CSV completo indisponível até atualizar o CRW.`;
    }


    // ============================================================
    // REAPLICA O ESTADO DAS CAIXAS
    // ============================================================

    document
      .querySelectorAll(
        ".serie-variavel"
      )
      .forEach(
        caixa => {

          const produto =
            caixa.dataset.produto;


          const dataset =
            graficoSerieTemporal
              .data
              .datasets
              .find(
                item =>
                  item.produto ===
                  produto
              );


          if (dataset) {

            dataset.hidden =
              !caixa.checked;


            graficoSerieTemporal
              .options
              .scales[
                CONFIG_SERIE_TEMPORAL[
                  produto
                ].eixo
              ].display =
                caixa.checked;
          }
        }
      );


    graficoSerieTemporal.update();


  } catch (erro) {

    if (idSerie !== requisicaoSerieAtual) return;
    console.error(
      "Erro série temporal:",
      erro
    );


    info.textContent =
      `Erro: ${erro.message}`;
    painel.querySelector("#indicadores-serie").textContent = "Indicadores indisponíveis nesta consulta.";
  }
}

function criarPopupAmbiental(dados) {

  const container =
    document.createElement("div");

  container.style.minWidth =
    "250px";


  // TÍTULO
  const titulo =
    document.createElement("strong");

  titulo.textContent =
    `Dados ambientais — ${dados.data}`;

  titulo.style.display =
    "block";

  titulo.style.marginBottom =
    "10px";

  container.appendChild(
    titulo
  );


  // NOMES DAS VARIÁVEIS
  const nomes = {
    CHL: "Clorofila-a",
    SST: "Temperatura da superfície",
    PAR: "Radiação fotossinteticamente ativa",
    KD: "Kd 490",
    WAVEHEIGHT: "Altura significativa de ondas",
    CRW_DHW: "DHW — máximo diário mensal (NOAA Coral Reef Watch)",
    CRW_HOTSPOT: "HotSpot — máximo diário mensal (NOAA Coral Reef Watch)"
  };


  // VALORES
  for (
    const produto
    of ["CHL", "SST", "PAR", "KD", "WAVEHEIGHT", "CRW_DHW", "CRW_HOTSPOT"]
  ) {

    const resultado =
      dados.resultados[produto];

    if (produto === "WAVEHEIGHT" && resultado) unidadeWaveHeight = resultado.unidade;

    const linha =
      document.createElement("div");

    linha.style.marginBottom =
      "6px";

    const nome =
      document.createElement("strong");

    nome.textContent =
      `${nomes[produto]}${resultado?.data ? ` · ${resultado.data}` : ""}: `;

    const valor =
      document.createElement("span");

    if (
      resultado &&
      resultado.valor !== null &&
      resultado.valor !== undefined
    ) {

      valor.textContent =
        formatarValorAmbiental(
          produto,
          resultado.valor
        );

    } else {

      valor.textContent =
        "Sem dado";
    }

    linha.append(
      nome,
      valor
    );

    if (produto.startsWith("CRW_") && resultado?.erro) {
      const erro = document.createElement("small");
      erro.style.display = "block";
      erro.textContent = `Falha na consulta ao NOAA CRW: ${resultado.erro}`;
      linha.appendChild(erro);
    }

    if (produto === "WAVEHEIGHT" && resultado?.pixel_utilizado) {
      const origem = document.createElement("small");
      origem.style.display = "block";
      origem.textContent = `Pixel: ${resultado.pixel_utilizado.latitude.toFixed(3)}, ${resultado.pixel_utilizado.longitude.toFixed(3)} | Distância: ${resultado.distancia_pixel_km.toFixed(2)} km | Grade: 0,5°`;
      if (resultado.erro) origem.textContent += ` | ${resultado.erro}`;
      linha.appendChild(origem);
    }

    container.appendChild(
      linha
    );
  }


  // SEPARADOR
  const separador =
    document.createElement("hr");

  separador.style.margin =
    "10px 0";

  container.appendChild(
    separador
  );


  // COORDENADA CONSULTADA
  const coordenadaConsulta =
    document.createElement("small");

  coordenadaConsulta.style.display =
    "block";

  coordenadaConsulta.textContent =
    "Clique: " +
    `${dados.coordenada_solicitada.latitude.toFixed(5)}, ` +
    `${dados.coordenada_solicitada.longitude.toFixed(5)}`;

  container.appendChild(
    coordenadaConsulta
  );


  // PIXEL UTILIZADO
  const primeiroResultado =
    dados.resultados.CHL;

  if (
    primeiroResultado &&
    primeiroResultado.pixel_utilizado
  ) {

    const pixel =
      document.createElement("small");

    pixel.style.display =
      "block";

    pixel.textContent =
      "Pixel utilizado: " +
      `${primeiroResultado.pixel_utilizado.latitude.toFixed(5)}, ` +
      `${primeiroResultado.pixel_utilizado.longitude.toFixed(5)}`;

    container.appendChild(
      pixel
    );


    // DISTÂNCIA ATÉ O CENTRO DO PIXEL
    if (
      primeiroResultado.distancia_pixel_km !== undefined &&
      primeiroResultado.distancia_pixel_km !== null
    ) {

      const distancia =
        document.createElement("small");

      distancia.style.display =
        "block";

      distancia.textContent =
        "Distância até o centro do pixel: " +
        `${primeiroResultado.distancia_pixel_km.toFixed(2)} km`;

      container.appendChild(
        distancia
      );
    }
  }

const botaoSerie =
  document.createElement("button");

botaoSerie.textContent =
  "📈 Ver série temporal";

botaoSerie.style.marginTop =
  "10px";

botaoSerie.style.cursor =
  "pointer";

botaoSerie.addEventListener(
  "click",
  function (evento) {
    evento.stopPropagation();

    abrirSerieTemporal(
      dados.coordenada_solicitada.latitude,
      dados.coordenada_solicitada.longitude
    );
  }
);

container.appendChild(
  botaoSerie
);

  return container;
}


// ================================================================
// 18. CONSULTAR API AMBIENTAL
// ================================================================

async function consultarAmbiente(
  latitude,
  longitude
) {

  const url =
    "/ambiente" +
    `?data=${encodeURIComponent(dataMensalSelecionada)}` +
    `&lat=${encodeURIComponent(latitude)}` +
    `&lon=${encodeURIComponent(longitude)}`;

  const resposta =
    await fetch(url);

  if (!resposta.ok) {
    throw new Error(
      `Erro HTTP ${resposta.status}`
    );
  }

  return await resposta.json();
}


// ================================================================
// 19. POPUP E TOOLTIP DOS PONTOS
// ================================================================

function configurarInformacoes(
  feicao,
  camada
) {

  const p =
    feicao.properties;

  const [
    longitude,
    latitude
  ] =
    feicao.geometry.coordinates;

  const nome =
    p.name ?? "Ponto sem nome";

  const janela =
    document.createElement("div");

  const titulo =
    document.createElement("strong");

  titulo.textContent =
    nome;

  janela.appendChild(
    titulo
  );

  const linhas = [
    `Família: ${p.wg_familia}`,
    `Grupo: ${p.wg_grupo}`,
    `Setor: ${p.wg_setor}`
  ];

  if (
    p.wg_ano_ref !== null
  ) {

    linhas.push(
      `Ano de referência: ${p.wg_ano_ref}`
    );
  }

  linhas.push(
    `Latitude: ${latitude.toFixed(6)}°`
  );

  linhas.push(
    `Longitude: ${longitude.toFixed(6)}°`
  );

  for (const [campo, rotulo] of [["ele", "Elevação GPS (m; não é profundidade)"],
    ["time", "Registro GPS"], ["desc", "Descrição"], ["profundidade", "Profundidade (m)"],
    ["habitat", "Habitat"], ["manejo", "Manejo"], ["metodo", "Método de amostragem"]]) {
    if (p[campo] !== null && p[campo] !== undefined && p[campo] !== "") linhas.push(`${rotulo}: ${p[campo]}`);
  }

  for (
    const texto of linhas
  ) {

    const linha =
      document.createElement("div");

    linha.textContent =
      texto;

    janela.appendChild(
      linha
    );
  }

  const blocoAmbiental =
    document.createElement("div");

  blocoAmbiental.style.marginTop =
    "10px";

  janela.appendChild(
    blocoAmbiental
  );

  camada.bindPopup(
    janela
  );

  camada.on(
    "click",
    async function (evento) {

      if (
        evento.originalEvent
      ) {
        L.DomEvent.stopPropagation(
          evento.originalEvent
        );
      }

      const separador =
        document.createElement("hr");

      separador.style.margin =
        "10px 0";

      const carregando =
        document.createElement("div");

      carregando.textContent =
        `Consultando dados ambientais de ${dataAmbientalSelecionada}...`;

      blocoAmbiental.replaceChildren(
        separador,
        carregando
      );

      try {

        const dados =
          await consultarAmbiente(
            evento.latlng.lat,
            evento.latlng.lng
          );

        const conteudoAmbiental =
          criarPopupAmbiental(
            dados
          );

        const novoSeparador =
          document.createElement("hr");

        novoSeparador.style.margin =
          "10px 0";

        blocoAmbiental.replaceChildren(
          novoSeparador,
          conteudoAmbiental
        );

        camada.openPopup();

      } catch (erro) {

        console.error(
          "Erro ao consultar ambiente do ponto:",
          erro
        );

        const erroTexto =
          document.createElement("div");

        erroTexto.textContent =
          "Não foi possível carregar os dados ambientais.";

        blocoAmbiental.replaceChildren(
          separador,
          erroTexto
        );
      }
    }
  );

  const rotulo =
    document.createElement("span");

  rotulo.textContent =
    `${nome} — ${p.wg_grupo} · ${p.wg_setor}`;

  camada.bindTooltip(
    rotulo,
    {
      permanent: false,
      direction: "top"
    }
  );
}


// ================================================================
// 20. LEGENDA DOS GRUPOS
// ================================================================

function criarLegenda(
  estrutura
) {

  const controle =
    L.control({
      position: "bottomright"
    });

  controle.onAdd =
    function () {

      const painel =
        L.DomUtil.create(
          "div",
          "leaflet-bar"
        );

      Object.assign(
        painel.style,
        {
          background: "white",
          color: "#253042",
          padding: "10px",
          borderRadius: "6px",
          width: "250px",
          maxHeight: "45vh",
          overflowY: "auto"
        }
      );

      for (
        const setor of SETORES
      ) {

        const info =
          estrutura[setor];

        const secao =
          document.createElement(
            "details"
          );

        const resumo =
          document.createElement(
            "summary"
          );

        resumo.textContent =
          `${setor} · ${info.quantidade} pontos`;

        resumo.style.color =
          CONTORNOS[setor];

        resumo.style.fontWeight =
          "bold";

        secao.appendChild(
          resumo
        );

        const grupos =
          [...info.grupos].sort(
            (a, b) =>
              ORDEM_GRUPOS.indexOf(a[0]) -
              ORDEM_GRUPOS.indexOf(b[0])
          );

        for (
          const [
            grupo,
            item
          ]
          of grupos
        ) {

          const linha =
            document.createElement(
              "label"
            );

          linha.style.display =
            "flex";

          linha.style.gap =
            "6px";

          linha.style.alignItems =
            "center";

          const caixa =
            document.createElement(
              "input"
            );

          caixa.type =
            "checkbox";

          caixa.checked =
            true;

          caixa.addEventListener(
            "change",
            () => {

              if (
                caixa.checked
              ) {

                info.camada.addLayer(
                  item.camada
                );

              } else {

                info.camada.removeLayer(
                  item.camada
                );
              }
            }
          );

          const cor =
            document.createElement(
              "span"
            );

          Object.assign(
            cor.style,
            {
              width: "11px",
              height: "11px",
              borderRadius: "50%",
              background:
                obterCor(
                  grupo,
                  setor
                ),
              border:
                `1px solid ${CONTORNOS[setor]}`
            }
          );

          const texto =
            document.createElement(
              "span"
            );

          texto.textContent =
            `${grupo} (${item.quantidade})`;

          linha.append(
            caixa,
            cor,
            texto
          );

          secao.appendChild(
            linha
          );
        }

        painel.appendChild(
          secao
        );
      }

      return painel;
    };

  controle.addTo(
    mapa
  );

  adicionarControleAoPainel(controle, "grupos");
}


// ================================================================
// 21. CARREGAR PONTOS
// ================================================================

async function carregarPontos() {

  try {

    const resposta =
      await fetch(
        CONFIG.arquivo
      );

    if (!resposta.ok) {

      throw new Error(
        `Falha ao abrir ${CONFIG.arquivo}`
      );
    }

    const originais =
      await resposta.json();

    const dados =
      prepararDados(
        originais
      );

    const estrutura = {};

    for (
      const setor of SETORES
    ) {

      estrutura[setor] = {
        camada:
          L.featureGroup()
            .addTo(mapa),

        grupos:
          new Map(),

        quantidade:
          0
      };
    }

    const pontos =
      L.geoJSON(
        dados,
        {
          pointToLayer:
            function (
              feicao,
              latlng
            ) {

              const p =
                feicao.properties;

              return L.circleMarker(
                latlng,
                {
                  radius:
                    CONFIG.raioPontos,

                  color:
                    CONTORNOS[
                      p.wg_setor
                    ],

                  weight: 1.4,

                  fillColor:
                    p.wg_cor,

                  fillOpacity:
                    0.92
                }
              );
            },

          onEachFeature:
            configurarInformacoes
        }
      );

    pontos.eachLayer(
      (marcador) => {

        const p =
          marcador.feature.properties;

        const info =
          estrutura[
            p.wg_setor
          ];

        if (
          !info.grupos.has(
            p.wg_grupo
          )
        ) {

          info.grupos.set(
            p.wg_grupo,
            {
              camada:
                L.featureGroup()
                  .addTo(
                    info.camada
                  ),

              quantidade:
                0
            }
          );
        }

        const grupo =
          info.grupos.get(
            p.wg_grupo
          );

        grupo.camada.addLayer(
          marcador
        );

        grupo.quantidade += 1;

        info.quantidade += 1;
      }
    );

    const limites =
      pontos.getBounds();

    mapa.fitBounds(
      limites,
      {
        padding:
          [30, 30]
      }
    );


    // ============================================================
    // LINHAS DOS SETORES
    // ============================================================

    const linhasSetores =
      L.layerGroup();

    const divisorias = [
      [
        CONFIG.limiteNorteMeio,
        "Norte / Meio"
      ],
      [
        CONFIG.limiteMeioSul,
        "Meio / Sul"
      ]
    ];

    for (
      const [
        latitude,
        nome
      ]
      of divisorias
    ) {

      const linha =
        L.polyline(
          [
            [
              latitude,
              limites.getWest() - 0.1
            ],
            [
              latitude,
              limites.getEast() + 0.1
            ]
          ],
          {
            color:
              "#6B7280",

            weight:
              1.5,

            dashArray:
              "7 6"
          }
        );

      linha.bindTooltip(
        `${nome}: ${latitude.toFixed(6)}°`
      );

      linha.addTo(
        linhasSetores
      );
    }


    // ============================================================
    // CONTROLE DOS SETORES
    // ============================================================

    const sobreposicoes = {};

    for (
      const setor of SETORES
    ) {

      sobreposicoes[
        `${setor} — ${estrutura[setor].quantidade} pontos`
      ] =
        estrutura[setor].camada;
    }

    sobreposicoes[
      "Limites dos setores"
    ] =
      linhasSetores;

    const controleSetores =
      L.control.layers(
        {},
        sobreposicoes,
        {
          collapsed: false,
          position: "topright"
        }
      );

    controleSetores.addTo(
      mapa
    );

    adicionarControleAoPainel(controleSetores, "setores");

    criarLegenda(
      estrutura
    );

  } catch (erro) {

    console.error(
      erro
    );

    alert(
      `Não foi possível carregar os pontos: ${erro.message}`
    );
  }
}


// ================================================================
// 22. PAINEL AMBIENTAL
// ================================================================

const MESES_AMBIENTAIS = [
  { numero: "01", nome: "Janeiro" },
  { numero: "02", nome: "Fevereiro" },
  { numero: "03", nome: "Março" },
  { numero: "04", nome: "Abril" },
  { numero: "05", nome: "Maio" },
  { numero: "06", nome: "Junho" },
  { numero: "07", nome: "Julho" },
  { numero: "08", nome: "Agosto" },
  { numero: "09", nome: "Setembro" },
  { numero: "10", nome: "Outubro" },
  { numero: "11", nome: "Novembro" },
  { numero: "12", nome: "Dezembro" }
];

const controleAmbiental =
  L.control({
    position: "topleft"
  });

controleAmbiental.onAdd =
  function () {

    const painel =
      L.DomUtil.create(
        "div",
        "leaflet-bar"
      );

    Object.assign(
      painel.style,
      {
        background: "white",
        padding: "10px",
        borderRadius: "6px",
        minWidth: "220px",
        font: "13px Arial, sans-serif"
      }
    );

    // ------------------------------------------------------------
    // VARIÁVEL
    // ------------------------------------------------------------

    const labelProduto =
      document.createElement(
        "label"
      );

    labelProduto.textContent =
      "Variável: ";

    labelProduto.style.display =
      "block";

    labelProduto.style.marginBottom =
      "8px";

    const seletorProduto =
      document.createElement(
        "select"
      );

    const produtos = [
      [
        "CHL",
        "Clorofila-a"
      ],
      [
        "SST",
        "SST"
      ],
      [
        "PAR",
        "PAR"
      ],
      [
        "KD",
        "Kd 490"
      ],
      [
        "WAVEHEIGHT",
        "Altura significativa de ondas"
      ],
      [
        "CRW_DHW",
        "NOAA CRW — DHW (máximo diário mensal)"
      ],
      [
        "CRW_HOTSPOT",
        "NOAA CRW — HotSpot (máximo diário mensal)"
      ]
    ];

    for (
      const [
        codigo,
        nome
      ]
      of produtos
    ) {

      const opcao =
        document.createElement(
          "option"
        );

      opcao.value =
        codigo;

      opcao.textContent =
        nome;

      if (
        codigo ===
        produtoRasterSelecionado
      ) {
        opcao.selected = true;
      }

      seletorProduto.appendChild(
        opcao
      );
    }

    labelProduto.appendChild(
      seletorProduto
    );

    painel.appendChild(
      labelProduto
    );


    // ------------------------------------------------------------
    // ANO
    // ------------------------------------------------------------

    const labelAno =
      document.createElement(
        "label"
      );

    labelAno.textContent =
      "Ano: ";

    labelAno.style.display =
      "block";

    labelAno.style.marginBottom =
      "8px";

    const seletorAno =
      document.createElement(
        "select"
      );

    for (
      let ano = 2012;
    ano <= new Date().getFullYear();
      ano++
    ) {

      const opcao =
        document.createElement(
          "option"
        );

      opcao.value =
        String(ano);

      opcao.textContent =
        String(ano);

      if (ano === 2020) {
        opcao.selected = true;
      }

      seletorAno.appendChild(
        opcao
      );
    }

    labelAno.appendChild(
      seletorAno
    );

    painel.appendChild(
      labelAno
    );


    // ------------------------------------------------------------
    // MÊS
    // ------------------------------------------------------------

    const labelMes =
      document.createElement(
        "label"
      );

    labelMes.textContent =
      "Mês: ";

    labelMes.style.display =
      "block";

    labelMes.style.marginBottom =
      "8px";

    const seletorMes =
      document.createElement(
        "select"
      );

    for (
      const mes
      of MESES_AMBIENTAIS
    ) {

      const opcao =
        document.createElement(
          "option"
        );

      opcao.value =
        mes.numero;

      opcao.textContent =
        mes.nome;

      if (
        mes.numero === "01"
      ) {
        opcao.selected = true;
      }

      seletorMes.appendChild(
        opcao
      );
    }

    labelMes.appendChild(
      seletorMes
    );

    painel.appendChild(
      labelMes
    );

    // ------------------------------------------------------------
    // MOSTRAR RASTER
    // ------------------------------------------------------------

    const labelRaster =
      document.createElement(
        "label"
      );

    labelRaster.style.display =
      "block";

    labelRaster.style.margin =
      "10px 0";

    const checkboxRaster =
      document.createElement(
        "input"
      );

    checkboxRaster.type =
      "checkbox";

    checkboxRaster.checked =
      rasterAmbientalVisivel;

    labelRaster.appendChild(
      checkboxRaster
    );

    labelRaster.appendChild(
      document.createTextNode(
        " Mostrar camada"
      )
    );

    painel.appendChild(
      labelRaster
    );


    // ------------------------------------------------------------
    // OPACIDADE
    // ------------------------------------------------------------

    const labelOpacidade =
      document.createElement(
        "label"
      );

    labelOpacidade.textContent =
      "Opacidade";

    labelOpacidade.style.display =
      "block";

    const sliderOpacidade =
      document.createElement(
        "input"
      );

    sliderOpacidade.type =
      "range";

    sliderOpacidade.min =
      "0";

    sliderOpacidade.max =
      "1";

    sliderOpacidade.step =
      "0.05";

    sliderOpacidade.value =
      String(
        opacidadeRasterAmbiental
      );

    sliderOpacidade.style.width =
      "100%";

    sliderOpacidade.style.marginTop =
      "5px";

    const textoOpacidade =
      document.createElement(
        "div"
      );

    textoOpacidade.style.fontSize =
      "11px";

    textoOpacidade.style.textAlign =
      "right";

    textoOpacidade.textContent =
      `${Math.round(
        opacidadeRasterAmbiental *
        100
      )}%`;

    labelOpacidade.appendChild(
      sliderOpacidade
    );

    labelOpacidade.appendChild(
      textoOpacidade
    );

    painel.appendChild(
      labelOpacidade
    );


    // ------------------------------------------------------------
    // PERÍODO
    // ------------------------------------------------------------

    const periodo =
      document.createElement(
        "div"
      );

    periodo.className =
      "wg-periodo-ambiental";

    periodo.style.fontWeight =
      "bold";

    periodo.style.marginTop =
      "10px";

    periodo.textContent =
      `${produtoRasterSelecionado} — ${dataAmbientalSelecionada}`;

    painel.appendChild(
      periodo
    );

    const exportar = document.createElement("button");
    const previa = document.createElement("button");
    previa.type = "button";
    previa.className = "wg-previa-abrir";
    previa.textContent = "Conferir planilha antes de exportar";
    previa.addEventListener("click", () => abrirPreviaDados());
    exportar.type = "button";
    exportar.className = "wg-exportar";
    exportar.textContent = "Exportar séries de todos os pontos";
    const estadoExportar = document.createElement("small");
    estadoExportar.className = "wg-estado-exportacao";
    const ajudaExportar = document.createElement("small");
    ajudaExportar.textContent = "ZIP/CSV · 6 parâmetros · DHW mensal desde 2012";
    ajudaExportar.style.display = "block";
    painel.append(previa, exportar, ajudaExportar, estadoExportar);
    exportar.addEventListener("click", () => exportarSeriesCompletas(exportar, estadoExportar));


    // ------------------------------------------------------------
    // ATUALIZAR
    // ------------------------------------------------------------

    async function atualizar() {

      produtoRasterSelecionado =
        seletorProduto.value;

      dataAmbientalSelecionada =
        `${seletorAno.value}-${seletorMes.value}`;

      dataMensalSelecionada =
        dataAmbientalSelecionada;

      const dataLegenda = document.querySelector(".wg-data-escala");
      if (dataLegenda) dataLegenda.textContent = dataAmbientalSelecionada;

      labelAno.style.display =
        "block";

      labelMes.style.display =
        "block";

      atualizarEscalas();

      periodo.textContent =
        produtoRasterSelecionado.startsWith("CRW_")
          ? "NOAA Coral Reef Watch · buscando máximos diários do mês..."
          : `${produtoRasterSelecionado} — ${dataAmbientalSelecionada}`;

      if (produtoRasterSelecionado === "WAVEHEIGHT") {
        periodo.textContent += " | NetCDF até jun/2025; grade 0,5°; escala 0–3 m";
      }

      if (
        rasterAmbientalVisivel
      ) {

        return await mostrarRasterAmbiental(
          produtoRasterSelecionado,
          dataAmbientalSelecionada
        );
      }
      return true;
    }

    seletorProduto.addEventListener(
      "change",
      function () {
        atualizar();
      }
    );

    seletorAno.addEventListener(
      "change",
      function () {
        atualizar();
      }
    );

    seletorMes.addEventListener(
      "change",
      function () {
        atualizar();
      }
    );

    checkboxRaster.addEventListener(
      "change",
      async function () {

        rasterAmbientalVisivel =
          checkboxRaster.checked;

        if (
          !rasterAmbientalVisivel
        ) {
          requisicaoRasterAtual++;

          if (
            camadaRasterAmbiental &&
            mapa.hasLayer(
              camadaRasterAmbiental
            )
          ) {

            mapa.removeLayer(
              camadaRasterAmbiental
            );
          }

          return;
        }

        await mostrarRasterAmbiental(
          produtoRasterSelecionado,
          dataAmbientalSelecionada
        );
      }
    );

    sliderOpacidade.addEventListener(
      "input",
      function () {

        opacidadeRasterAmbiental =
          Number(
            sliderOpacidade.value
          );

        textoOpacidade.textContent =
          `${Math.round(
            opacidadeRasterAmbiental *
            100
          )}%`;

        if (
          camadaRasterAmbiental
        ) {

          if (typeof camadaRasterAmbiental.setOpacity === "function") {
            camadaRasterAmbiental.setOpacity(opacidadeRasterAmbiental);
          } else {
            camadaRasterAmbiental.setStyle({fillOpacity: opacidadeRasterAmbiental});
          }
        }
      }
    );

    L.DomEvent.disableClickPropagation(
      painel
    );

    L.DomEvent.disableScrollPropagation(
      painel
    );

    return painel;
  };

controleAmbiental.addTo(
  mapa
);

adicionarControleAoPainel(controleAmbiental, "ambiente");


// ================================================================
// 23. CLIQUE NO MAPA
// ================================================================

mapa.on(
  "click",
  async function (evento) {

    const popup =
      L.popup()
        .setLatLng(
          evento.latlng
        )
        .setContent(
          "Consultando CHL, SST, PAR, KD e WaveHeight..."
        )
        .openOn(
          mapa
        );

    try {

      const dados =
        await consultarAmbiente(
          evento.latlng.lat,
          evento.latlng.lng
        );

      popup.setContent(
        criarPopupAmbiental(
          dados
        )
      );

    } catch (erro) {

      console.error(
        "Erro na consulta ambiental:",
        erro
      );

      popup.setContent(
        "Não foi possível consultar os dados ambientais."
      );
    }
  }
);


// ================================================================
// 24. INICIAR
// ================================================================

const controleEscalas = L.control({position: "topleft"});
let conteudoEscalas;
let pedidoEscalas = 0;
controleEscalas.onAdd = () => {
  const painel = L.DomUtil.create("div", "wg-legendas leaflet-bar");
  Object.assign(painel.style, {background: "white", padding: "0", width: "100%", height: "auto", maxHeight: "none", borderRadius: "0"});
  conteudoEscalas = document.createElement("div");
  painel.appendChild(conteudoEscalas);
  return painel;
};
controleEscalas.addTo(mapa);
adicionarControleAoPainel(controleEscalas, "escalas");

async function atualizarEscalas() {
  const pedido = ++pedidoEscalas;
  try {
    const resposta = await fetch(`/escalas?data=${encodeURIComponent(dataAmbientalSelecionada)}`);
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    const dados = await resposta.json();
    if (pedido !== pedidoEscalas) return;
    conteudoEscalas.replaceChildren();
    const mes = document.createElement("strong");
    mes.className = "wg-data-escala";
    mes.textContent = dados.data;
    conteudoEscalas.appendChild(mes);
    const entradas = Object.entries(dados.escalas).sort(([a], [b]) =>
      a === produtoRasterSelecionado ? -1 : b === produtoRasterSelecionado ? 1 : 0);
    for (const [produto, escala] of entradas) {
      const item = document.createElement("section");
      item.className = `wg-escala${produto === produtoRasterSelecionado ? " ativa" : ""}`;
      Object.assign(item.style, {margin: "10px 0 14px", font: "12px Arial, sans-serif"});
      const titulo = document.createElement("strong");
      titulo.textContent = `${escala.nome || produto}${escala.unidade ? ` (${escala.unidade})` : ""}${produto === produtoRasterSelecionado ? " • camada selecionada" : ""}`;
      item.appendChild(titulo);
      if (escala.erro) {
        const aviso = document.createElement("div");
        aviso.textContent = "Sem dados neste mês";
        item.appendChild(aviso);
      } else {
        item.title = escala.nome;
        const barra = document.createElement("canvas");
        barra.width = 256;
        barra.height = 18;
        barra.className = "wg-gradiente";
        barra.setAttribute("role", "img");
        barra.setAttribute("aria-label", `Escala de ${escala.nome}: ${escala.minimo} a ${escala.maximo} ${escala.unidade}`);
        Object.assign(barra.style, {display: "block", width: "100%", height: "18px", minHeight: "18px", border: "1px solid #94a3b8", boxSizing: "border-box", margin: "6px 0 4px"});
        const ctx = barra.getContext("2d");
        const gradiente = ctx.createLinearGradient(0, 0, 256, 0);
        escala.cores.forEach((cor, i) => gradiente.addColorStop(i / (escala.cores.length-1), cor));
        ctx.fillStyle = gradiente;
        ctx.fillRect(0, 0, 256, 18);
        const marcas = document.createElement("div");
        marcas.className = "wg-marcas";
        Object.assign(marcas.style, {display: "flex", justifyContent: "space-between", gap: "3px", fontSize: "10px"});
        for (const valor of escala.marcas) {
          const marca = document.createElement("span");
          marca.textContent = Number(valor.toPrecision(3)).toLocaleString("pt-BR", {maximumSignificantDigits: 3});
          marcas.appendChild(marca);
        }
        const detalhe = document.createElement("small");
        detalhe.textContent = `${escala.tipo === "logaritmica" ? "Logarítmica" : "Linear"} · ${escala.limites}`;
        item.append(barra, marcas, detalhe);
      }
      conteudoEscalas.appendChild(item);
    }
  } catch (erro) {
    if (pedido === pedidoEscalas) conteudoEscalas.textContent = `Falha ao carregar escalas: ${erro.message}`;
  }
}

atualizarEscalas();
carregarPontos();

mostrarRasterAmbiental(
  produtoRasterSelecionado,
  dataAmbientalSelecionada
);

window.addEventListener(
  "resize",
  function () {
    mapa.invalidateSize();
  }
);

window.matchMedia("(min-width: 701px)").addEventListener("change", () => {
  document.getElementById("wg-painel-lateral").classList.remove("wg-painel-visivel");
  botaoPainelApp.setAttribute("aria-expanded", "false");
  setTimeout(() => mapa.invalidateSize(), 200);
});

setTimeout(
  function () {
    mapa.invalidateSize();
  },
  300
);
