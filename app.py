import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- TRUQUE CSS PERFEITO PARA TELA ESTREITA ---
st.markdown(
    """
    <style>
    /* Força o container da câmera a aceitar elementos posicionados */
    div[data-testid="stCameraInput"] {
        position: relative !important;
    }
    
    /* Cria o retângulo vermelho fixo perfeitamente dentro da área clara da câmera */
    div[data-testid="stCameraInput"]::after {
        content: "ALINHE O SELO AQUI";
        position: absolute;
        top: 42%;            /* Centralizado verticalmente na área da câmera */
        left: 50%;
        transform: translate(-50%, -50%);
        width: 38%;          /* Reduzido de 48% para 38% para sumir com as bordas pretas */
        height: 18%;         /* Ajustado para 18% para manter a proporção retangular do selo */
        border: 4px solid #FF0000; /* Linha vermelha bem visível */
        border-radius: 4px;
        color: #FF0000;
        font-weight: bold;
        font-size: 10px;     /* Fonte ligeiramente menor para não quebrar linha */
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
    
    # Pegar as dimensões reais da imagem capturada
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- RECORTAR APENAS A ÁREA DESTACADA (ROI) ---
    # Mapeando matematicamente as porcentagens do CSS (width: 38%, height: 18%, top: 42%)
    largura_alvo = int(largura_img * 0.38)
    altura_alvo = int(altura_img * 0.18)
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img * 0.42) - (altura_alvo / 2))
    
    # Recorta o bloco correspondente ao retângulo vermelho
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # Processamento de imagem aplicado APENAS na área recortada
    cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (7, 7), 0)
    bordas = cv2.Canny(desfoque, 50, 100)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        maior_contorno = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior_contorno)
        
        # Fator de calibração adaptado para o novo recorte restrito
        proporcao_pixel_cm = 0.038  
        
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenha o contorno detectado de volta na imagem original para o operador ver
        cv2.rectangle(imagem_cv, (x_inicio + x, y_inicio + y), (x_inicio + x + w, y_inicio + y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"{w}px | {largura_medida}cm x {altura_medida}cm", (x_inicio + x, y_inicio + y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (36, 255, 12), 2)
        
        # Desenha um retângulo vermelho definitivo na foto final para mostrar onde foi lido
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Superfície Detectada Restrita à Área do Alvo")
        
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
        # Mostra onde estava o alvo mesmo se falhar a detecção
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
        st.image(imagem_cv, channels="BGR", caption="Falha na Detecção")
        st.warning("⚠️ Não foi possível identificar as bordas do objeto dentro do retângulo destacado.")
