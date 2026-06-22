import streamlit as st
import cv2
import numpy as np
import base64

st.set_page_config(page_title="Verificador CCB", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("Parâmetros Normativos (Fixos)")
st.sidebar.info("Modo Industrial Automático")
st.sidebar.write("Comprimento Mínimo: 50 mm (5.0 cm)")
st.sidebar.write("Altura Mínima: 22 mm (2.2 cm)")

# Inicializa o estado para guardar a imagem tirada pelo componente JS
if "foto_js" not in st.session_state:
    st.session_state.foto_js = None

# --- COMPONENTE CUSTOMIZADO EM HTML5 / JAVASCRIPT ---
# Ele força o 'facingMode: environment' (Câmera traseira) e desenha o guia na tela
html_camera = """
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%;">
    <div style="position: relative; width: 100%; max-width: 400px; aspect-ratio: 4/3; background: #222; border-radius: 8px; overflow: hidden;">
        <video id="video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
        
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70%; height: 35%; border: 4px solid #00FF00; border-radius: 8px; box-shadow: 0 0 15px rgba(0,255,0,0.6); pointer-events: none; display: flex; align-items: center; justify-content: center;">
            <span style="color: #00FF00; font-family: sans-serif; font-size: 10px; font-weight: bold; text-shadow: 1px 1px 2px #000;">ALINHE O SELO AQUI</span>
        </div>
    </div>
    <br>
    <button id="snap" style="width: 100%; max-width: 400px; padding: 12px; background-color: #FF4B4B; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">CAPTURAR FOTO</button>
    <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
</div>

<script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const snap = document.getElementById('snap');

    // Força estritamente o uso da câmera traseira (environment)
    navigator.mediaDevices.getUserMedia({ 
        video: { 
            facingMode: { exact: "environment" } 
        }, 
        audio: false 
    })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(err => {
        // Se falhar (ex: rodando no PC que não tem câmera traseira), tenta qualquer câmera disponível
        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { video.srcObject = stream; });
    });

    snap.addEventListener('click', () => {
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, 640, 480);
        const dataUrl = canvas.toDataURL('image/jpeg');
        
        # Envia a foto capturada de volta para o Streamlit
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: dataUrl}, '*');
    });
</script>
"""

# Renderiza o componente de câmera customizado e captura o retorno do JS
st.markdown("### 📸 Câmera de Inspeção")
st.write("Dê permissão de câmera. O sistema abrirá a traseira automaticamente.")
componente_foto = st.components.v1.html(html_camera, height=420)

# Trata a foto recebida via JavaScript
if componente_foto:
    st.session_state.foto_js = componente_foto

if st.session_state.foto_js:
    # Decodifica a imagem Base64 enviada pelo JavaScript para o formato OpenCV
    dados_b64 = st.session_state.foto_js.split(',')[1]
    bytes_img = base64.b64decode(dados_b64)
    imagem_np = np.frombuffer(bytes_img, dtype=np.uint8)
    imagem_cv = cv2.imdecode(imagem_np, cv2.IMREAD_COLOR)
    
    altura_img, largura_img, _ = imagem_cv.shape
    
    # --- ROI CENTRALIZADO COMBINANDO COM OS 70% x 35% DO JAVASCRIPT ---
    largura_alvo = int(largura_img * 0.70)  
    altura_alvo = int(altura_img * 0.35)    
    
    x_inicio = int((largura_img - largura_alvo) / 2)
    y_inicio = int((altura_img - altura_alvo) / 2) 
    
    imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
    
    # --- PROCESSAMENTO OPENCV ---
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
        
        proporcao_pixel_cm = 0.0296  
        largura_medida = round(w * proporcao_pixel_cm, 2)
        altura_medida = round(h * proporcao_pixel_cm, 2)
        
        abs_x1, abs_y1 = x_inicio + x, y_inicio + y
        abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
        
        cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 4)
        cv2.putText(imagem_cv, f"{largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Moldura azul de corte
        cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
        
        st.image(imagem_cv, channels="BGR", caption="Resultado da Análise Física")
        
        aprovado_comprimento = largura_medida >= 5.0
        aprovado_altura = altura_medida >= 2.2
        
        st.subheader("📊 Resultado da Análise")
        st.write(f"**Comprimento Medido:** {largura_medida} cm ({largura_medida * 10:.1f} mm)")
        st.write(f"**Altura Medida:** {altura_medida} cm ({altura_medida * 10:.1f} mm)")
        
        if aprovado_comprimento and aprovado_altura:
            st.success("✅ APROVADO: Selo CCB em conformidade!")
        else:
            st.error("❌ REPROVADO: Dimensões fora do padrão normativo.")
    else:
        st.image(imagem_cv, channels="BGR", caption="Falha")
        st.warning("⚠️ Não foi possível ler as bordas. Certifique-se de alinhar o selo dentro da caixa.")
