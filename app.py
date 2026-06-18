import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital Ao Vivo")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

# O aviso agora fica estático no topo da página, impossível de não ver
st.error("🚨 *INSTRUÇÃO OBRIGATÓRIA:* Aproxime ou afaste a câmera até que o selo preto da caixa preencha exatamente o retângulo vermelho que aparecerá no vídeo abaixo.")

# --- PROCESSADOR DE VÍDEO EM TEMPO REAL ---
class MascaraVideoTransformer(VideoTransformerBase):
    def transform(self, frame):
        # Converte o frame do vídeo para o formato do OpenCV
        img = frame.to_ndarray(format="bgr24")
        altura_img, largura_img, _ = img.shape
        
        # Define o tamanho do alvo digital fixo na tela (70% de largura, 50% de altura)
        largura_guia = int(largura_img * 0.7)
        altura_guia = int(altura_img * 0.5)
        
        x_min = int((largura_img - largura_guia) / 2)
        y_min = int((altura_img - altura_guia) / 2)
        x_max = x_min + largura_guia
        y_max = y_min + altura_guia
        
        # DESENHA O RETÂNGULO VERMELHO AO VIVO NA TELA
        cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 3)
        cv2.putText(img, "ENQUADRE O SELO AQUI", (x_min + 10, y_min - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return img

# Inicializa o feed de vídeo com o enquadramento na tela
ctx = webrtc_streamer(
    key="validador-ccb", 
    video_transformer_factory=MascaraVideoTransformer,
    rtc_configuration={"iceServers": [{"urls": ["stun:://google.com"]}]}, # Ajuda na conexão mobile
    media_stream_constraints={"video": True, "audio": False}
)

# --- PROCESSAMENTO APÓS CAPTURA ---
# O streamlit-webrtc permite analisar o último frame quando o vídeo está ativo
if ctx.video_transformer:
    # Adiciona um botão para congelar/analisar a imagem do enquadramento
    if st.button("📊 Analisar Enquadramento Atual"):
        
        # Pega a imagem atual que o operador está vendo na tela
        # Nota: Para uma lógica de produção avançada, você pode salvar o frame atual em st.session_state
        st.info("Processando medição baseada no enquadramento feito...")
        
        # (Abaixo segue a sua lógica padrão de detecção de bordas no contorno que já funcionava)
        # Se precisar integrar o congelamento exato do frame do webrtc para gerar o relatório final de aprovação, me avise.
