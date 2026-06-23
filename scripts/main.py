import sys
import time
import cv2
from ultralytics import YOLO

import config
import impressora
import telegram_bot
import armazenamento


def main() -> None:
    # Inicialização 
    print("[INFO] Carregando o modelo YOLOv11...")
    model = YOLO(config.MODEL_PATH)

    print("[INFO] Abrindo a webcam...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERRO] Não foi possível abrir a webcam.")
        sys.exit(1)

    cv2.namedWindow("Deteccao de Falha", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Deteccao de Falha", 640, 480)

    telegram_bot.iniciar_thread_telegram()
    print("[INFO] Sistema de monitoramento pelo Telegram iniciado.")
    print("Pressione 'q' na janela de imagem para encerrar manualmente.\n")

    # Estado do loop 
    impressora_pausada = False
    contador_spaghetti = 0
    contador_warping   = 0
    ultimo_tempo_salvo = time.time()

    # Loop principal 
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("[ERRO] Falha ao capturar o frame da webcam.")
            break

        frame_limpo = frame.copy()
        tempo_atual = time.time()

        falha_automatica_detectada = False
        notificacao_solicitada     = False

        # Inferência 
        results = model(frame, conf=0.10, verbose=False)

        maior_confianca_encontrada = 0.0
        classe_maior_confianca     = "spaghetti"
        maior_conf_spaghetti_frame = 0.0
        maior_conf_warping_frame   = 0.0

        # Varredura das detecções 
        for result in results:
            for box in result.boxes:
                nome_classe = model.names[int(box.cls[0])].lower()
                if nome_classe not in ("spaghetti", "warping"):
                    continue

                conf = float(box.conf[0])

                if conf > maior_confianca_encontrada:
                    maior_confianca_encontrada = conf
                    classe_maior_confianca     = nome_classe

                if nome_classe == "spaghetti" and conf > maior_conf_spaghetti_frame:
                    maior_conf_spaghetti_frame = conf
                elif nome_classe == "warping" and conf > maior_conf_warping_frame:
                    maior_conf_warping_frame = conf

        # Filtro temporal consecutivo 
        if maior_conf_spaghetti_frame >= config.LIMIAR_NOTIFICACAO_SPAGHETTI:
            contador_spaghetti += 1
        else:
            contador_spaghetti = max(0, contador_spaghetti - 1)

        if maior_conf_warping_frame >= config.LIMIAR_NOTIFICACAO_WARPING:
            contador_warping += 1
        else:
            contador_warping = max(0, contador_warping - 1)

        # Avaliação de spaghetti 
        if contador_spaghetti >= config.FRAMES_CONSECUTIVOS_VALIDACAO:
            if maior_conf_spaghetti_frame >= config.LIMIAR_PAUSA_SPAGHETTI:
                falha_automatica_detectada = True
            else:
                notificacao_solicitada = True

        # Avaliação de warping
        if contador_warping >= config.FRAMES_CONSECUTIVOS_VALIDACAO:
            if maior_conf_warping_frame >= config.LIMIAR_PAUSA_WARPING:
                falha_automatica_detectada = True
            elif not notificacao_solicitada:
                notificacao_solicitada = True

        # Log dos contadores 
        if contador_spaghetti > 0 or contador_warping > 0:
            print(
                f"[FILTRO] Contadores -> "
                f"Spaghetti: {contador_spaghetti}/{config.FRAMES_CONSECUTIVOS_VALIDACAO} | "
                f"Warping: {contador_warping}/{config.FRAMES_CONSECUTIVOS_VALIDACAO}  ",
                end="\r",
            )

        # pausa automática 
        if falha_automatica_detectada and not impressora_pausada:
            armazenamento.salvar_frame_limpo(frame_limpo, maior_confianca_encontrada,
                                             classe_maior_confianca)
            frame_anotado = results[0].plot()
            caminho_foto  = armazenamento.salvar_frame_anotado(frame_anotado,
                                                                maior_confianca_encontrada,
                                                                classe_maior_confianca)
            porcentagem = int(maior_confianca_encontrada * 100)
            msg = (
                f"*[ATENÇÃO]*\n\n"
                f"{classe_maior_confianca.upper()} detectado com *{porcentagem}%* de confiança!\n"
                f"A impressão foi interrompida automaticamente."
            )
            telegram_bot.enviar_alerta_com_foto(caminho_foto, msg, incluir_botao_resume=True)
            impressora.pausar()
            impressora_pausada = True

        # notificação de suspeita 
        elif (notificacao_solicitada
              and not impressora_pausada
              and (tempo_atual - ultimo_tempo_salvo >= 10.0)):

            armazenamento.salvar_frame_limpo(frame_limpo, maior_confianca_encontrada,
                                             classe_maior_confianca)
            frame_anotado = results[0].plot()
            caminho_foto  = armazenamento.salvar_frame_anotado(frame_anotado,
                                                                maior_confianca_encontrada,
                                                                classe_maior_confianca)
            porcentagem = int(maior_confianca_encontrada * 100)
            msg = (
                f"*[ALERTA DE SUSPEITA]*\n\n"
                f"{classe_maior_confianca.upper()} detectado com *{porcentagem}%* de confiança.\n"
                f"Deseja interromper a impressão?"
            )
            telegram_bot.enviar_alerta_com_foto(caminho_foto, msg, incluir_botao_pausa=True)
            ultimo_tempo_salvo = tempo_atual

        # pausa manual via Telegram 
        if telegram_bot.pausa_manual_event.is_set() and not impressora_pausada:
            impressora.pausar()
            impressora_pausada = True
            telegram_bot.pausa_manual_event.clear()

        # retomada via Telegram 
        if impressora_pausada and not telegram_bot.pausa_manual_event.is_set():
            impressora_pausada = False

        # Exibição 
        cv2.imshow("Deteccao de Falha", results[0].plot())

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Monitoramento encerrado pelo utilizador.")
            break

    # Encerramento 
    telegram_bot.script_ativo_event.clear()
    cap.release()
    cv2.destroyAllWindows()
    print("--- SISTEMA DESCONECTADO ---")


if __name__ == "__main__":
    main()
