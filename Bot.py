# -*- coding: utf-8 -*-
import asyncio
import logging
import json
import urllib.request
import urllib.error
import socket
from datetime import datetime, timedelta
from telegram.ext import Application

# ================= CONFIGURAÇÃO =================
TOKEN = "8864077129:AAGMv6t9q-ZjirwsZVuYuFU3kdHIjs3nDQQ"
CHAT_ID = "-1003954099833"

# URL da API de resultados
API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("SUPREMO-V4")

state = {
    "history": [],
    "last_id": None,
    "waiting": False,
    "target": None,
    "is_gale": False,
    "wins": 0,
    "losses": 0,
    "streak": 0,
    "streak_loss": 0,
    "pause_until": None,
    "msg_placar": None,
    "msg_analise": None,
    "msg_gale": None
}

PADROES = [
    {"seq": ["🔵","🔵","🔵","🔵","🔵"], "sinal": "🔴"}, 
    {"seq": ["🔴","🔴","🔴","🔴","🔴"], "sinal": "🔵"}, 
    {"seq": ["🔵","🔴","🔵","🔴","🔵"], "sinal": "🔴"}, 
    {"seq": ["🔴","🔵","🔴","🔵","🔴"], "sinal": "🔵"}, 
    {"seq": ["🔵","🔵","🔴","🔴","🔵"], "sinal": "🔵"}, 
    {"seq": ["🔴","🔴","🔵","🔵","🔴"], "sinal": "🔴"},  
    {"seq": ["🔵","🔵","🔴","🔴"], "sinal": "🔵"}, 
    {"seq": ["🔴","🔴","🔵","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔴","🔴","🔵"], "sinal": "🔴"}, 
    {"seq": ["🔴","🔵","🔵","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔴","🔵","🔴"], "sinal": "🔵"}, 
    {"seq": ["🔴","🔵","🔴","🔵"], "sinal": "🔴"},
    {"seq": ["🔵","🔵","🔵","🔵"], "sinal": "🔵"}, 
    {"seq": ["🔴","🔴","🔴","🔴"], "sinal": "🔴"}, 
    {"seq": ["🔵","🔵","🔵"], "sinal": "🔴"}, 
    {"seq": ["🔴","🔴","🔴"], "sinal": "🔵"},
    {"seq": ["🔵","🔵","🔴"], "sinal": "🔴"}, 
    {"seq": ["🔴","🔴","🔵"], "sinal": "🔵"},
    {"seq": ["🔵","🔴"], "sinal": "🔵"}, 
    {"seq": ["🔴","🔵"], "sinal": "🔴"}
]

