import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

# --- TRUQUE CSS DE VISUALIZAÇÃO ---
st.markdown(
    """
    <style>
    div[data-testid="stCameraInput"] {
        position: relative !important;
    }
    div[data-testid="stCameraInput"]::after {
        content: "ALINHE O SELO AQUI";
        position: absolute;
        top: 42%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 38%;
        height: 18%;
        border: 4px solid #FF0000;
        border-radius: 4px;
        color: #FF0000;
        font-weight: bold;
        font-size: 10px;
        text-align: center;
        padding-top: 3px;
        pointer-events: none; 
        z-index: 99;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.error("🚨 *INSTRUÇÃO OBRIGATÓRIA:* Aproxime ou afaste a câmera até que o selo preto da caixa preencha o retângulo vermelho na tela antes de clicar em bater foto.")

# Captura da foto usando o componente nativo em tela cheia do Streamlit
foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- AJUSTE MATEMÁTICO DO ALVO (ROI) ---
    largura_alvo = int(largura_img * 0.45)  
    altura_alvo = int(altura_img * 0.22)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    # Mudado para 0.42 para alinhar milimetricamente com a posição do retângulo do CSS da tela
    y_inicio = int((altura_img * 0.42) - (altura_alvo / 2)) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- NOVO PROCESSAMENTO DE ALTO CONTRASTE CONTRA PAPELÃO ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (3, 3), 0)
    
    # Threshold Adaptativo de Otsu (Perfeito para detectar linhas pretas finas em fundo pardo)
    _, threshold = cv2.threshold(desfoque, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # RETR_TREE mapeia a hierarquia para priorizar a borda mais externa do selo
    contornos, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        # Filtro de tamanho para ignorar ruídos textuais pequenos
        contornos_filtrados = [c for c in contornos if cv2.contourArea(c) > 400]
        
        if contornos_filtrados:
            # Seleciona o maior contorno (que agora com RETR_TREE será a borda de fora)
            maior_contorno = max(contornos_filtrados, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(maior_contorno)
            
            # --- NOVO FATOR DE CALIBRAÇÃO PROPORCIONAL ---
            # Como expandimos a janela, recalibramos para manter a precisão dos 5.0 cm
            proporcao_pixel_cm = 0.0165  
            
            largura_medida = round(w * proporcao_pixel_cm, 2)
            altura_medida = round(h * proporcao_pixel_cm, 2)
            
            # Desenha a detecção verde do selo
            cv2.rectangle(imagem_cv, (x_inicio + x, y_inicio + y), (x_inicio + x + w, y_inicio + y + h), (0, 255, 0), 3)
            cv2.putText(imagem_cv, f"{w}px | {largura_medida}cm x {altura_medida}cm", (x_inicio + x, y_inicio + y - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (36, 255, 12), 2)
            
            # Desenha a área vermelha de escaneamento corrigida na tela
            cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
            
            st.image(imagem_cv, channels="BGR", caption="Área Analisada Corrigida")
            
            # Validação estrita de limites mínimos
            aprovado_comprimento = largura_medida >= 5.0
            aprovado_altura = altura_medida >= 2.2
            
            st.subheader("📊 Resultado da Análise")
            st.write(f"*Comprimento Medido:* {largura_medida} cm ({largura_medida * 10:.1f} mm)")
            st.write(f"*Altura Medida:* {altura_medida} cm ({altura_medida * 10:.1f} mm)")
            
            if aprovado_comprimento and aprovado_altura:
                st.success("✅ APROVADO: O CCB está dentro do padrão mínimo!")
            else:
                erros = []
                if not aprovado_comprimento:
                    erros.append("Comprimento abaixo de 50mm")
                if not aprovado_altura:
                    erros.append("Altura abaixo de 22mm")
                st.error(f"❌ REPROVADO: {', '.join(erros)}.")
        else:
            st.warning("⚠️ Borda externa do selo não detectada. Centralize e tente novamente.")
    else:
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha de Leitura")
        st.warning("⚠️ Não foi possível identificar as bordas do objeto dentro da área delimitada.")
