from flask import Flask, render_template_string, jsonify, request
import requests
import random
import time
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
RAIO_KM = 120.0
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass</title>
        <style>
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #f0f4f7; }
            * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
            body { background: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: Arial, sans-serif; overflow: hidden; }

            /* BUSCA */
            #search-section { background: #fff; padding: 20px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); display: flex; gap: 10px; width: 90%; max-width: 800px; margin-bottom: 20px; z-index: 1000; }
            #search-section.hidden { display: none; }
            #search-section input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; }
            #search-section button { background: var(--air-blue); color: #fff; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; }

            /* TICKET */
            .card { background: #fff; width: 95%; max-width: 850px; border-radius: 20px; display: flex; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.1); border: 1px solid #ccc; }
            .left-stub { width: 28%; background: var(--air-blue); color: #fff; padding: 30px 20px; border-right: 3px dashed rgba(255,255,255,0.3); position: relative; }
            .left-stub::before, .left-stub::after { content: ""; position: absolute; right: -13px; width: 26px; height: 26px; background: var(--bg-dark); border-radius: 50%; }
            .left-stub::before { top: -13px; } .left-stub::after { bottom: -13px; }
            .seat-num { font-size: 4.5em; font-weight: 900; line-height: 1; margin-top: 10px; }
            .proximity-scale { display: flex; gap: 5px; margin-top: 25px; }
            .scale-step { width: 12px; height: 12px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            .scale-step.active { background: #fff; box-shadow: 0 0 8px #fff; }

            /* CONTEUDO */
            .main-ticket { flex: 1; display: flex; flex-direction: column; }
            .header-bar { background: var(--air-blue); height: 80px; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; color: #fff; }
            .header-bar h1 { font-size: 1.5em; letter-spacing: 5px; }
            .content-area { padding: 30px 45px; display: flex; flex: 1; }
            .col-data { flex: 1.8; border-right: 1px solid #eee; display: flex; flex-direction: column; gap: 20px; }
            .col-side { flex: 1; padding-left: 30px; display: flex; flex-direction: column; align-items: center; justify-content: space-around; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.7em; font-weight: 900; color: var(--air-blue); min-height: 1.2em; }

            /* RODAPÉ PRETO - ONDE ESTÁ O PROBLEMA */
            .terminal-footer { 
                background: #000 !important; 
                padding: 10px 40px; 
                border-top: 4px solid var(--warning-gold);
                min-height: 60px; 
                display: flex; 
                align-items: center;
                width: 100%;
            }
            .letter-slot { 
                color: var(--warning-gold) !important; 
                font-family: 'Courier New', monospace; 
                font-weight: 900; 
                font-size: 1.2em;
                margin-right: 1px;
            }
            #compass { font-size: 3em; transition: transform 1s ease; color: #ff8c00; }
            .barcode { width: 150px; height: 50px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 6px); opacity: 0.2; }
            .active .barcode { opacity: 1; }
        </style>
    </head>
    <body>

        <div id="search-section">
            <input type="text" id="address-input" placeholder="Digite sua cidade...">
            <button onclick="geocodeAddress()">CONECTAR</button>
        </div>

        <div class="card">
            <div class="left-stub">
                <div class="label" style="color:#abd1e6">Radar Base</div>
                <div class="seat-num">19 A</div>
                <div class="proximity-scale">
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div>
                </div>
            </div>
            <div class="main-ticket">
                <div class="header-bar"><span>✈</span><h1>BOARDING BOARD</h1><span>✈</span></div>
                <div class="content-area">
                    <div class="col-data">
                        <div><div class="label">Ident / Voo</div><div id="callsign" class="value">AGUARDANDO</div></div>
                        <div><div class="label">Distância</div><div id="dist_body" class="value">---</div></div>
                        <div><div class="label">Altitude</div><div id="alt" class="value">---</div></div>
                    </div>
                    <div class="col-side">
                        <div id="compass">↑</div>
                        <div id="radar-link"><div class="barcode"></div></div>
                    </div>
                </div>
                <div class="terminal-footer" id="terminal-footer">
                    <div id="status-container"></div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, currentTarget = null, step = 0;
            let weather = { temp: '22°C', sky: 'LIMPO' };

            // Função de escrita simplificada para garantir que apareça na faixa preta
            function writeTerminal(text) {
                const container = document.getElementById('status-container');
                if(!container) return;
                container.innerHTML = '';
                const cleanText = text.toUpperCase();
                for(let char of cleanText) {
                    const span = document.createElement('span');
                    span.className = 'letter-slot';
                    span.innerText = char === ' ' ? '\u00A0' : char;
                    container.appendChild(span);
                }
            }

            async function geocodeAddress() {
                const query = document.getElementById('address-input').value;
                if(!query) return;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=1`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-section').classList.add('hidden');
                    setInterval(executarBusca, 8000);
                    executarBusca();
                }
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        currentTarget = data;
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('dist_body').innerText = data.dist.toFixed(1) + " KM";
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('radar-link').classList.add('active');
                        
                        const steps = document.querySelectorAll('.scale-step');
                        const active = Math.max(1, Math.min(8, Math.ceil(8 - (data.dist/15))));
                        steps.forEach((s,i) => i < active ? s.classList.add('active') : s.classList.remove('active'));
                    }
                });
            }

            // Loop de mensagens da faixa preta (TOTALMENTE REFEITO)
            setInterval(() => {
                let msg = "";
                if(!currentTarget) {
                    const msgs = ["> BUSCANDO SINAL ATC...", "> AGUARDANDO DADOS...", "> RADAR OPERACIONAL"];
                    msg = msgs[step % msgs.length];
                } else {
                    const msgs = [
                        `> ALVO: ${currentTarget.callsign}`,
                        `> VELOCIDADE: ${currentTarget.speed} KT`,
                        `> STATUS: SINAL FORTE`
                    ];
                    msg = msgs[step % msgs.length];
                }
                writeTerminal(msg);
                step++;
            }, 4000);

            window.onload = () => {
                writeTerminal("> SISTEMA INICIALIZADO");
                // Tenta pegar GPS
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    document.getElementById('search-section').classList.add('hidden');
                    setInterval(executarBusca, 8000);
                    executarBusca();
                });
            };
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=5).json()
        if r.get('ac'):
            ac = sorted([a for a in r['ac'] if 'lat' in a], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call') or "N/A").strip(),
                "dist": haversine(lat_u, lon_u, ac['lat'], ac['lon']),
                "alt_ft": int(ac.get('alt_baro', 0)),
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "speed": ac.get('gs', 0),
                "lat": ac['lat'], "lon": ac['lon']
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
