async def send_msg(app, text):
    try: 
        return await app.bot.send_message(CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Erro ao enviar mensagem: {e}")
        return None

async def delete_msg(app, mid):
    if mid:
        try: 
            await app.bot.delete_message(CHAT_ID, mid)
        except Exception: 
            pass

async def enviar_placar(app):
    if state["msg_placar"]: 
        await delete_msg(app, state["msg_placar"])
    
    texto = (f"🏆 <b>PLACAR ATUALIZADO</b>\n\n"
             f"✅ 𝗚𝗥𝗘𝗘𝗡𝗦: {state['wins']}\n"
             f"❌ 𝗟𝗢𝗦𝗦: {state['losses']}")
    
    msg = await send_msg(app, texto)
    if msg: 
        state["msg_placar"] = msg.message_id

async def processar_resultado(app, cor):
    if cor == "🟡" or cor == state["target"]:
        state["wins"] += 1
        state["streak"] += 1
        state["streak_loss"] = 0 
        
        tipo = "G1" if state["is_gale"] else "SG"
        
        if cor == "🟡":
            msg_vitoria = (f"🟠 <b>EMPATE</b>\n"
                           f"❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥 𝗣𝗔𝗚𝗢𝗢𝗢! 🔥 ({tipo})\n\n"
                           f"🚀 TOMAA! {state['streak']} GREENS SEGUIDOS 🚀")
        else:
            msg_vitoria = (f"❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥 𝗣𝗔𝗚𝗢𝗢𝗢! 🔥 ({tipo})\n\n"
                           f"🚀 TOMAA! {state['streak']} GREENS SEGUIDOS 🚀")
        
        await send_msg(app, msg_vitoria)
        await delete_msg(app, state["msg_analise"])
        await delete_msg(app, state["msg_gale"])
        state.update({"waiting": False, "is_gale": False, "msg_analise": None, "msg_gale": None})
        await enviar_placar(app)

    elif not state["is_gale"]:
        state["is_gale"] = True
        msg_g = await send_msg(app, "⚠️ <b>VAMOS PARA O GALE 1</b>")
        if msg_g: 
            state["msg_gale"] = msg_g.message_id
    
    else:
        state["losses"] += 1
        state["streak"] = 0
        state["streak_loss"] += 1
        
        await send_msg(app, "❌ <b>LOSS!</b>")
        await delete_msg(app, state["msg_analise"])
        await delete_msg(app, state["msg_gale"])
        state.update({"waiting": False, "is_gale": False, "msg_analise": None, "msg_gale": None})

        if state["streak_loss"] >= 2:
            state["pause_until"] = datetime.now() + timedelta(minutes=10)
            await send_msg(app, "🛑 <b>PAUSA DE SEGURANÇA (10 MIN)</b>\n2 Reds seguidos. Preservando a banca!")
            state["streak_loss"] = 0
            
        await enviar_placar(app)

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
        # Timeout curto (2s) para evitar travamentos e atrasos na leitura do bot
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, Exception) as e:
        return None
    return None

async def background_worker(app):
    while True:
        if state["pause_until"]:
            if datetime.now() < state["pause_until"]:
                await asyncio.sleep(5)
                continue
            else:
                state["pause_until"] = None
                await send_msg(app, "🔄 <b>BOT ONLINE - REINICIANDO ANÁLISES</b>")

        try:
            data = await asyncio.to_thread(fetch_api_data)
            if data:
                d = data.get("data", data)
                if isinstance(d, dict):
                    rid = d.get("id")
                    
                    if rid and rid != state["last_id"]:
                        state["last_id"] = rid
                        result_block = d.get("result", {})
                        res_raw = result_block.get("outcome") if isinstance(result_block, dict) else None
                        
                        # Mapeamento do resultado aceitando o padrao da API em Ingles e Portugues
                        cor = {
                            "PlayerWon": "🔵", "Jogador": "🔵", "Player": "🔵",
                            "BankerWon": "🔴", "Bancao": "🔴", "Banker": "🔴",
                            "Tie": "🟡", "Empate": "🟡"
                        }.get(res_raw)
                        
                        if cor:
                            if cor != "🟡":
                                state["history"].append(cor)
                                state["history"] = state["history"][-20:]
                            
                            if state["waiting"]:
                                await processar_resultado(app, cor)
                            else:
                                found = False
                                for p in PADROES:
                                    if len(state["history"]) >= len(p["seq"]) and state["history"][-len(p["seq"]):] == p["seq"]:
                                        state["target"] = p["sinal"]
                                        state["waiting"] = True
                                        
                                        await delete_msg(app, state["msg_analise"])
                                        state["msg_analise"] = None

                                        entrada = (f"🚀 <b>ENTRADA CONFIRMADA</b>\n\n"
                                                   f"Apostar: {p['sinal']}\n"
                                                   f"Proteção: 🟡 Empate\n"
                                                   f"Limite: 1 Gale")
                                        await send_msg(app, entrada)
                                        found = True
                                        break
                                
                                if not found and not state["msg_analise"]:
                                    msg_a = await send_msg(app, "🔍 <b>Analisando padrões...</b>")
                                    if msg_a: 
                                        state["msg_analise"] = msg_a.message_id

        except Exception as e:
            log.error(f"Erro na captura dos dados: {e}")
            
        await asyncio.sleep(1)

async def main():
    app = Application.builder().token(TOKEN).build()
    await app.initialize()
    await app.start()
    
    try:
        await enviar_placar(app)
        await background_worker(app)
    finally:
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Aplicação encerrada manualmente.")
