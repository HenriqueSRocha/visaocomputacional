import os
import cv2

from config import DATASET, CONFIANCA


def criar_pasta_se_nao_existir(caminho: str) -> None:
    os.makedirs(caminho, exist_ok=True)


def _salvar_imagem_em_pasta(base_dir: str, frame, confianca_decimal: float,
                             nome_classe: str, prefixo: str = "") -> str:
    porcentagem  = int(confianca_decimal * 100)
    dezena_pasta = (porcentagem // 10) * 10

    nome_pasta    = f"{nome_classe.lower()}{dezena_pasta}"
    caminho_pasta = os.path.join(base_dir, nome_pasta)
    criar_pasta_se_nao_existir(caminho_pasta)

    total        = len(os.listdir(caminho_pasta))
    nome_arquivo = f"{prefixo}{nome_classe.lower()}_conf_{porcentagem}_{total + 1}.jpg"
    caminho_img  = os.path.join(caminho_pasta, nome_arquivo)

    cv2.imwrite(caminho_img, frame)
    print(f"[HISTÓRICO] Imagem arquivada em: {nome_pasta}/{nome_arquivo}")
    return caminho_img


def salvar_frame_anotado(frame_anotado, confianca_decimal: float,
                          nome_classe: str) -> str:
    """Salva frame com anotações YOLO na pasta CONFIANCA."""
    return _salvar_imagem_em_pasta(CONFIANCA, frame_anotado, confianca_decimal, nome_classe)


def salvar_frame_limpo(frame_bruto, confianca_decimal: float,
                        nome_classe: str) -> str:
    """Salva frame sem anotações na pasta DATASET."""
    return _salvar_imagem_em_pasta(DATASET, frame_bruto, confianca_decimal,
                                   nome_classe, prefixo="limpo_")
