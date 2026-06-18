import streamlit as st
import cv2
import numpy as np

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

# --- INSTRUÇÃO DE ENQUADRAMENTO ---
st.warning("⚠️ *INSTRUÇÃO:* Aproxime ou afaste a câmera até que o selo da caixa preencha o centro da tela, respeitando as margens do retângulo vermelho.")

# Captura da foto pelo Streamlit
foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    # Pegar as dimensões da imagem capturada para desenhar o guia proporcional
    altura_img, largura_img, _ = imagem_cv.shape
    
    # Definir coordenadas da máscara digital fixa no centro da tela
    # Modifique esses percentuais (0.7 e 0.5) se quiser ajustar o tamanho da caixa guia na tela
    largura_guia = int(largura_img * 0.7)  # Ocupa 70% da largura da tela
    altura_guia = int(altura_img * 0.5)   # Ocupa 50% da altura da tela
    
    x_min = int((largura_img - largura_guia) / 2)
    y_min = int((altura_img - altura_guia) / 2)
    x_max = x_min + largura_guia
    y_max = y_min + altura_guia

    # Processamento de imagem para detectar o selo
    cinza = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (7, 7), 0)
    bordas = cv2.Canny(desfoque, 50, 100)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        maior_contorno = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior_contorno)
        
        # --- FATOR DE CALIBRAÇÃO ---
        # Como o operador enquadra o selo no retângulo guia, a distância fica padronizada.
        # Ajuste esse valor decimal caso a medição em cm precise de calibração fina.
        proporcao_pixel_cm = 0.057  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenha o retângulo verde do selo detectado
        cv2.rectangle(imagem_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"Medido: {largura_medida}cm x {altura_medida}cm", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 255, 12), 2)
        
        # Desenha a Máscara Digital na foto (Retângulo Vermelho de Referência)
        cv2.rectangle(imagem_cv, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)
        cv2.putText(imagem_cv, "Alvo de Enquadramento", (x_min + 5, y_min + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        st.image(imagem_cv, channels="BGR", caption="Superfície Analisada com Máscara de Enquadramento")
        
        # --- VALIDAÇÃO EXCLUSIVA DE LIMITE MÍNIMO ---
        # Comprimento deve ser a partir de 5.0 cm (50mm)
        # Altura deve ser a partir de 2.2 cm (22mm)
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"*Comprimento Medido:* {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"*Altura Medida:* {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O CCB está dentro do padrão (A partir de 50mm x 22mm)!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append("Comprimento abaixo de 50mm")
            if not aprovado_altura:
                erros.append("Altura abaixo de 22mm")
            
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        # Desenha o retângulo guia mesmo se falhar na detecção inicial das bordas
        cv2.rectangle(imagem_cv, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)
        st.image(imagem_cv, channels="BGR", caption="Área de Enquadramento")
        st.warning("⚠️ Não foi possível identificar as bordas do objeto claramente. Centralize o selo no retângulo vermelho.")
