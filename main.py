from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, date
import httpx

def safe_float(value):
    """Converte um valor para float, retornando 0 se a conversão falhar."""
    try:
        return round(float(value.replace(',', '.')), 2)
    except (ValueError, AttributeError):
        return 0.0

async def obter_taxa_selic(data_pagamento):
    url = f"https://fast-selic.onrender.com/selic/{data_pagamento}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            dados = response.json()
            # Acessa a chave "taxa_selic" como está na resposta JSON
            return safe_float(dados["taxa_selic"])
        return None

app = FastAPI()

class GuiaData(BaseModel):
    valor: float
    data_vencimento: str  # Formato: YYYY-MM-DD
    data_pagamento: str = None  # Opcional; se não informado, utiliza a data atual

@app.post("/calcular")
async def calcular_guia(guia: GuiaData):
    # Converter as datas de string para objeto date
    try:
        vencimento = datetime.strptime(guia.data_vencimento, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data_vencimento inválido. Use YYYY-MM-DD.")

    if guia.data_pagamento:
        try:
            pagamento = datetime.strptime(guia.data_pagamento, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data_pagamento inválido. Use YYYY-MM-DD.")
    else:
        pagamento = date.today()

    # Se o pagamento ocorrer até a data de vencimento, não há multa nem juros
    if pagamento <= vencimento:
        dias_atraso = 0
        multa = 0.0
        juros = 0.0
    else:
        dias_atraso = (pagamento - vencimento).days
        # Calcula a multa: 0,3% por dia, limitada a 20% do valor
        multa_calculada = guia.valor * 0.003 * dias_atraso
        multa = min(multa_calculada, guia.valor * 0.20)
        # Obter a taxa SELIC (mensal) da API externa
        taxa_selic = await obter_taxa_selic(pagamento)
        if taxa_selic is None:
            raise HTTPException(status_code=500, detail="Não foi possível obter a taxa SELIC.")
        # Juros baseados na taxa SELIC
        juros = guia.valor * taxa_selic

    total = guia.valor + multa + juros

    return {
        "valor_original": round(guia.valor, 2),
        "data_vencimento": guia.data_vencimento,
        "data_pagamento": pagamento.isoformat(),
        "dias_atraso": dias_atraso,
        "multa": round(multa, 2),
        "juros": round(juros, 2),
        "valor_total": round(total, 2)
    }
