# -*- coding: utf-8 -*-
import asyncio
import logging
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from telegram import Bot

# ================= CONFIGURAÇÃO =================
TOKEN = "8864077129:AAGynp2700ocgTeh-0aWoTkD-UwE95_jeuQ"
CHAT_ID = "-1003954099833"

API_URL = "https://api-cs.casino.org/svc-evolution-game-events/api/bacbo/latest"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("SUPREMO-V4")

bot = Bot(token=TOKEN)

state = {
    "history": [],
    "last_id": None,
    "waiting": False,
    "target": None,
    "gale_step": 0,  # 0 = Entrada Normal, 1 = Gale 1, 2 = Gale 2
    "wins": 0,
    "losses": 0,
    "streak": 0,
    "streak_loss": 0,
    "pause_until": None,
    "msg_placar": None,
    "msg_analise": None,
    "msg_gale": None
}

# Tradutor universal para converter as letras (A/V/E) para os emojis do bot
def traduzir_sequencia(seq_str):
    mapa = {'A': '🔵', 'V': '🔴', 'E': '🟡'}
    return [mapa.get(c, c) for c in seq_str]

# Lista expandida com os seus 579 padrões
PADROES_RAW = [
    "AVVVAVV=V", "VVVAVVA=V", "AVVAAVV=V", "AVVVVAV=A", "AAVVVAV=V", "VVAVVAV=A", "VVAAVVV=V", "AVAVAAV=A", "AAVAVAA=A", "VVAVVAA=V", 
    "AAVVAAA=V", "AVAAVAA=A", "VAAAVAA=A", "VAVVAVA=A", "AVAAAVA=A", "AAAAVAV=V", "AAAVVVA=A", "VAAVVVA=V", "VAVAAVA=V", "VAVVVAV=V", 
    "VAAVAAA=A", "VVAVAAA=A", "VVAVAVV=A", "VAVAVAA=A", "AVVAVVA=V", "VAAVAVA=A", "VVVAVAV=A", "VAAAVVV=V", "VAAAAAV=V", "AAVAAAA=A", 
    "AAAAAAA=V", "AVAVAVA=A", "AAVAAAV=A", "AAAVAAV=A", "AVVAAAV=V", "AVAAVAV=A", "VAAVVAA=V", "VAVAAAA=A", "AAAVAVA=V", "VAVAVVV=A", 
    "AAAVVVV=V", "AVAAAAA=A", "VVVVAVA=A", "AVVAAAA=A", "VVVAAVV=A", "VAAAAAA=A", "VAAVVVV=A", "VAVVAAA=A", "VVAAAAA=V", "VVAAVVA=A", 
    "AAAAVVV=V", "VAVAAVV=A", "AVAAVVV=V", "AVAVAAA=V", "VAVVVVA=V", "AAVAAVA=A", "VAVVAVV=A", "VVAVAVA=A", "VAAAAVA=A", "AVVAVAA=A", 
    "AVAVVVA=V", "AVVVAVA=V", "AVVAVAV=A", "VVAVAAV=A", "VVAAAVV=V", "AAAVAVV=A", "AAVVVVA=A", "AAAAAVA=V", "AAAVAAA=A", "AVVVAAV=V", 
    "VVVVAVV=A", "AVAAVVA=A", "AVAAAAV=V", "VAVAAAV=V", "AAVVVAA=A", "VAVAVAV=A", "VVAVVVA=V", "AAAAVAA=A", "AAVVAVA=V", "VVVAVAA=V", 
    "AVAVVVV=V", "AAVAVAV=A", "VAVVAAV=A", "VVVAVVV=A", "AVAVVAV=A", "VVVAAVA=V", "AAVAVVV=V", "AAVVVVV=A", "AAVAAVV=V", "AAVVAAV=V", 
    "VVAAAVA=A", "VAVVVAA=V", "AAVAVVA=A", "AAAVVAA=V", "AVVAVVV=V", "VAAVAVV=A", "VAAVVAV=A", "VAVAVVA=A", "VVVVAAV=V", "AVAVVAA=A", 
    "AVVVVAA=A", "AVVVAAA=A", "VVAAVAV=A", "VVVVVVA=V", "AAAAAVV=A", "VVAAAAV=V", "AVVVVVV=V", "AVAAAVV=V", "VVVAAAV=A", "AAAAAAV=A", 
    "VAAAVAV=A", "AVAVAVV=A", "VAAAAVV=V", "VAAAVVA=V", "VAAVAAV=A", "VVAAVAA=V", "VVAVVVV=V", "AAAAVVA=A", "VAVVVVV=V", "AAVVAVV=V", 
    "VVVAAAA=A", "AAAVVAV=V", "VVVVVAV=A", "AVVVVVA=A", "VVVVAAA=V", "VVVVVAA=A", "AVVAAVA=A", "VVVVVVV=A", "AEVVAVA=A", "AAAAEAV=V", 
    "AAEVVAV=V", "VAEVAVV=A", "AAAAEVA=A", "AAAEAVA=V", "AAAEAVV=V", "VVEAAAA=V", "AAVVVVE=A", "VAVAEVV=A", "EVAAAAA=A", "AVVEVVA=V", 
    "VVEVVAA=V", "VAAAAEA=A", "AVAEVAV=V", "AAVEVVV=A", "EAVVVVA=A", "AAAAAEV=V", "AAVVVAE=V", "VAAVVVE=A", "EVVVVAA=V", "EAVVAAV=A", 
    "VVVVVAE=A", "VVAVVAE=A", "VVVAAEA=A", "AVVVEVA=V", "AAAAAAE=V", "EVVAVVA=V", "VVVVAAE=V", "AAEAVVV=V", "AAEAAAV=V", "VVVEAAA=V", 
    "AVAAAAE=V", "AVVEAAA=A", "VEAAAAV=V", "VVAVAEV=A", "VVVVAEV=A", "VVVAEVA=A", "AEAAAVV=A", "VVVVVEV=A", "VVVVEVV=A", "VAVVAAE=V", 
    "AAEAVAA=V", "VAAAAAE=A", "AVVAAAE=A", "VEAVAAV=A", "AAAVEVA=A", "VEAVVVV=V", "EAVAAVV=A", "VEVVAAA=V", "AEVAAAA=A", "VAAVEVV=A", 
    "AAEVAAV=V", "AAVEAVV=V", "AVEAVVA=A", "VAAEVVA=V", "AAAEVAA=V", "AVAEVVA=A", "VVEVAVV=V", "EVVAAAA=V", "EAAAAVV=V", "VEVAAVA=V", 
    "EVAAVAV=V", "VAEAVVA=V", "VVEVAAV=V", "VVEAVAA=A", "VVAAEAA=V", "VEVAVVA=V", "AVAVAAE=A", "AEAVVAA=V", "VVAAEAV=V", "VAEVVAV=V", 
    "AEVVVVA=V", "AEVAVVV=V", "VVVEVAA=V", "AVEVVVA=V", "EVAVVAV=A", "AAEAAVA=A", "AVVVVEA=A", "EAAVAAA=A", "AAVVEAV=A", "EVVAVAA=A", 
    "EVAAVVV=V", "VVAEAVV=V", "VVVAVAE=V", "VVVVEVA=V", "VAVAAAE=V", "AAVAEVA=V", "VAVAEVA=V", "AEAVAAV=A", "VEVAAVV=V", "AAVVVEA=A", 
    "AVVVVEV=A", "VAVVAEV=A", "AVAAAEV=V", "VEAVVAA=A", "AAAAAEA=A", "VVVEVVA=A", "AAVVVEV=A", "AAEVAAA=V", "VAAAVAE=A", "VAVVAEA=A", 
    "AVVAAEA=V", "EAVAAVA=A", "AVEVVVV=V", "EVAVVVV=A", "AVEAVAA=V", "VEVAVVV=A", "VVVEVAV=V", "AAAAEAA=A", "AAVAAEV=A", "AAAVAEA=V", 
    "AVVVVVE=V", "VAVVAVE=V", "AVAEAAV=A", "EAAVVVA=A", "AVAVAEV=V", "VVAAVVE=V", "EAAAVVV=A", "VVAAAVE=V", "VAAAVEV=V", "VVAEVAV=V", 
    "VAEVAVA=V", "AAEAVVA=A", "VAAAAEV=A", "VVEAVAV=A", "VVVVEAA=A", "AVEVAVV=V", "AEAAVAA=A", "VAAEAAV=A", "VAEVAAA=V", "VAAVAAE=A", 
    "EVVAAAV=V", "VVVAEVV=A", "EVVVAVA=V", "AVVVAEA=V", "AAVAVVE=A", "AVAVVEV=A", "VVEAAAV=A", "EVVAAVA=V", "EAVVAVV=A", "VAVAVEA=A", 
    "VEVVVAA=A", "AAAEVAV=A", "AVAAVVE=A", "VVEVAAA=V", "AAEVVVV=A", "EAAVVAA=A", "VAVEAAV=V", "VAAAEAV=V", "AAVEVAV=A", "AAAEVVV=A", 
    "VAVVEVV=A", "EVVAVAV=A", "EAAAAVA=V", "VVAEVVV=A", "VVVAEAV=A", "VAVVEVA=V", "AVVEAVA=A", "VAAVAVE=A", "AAVAVEV=A", "EVAVVVA=V", 
    "AVEAAAA=A", "AVAVEVA=A", "EAAAVAV=A", "VAAVVEV=A", "AVVVEAV=A", "AEAAVVV=V", "VAAVVEA=V", "VAAEAVV=A", "AAEAVAV=V", "VEVAAAA=V", 
    "VVEVVAV=A", "AAAAAVE=A", "VAAEAAA=V", "AVVAAVE=V", "AAAVEAV=V", "AEVVAVV=V", "AVAAVEV=A", "AAVAVAE=V", "EVAAAVV=A", "VAAEVAA=A", 
    "EAVAVVA=A", "AEVAVVA=A", "VEAAAVA=A", "VEVVAAV=V", "AVVVEAA=A", "VVAVAVE=V", "AEVAAVV=V", "AVVAEVV=A", "AEAVVVV=V", "AEVAAAV=V", 
    "AEAAVVA=A", "AAAAEVV=V", "VAAAEVV=V", "AVVVVAE=A", "AVAAEVV=V", "AVVVAEV=A", "VEVVVVV=V", "AAVAEAA=V", "AAAAVEV=A", "AVAVEAA=A", 
    "EVVVAAV=A", "EAVVAAA=A", "AAEVAVV=A", "AAVEAAA=V", "VAVVVEV=A", "VVAAAEA=V", "AVAAEAA=V", "AAVVEVV=A", "VEAVAVA=V", "EAAVAAV=V", 
    "VVAEVAA=A", "AEAAAAV=A", "EAVAVAA=V", "VAVAAEA=V", "EAAAVVA=V", "AVEVAAV=V", "AEAAVAV=V", "AVAVVAE=A", "EVAVVAA=V", "VAAEAVA=V", 
    "VVAVEVV=A", "AAVVEAA=A", "AVEVAVA=A", "VEAAAAA=A", "VVVAAEV=V", "VVVAVEV=V", "VAVEVVV=V", "VVVEAVA=V", "VVEAAVA=A", "AVVAEVA=V", 
    "VAAAEVA=V", "VAAVVAE=A", "VVAAAEV=A", "AAAVAEV=A", "VAAAVEA=V", "VEVAAAV=A", "EVAAVAA=A", "AVAAEVA=A", "AVEVVAA=V", "VAVAAEV=V", 
    "AVVEVAA=A", "VVAEVVA=A", "VEAVAAA=V", "EAAVAVA=A", "AAEAAVV=A", "VVAAAAE=A", "VVVAAAE=A", "VVVVAEA=A", "AVAAAVE=A", "VVVEAVV=V", 
    "AVAVEAV=A", "VVEAVVV=A", "EVVVVAV=A", "AEVVAAA=A", "AAVAAAE=A", "AEAVAVA=V", "VAEVVVA=A", "VAVVVAE=V", "AVVAEAV=V", "VVAAVEV=V", 
    "VVAVVVE=A", "EVAVAVV=A", "VVVAEAA=A", "VAVAEAA=A", "EVVVAAA=A", "AAAVVEA=A", "AEAVVAV=A", "VAVAAVE=V", "VEAAVAA=V", "VAVEAVA=A", 
    "VAAAVVE=V", "AEVVVAV=V", "VVVAVVE=A", "EAAVAVV=V", "EAVAAAA=V", "AVAAAEA=V", "AAAEAAV=A", "VEVVAVV=A", "VAVVVVE=A", "VAVEVAV=V", 
    "VVVVEAV=V", "VEVVVVA=A", "VAAEVAV=A", "AVVVAAE=A", "AAAVVVE=V", "EVAAAVA=A", "AVEAVVV=V", "AVVAVEA=A", "AAAEVVA=V", "VAEVVVV=V", 
    "AAAEAAA=A", "VAEAAAA=V", "VVEVVVV=A", "EAVAVAV=V", "AVEAAVV=A", "VVAEAAA=V", "VAVEVAA=A", "VAEVVAA=A", "VAAVEAV=A", "AAVVAEV=V", 
    "VAAVAEV=V", "VAVAVEV=V", "AVAAEAV=A", "AVAVAVE=A", "AVAAVEA=A", "AAVEVAA=A", "VEVVAVA=A", "AAAVVAE=A", "VAEAAVA=A", "AEVVVAA=A", 
    "VVAVVEV=V", "AEVAVAA=V", "VAEAVAV=V", "AVAEAVV=V", "EAVVVAA=V", "EAVAAAV=A", "EVVAAVV=V", "VEAAAVV=A", "AAAVEVV=A", "VEAVVAV=A", 
    "AEVAVAV=A", "AEVAAVA=V", "AVVVAVE=V", "AAVAAVE=A", "VVAAEVV=V", "AVAEVAA=V", "EVVVVVA=V", "VAVAVVE=A", "VAAAAVE=A", "AAAAVEA=A", 
    "VVAVAEA=A", "AVAAVAE=A", "VEAVAVV=V", "EVAAVVA=V", "AVVAVAE=A", "VVAAEVA=V", "VVAVEAA=V", "AVVEAVV=A", "VEVAVAA=V", "VVVVAVE=A", 
    "EVAVAAA=V", "EAAVVAV=V", "VAEAAVV=V", "AVVVEVV=A", "EVAAAAV=V", "VAVEVVA=A", "VAAVAEA=A", "AVVAEAA=A", "VAVAVAE=A", "VAAAEAA=V", 
    "VEAVVVA=V", "EAAAAAV=V", "VVAVEVA=A", "AAVAVEA=A", "AVEVAAA=A", "EAVVVVV=V", "AAAAVAE=V", "VEAAVVV=A", "AVVAVEV=V", "VAVVVEA=A", 
    "VAVEAAA=A", "AVAVEVV=V", "VVAAVEA=A", "AAAVAVE=A", "AAAAVVE=A", "VVAAVAE=V", "AAVAEAV=V", "AEAVAVV=A", "VVVEVVV=A", "AVAEAAA=V", 
    "EAAVVVV=A", "EAVVVAV=V", "VAVEAVV=A", "AEAAAVA=A", "AAVAEVV=A", "AVAVVEA=A", "AAEVAVA=V", "EVAVAAV=V", "VVAVAAE=V", "VVAEAVA=A", 
    "AAVEVVA=A", "AAEVVVA=V", "EVVVAVV=V", "VVVVVEA=A", "EVVVVVV=V", "VAEAVVV=V", "AAAVVEV=V", "VVVEAAV=A", "AAAVAAE=V", "VAEVAAV=V", 
    "AAVEAVA=V", "AAVVAEA=V", "VEVVVAV=V", "AAVAAEA=V", "VVAEAAV=A", "AVEAAVA=V", "AAVVAAE=A", "VAAVEVA=V", "AVAVVVE=A", "VVVVVVE=A", 
    "AEVVVVV=A", "VVVAVEA=A", "VVAVEAV=A", "VEAAVAV=A", "EVVAVVV=V", "VAAVEAA=V", "AVEAAAV=V", "EAAAAAA=V", "VEVAVAV=V", "VVEAVVA=V", 
    "EVAVAVA=A", "AVAVAEA=A", "AEAVAAA=A", "EAVAVVV=V", "VAEAAAV=V", "AVAEVVV=A", "AVVEVAV=V", "AVEAVAV=V", "VAVVEAA=A", "AEAVVVA=V", 
    "VAEAVAA=V", "VVVAAVE=V", "AVVEVVV=A", "AVVAAEV=A", "AAVVEVA=V", "AEVVAAV=A", "AVAEAVA=V", "VAVVEAV=V", "AVVEAAV=A", "EAVVAVA=A", 
    "AAAVEAA=A", "VVEAAVV=A", "VEAAVVA=V", "VVEVAVA=V", "AAVVAVE=A", "AAEVVAA=A", "AAEAAAA=V", "VAAEVVV=A", "VVEVVVA=A", "EAAAVAA=V", 
    "VAVAEAV=A", "AVEVVAV=A", "AEAAAAA=A", "AVVAVVE=A", "AAVEAAV=A", "VVAVVEA=A", "VVEVAEV=V", "AEAAEVV=A", "AAEVEVV=A"
]

