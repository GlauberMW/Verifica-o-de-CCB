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

st.error("🚨 *INSTRUÇÃO:* Dê permissão à câmera e aproxime ou afaste o celular até que o selo se encaixe no retângulo vermelho.")

# --- PROCESSADOR DE VÍDEO ATUALIZADO (Mais estável para mobile) ---
class MascaraVideoProcessor(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        altura_img, largura_img, _ = img.shape
        
        # Alvo digital fixo ocupando o centro da tela
        largura_guia = int(largura_img * 0.7)
        altura_guia = int(altura_img * 0.5)
        
        x_min = int((largura_img - largura_guia) / 2)
        y_min = int((altura_img - altura_guia) / 2)
        x_max = x_min + largura_guia
        y_max = y_min + altura_guia
        
        # Desenha o Retângulo Vermelho Fixo
        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 4)
        cv2.putText(img, "ENQUADRE O SELO AQUI", (x_min + 10, y_min - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return frame.from_ndarray(img, format="bgr24")

# Inicializa o componente com parâmetros simplificados para evitar o Bad Configuration no celular
ctx = webrtc_streamer(
    key="validador-ccb-vivo", 
    video_processor_factory=MascaraVideoProcessor,
    rtc_configuration={"iceServers": [{"urls": ["stun:://google.com"]}]},
    media_stream_constraints={"video": True, "audio": False} # Configuração universal padrão
)

# --- BOTÃO DE ANÁLISE SEGURO ---
# Evita o erro AttributeError checando se o objeto realmente existe na memória
if ctx and hasattr(ctx, 'video_processor') and ctx.video_processor:
    if st.button("📊 Analisar Enquadramento Atual"):
        st.info("Processando a medição do selo baseado no enquadramento atual...")
