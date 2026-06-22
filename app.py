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
        x, y, w, h = cv2.boundingRect(pontos)
        
        # Travas para não estourar a matriz da imagem
        w = min(int(w * 1.02), largura_alvo - x) # Reduzi a folga para 2% já que o operador está guiado
        h = min(int(h * 1.02), altura_alvo - y)
        
        # Proporção calibrada (Alinhada à distância da nova máscara)
        proporcao_pixel_cm = 0.0296  
        
        largura_medida = round(w * proportion_pixel_cm if 'proportion_pixel_cm' in locals() else w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Coordenadas de desenho
        abs_x1, abs_y1 = x_inicio + x, y_inicio + y
        abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
        
        # Resultado visual
        cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 3)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Resultado da Captura com Máscara")
        
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O CCB está em conformidade!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append(f"Comprimento abaixo do padrão (Medido: {largura_medida*10:.1f}mm)")
            if not aprovado_altura:
                erros.append(f"Altura abaixo do padrão (Medido: {altura_medida*10:.1f}mm)")
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        st.image(imagem_cv, channels="BGR", caption="Falha de Leitura")
        st.error("❌ Erro de leitura: Certifique-se de que o CCB preenche a área iluminada e que o ambiente está bem iluminado.")