PADROES = []
for item in PADROES_RAW:
    partes = item.split("=")
    if len(partes) == 2:
        seq_str, sinal_letra = partes[0], partes[1]
        seq_emojis = traduzir_sequencia(seq_str)
        sinal_emoji = traduzir_sequencia(sinal_letra)[0]
        PADROES.append({"seq": seq_emojis, "sinal": sinal_emoji})

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
             f"✅ 𝗚𝗥𝗘𝗘𝗡𝗦: {state['wins']}\n"
             f"❌ 𝗟𝗢𝗦𝗦: {state['losses']}")
    
    state["msg_placar"] = await send_msg(texto)

async def processar_resultado(cor):
    if cor == "🟡" or cor == state["target"]:
        state["wins"] += 1
        state["streak"] += 1
        state["streak_loss"] = 0 
        
        if state["gale_step"] == 0:
            tipo = "SG"
        elif state["gale_step"] == 1:
            tipo = "G1"
        else:
            tipo = "G2"
        
        if cor == "🟡":
            msg_vitoria = (f"🟠 <b>EMPATE</b>\n"
                           f"❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥 𝗣𝗔𝗚𝗢𝗢𝗢! 🔥 ({tipo})\n\n"
                           f"🚀 TOMAA! {state['streak']} GREENS SEGUIDOS 🚀")
        else:
            msg_vitoria = (f"❇️❇️❇️❇️❇️❇️❇️❇️\n"
                           f"🔥 𝗣𝗔𝗚𝗢𝗢𝗢! 🔥 ({tipo})\n\n"
                           f"🚀 TOMAA! {state['streak']} GREENS SEGUIDOS 🚀")
        
        await send_msg(msg_vitoria)
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})
        await enviar_placar()

    elif state["gale_step"] == 0:
        state["gale_step"] = 1
        state["msg_gale"] = await send_msg("⚠️ <b>VAMOS PARA O GALE 1</b>")
    
    elif state["gale_step"] == 1:
        state["gale_step"] = 2
        await delete_msg(state["msg_gale"])
        state["msg_gale"] = await send_msg("⚠️ <b>VAMOS PARA O GALE 2</b>")
    
    else:
        state["losses"] += 1
        state["streak"] = 0
        state["streak_loss"] += 1
        
        await send_msg("❌ <b>LOSS!</b>")
        await delete_msg(state["msg_analise"])
        await delete_msg(state["msg_gale"])
        state.update({"waiting": False, "gale_step": 0, "msg_analise": None, "msg_gale": None})

        if state["streak_loss"] >= 2:
            state["pause_until"] = datetime.now() + timedelta(minutes=10)
            await send_msg("🛑 <b>PAUSA DE SEGURANÇA (10 MIN)</b>\n2 Reds seguidos. Preservando a banca!")
            state["streak_loss"] = 0
            
        await enviar_placar()

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
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
    except Exception as e:
        log.error(f"Erro na requisição HTTP: {e}")
        return None
    return None

