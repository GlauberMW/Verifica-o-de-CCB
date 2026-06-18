import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

st.error("🚨 *INSTRUÇÃO:* Aproxime ou afaste o celular até que o selo preto se encaixe perfeitamente dentro do retângulo vermelho centralizado.")

# --- PROCESSADOR DE VÍDEO CORRIGIDO PARA CELULAR ---
class MascaraVideoProcessor(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        altura_img, largura_img, _ = img.shape
        
        # Se a imagem vier rotacionada do celular (mais alta do que larga), ajustamos as guias para modo retrato
        if altura_img > largura_img:
            largura_guia = int(largura_img * 0.85)  # Ocupa 85% da largura da tela do celular
            altura_guia = int(altura_img * 0.25)   # Cria um retângulo deitado proporcional ao selo
        else:
            largura_guia = int(largura_img * 0.7)
            altura_guia = int(altura_img * 0.5)
        
        # Calcula o centro exato
        x_min = int((largura_img - largura_guia) / 2)
        y_min = int((altura_img - altura_guia) / 2)
        x_max = x_min + largura_guia
        y_max = y_min + altura_guia
        
        # Desenha o Retângulo Vermelho Fixo com linha mais grossa para fácil visualização
        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 5)
        cv2.putText(img, "ENQUADRE O SELO AQUI", (x_min + 5, y_min - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)
        
        return frame.from_ndarray(img, format="bgr24")

# Configurações universais com forçamento de tamanho para telas de smartphones
ctx = webrtc_streamer(
    key="validador-ccb-celular", 
    video_processor_factory=MascaraVideoProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:://google.com"]}]},
    media_stream_constraints={
        "video": {
            "width": {"ideal": 640},
            "height": {"ideal": 480},
            "aspectRatio": {"ideal": 1.333333}
        }, 
        "audio": False
    }
)

# --- BOTÃO DE ANÁLISE SEGURO ---
if ctx and hasattr(ctx, 'video_processor') and ctx.video_processor:
    if st.button("📊 Analisar Enquadramento Atual"):
        st.info("Processando a medição do selo baseado no enquadramento atual...")
