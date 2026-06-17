import streamlit as st
import cv2
import numpy as np

st.title("Verificador de Superfície - CCB")

# 1. Definição do Padrão Aceitável (em centímetros)
PADRAO_LARGURA = 20.0
PADRAO_ALTURA = 10.0
TOLERANCIA = 0.5  # Margem de erro aceitável

st.sidebar.header("Configurações do Padrão")
largura_ref = st.sidebar.number_input("Largura Padrão (cm)", value=PADRAO_LARGURA)
altura_ref = st.sidebar.number_input("Altura Padrão (cm)", value=PADRAO_ALTURA)

# 2. Captura da imagem via Câmera do Streamlit
foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    # Converter a imagem recebida para o formato que o OpenCV entende
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    # --- PROCESSO DE MEDIÇÃO ---
    cinza = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (7, 7), 0)
    
    # Detecção de bordas
    bordas = cv2.Canny(desfoque, 50, 100)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        # Pega o maior contorno encontrado
        maior_contorno = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior_contorno)
        
        # FATOR DE CONVERSÃO (Calibração de Pixels para Centímetros)
        proporcao_pixel_cm = 0.05
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenhar o retângulo delimitador na imagem
        cv2.rectangle(imagem_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 255, 12), 2)
        
        # Exibir imagem processada no Streamlit
        st.image(imagem_cv, channels="BGR", caption="Superfície Detectada")
        
        # 3. Validação do Padrão
        dentro_largura = abs(largura_medida - largura_ref) <= TOLERANCIA
        dentro_altura = abs(altura_medida - altura_ref) <= TOLERANCIA
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"*Largura Medida:* {largura_medida} cm (Esperado: {largura_ref} cm)")
        st.write(f"*Altura Medida:* {altura_medida} cm (Esperado: {altura_ref} cm)")
        
        if dentro_largura and dentro_altura:
            st.success("✅ APROVADO: A superfície está dentro dos padrões normativos!")
        else:
            st.error("❌ REPROVADO: Dimensões fora do padrão estipulado.")
    else:
        st.warning("⚠️ Não foi possível identificar as bordas do objeto claramente. Verifique a iluminação.")