import streamlit as st
import cv2
import numpy as np

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Operador")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

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
        
        # Fator de calibração (ajuste se necessário para sua câmera)
        proporcao_pixel_cm = 0.05
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        # Desenha na tela
        cv2.rectangle(imagem_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (36, 255, 12), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Superfície Detectada")
        
        # --- VALIDAÇÃO CONFORME A SUA NOVA REGRA ---
        # Dentro do padrão se: Comprimento >= 5.0cm (50mm) E Altura >= 2.2cm (22mm)
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"Comprimento Medido: {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"Altura Medida: {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: O CCB está dentro do padrão (Acima de 50mm x 22mm)!")
        else:
            erros = []
            if not aprovado_comprimento:
                erros.append("Comprimento abaixo de 50mm")
            if not aprovado_altura:
                erros.append("Altura abaixo de 22mm")
            
            st.error(f"❌ REPROVADO: {', '.join(erros)}.")
    else:
        st.warning("⚠️ Não foi possível identificar as bordas do objeto claramente.")
