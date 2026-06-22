import streamlit as st
import cv2
import numpy as np
import base64
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Industrial por Contornos")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# --- COMPONENTE DE CÂMERA EM JAVASCRIPT ---
html_camera = """
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%;">
    <div style="position: relative; width: 100%; max-width: 400px; aspect-ratio: 4/3; background: #222; border-radius: 8px; overflow: hidden;">
        <video id="video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
        
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 75%; height: 40%; border: 4px solid #00FF00; border-radius: 8px; box-shadow: 0 0 15px rgba(0,255,0,0.6); pointer-events: none; display: flex; align-items: center; justify-content: center;">
            <span style="color: #00FF00; font-family: sans-serif; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px #000;">ENCAIXE AS BORDAS DO SELO AQUI</span>
        </div>
    </div>
    <br>
    <button id="snap" style="width: 100%; max-width: 400px; padding: 14px; background-color: #FF4B4B; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px;">📸 CAPTURAR FOTO</button>
    <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
</div>

<script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const snap = document.getElementById('snap');

    navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: { ideal: "environment" } }, 
        audio: false 
    })
    .then(stream => { video.srcObject = stream; })
    .catch(err => {
        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { video.srcObject = stream; });
    });

    snap.addEventListener('click', () => {
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, 640, 480);
        const dataUrl = canvas.toDataURL('image/jpeg');
        
        localStorage.setItem('foto_capturada', dataUrl);
        window.parent.location.reload();
    });
</script>
"""

st.markdown("### 📸 Câmera de Inspeção")
st.components.v1.html(html_camera, height=360)

foto_salva = streamlit_js_eval(js_expressions="localStorage.getItem('foto_capturada')", key="busca_foto")

if foto_salva and "," in foto_salva:
    try:
        dados_b64 = foto_salva.split(',')[1]
        bytes_img = base64.b64decode(dados_b64)
        imagem_np = np.frombuffer(bytes_img, dtype=np.uint8)
        imagem_cv = cv2.imdecode(imagem_np, cv2.IMREAD_COLOR)
        
        altura_img, largura_img, _ = imagem_cv.shape
        
        # --- ROI CENTRALIZADO AJUSTADO (75% x 40%) ---
        largura_alvo = int(largura_img * 0.75)  
        altura_alvo = int(altura_img * 0.40)    
        
        x_inicio = int((largura_img - largura_alvo) / 2)
        y_inicio = int((altura_img - altura_alvo) / 2) 
        
        imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
        
        # --- PROCESSAMENTO INTELIGENTE DE CONTORNOS ---
        cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
        
        # Um leve desfoque para sumir com texturas do papelão áspero
        desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
        
        # Limiarização binária: transforma o selo em preto e branco absoluto
        # Como a borda do selo é bem escura, o OTSU isola ela perfeitamente
        _, threshold = cv2.threshold(desfoque, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Encontra todos os contornos gerados pelas formas pretas
        contornos, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        selo_detectado = False
        
        if contornos:
            # Ordena os contornos pelo tamanho da área (o maior será o retângulo de fora do selo)
            maior_contorno = max(contornos, key=cv2.contourArea)
            
            # Se a área do contorno for minimamente relevante (evita pegar sujeira)
            if cv2.contourArea(maior_contorno) > 2000:
                x, y, w, h = cv2.boundingRect(maior_contorno)
                selo_detectado = True
                
                # Fator de calibração pixel -> cm 
                proporcao_pixel_cm = 0.0296  
                
                largura_medida = round(w * proporcao_pixel_cm, 2)
                altura_medida = round(h * proporcao_pixel_cm, 2)
                
                abs_x1, abs_y1 = x_inicio + x, y_inicio + y
                abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
                
                # Desenha o retângulo VERDE exatamente na linha preta externa do selo real
                cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 4)
                cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Mostra o resultado final tratado
                st.image(imagem_cv, channels="BGR", caption="Selo CCB Detectado com Sucesso")
                
                aprovado_comprimento = largura_medida >= 5.0
                aprovado_altura = altura_medida >= 2.2
                
                st.subheader("📊 Resultado da Análise")
                st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
                st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
                
                if aprovado_comprimento and aprovado_altura:
                    st.success("✅ APROVADO: O selo CCB cumpre integralmente os padrões exigidos!")
                else:
                    st.error("❌ REPROVADO: Dimensões abaixo do padrão normativo.")
                    
        if not selo_detectado:
            # Desenha a área de rastreio em vermelho caso falhe
            cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
            st.image(imagem_cv, channels="BGR", caption="Falha de Rastreamento")
            st.warning("⚠️ Borda externa não identificada. Enquadre o retângulo preto do selo dentro do espaço verde.")
            
    except Exception as e:
        st.error(f"Erro no processamento técnico: {e}")
