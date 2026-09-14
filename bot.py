# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from telegram import Bot

# ================= CONFIGURAÇÃO (RAILWAY & ENV) =================
TOKEN = os.getenv("TELEGRAM_TOKEN", "8864077129:AAGynp2700ocgTeh-0aWoTkD-UwE95_jeuQ")
CHAT_ID = os.getenv("CHAT_ID", "-1003937431244")
API_URL = os.getenv("API_URL", "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("SUPREMO-G2")

bot = Bot(token=TOKEN)

state = {
    "history": [],
    "last_id": None,
    "waiting": False,
    "target": None,
    "gale_step": 0,  # 0 = SG, 1 = G1, 2 = G2
    "wins": 0,
    "losses": 0,
    "streak": 0,
    "streak_loss": 0,
    "pause_until": None,
    "msg_placar": None,
    "msg_analise": None,
    "msg_gale": None
}

# ================= BANCO DE ESTRATÉGIAS TURBINADO (G2) =================
PADROES = [
    # ALTERNÂNCIAS (XADREZ)
    {"seq": ["🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔴","🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔵","🔴","🔵"], "sinal": "🔴"},
    
    # QUEBRAS DE TENDÊNCIA (ANTI-SURF)
    {"seq": ["🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔵","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔴","🔴","🔴","🔴"], "sinal": "🔵"},
    
    # RAMPA E SURF (FLUXO)
    {"seq": ["🔵","🔵"], "sinal": "🔵"}, {"seq": ["🔴","🔴"], "sinal": "🔴"},
    {"seq": ["🔴","🔵","🔵"], "sinal": "🔵"}, {"seq": ["🔵","🔴","🔴"], "sinal": "🔴"},
    
    # BLOCOS E ESPELHAMENTOS
    {"seq": ["🔵","🔵","🔴","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔴","🔵","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔴","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔵","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔴"], "sinal": "🔵"}, {"seq": ["🔴","🔴","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔵","🔵"], "sinal": "🔴"}, {"seq": ["🔴","🔵","🔴","🔴"], "sinal": "🔵"},
    
    # ESTRATÉGIAS DE REPETIÇÃO
    {"seq": ["🔵","🔴","🔵","🔴","🔵"], "sinal": "🔵"},
    {"seq": ["🔴","🔵","🔴","🔵","🔴"], "sinal": "🔴"},
    {"seq": ["🔵","🔵","🔵","🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔴","🔴","🔴","🔵","🔵","🔵"], "sinal": "🔴"}
]

# ================= FUNÇÕES DE ENVIO E MENSAGENS =================
async def send_msg(text):
    try: 
        m = await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        return m.message_id
    except Exception as e:
        log.error(f"Erro ao enviar mensagem: {e}")
        return None

async def delete_msg(mid):
    if mid:
        try: 
            await bot.delete_message(chat_id=CHAT_ID, message_id=mid)
        except Exception: 
            pass

async def enviar_placar():
    if state["msg_placar"]: 
        await delete_msg(state["msg_placar"])
    
    texto = (f"🏆 <b>PLACAR ATUALIZADO</b>\n\n"
             f"✅ GREENS: {state['wins']}\n"
             f"❌ LOSS: {state['losses']}")
    
    state["msg_placar"] = await send_msg(texto)

async def processar_resultado(cor):
    if cor == "🟡" or cor == state["target"]:
        state["wins"] += 1
        state["streak"] += 1
        state["streak_loss"] = 0 
        
        if state["gale_step"] == 0:
            tipo = "SG"
        else:
            tipo = f"G{state['gale_step']}"
        
        if cor == "🟡":
            msg_vitoria = (f"🟠 <b>EMPATE</b>\n"
                           f"❇️❇️❇️❇️❇️❇️❇️❇️\n❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥𝗣𝗔𝗚𝗢𝗢𝗢!🔥\n\n"
                           f"🚀 TOMAA!!! {state['streak']} GREENS SEGUIDOS 🚀")
        else:
            msg_vitoria = (f"❇️❇️❇️❇️❇️❇️❇️❇️\n❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥𝗣𝗔𝗚𝗢𝗢𝗢!🔥 {tipo}\n\n"
                           f"🚀 TOMAA!!! {state['streak']} GREENS SEGUIDOS 🚀")
        
        await send_msg(msg_vitoria)
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})
        await enviar_placar()

    elif state["gale_step"] == 0:
        state["gale_step"] = 1
        await delete_msg(state["msg_gale"])
        state["msg_gale"] = await send_msg("⚠️ <b>VAMOS PARA O GALE 1</b>")
    
    elif state["gale_step"] == 1:
        state["gale_step"] = 2
        await delete_msg(state["msg_gale"])
        state["msg_gale"] = await send_msg("⚠️⚠️ <b>VAMOS PARA O GALE 2</b>")
    
    else:
        state["losses"] += 1
        state["streak"] = 0
        state["streak_loss"] += 1
        
        await send_msg("❌ <b>LOSS NO G2!</b>")
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})

        if state["streak_loss"] >= 2:
            state["pause_until"] = datetime.now() + timedelta(minutes=10)
            await send_msg("🛑 <b>PAUSA DE SEGURANÇA (10 MIN)</b>\n2 Reds seguidos. Preservando a banca!")
            state["streak_loss"] = 0
            
        await enviar_placar()

