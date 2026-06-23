import json
import time
import threading
import urllib.request

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
import impressora

# Eventos para comunicação com o loop principal
pausa_manual_event = threading.Event()
script_ativo_event = threading.Event()
script_ativo_event.set()


# ENVIO DE ALERTAS
def enviar_alerta_com_foto(caminho_imagem: str, texto_mensagem: str,
                            incluir_botao_pausa: bool = False,
                            incluir_botao_resume: bool = False) -> bool:
    """Envia uma foto com legenda e botão opcional ao chat do Telegram."""
    url      = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    headers  = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    reply_markup = ""
    if incluir_botao_pausa:
        botao        = {"inline_keyboard": [[{"text": "Pausar Impressão Agora",
                                              "callback_data": "executar_pausa_manual"}]]}
        reply_markup = json.dumps(botao)
    elif incluir_botao_resume:
        botao        = {"inline_keyboard": [[{"text": "Retomar Impressão",
                                              "callback_data": "executar_resume_manual"}]]}
        reply_markup = json.dumps(botao)

    try:
        with open(caminho_imagem, "rb") as f:
            img_bytes = f.read()

        partes = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{TELEGRAM_CHAT_ID}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{texto_mensagem}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nMarkdown\r\n".encode(),
        ]

        if reply_markup:
            partes.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"reply_markup\"\r\n\r\n{reply_markup}\r\n".encode()
            )

        partes.extend([
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"detection.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode(),
            img_bytes,
            f"\r\n--{boundary}--\r\n".encode(),
        ])

        payload = b"".join(partes)
        req     = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req):
            print("[TELEGRAM] Alerta enviado com sucesso!")
            return True

    except Exception as e:
        print(f"[TELEGRAM][ERRO] Falha ao enviar alerta: {e}")
        return False


def _responder_callback(callback_id: str, texto: str) -> None:
    """Responde ao callback do Telegram para remover o indicador de carregamento."""
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
    payload = json.dumps({"callback_query_id": callback_id, "text": texto}).encode()
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass


def _limpar_updates(update_id: int) -> None:
    """Descarta updates já processados para evitar repetições."""
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    payload = json.dumps({"offset": update_id + 1}).encode()
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass


# THREAD DE ESCUTA
def iniciar_thread_telegram() -> threading.Thread:
    """Cria e inicia a thread que escuta callbacks do Telegram."""
    thread = threading.Thread(target=_loop_escuta, daemon=True)
    thread.start()
    return thread


def _loop_escuta() -> None:
    """Loop que verifica continuamente os updates do Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

    try:
        req = urllib.request.Request(url + "?offset=-1", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception:
        pass

    while script_ativo_event.is_set():
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=4) as response:
                dados = json.loads(response.read().decode("utf-8"))

            if dados.get("ok") and dados.get("result"):
                for update in dados["result"]:
                    if "callback_query" not in update:
                        continue

                    callback_data = update["callback_query"]["data"]
                    callback_id   = update["callback_query"]["id"]
                    update_id     = update["update_id"]

                    if callback_data == "executar_pausa_manual":
                        print("\n[TELEGRAM] Comando de PAUSA MANUAL recebido!")
                        _responder_callback(callback_id, "Enviando comando de Pausa...")
                        pausa_manual_event.set()
                        _limpar_updates(update_id)

                    elif callback_data == "executar_resume_manual":
                        print("\n[TELEGRAM] Comando de RETOMAR recebido!")
                        _responder_callback(callback_id, "Retomando impressão...")
                        if impressora.resumir():
                            pausa_manual_event.clear()
                        _limpar_updates(update_id)

        except Exception:
            pass

        time.sleep(0.8)
