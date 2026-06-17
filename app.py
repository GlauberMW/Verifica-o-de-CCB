import streamlit as st
import cv2
import numpy as np

st.title("Verificador de Superfície - CCB")

# --- SISTEMA DE SENHA DO ADMINISTRADOR ---
st.sidebar.header("Painel de Controle")

# Criamos uma chave para salvar os valores padrão e não resetarem
if "largura_padrao" not in st.session_state:
    st.session_state["largura_padrao"] = 20.0
if "altura_padrao" not in st.session_state:
    st.session_state["altura_padrao"] = 10.0

# Campo para digitar a senha do administrador
senha = st.sidebar.text_input("Senha do Administrador", type="password")

# Defina a senha que você quiser aqui (ex: "admin123")
if senha == "admin123":
    st.sidebar.success("🔑 Modo Administrador Ativado")
    # Se a senha estiver correta, permite que você altere os valores padrão
    st.session_state["largura_padrao"] = st.sidebar.number_input("Largura Padrão (cm)", value=st.session_state["largura_padrao"])
    st.session_state["altura_padrao"] = st.sidebar.number_input("Altura Padrão (cm)", value=st.session_state["altura_padrao"])
else:
    if senha != "":
        st.sidebar.error("❌ Senha Incorreta")
    # Se não tiver senha ou estiver errada, apenas exibe os valores atuais travados
    st.sidebar.info("Modo Operador (Valores Travados)")
    st.sidebar.write(f"*Largura Esperada:* {st.session_state['largura_padrao']} cm")
    st.sidebar.write(f"*Altura Esperada:* {st.session_state['altura_padrao']} cm")

# Pegando os valores que serão usados na validação
largura_ref = st.session_state["largura_padrao"]
altura_ref = st.session_state["altura_padrao"]
TOLERANCIA = 0.5 

# --- PROCESSO DE CAPTURA E MEDIÇÃO ---
foto_capturada = st.camera_input("Posicione o CCB centralizado na câmera")

if foto_capturada:
    bytes_data = foto_capturada.getvalue()
    imagem_cv = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    
    cinza = cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2GRAY)
    desfoque = cv2.GaussianBlur(cinza, (7, 7), 0)
    
    bordas = cv2.Canny(desfoque, 50, 100)
    contornos, _ = cv2.findContours(bordas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contornos:
        maior_contorno = max(contornos, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(maior_contorno)
        
        proporcao_pixel_cm = 0.05
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        cv2.rectangle(imagem_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 255, 12), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Superfície Detectada")
        
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
        st.warning("⚠️ Não foi possível identificar as bordas do objeto claramente.")
