"""Resumos de séries mensais, sem consultas adicionais às fontes."""
from collections import defaultdict
import math

UNIDADES = {"CHL": "mg/m³", "SST": "°C", "PAR": "mol/m²/dia",
            "KD": "m⁻¹", "WAVEHEIGHT": "m", "CRW_DHW": "°C-semanas",
            "CRW_HOTSPOT": "°C"}


def resumir_serie(produto, serie, unidade=None, incompleto=False):
    unidade = unidade or UNIDADES.get(produto, "")
    # Um valor por mês; valores ausentes nunca viram zero.
    meses = {item["data"]: item.get("valor") for item in serie}
    validos = {mes: float(v) for mes, v in meses.items()
               if v is not None and math.isfinite(float(v))}
    datas = sorted(meses)
    esperados = 0
    if datas:
        a, m = map(int, datas[0].split("-"))
        b, n = map(int, datas[-1].split("-"))
        esperados = (b-a)*12+n-m+1
    resultado = {"inicio": datas[0] if datas else None, "fim": datas[-1] if datas else None,
                 "meses_validos": len(validos), "meses_esperados": esperados,
                 "incompleto": bool(incompleto or len(validos) < esperados),
                 "metricas": [], "anuais": []}

    def adicionar(codigo, nome, valor, medida=unidade):
        resultado["metricas"].append({"codigo": codigo, "nome": nome,
                                       "valor": valor if valor is None or math.isfinite(valor) else None,
                                       "unidade": medida})

    valores = list(validos.values())
    if not valores:
        return resultado
    media = sum(valores)/len(valores)
    desvios = [v-media for v in valores]
    variancia = sum(d*d for d in desvios)/len(valores)
    sd = math.sqrt(variancia)
    adicionar("media", "Média dos valores mensais", media)
    adicionar("sd", "Desvio padrão populacional", sd)
    adicionar("minimo", "Mínimo mensal", min(valores))
    adicionar("maximo", "Máximo mensal", max(valores))
    if produto in ("CHL", "SST"):
        adicionar("cv", "CV (SD / média)" + (" em °C" if produto == "SST" else ""),
                  sd/abs(media) if media != 0 else None, "adimensional")
        adicionar("assimetria", "Assimetria (momentos populacionais)",
                  sum((d/sd)**3 for d in desvios)/len(valores)
                  if sd > 0 and len(valores) >= 3 else None, "adimensional")
        adicionar("curtose", "Excesso de curtose (normal = 0)",
                  sum((d/sd)**4 for d in desvios)/len(valores)-3
                  if sd > 0 and len(valores) >= 4 else None, "adimensional")
    anos = defaultdict(dict)
    for mes, valor in validos.items():
        anos[mes[:4]][mes[5:]] = valor
    for ano, observacoes in sorted(anos.items()):
        vs = list(observacoes.values())
        resultado["anuais"].append({"ano": ano, "meses_validos": len(vs),
                                    "completo": len(vs) == 12,
                                    "media": sum(vs)/len(vs), "maximo": max(vs)})
    if produto == "CRW_DHW":
        for limiar in (4, 8):
            adicionar(f"meses_gt_{limiar}", f"Meses com máximo DHW > {limiar}",
                      sum(v > limiar for v in valores), "meses")
        completos = [a["maximo"] for a in resultado["anuais"] if a["completo"]]
        adicionar("media_maximos_anuais", "Média dos máximos anuais (anos com 12 meses)",
                  sum(completos)/len(completos) if completos else None)
        adicionar("anos_completos", "Anos com 12 meses válidos", len(completos), "anos")
    return resultado


def linhas_indicadores(produto, resumo):
    """Linhas compartilhadas pelas exportações, com cobertura explícita."""
    for item in resumo["metricas"]:
        yield [produto, item["codigo"], item["nome"], item["valor"], item["unidade"],
               resumo["inicio"], resumo["fim"], resumo["meses_validos"],
               resumo["meses_esperados"], resumo["incompleto"]]


CABECALHO = ["produto", "indicador", "descricao", "valor", "unidade", "inicio", "fim",
             "meses_validos", "meses_esperados", "incompleto"]
