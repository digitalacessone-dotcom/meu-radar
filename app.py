from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees
import os

app = Flask(__name__)

# Configuração: Raio de busca em KM
RAIO_KM = 25.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    start_lat, start_lon = radians(lat1), radians(lon1)
    end_lat, end_lon = radians(lat2), radians(lon2)
    d_lon = end_lon - start_lon
    y = sin(d_lon) * cos(end_lat)
    x = cos(start_lat) * sin(end_lat) - sin(start_lat) * cos(end_lat) * cos(d_lon)
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/api/data')
def get_data():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        # API pública de exemplo (ADS-B Exchange ou OpenSky)
        url = f"https://opendata.adsbexchange.com/api/slots/v2/lat/{lat}/lon/{lon}/dist/15"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('ac'):
            # Encontra o avião mais próximo do seu GPS
            closest = min(data['ac'], key=lambda x: haversine(lat, lon, x['lat'], x['lon']))
            dist = haversine(lat, lon, closest['lat'], closest['lon'])
            bearing = calculate_bearing(lat, lon, closest['lat'], closest['lon'])
            
            return jsonify({
                "found": True,
                "callsign": closest.get('flight', 'N/A').strip(),
                "alt_ft": closest.get('alt_baro', 0),
                "dist": round(dist, 1),
                "squawk": closest.get('squawk', '0000'),
                "bearing": bearing,
                "type": closest.get('t', 'UNK'),
                "hex": closest.get('hex', '000000')
            })
    except Exception as e:
        print(f"Erro: {e}")
    return jsonify({"found": False})

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>ATC Radar Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; }

            body { 
                background-color: var(--bg-dark); margin: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                width: 100vw; height: 100vh; font-family: 'Courier New', monospace; overflow: hidden;
            }

            /* CAMPO DE PESQUISA (Aparece se o GPS falhar) */
            #search-box { 
                display: none; width: 90%; max-width: 500px; background: rgba(0,0,0,0.6);
                padding: 15px; border-radius: 12px; margin-bottom: 20px; 
                border: 2px solid var(--warning-gold); gap: 10px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 12px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 20px; font-weight: 900; border-radius: 6px; cursor: pointer; }

            /* CABEÇALHO COM AVIÕES BEM GRANDES */
            .header { 
                padding: 15px 0; text-align: center; color: white; font-weight: 900; 
                font-size: 1.1em; letter-spacing: 2px; display: flex; align-items: center; 
                justify-content: center; gap: 30px; 
            }
            .header .plane-icon { font-size: 3em; color: white; } 

            .card { 
                background: var(--air-blue); width: 95%; max-width: 600px;
                border-radius: 15px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden;
            }

            .white-area { 
                background: #fdfdfd; margin: 0 10px; padding: 20px; min-height: 280px; border-radius: 4px; 
                display: flex; flex-direction: column;
            }

            /* ESTILO DAS LETRAS */
            .letter-slot { display: inline-block; min-width: 0.65em; text-align: center; }
            .white-area .letter-slot { color: var(--air-blue); font-weight: 900; }
            
            /* APENAS EMBAIXO: Letras Amarelas com fundo preto */
            .status-msg .letter-slot {
                color: var(--warning-gold); background: #000; margin: 0 1px; padding: 0 2px; border-radius: 2px;
            }

            .label { color: #aaa; font-size: 0.7em; font-weight: 800; text-transform: uppercase; margin-bottom: 5px; }
            .value { color: var(--air-blue); font-weight: 900; margin-bottom: 15px; display: flex; flex-wrap: wrap; }
            
            #callsign { font-size: 2.5em; } 
            #dist_body { font-size: 1.8em; }
            
            #compass { display: inline-block; transition: transform 0.8s; color: var(--warning-gold); font-size: 2em; }
            .barcode { height: 50px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; }
            
            .footer { padding: 15px 0; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 8px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 10px; }
            .status-msg { font-size: 0.8em; text-align: center; min-height: 1.5em; display: flex; justify-content: center; }

            .flapping { animation: flip 0.08s ease-in-out; }
            @keyframes flip { 0%, 100% { transform: scaleY(1); } 50% { transform: scaleY(0.4); } }
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CIDADE OU CEP...">
            <button onclick="buscarEndereco()">BUSCAR</button>
        </div>

        <div class="card" onclick="enableAudio()">
            <div class="header">
                <span class="plane-icon">✈</span> BOARDING PASS <span class="plane-icon">✈</span>
            </div>
            <div class="white-area">
                <div class="label">IDENT / CALLSIGN</div>
                <div id="callsign" class="value"></div>
                
                <div style="display:flex; justify-content: space-between;">
                    <div>
                        <div class="label">DISTANCE</div>
                        <div id="dist_body" class="value"></div>
                        <div class="label">ALTITUDE</div>
                        <div id="alt" class="value" style="font-size:1.4em"></div>
                    </div>
                    <div style="text-align:center; padding-left:20px; border-left: 1px dashed #ccc;">
                        <div class="label">BEARING</div>
                        <div class="value"><span id="compass">↑</span></div>
                        <div class="barcode"></div>
                    </div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            let latAlvo, lonAlvo;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:-";
            let audioCtx;

            function enableAudio() { if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)(); }
            function playTick() {
                if (!audioCtx) return;
                let osc = audioCtx.createOscillator();
                let g = audioCtx.createGain();
                osc.type = 'square'; osc.frequency.value = 120;
                g.gain.value = 0.01; osc.connect(g); g.connect(audioCtx.destination);
                osc.start(); osc.stop(audioCtx.currentTime + 0.01);
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                while (container.childNodes.length < newText.length) {
                    let s = document.createElement("span"); s.className = "letter-slot"; s.innerText = " ";
                    container.appendChild(s);
                }
                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((target, i) => {
                    if (slots[i].innerText === target) return;
                    setTimeout(() => {
                        let idx = chars.indexOf(slots[i].innerText);
                        let itv = setInterval(() => {
                            idx = (idx + 1) % chars.length;
                            slots[i].innerText = chars[idx] === " " ? "\u00A0" : chars[idx];
                            slots[i].classList.add('flapping'); playTick();
                            if (chars[idx] === target) { clearInterval(itv); slots[i].classList.remove('flapping'); }
                        }, 50);
                    }, i * 40);
                });
            }

            window.onload = () => {
                updateWithEffect('callsign', 'BUSCANDO');
                updateWithEffect('status', 'AGUARDANDO GPS...');
                navigator.geolocation.getCurrentPosition(p => {
                    latAlvo = p.coords.latitude; lonAlvo = p.coords.longitude;
                    setInterval(fetchData, 8000); fetchData();
                }, () => document.getElementById('search-box').style.display = "flex");
            };

            function fetchData() {
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(r => r.json()).then(d => {
                    if(d.found) {
                        updateWithEffect('callsign', d.callsign);
                        updateWithEffect('dist_body', d.dist + " KM");
                        updateWithEffect('alt', d.alt_ft + " FT");
                        updateWithEffect('status', "RADAR ATIVO");
                        document.getElementById('compass').style.transform = `rotate(${d.bearing}deg)`;
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    # Porta configurada para o ambiente do Render/Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



