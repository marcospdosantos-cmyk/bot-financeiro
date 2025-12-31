from fastapi import FastAPI
from pydantic import BaseModel, Field
import os
import re
import requests
from supabase import create_client
from datetime import datetime, date

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
# MODELO DE ENTRADA
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
# DETECTA INTENÇÃO
# =============================
def detectar_intencao(texto: str):
    texto = texto.lower()

    if any(p in texto for p in ["quanto", "resumo", "gastei hoje", "hoje", "mês", "mes"]):
        return "consulta"

    if any(p in texto for p in ["gastei", "paguei", "comprei", "recebi"]):
        return "registro"

    return "desconhecido"


# =============================
# INTERPRETA TEXTO DE GASTO
# =============================
def interpretar_texto(texto: str):
    texto_lower = texto.lower()

    # valor
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
        "uber": "transporte",
    }

    for palavra, cat in categorias.items():
        if palavra in texto_lower:
            categoria = cat
            break

    return {
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria
    }


# =============================
# CONSULTA GASTOS
# =============================
def consultar_gastos(telefone: str, periodo: str):
    hoje = date.today()

    query = supabase.table("movimentos").select("*").eq("telefone", telefone)

    if periodo == "hoje":
        query = query.gte("criado_em", hoje.isoformat())

    elif periodo == "mes":
        primeiro_dia = hoje.replace(day=1)
        query = query.gte("criado_em", primeiro_dia.isoformat())

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

    resposta = "Não entendi 😅 Pode repetir?"

    # -------------------------
    # CONSULTA
    # -------------------------
    if intencao == "consulta":
        periodo = "hoje" if "hoje" in texto.lower() else "mes"

        total, dados = consultar_gastos(telefone, periodo)

        if total == 0:
            resposta = "📭 Ainda não encontrei gastos nesse período."
        else:
            resposta = f"📊 Você gastou R$ {total:.2f} "

            if periodo == "hoje":
                resposta += "hoje.\n"
            else:
                resposta += "este mês.\n"

            categorias = {}
            for item in dados:
                cat = item["categoria"]
                categorias[cat] = categorias.get(cat, 0) + item["valor"]

            for cat, valor in categorias.items():
                resposta += f"• {cat}: R$ {valor:.2f}\n"

    # -------------------------
    # REGISTRO
    # -------------------------
    elif intencao == "registro":
        parsed = interpretar_texto(texto)

        if parsed["valor"] is not None and supabase:
            supabase.table("movimentos").insert({
                "telefone": telefone,
                "tipo": parsed["tipo"],
                "categoria": parsed["categoria"],
                "valor": parsed["valor"],
                "texto_original": texto
            }).execute()

            resposta = f"✅ Anotado! {parsed['tipo']} de R$ {parsed['valor']:.2f} em {parsed['categoria']}."

        else:
            resposta = "Não consegui identificar o valor 😕"

    # -------------------------
    # ENVIA RESPOSTA NO WHATS
    # -------------------------
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
        "received": {
            "from": telefone,
            "body": texto
        },
        "response": resposta
    }
