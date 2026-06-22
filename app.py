import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- TRUQUE CSS PARA CASAR EXATAMENTE COM A FOTO REAL ---
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
        width: 45%; 
        height: 22%; 
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

st.error("🚨 INSTRUÇÃO OBRIGATÓRIA: Aproxime ou afaste a câmera até que o selo preto da caixa preencha o retângulo vermelho na tela antes de clicar em bater foto.")

foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ÁREA DE CORTE DO ALVO (ROI) ---
    largura_alvo = int(largura_img * 0.45)  
    altura_alvo = int(altura_img * 0.22)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img * 0.42) - (altura_alvo / 2)) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO DIGITAL DE IMAGENS ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
    bordas = cv2.Canny(desfoque, 20, 60)
    
    # Um kernel levemente mais equilibrado (11x5) ajuda a não perder a altura em ambientes com sombra
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 5))
    bordas_conectadas = cv2.dilate(bordas, kernel, iterations=2)
    bordas_conectadas = cv2.erode(bordas_conectadas, kernel, iterations=1)
    
    pontos = cv2.findNonZero(bordas_conectadas)
    
    if pontos is not None:
        x, y, w, h = cv2.boundingRect(pontos)
        
        # Aplicando a margem com travas de segurança para não estourar o tamanho da imagem recortada
        w = min(int(w * 1.05), largura_alvo - x)
        h = min(int(h * 1.15), altura_alvo - y)
        
        # Fator de calibração fornecido por você
        proporcao_pixel_cm = 0.0296  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Coordenadas absolutas para desenhar na imagem original (evita bugs visuais)
        abs_x1, abs_y1 = x_inicio + x, y_inicio + y
        abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
        
        # Desenha a detecção final (Verde)
        cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 3)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Desenha a área limite do escaneamento (Vermelha)
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Análise por Varredura de Pontos Extremos")
        
        # Validação dos limites
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O CCB está dentro do padrão mínimo!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append(f"Comprimento abaixo de 50mm (Medido: {largura_medida*10:.1f}mm)")
            if not aprovado_altura:
                erros.append(f"Altura abaixo de 22mm (Medido: {altura_medida*10:.1f}mm)")
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha de Leitura")
        st.warning("⚠️ Não foram encontrados elementos gráficos suficientes dentro do retângulo destacado. Verifique a iluminação.")
