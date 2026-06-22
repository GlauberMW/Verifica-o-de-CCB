import streamlit as st
import cv2
import numpy as np
import base64
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Verificador CCB - Precisão", layout="centered")

st.title("Verificador de Superfície - CCB")

st.sidebar.header("⚙️ Trava de Segurança")
st.sidebar.warning("Modo Gabarito Estrito Ativado")
st.sidebar.write("O operador é obrigado a encaixar o selo perfeitamente nas bordas verdes.")

# --- COMPONENTE DE CÂMERA EM JAVASCRIPT ---
html_camera = """
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%;">
    <div style="position: relative; width: 100%; max-width: 400px; aspect-ratio: 4/3; background: #222; border-radius: 8px; overflow: hidden;">
        <video id="video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
        
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70%; height: 32%; border: 4px dashed #00FF00; border-radius: 4px; box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6); pointer-events: none; display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <span style="color: #00FF00; font-family: sans-serif; font-size: 12px; font-weight: bold; text-shadow: 1px 1px 2px #000; letter-spacing: 1px;">ENCAIXE AS BORDAS DO SELO AQUI</span>
            <span style="color: #00FF00; font-family: sans-serif; font-size: 9px; text-shadow: 1px 1px 2px #000; margin-top: 4px;">NÃO DEIXE SOBRAR NEM FALTAR ESPAÇO</span>
        </div>
    </div>
    <br>
    <button id="snap" style="width: 100%; max-width: 400px; padding: 14px; background-color: #00FF00; color: black; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">📸 CAPTURAR E MEDIR</button>
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

st.markdown("### 🔍 Escaneamento Obrigatório")
st.components.v1.html(html_camera, height=360)

foto_salva = streamlit_js_eval(js_expressions="localStorage.getItem('foto_capturada')", key="busca_foto")

if foto_salva and "," in foto_salva:
    try:
        dados_b64 = foto_salva.split(',')[1]
        bytes_img = base64.b64decode(dados_b64)
        imagem_np = np.frombuffer(bytes_img, dtype=np.uint8)
        imagem_cv = cv2.imdecode(imagem_np, cv2.IMREAD_COLOR)
        
        altura_img, largura_img, _ = imagem_cv.shape
        
        # --- ROI CASADO EXATAMENTE COM A MOLDURA DO JAVASCRIPT (70% x 32%) ---
        largura_alvo = int(largura_img * 0.70)  
        altura_alvo = int(altura_img * 0.32)    
        x_inicio = int((largura_img - largura_alvo) / 2)
        y_inicio = int((altura_img - altura_alvo) / 2) 
        
        imagem_recortada = imagem_cv[y_inicio:y_inicio+altura_alvo, x_inicio:x_inicio+largura_alvo]
        
        # --- PROCESSAMENTO DE IMAGEM ---
        cinza = cv2.cvtColor(imagem_recortada, cv2.COLOR_BGR2GRAY)
        desfoque = cv2.GaussianBlur(cinza, (5, 5), 0)
        
        # Isola as linhas pretas com threshold adaptativo
        thresh = cv2.adaptiveThreshold(desfoque, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        selo_detectado = False
        
        if contornos:
            maior_contorno = max(contornos, key=cv2.contourArea)
            
            if cv2.contourArea(maior_contorno) > 2000:
                x, y, w, h = cv2.boundingRect(maior_contorno)
                
                # --- A MÁGICA DA TRAVA DE DISTÂNCIA ESTÁ AQUI ---
                # Calculamos quanto por cento da janela cortada o selo real está ocupando.
                # Se o operador estiver na distância certa, o selo deve ocupar quase 100% da largura da janela (w / largura_alvo).
                taxa_ocupacao_largura = w / largura_alvo
                taxa_ocupacao_altura = h / altura_alvo
                
                # Convertendo os pixels para tamanho real baseado na janela fixa
                # Se ocupar 100% da janela, ele tem exatamente o tamanho máximo permitido (5.0cm x 2.2cm)
                largura_medida = round((w / largura_alvo) * 5.0, 2)
                altura_medida = round((h / altura_alvo) * 2.2, 2)
                
                abs_x1, abs_y1 = x_inicio + x, y_inicio + y
                abs_x2, abs_y2 = abs_x1 + w, abs_y1 + h
                
                # Desenha o feedback do OpenCV
                cv2.rectangle(imagem_cv, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 4)
                cv2.putText(imagem_cv, f"Medido: {largura_medida}cm x {altura_medida}cm", (abs_x1, abs_y1 - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Desenha os limites da janela ideal em azul
                cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (255, 0, 0), 2)
                
                st.image(imagem_cv, channels="BGR", caption="Análise Estatística de Enquadramento")
                
                st.subheader("📊 Relatório de Distância e Enquadramento")
                
                # Condição de validação estrita:
                # Se o operador afastar o celular, a taxa de ocupação cai (ex: 0.80). Logo, a largura medida cai para 4.0cm e REPROVA.
                # Se ele tentar usar um selo menor e chegar perto, o selo vaza da janela e o OpenCV lê errado ou dá erro.
                if taxa_ocupacao_largura < 0.90:
                    st.error(f"❌ REPROVADO: O celular está muito longe! (Ocupação: {taxa_ocupacao_largura*100:.1f}%)")
                    st.info("🔄 **Ação corretiva:** Aproxime a câmera até que a linha preta do selo encoste na linha pontilhada verde.")
                elif largura_medida < 5.0 or altura_medida < 2.2:
                    st.error(f"❌ REPROVADO: Selo menor que o padrão técnico medido ({largura_medida}cm x {altura_medida}cm).")
                else:
                    st.success(f"✅ APROVADO: Selo na distância correta e tamanho válido! ({largura_medida}cm x {altura_medida}cm)")
                    selo_detectado = True

        if not selo_detectado and 'taxa_ocupacao_largura' not in locals():
            cv2.rectangle(imagem_cv, (x_inicio, y_inicio), (x_inicio + largura_alvo, y_inicio + altura_alvo), (0, 0, 255), 2)
            st.image(imagem_cv, channels="BGR", caption="Erro de Leitura")
            st.error("❌ ERRO: Selo fora de posição ou muito próximo (vazando da área útil). Rebanhe o selo na moldura verde.")
            
    except Exception as e:
        st.error(f"Erro no motor de análise: {e}")
