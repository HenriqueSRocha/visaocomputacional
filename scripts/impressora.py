import urllib.request

from config import IP_IMPRESSORA, PORTA_MOONRAKER


def _chamar_endpoint(acao: str, timeout: int) -> bool:
    """Faz uma requisição POST para um endpoint do Moonraker."""
    url = f"http://{IP_IMPRESSORA}:{PORTA_MOONRAKER}/printer/print/{acao}"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception as e:
        print(f"[IMPRESSORA][ERRO] Falha ao chamar '{acao}': {e}")
        return False


def pausar() -> bool:
    """Pausa a impressão via Moonraker."""
    print("\n********** Falha detectada! **********")
    print("********** Pausando a Impressão  **********")
    sucesso = _chamar_endpoint("pause", timeout=10)
    if sucesso:
        print("[IMPRESSORA][SUCESSO] Impressão pausada!")
    return sucesso


def resumir() -> bool:
    """Retoma a impressão via Moonraker."""
    print("\n[IMPRESSORA] Enviando comando para RETOMAR a impressão...")
    sucesso = _chamar_endpoint("resume", timeout=30)
    if sucesso:
        print("[IMPRESSORA][SUCESSO] Impressão retomada!")
    return sucesso
