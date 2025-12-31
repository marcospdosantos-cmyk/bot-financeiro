from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import re
import requests
from supabase import create_client
from datetime import datetime, date, timedelta

app = FastAPI()

# =============================
# SUPABASE
# =============================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =============================
# MODELO
# =============================
class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str


# =============================
# HOME
# =============================
@app.get("/")
def home():
    return {"status": "ok", "message": "Bot financeiro rodando 🚀"}


# =============================
# INTENÇÃO
# =============================
def detectar_intencao(texto: str):
    t = texto.lower()

    if any(p in t for p in ["quanto", "resumo", "hoje", "ontem", "mês", "mes", "dia"]):
        return "consulta"

    if any(p in t for p in ["gastei", "paguei", "comprei", "recebi"]):
        return "registro"

    return "desconhecido"


# =============================
# DATA
# =============================
def extrair_data(texto: str):
    texto = texto.lower()
    hoje = date.today()

    if "hoje" in texto:
        return hoje

    if "ontem" in texto:
        return hoje - timedelta(days=1)

    if "anteontem" in texto:
        return hoje - timedelta(days=2)

    match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?", texto)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        ano = int(match.group(3)) if match.group(3) else hoje.year
        try:
            return date(ano, mes, dia)
        except:
            return None

    return None


# =============================
# INTERPRETAR TEXTO
# =============================
def interpretar_texto(texto: str):
    texto_lower = texto.lower()

    valor_match = re.search(r"(\d+[.,]?\d*)", texto_lower)
    valor = float(valor_match.group(1).replace(",", ".")) if valor_match else None

    tipo = "despesa"
    if any(p in texto_lower for p in ["ganhei", "recebi", "salário", "salario"]):
        tipo = "receita"

    categoria = "outros"
    categorias = {
        "mercado": "mercado",
        "supermercado": "mercado",
        "roupa": "roupas",
        "almoço": "alimentação",
        "janta": "alimentação",
        "comida": "alimentação",
        "aluguel": "moradia",
        "luz": "contas",
        "água": "contas",
        "internet": "contas",
        "gasolina": "transporte",
        "uber": "transporte"
    }

    for palavra, cat in categorias.items():
        if palavra in texto_lower:
            categoria = cat
            break

    data_mov = extrair_data(texto)

    return {
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria,
        "data": data_mov
    }


# =============================
# CONSULTA
# =============================
def consultar_gastos(telefone: str, data_ref: date | None):
    query = supabase.table("movimentos").select("*").eq("telefone", telefone)

    if data_ref:
        inicio = datetime.combine(data_ref, datetime.min.time())
        fim = inicio + timedelta(days=1)

        query = query.gte("criado_em", inicio.isoformat())
        query = query.lt("criado_em", fim.isoformat())

    dados = query.execute().data or []

    total = sum(item["valor"] for item in dados if item["tipo"] == "despesa")
    return total, dados


# =============================
# WEBHOOK
# =============================
@app.post("/webhook")
async def webhook(data: WebhookMessage):
    telefone = data.from_
    texto = data.body.strip()

    intencao = detectar_intencao(texto)
    resposta = "Não entendi 😅 Pode tentar de outro jeito?"

    # ================= CONSULTA =================
    if intencao == "consulta":
        data_ref = extrair_data(texto)
        total, dados = consultar_gastos(telefone, data_ref)

        if not dados:
            resposta = "📭 Não encontrei gastos nesse período."
        else:
            if data_ref:
                resposta = f"📊 Gastos em {data_ref.strftime('%d/%m/%Y')}:\n"
            else:
                resposta = "📊 Seus gastos:\n"

            categorias = {}
            for item in dados:
                categorias[item["categoria"]] = categorias.get(item["categoria"], 0) + item["valor"]

            for cat, valor in categorias.items():
                resposta += f"• {cat}: R$ {valor:.2f}\n"

    # ================= REGISTRO =================
    elif intencao == "registro":
        parsed = interpretar_texto(texto)

        if parsed["valor"] is not None and supabase:
            data_final = parsed["data"]
            if data_final:
                criado_em = datetime.combine(data_final, datetime.min.time())
            else:
                criado_em = datetime.utcnow()

            try:
                supabase.table("movimentos").insert({
                    "telefone": telefone,
                    "tipo": parsed["tipo"],
                    "categoria": parsed["categoria"],
                    "valor": parsed["valor"],
                    "texto_original": texto,
                    "criado_em": criado_em.isoformat()
                }).execute()

                resposta = (
                    f"✅ Anotado!\n"
                    f"{parsed['tipo'].capitalize()} de R$ {parsed['valor']:.2f}\n"
                    f"Categoria: {parsed['categoria']}"
                )
            except Exception as e:
                resposta = "❌ Erro ao salvar o lançamento."

    # ================= ENVIO WHATSAPP =================
    ULTRA_INSTANCE = os.getenv("ULTRA_INSTANCE")
    ULTRA_TOKEN = os.getenv("ULTRA_TOKEN")

    if ULTRA_INSTANCE and ULTRA_TOKEN:
        try:
            requests.post(
                f"https://api.ultramsg.com/{ULTRA_INSTANCE}/messages/chat",
                data={
                    "token": ULTRA_TOKEN,
                    "to": telefone,
                    "body": resposta
                },
                timeout=10
            )
        except:
            pass

    return {
        "status": "ok",
        "received": {"from": telefone, "body": texto},
        "response": resposta
    }
