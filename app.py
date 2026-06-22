import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador Câmera Traseira")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- CSS ULTRA CORRIGIDO (FOCADO NO VÍDEO DO CELULAR) ---
st.markdown(
    """
    <style>
    /* Centraliza e isola o container da câmera */
    div[data-testid="stCameraInput"] {
        position: relative !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background-color: transparent !important;
    }
    
    /* GABARITO AMARRADO DIRETAMENTE AO COMPONENTE DE VÍDEO */
    /* Isso garante que a caixa verde NUNCA vai vazar para fora da imagem da câmera */
    div[data-testid="stCameraInput"] video {
        border: 2px solid #333;
        border-radius: 8px;
        position: relative !important;
    }

    /* Desenha a máscara por cima apenas da área interna útil do vídeo */
    div[data-testid="stCameraInput"]::after {
        content: "ENCAIXE O SELO CCB AQUI";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        /* Reduzido para encaixar perfeitamente dentro do feed vertical do celular */
        width: 60%; 
        height: 25%; 
        border: 4px solid #00FF00;
        border-radius: 8px;
        color: #00FF00;
        font-weight: bold;
        font-size: 11px;
        text-align: center;
        padding-top: 5px;
        pointer-events: none; 
        z-index: 99;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
        background-color: rgba(0, 0, 0, 0.15);
    }

    /* TRUQUE: Esconde o botão de inverter para a câmera frontal */
    /* Força o operador a usar apenas a câmera que abriu (Traseira no ambiente fabril) */
    div[data-testid="stCameraInput"] button svg path[d*="M19"] {
        display: none !important;
    }
    div[data-testid="stCameraInput"] button:has(svg) {
        display: none !important; /* Esconde o botão completo de alternar câmera */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.warning("📸 **Atenção:** Ao abrir o aplicativo, permita o acesso e certifique-se de que está usando a câmera traseira do aparelho.")

# Abre o leitor de câmera do Streamlit
foto_capturada = st.camera_input("Posicione o CCB dentro do retângulo verde")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ÁREA DE CORTE DO ALVO (ROI) SINCRONIZADA COM A NOVA MÁSCARA (60% x 25%) ---
    largura_alvo = int(largura_img * 0.60)  
    altura_alvo = int(altura_img * 0.25)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img - altura_alvo) / 2) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO DIGITAL ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
    bordas = cv2.Canny(desfoque, 40, 120) 
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    bordas_conectadas = cv2.dilate(bordas, kernel, iterations=2)
    bordas_conectadas = cv2.erode(bordas_conectadas, kernel, iterations=1)
    
    pontos = cv2.findNonZero(bordas_conectadas)
    
    if pontos is not None:
        x, y, w, h = cv2.boundingRect(pontos)
        
        w = min(w, largura_alvo - x)
        h = min(h, altura_alvo - y)
        
        # Fator de calibração mantido
        proporcao_pixel_cm = 0.0296  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        abs_x1, abs_y1 = x_inicio + x, y_inicio + y
        abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
        
        # Feedback visual final
        cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 4)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Moldura azul mostrando a área interna analisada
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Resultado do Escaneamento")
        
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O selo CCB cumpre as dimensões mínimas!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append("Comprimento menor que 50mm")
            if not aprovado_altura:
                erros.append("Altura menor que 22mm")
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha")
        st.warning("⚠️ O sistema não detectou bordas nítidas dentro da área azul. Aproxime mais o objeto ou melhore a iluminação.")