async def main():
    log.info(f"Bot iniciado com sucesso. Total de padrões carregados: {len(PADROES)}")
    await enviar_placar()
    
    while True:
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
                        
                        cor = {
                            "PlayerWon": "🔵", "Jogador": "🔵", "Player": "🔵",
                            "BankerWon": "🔴", "Bancao": "🔴", "Banker": "🔴",
                            "Tie": "🟡", "Empate": "🟡"
                        }.get(res_raw)
                        
                        if cor:
                            if cor != "🟡":
                                state["history"].append(cor)
                                state["history"] = state["history"][-25:]
                            
                            if state["waiting"]:
                                await processar_resultado(cor)
                            else:
                                found = False
                                for p in PADROES:
                                    if len(state["history"]) >= len(p["seq"]) and state["history"][-len(p["seq"]):] == p["seq"]:
                                        state["target"] = p["sinal"]
                                        state["waiting"] = True
                                        state["gale_step"] = 0
                                        
                                        # Apaga a mensagem de "Analisando..." se houver uma ativa
                                        await delete_msg(state["msg_analise"])
                                        state["msg_analise"] = None

                                        entrada = (f"🚀 <b>ENTRADA CONFIRMADA</b>\n\n"
                                                   f"Apostar: {p['sinal']}\n"
                                                   f"Proteção: 🟡 Empate\n"
                                                   f"Limite: Até 2 Gales")
                                        await send_msg(entrada)
                                        found = True
                                        break
                                
                                # Se nenhum padrão foi encontrado, envia a mensagem de analise caso ela já não exista
                                if not found and not state["msg_analise"]:
                                    state["msg_analise"] = await send_msg("🔍 <b>Analisando padrões...</b>")

        except Exception as e:
            log.error(f"Erro no loop principal: {e}")
            
        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Aplicação encerrada manualmente.")
    
