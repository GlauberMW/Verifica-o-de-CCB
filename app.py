import streamlit as st
import cv2
import numpy as np
import base64
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Scanner de Linha CCB", layout="centered")

st.title("Gabarito Digital CCB 🛠️")
st.write("A câmera funciona como o seu gabarito físico de metal. Encaixe o selo nas marcações.")

# --- SCANNER EM VÍDEO COM MOLDURA DE MEDIÇÃO REAL ---
html_scanner = """
<div style="display: flex; flex-direction: column; align-items: center; width: 100%;">
    <div style="position: relative; width: 100%; max-width: 400px; aspect-ratio: 4/3; background: #111; border-radius: 12px; overflow: hidden; border: 3px solid #333;">
        <video id="video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
        
        <div id="gabarito" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 75%; height: 35%; border: 4px dashed #FF0000; border-radius: 2px; box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6); pointer-events: none; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: all 0.2s;">
            <span id="texto-guia" style="color: #FF0000; font-family: sans-serif; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px #000; letter-spacing: 1px; text-align: center; padding: 0 5px;">ALINHE O SELO NAS MARCAÇÕES</span>
        </div>
    </div>
    <br>
    <canvas id="canvas_process" width="320" height="240" style="display:none;"></canvas>
</div>

<script src="https://docs.opencv.org/4.5.4/opencv.js" type="text/javascript"></script>

<script>
    const video = document.getElementById('video');
    const gabarito = document.getElementById('gabarito');
    const textoGuia = document.getElementById('texto-guia');
    const canvas = document.getElementById('canvas_process');

    navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: { ideal: "environment" }, width: 640, height: 480 }, 
        audio: false 
    })
    .then(stream => { 
        video.srcObject = stream;
        video.ready = true;
    });

    function analisarGabarito() {
        if (!video.ready) {
            setTimeout(analisarGabarito, 100);
            return;
        }

        try {
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            let src = cv.imread(canvas);
            let dst = new cv.Mat();
            
            // Filtro para achar as bordas escuras do selo
            cv.cvtColor(src, dst, cv.COLOR_RGBA2GRAY);
            cv.threshold(dst, dst, 90, 255, cv.THRESH_BINARY_INV);
            
            let contours = new cv.MatVector();
            let hierarchy = new cv.Mat();
            cv.findContours(dst, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
            
            let alcancouMarcacaoMinima = false;

            for (let i = 0; i < contours.size(); ++i) {
                let cnt = contours.get(i);
                let rect = cv.boundingRect(cnt);
                
                // MÁGICA: Se o contorno preto do selo cobrir ou passar da largura pontilhada do visor
                if (rect.width >= (canvas.width * 0.70) && rect.height >= (canvas.height * 0.30)) {
                    alcancouMarcacaoMinima = true;
                    break;
                }
            }

            // MUDANÇA EM TEMPO REAL BASEADO NAS SUAS MARCAÇÕES
         # TRAVA DE SEGURANÇA: Só tenta ler se a foto realmente existir no sistema!
if "foto_js" in st.session_state and st.session_state.foto_js is not None:
    try:
        dados_b64 = st.session_state.foto_js.split(',')[1]
        bytes_img = base64.b64decode(dados_b64)
        # ... resto do seu código de processamento que já funciona ...
    except Exception as e:
        st.error(f"Erro ao processar imagem: {e}")
else:
    st.info("💡 Aguardando a captura da foto para iniciar a medição do selo.")
            if (alcancouMarcacaoMinima) {
                gabarito.style.borderColor = "#00FF00";
                gabarito.style.boxShadow = "0 0 30px rgba(0, 255, 0, 0.9), 0 0 0 9999px rgba(0, 0, 0, 0.3)";
                textoGuia.style.color = "#00FF00";
                textoGuia.innerText = "✓ TAMANHO OK (DENTRO DA NORMA)";
                
                // Disparo automático rápido para não deixar o operador perder o foco
                setTimeout(() => {
                    const dataUrl = canvas.toDataURL('image/jpeg');
                    localStorage.setItem('foto_capturada', dataUrl);
                    window.parent.location.reload();
                }, 350);
                
            } else {
                gabarito.style.borderColor = "#FF0000";
                gabarito.style.boxShadow = "0 0 15px rgba(255, 0, 0, 0.5), 0 0 0 9999px rgba(0, 0, 0, 0.6)";
                textoGuia.style.color = "#FF0000";
                textoGuia.innerText = "REPROVADO: ABAIXO DA MARCAÇÃO MÍNIMA";
            }

            src.delete(); dst.delete(); contours.delete(); hierarchy.delete();
            
            if (!localStorage.getItem('foto_capturada')) {
                requestAnimationFrame(analisarGabarito);
            }
        } catch (e) {
            requestAnimationFrame(analisarGabarito);
        }
    }

    setTimeout(analisarGabarito, 2000);
</script>
"""

st.components.v1.html(html_scanner, height=380)

if st.button("🔄 Liberar para Nova Medição / Próxima Caixa"):
    streamlit_js_eval(js_expressions="localStorage.removeItem('foto_capturada')")
    st.rerun()

foto_salva = streamlit_js_eval(js_expressions="localStorage.getItem('foto_capturada')", key="busca_foto")

if foto_salva and "," in foto_salva:
    try:
        dados_b64 = foto_salva.split(',')[1]
        bytes_img = base64.b64decode(dados_b64)
        imagem_np = np.frombuffer(bytes_img, dtype=np.uint8)
        imagem_cv = cv2.imdecode(imagem_np, cv2.IMREAD_COLOR)
        
        st.image(imagem_cv, channels="BGR", caption="Evidência Registrada do Selo")
        
        st.subheader("📋 Relatório de Conformidade Física")
        st.success("✅ APROVADO: O selo preencheu com sucesso os limites estabelecidos pelas marcações de tolerância do gabarito.")
        st.info("O registro desta verificação foi salvo no banco local. Pode prosseguir para o próximo item.")
        
    except Exception as e:
        st.error(f"Erro ao salvar evidência: {e}")
