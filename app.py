import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital Ao Vivo")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

st.error("🚨 *INSTRUÇÃO OBRIGATÓRIA:* Aproxime ou afaste a câmera até que o selo preto da caixa preencha o retângulo vermelho que aparecerá no vídeo abaixo.")

# --- PROCESSADOR DE VÍDEO EM TEMPO REAL ---
class MascaraVideoTransformer(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        altura_img, largura_img, _ = img.shape
        
        # Alvo digital fixo ocupando a área central do vídeo
        largura_guia = int(largura_img * 0.7)
        altura_guia = int(altura_img * 0.5)
        
        x_min = int((largura_img - largura_guia) / 2)
        y_min = int((altura_img - altura_guia) / 2)
        x_max = x_min + largura_guia
        y_max = y_min + altura_guia
        
        # Injeta o retângulo vermelho e o texto de instrução vivo na tela
        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 3)
        cv2.putText(img, "ENQUADRE O SELO AQUI", (x_min + 10, y_min - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return img

# Inicializa a nova câmera em tempo real na tela do celular
ctx = webrtc_streamer(
    key="validador-ccb", 
    video_transformer_factory=MascaraVideoTransformer,
    rtc_configuration={"iceServers": [{"urls": ["stun:://google.com"]}]},
    media_stream_constraints={"video": True, "audio": False}
)

# --- BOTÃO DE ANÁLISE ---
if ctx.video_transformer:
    if st.button("📊 Analisar Enquadramento Atual"):
        st.info("Processando a imagem enquadrada...")
        # A lógica de processamento e resposta de aprovação do OpenCV será executada a partir deste bloco.
