import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador Mobile")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- CSS CORRIGIDO PARA ADAPTAR À PROPORÇÃO DA CÂMERA DO CELULAR ---
st.markdown(
    """
    <style>
    /* Alinha o container de vídeo */
    div[data-testid="stCameraInput"] {
        position: relative !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* Força o elemento de vídeo/preview interno a se comportar como o container */
    div[data-testid="stCameraInput"] video {
        position: relative !important;
        z-index: 1;
    }

    /* Nova máscara estrita: se adapta ao tamanho real do vídeo renderizado */
    div[data-testid="stCameraInput"]::after {
        content: "ENCAIXE O SELO CCB AQUI";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        /* Proporções ajustadas para cobrir a área central real do sensor da câmera */
        width: 70%; 
        height: 35%; 
        border: 4px solid #00FF00;
        border-radius: 12px;
        color: #00FF00;
        font-weight: bold;
        font-size: 12px;
        text-align: center;
        padding-top: 10px;
        pointer-events: none; 
        z-index: 99;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.6), inset 0 0 20px rgba(0, 255, 0, 0.3);
        background-color: rgba(0, 0, 0, 0.15); /* Leve contraste no centro para ajudar a focar */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.info("💡 **DICA:** Centralize o selo 'Conformidade CCB' preenchendo o retângulo verde antes de bater a foto.")

foto_capturada = st.camera_input("Posicione o CCB")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ÁREA DE CORTE (ROI) RECALCULADA PARA CASAR COM O DESENHO DA TELA ---
    # Como definimos 70% de largura e 35% de altura centralizados:
    largura_alvo = int(largura_img * 0.70)  
    altura_alvo = int(altura_img * 0.35)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img - altura_alvo) / 2) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO DE IMAGEM ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
    
    # Ajuste fino nos thresholds para destacar o retângulo preto do selo
    bordas = cv2.Canny(desfoque, 40, 120) 
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bordas_conectadas = cv2.dilate(bordas, kernel, iterations=2)
    bordas_conectadas = cv2.erode(bordas_conectadas, kernel, iterations=1)
    
    pontos = cv2.findNonZero(bordas_conectadas)
    
    if pontos is not None:
        x, y, w, h = cv2.boundingRect(pontos)
        
        # Como o operador agora aproxima mais a câmera e o enquadramento está maior,
        # eliminamos os multiplicadores exagerados para não medir fora do objeto.
        w = min(w, largura_alvo - x)
        h = min(h, altura_alvo - y)
        
        # Mantendo o fator baseado na nova distância que a caixa maior exige
        proporcao_pixel_cm = 0.0296  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Coordenadas absolutas
        abs_x1, abs_y1 = x_inicio + x, y_inicio + y
        abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
        
        # Desenha a linha verde ao redor do que foi medido de fato
        cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 4)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Desenha em azul os limites do corte (apenas para verificação visual do operador)
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Análise Realizada")
        
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O selo CCB está em conformidade com o padrão!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append("Comprimento abaixo de 50mm")
            if not aprovado_altura:
                erros.append("Altura abaixo de 22mm")
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        # Desenha a caixa limite azul caso falhe
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha na Detecção")
        st.warning("⚠️ Não foi possível isolar o selo. Garanta que ele esteja centralizado dentro do retângulo verde.")
