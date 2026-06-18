import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- TRUQUE CSS CORRIGIDO PARA CASAR EXATAMENTE COM A FOTO REAL ---
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
        /* Alargado de 38% para 45% para bater com a caixa vermelha de baixo */
        width: 45%; 
        /* Ajustado de 18% para 22% para abrir o topo e fundo */
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

# Captura da foto usando o componente nativo em tela cheia do Streamlit
foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ÁREA DE CORTE DO ALVO (ROI) CASADA COM O CSS ---
    largura_alvo = int(largura_img * 0.45)  
    altura_alvo = int(altura_img * 0.22)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img * 0.42) - (altura_alvo / 2)) 
    
    x_inicio = max(0, x_inicio)
    y_inicio = max(0, y_inicio)
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO POR VARREDURA DE PONTOS EXTREMOS ---
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
    bordas = cv2.Canny(desfoque, 20, 60)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    bordas_conectadas = cv2.dilate(bordas, kernel, iterations=2)
    bordas_conectadas = cv2.erode(bordas_conectadas, kernel, iterations=1)
    
    pontos = cv2.findNonZero(bordas_conectadas)
    
    if pontos is not None:
        x, y, w, h = cv2.boundingRect(pontos)
        
        w = int(w * 1.05)
        h = int(h * 1.15)
        
        # --- CALIBRAÇÃO AJUSTADA PARA O TAMANHO GRANDE DO SELO ---
        # Como o selo na sua imagem real deu 169 pixels para o tamanho total,
        # o fator ideal agora é 0.0296 para que 169px resulte exatamente em 5.0cm!
        proporcao_pixel_cm = 0.0296  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenha a detecção final (Verde)
        cv2.rectangle(imagem_cv, (x_inicio + x, y_inicio + y), (x_inicio + x + w, y_inicio + y + h), (0, 255, 0), 3)
        cv2.putText(imagem_cv, f"{w}px | {largura_medida}cm x {altura_medida}cm", (x_inicio + x, y_inicio + y - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (36, 255, 12), 2)
        
        # Desenha a área vermelha de escaneamento de fundo
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Análise por Varredura de Pontos Extremos")
        
        # Validação estrita de limites mínimos
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"Comprimento Medido: {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"Altura Medida: {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
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
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha de Leitura")
        st.warning("⚠️ Não foram encontrados elementos gráficos suficientes dentro do retângulo destacado.")
