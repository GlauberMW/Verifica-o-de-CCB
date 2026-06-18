import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador com Enquadramento Digital")
st.sidebar.write("*Comprimento Mínimo:* 50 mm (5.0 cm)")
st.sidebar.write("*Altura Mínima:* 22 mm (2.2 cm)")

# --- TRUQUE CSS PARA DESENHAR A MÁSCARA POR CIMA DA CÂMERA EM TEMPO REAL ---
st.markdown(
    """
    <style>
    /* Força o container da câmera a aceitar elementos posicionados */
    div[data-testid="stCameraInput"] {
        position: relative !important;
    }
    
    /* Cria o retângulo vermelho fixo no centro exato da câmera antes de tirar a foto */
    div[data-testid="stCameraInput"]::after {
        content: "ALINHE O SELO AQUI";
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 75%;  /* Ocupa 75% da largura da tela */
        height: 35%; /* Ocupa 35% da altura da tela (formato deitado do selo) */
        border: 5px solid #FF0000; /* Linha vermelha grossa */
        border-radius: 4px;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.3); /* Escurece o fundo para destacar o centro */
        color: #FF0000;
        font-weight: bold;
        font-size: 14px;
        text-align: center;
        padding-top: 5px;
        pointer-events: none; /* Permite clicar no botão por trás da máscara */
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
    
    # Processamento de imagem padrão
    cinza = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (7, 7), 0)
    bordas = cv2.Canny(desfoque, 50, 100)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        maior_contorno = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior_contorno)
        
        # Fator de calibração baseado no enquadramento fixado pela máscara CSS
        proporcao_pixel_cm = 0.055  
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenha o resultado na imagem para o relatório
        cv2.rectangle(imagem_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"Medido: {largura_medida}cm x {altura_medida}cm", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 255, 12), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Superfície Detectada")
        
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
        st.warning("⚠️ Não foi possível identificar as bordas do objeto claramente.")
