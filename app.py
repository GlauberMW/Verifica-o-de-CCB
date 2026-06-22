import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Estrito")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- MÁSCARA AVANÇADA DE DOCUMENTO (CSS INJETADO) ---
st.markdown(
    """
    <style>
    /* Garante posicionamento relativo no container da câmera */
    div[data-testid="stCameraInput"] {
        position: relative !important;
        overflow: hidden;
    }
    
    /* Máscara de fundo escurecido com um 'furo' central (clip-path) */
    div[data-testid="stCameraInput"]::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.65); /* Escurece o fundo para destacar o alvo */
        pointer-events: none;
        z-index: 98;
        /* Cria a janela transparente no centro exato (batendo com o ROI de 45% x 22%) */
        clip-path: polygon(
            0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%,
            27.5% 31%, 72.5% 31%, 72.5% 53%, 27.5% 53%, 27.5% 31%
        );
    }
    
    /* Moldura verde de enquadramento (Estilo Leitor de Cartão/CNH) */
    div[data-testid="stCameraInput"]::after {
        content: "ENCAIXE O CCB NESTA MOLDURA";
        position: absolute;
        top: 42%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 45%; 
        height: 22%; 
        border: 3px solid #00FF00; /* Verde passa ideia de guia correto */
        border-radius: 8px;
        color: #00FF00;
        font-weight: bold;
        font-size: 11px;
        letter-spacing: 1px;
        text-align: center;
        padding-top: 5px;
        pointer-events: none; 
        z-index: 99;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.warning("⚠️ **AÇÃO REQUERIDA:** Alinhe as bordas do CCB perfeitamente dentro da janela iluminada antes de capturar a foto.")

foto_capturada = st.camera_input("Posicione o CCB na área demarcada")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ÁREA DE CORTE DO ALVO (ROI) TOTALMENTE CASADA COM O CLIP-PATH ---
    largura_alvo = int(largura_img * 0.45)  
    altura_alvo = int(altura_img * 0.22)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img * 0.42) - (altura_alvo / 2)) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO DIGITAL ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
    bordas = cv2.Canny(desfoque, 30, 90) # Ajustado o limiar para ignorar pequenos ruídos de fundo
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5))
    bordas_conectadas = cv2.dilate(bordas, kernel, iterations=2)
    bordas_conectadas = cv2.erode(bordas_conectadas, kernel, iterations=1)
    
    pontos = cv2.findNonZero(bordas_conectadas)
    
    if pontos is not None:
