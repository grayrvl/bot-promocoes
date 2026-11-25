import json
import os
import time
import requests
from bs4 import BeautifulSoup

CANAIS = ["wolf_ofertas"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]
PALAVRAS_CHAVE = []
ARQUIVO_HISTORICO = "enviados.json"


def carregar_historico() -> set:
  if os.path.exists(ARQUIVO_HISTORICO):
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
      return set(json.load(f))
  return set()


def salvar_historico(enviados: set) -> None:
  with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
    json.dump(list(enviados)[-500:], f)


def extrair_imagem(msg) -> str | None:
  foto = msg.select_one(".tgme_widget_message_photo_wrap")
  if foto and "style" in foto.attrs:
    style = foto["style"]
    if "url('" in style:
      partes = style.split("url('")
      if len(partes) > 1:
        return partes[1].split("')")[0]
  return None


def checar_canal(canal: str, enviados: set) -> None:
  url = "https://t.me" + "/s/" + canal
  resp = requests.get(url, timeout=15)
  soup = BeautifulSoup(resp.text, "html.parser")

  mensagens = soup.select(".tgme_widget_message")

  if not enviados:
    for msg in mensagens:
      if msg.get("data-post"):
        enviados.add(msg.get("data-post"))
    salvar_historico(enviados)
    print(f"[{canal}] Histórico inicial salvo ({len(enviados)} posts ignorados).")
    return

  for msg in mensagens:
    post_id = msg.get("data-post")
    texto_el = msg.select_one(".tgme_widget_message_text")
    if not post_id or not texto_el or post_id in enviados:
      continue

    texto = texto_el.get_text("\n").strip()

    if PALAVRAS_CHAVE and not any(p.lower() in texto.lower() for p in PALAVRAS_CHAVE):
      enviados.add(post_id)
      continue

    embed = {
        "title": f"Nova oferta em @{canal}",
        "description": f"{texto[:3800]}\n\n[Abrir no Telegram](https://t.me{post_id})",
        "color": 5763719,
    }

    imagem = extrair_imagem(msg)
    if imagem:
      embed["image"] = {"url": imagem}

    r = requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=10)
    if r.status_code in (200, 204):
      enviados.add(post_id)
      print(f"Enviado: {post_id}")
    time.sleep(1)

  salvar_historico(enviados)


if __name__ == "__main__":
  enviados = carregar_historico()
  for canal in CANAIS:
    try:
      checar_canal(canal, enviados)
    except Exception as e:
      print(f"Erro ao ler {canal}: {e}")
      