# ================= REQUISIÇÃO DA API =================
def fetch_api_data():
    req = urllib.request.Request(
        API_URL, 
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
    except urllib.error.HTTPError as e:
        log.warning(f"API retornou erro HTTP {e.code}: {e.reason}")
    except Exception as e:
        log.warning(f"Aviso de conexão com a API: {e}")
    return None

# ================= LOOP PRINCIPAL =================
async def main():
    log.info(f"BlackG2 iniciado com sucesso. Total de padrões carregados: {len(PADROES)}")
    await enviar_placar()
    
    while True:
        try:
            if state["pause_until"]:
                if datetime.now() < state["pause_until"]:
                    await asyncio.sleep(5)
                    continue
                else:
                    state["pause_until"] = None
                    await send_msg("🔄 <b>RETOMANDO ANÁLISES!</b>\nPausa encerrada.")

            data = await asyncio.to_thread(fetch_api_data)
            if data:
                d = data.get("data", data)
                if isinstance(d, list) and len(d) > 0:
                    d = d[0]
                
                if isinstance(d, dict):
                    rid = d.get("id") or d.get("gameId")
                    
                    if rid and rid != state["last_id"]:
                        state["last_id"] = rid
                        res_block = d.get("result", {})
                        res_raw = res_block.get("outcome") if isinstance(res_block, dict) else d.get("outcome")
                        
                        cor = {
                            "PlayerWon": "🔵", "Jogador": "🔵", "Player": "🔵", "PLAYER": "🔵",
                            "BankerWon": "🔴", "Bancao": "🔴", "Banker": "🔴", "BANKER": "🔴",
                            "Tie": "🟡", "Empate": "🟡", "TIE": "🟡"
                        }.get(res_raw)
                        
                        if cor:
                            if cor != "🟡":
                                state["history"].append(cor)
                                state["history"] = state["history"][-30:]
                            
                            if state["waiting"]:
                                await processar_resultado(cor)
                            else:
                                found = False
                                for p in PADROES:
                                    if len(state["history"]) >= len(p["seq"]) and state["history"][-len(p["seq"]):] == p["seq"]:
                                        state["target"] = p["sinal"]
                                        state["waiting"] = True
                                        state["gale_step"] = 0
                                        
                                        if state["msg_analise"]:
                                            await delete_msg(state["msg_analise"])
                                            state["msg_analise"] = None

                                        entrada = (f"🚀 <b>ENTRADA CONFIRMADA</b>\n\n"
                                                   f"Apostar: {p['sinal']}\n"
                                                   f"Proteção: 🟡 Empate\n"
                                                   f"Limite: 2 Gales")
                                        await send_msg(entrada)
                                        found = True
                                        break
                                
                                if not found and not state["msg_analise"]:
                                    state["msg_analise"] = await send_msg("🔍 <b>Analisando padrões...</b>")

        except Exception as e:
            log.error(f"Erro crítico no loop principal: {e}")
            
        await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Aplicação encerrada manualmente.")
