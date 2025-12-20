from flask import Flask, render_template_string, jsonify, request
import requests
import random
import time
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# --- CONFIGURAÇÕES DO SISTEMA (REVISÃO 1/5: CONECTIVIDADE) ---
# Raio de busca ajustado para 120km para garantir que sempre haja aviões na lista
RAIO_KM = 120.0
# User-Agents diversificados para evitar bloqueios de API durante requisições frequentes
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância esférica entre dois pontos (Fórmula de Haversine)."""
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Determina o ângulo (bearing) do usuário em relação à aeronave para a bússola."""
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    bearing = degrees(atan2(y, x))
    return (bearing + 360) % 360

@app.route('/')
def index():
    # --- INTERFACE FRONT-END (REVISÃO 2/5: ESTILO E UX) ---
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass - Radar System</title>
        <style>
            :root { 
                --air-blue: #226488; 
                --warning-gold: #FFD700; 
                --bg-dark: #f0f4f7; 
                --text-gray: #888;
                --ticket-white: #ffffff;
            }

            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; margin: 0; padding: 0; }

            body { 
                background-color: var(--bg-dark); 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; 
                overflow: hidden; color: #333;
            }

            /* --- SEÇÃO DE BUSCA --- */
            #search-section {
                background: #ffffff; padding: 20px 30px; border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: flex; gap: 12px; align-items: center; border: 1px solid #e0e0e0;
                width: 90%; max-width: 800px; z-index: 1000; margin-bottom: 30px;
                transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.5s ease;
            }
            #search-section.hidden { transform: translateY(-150%); opacity: 0; position: absolute; pointer-events: none; }
            
            #search-section input { 
                border: 2px solid #eee; padding: 12px 18px; border-radius: 8px; flex: 1; 
                outline: none; font-size: 16px; transition: border-color 0.3s;
            }
            #search-section input:focus { border-color: var(--air-blue); }
            
            #search-section button { 
                background: var(--air-blue); color: white; border: none; padding: 12px 25px; 
                border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px;
                text-transform: uppercase; letter-spacing: 1px; transition: background 0.3s;
            }

            /* --- CARTÃO / TICKET --- */
            .card { 
                background: var(--ticket-white); width: 95%; max-width: 850px;
                border-radius: 24px; position: relative; 
                box-shadow: 0 30px 60px rgba(0,0,0,0.12); 
                display: flex; overflow: hidden; border: 1px solid #dcdcdc;
            }

            .left-stub {
                width: 28%; background: var(--air-blue); color: white;
                padding: 35px 20px; display: flex; flex-direction: column;
                border-right: 3px dashed rgba(255,255,255,0.3);
                position: relative;
            }

            /* Detalhes de corte do ticket (Essencial para estética) */
            .left-stub::before, .left-stub::after {
                content: ""; position: absolute; right: -13px; width: 26px; height: 26px;
                background: var(--bg-dark); border-radius: 50%; z-index: 5;
            }
            .left-stub::before { top: -13px; }
            .left-stub::after { bottom: -13px; }

            .seat-label { font-size: 0.85em; text-transform: uppercase; opacity: 0.7; letter-spacing: 1.2px; font-weight: 300; }
            .seat-num { font-size: 4.8em; font-weight: 900; margin-top: 5px; line-height: 1; letter-spacing: -3px; }
            
            .proximity-scale { display: flex; gap: 6px; margin-top: 30px; }
            .scale-step { width: 14px; height: 14px; background: rgba(255,255,255,0.15); border-radius: 3px; transition: 0.4s; }
            .scale-step.active { background: #ffffff; box-shadow: 0 0 12px #ffffff; }

            /* --- CORPO DO TICKET --- */
            .main-ticket { flex: 1; display: flex; flex-direction: column; position: relative; }
            
            .header-bar { 
                background: var(--air-blue); height: 95px; display: flex; 
                align-items: center; justify-content: space-between; padding: 0 45px; color: white;
            }
            .header-bar h1 { font-size: 1.8em; font-weight: 900; letter-spacing: 7px; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
            .header-bar .icon { font-size: 1.6em; opacity: 0.6; }

            .content-area { padding: 40px 50px; display: flex; flex: 1; background: white; }
            
            .col-data { flex: 1.8; border-right: 1px solid #f0f0f0; display: flex; flex-direction: column; gap: 30px; }
            .col-side { flex: 1; padding-left: 45px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; }

            .data-group { display: flex; flex-direction: column; }
            .label { color: var(--text-gray); font-size: 0.75em; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.8px; }
            .value { font-size: 1.9em; font-weight: 900; color: var(--air-blue); min-height: 1.3em; display: flex; align-items: center; }

            /* --- RODAPÉ TERMINAL --- */
            .terminal-footer { 
                background: #000; padding: 15px 45px; border-top: 4px solid var(--warning-gold);
                min-height: 70px; display: flex; align-items: center; overflow: hidden;
            }

            /* --- EFEITO FLAP BOARD (REVISÃO 3/5: ANIMAÇÃO) --- */
            .letter-slot { 
                display: inline-block; color: var(--warning-gold); 
                font-family: 'Courier New', Courier, monospace; font-weight: 900; 
                min-width: 0.65em; text-align: center; font-size: 1.15em;
                transition: transform 0.1s;
            }
            .flapping { animation: flap-anim 0.08s infinite; }
            @keyframes flap-anim { 
                0% { transform: scaleY(1); opacity: 1; }
                50% { transform: scaleY(0.1); opacity: 0.4; }
                100% { transform: scaleY(1); opacity: 1; }
            }

            /* ÍCONES E LINKS */
            #compass { font-size: 3.2em; transition: transform 1.2s cubic-bezier(0.19, 1, 0.22, 1); color: #ff8c00; filter: drop-shadow(0 3px 6px rgba(0,0,0,0.15)); }
            
            #radar-link { 
                display: block; text-decoration: none; opacity: 0.1; 
                transition: opacity 0.6s ease; cursor: default; pointer-events: none;
            }
            #radar-link.active { opacity: 1; cursor: pointer; pointer-events: auto; }
            
            .barcode { 
                width: 170px; height: 65px; 
                background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 7px); 
                border-radius: 4px;
            }
        </style>
    </head>
    <body>

        <div id="search-section">
            <input type="text" id="address-input" placeholder="Digite cidade ou coordenadas...">
            <button onclick="geocodeAddress()">Sincronizar Radar</button>
        </div>

        <div class="card">
            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.6)">Radar Station</div>
                <div class="seat-label" style="margin-top: 15px;">Assento:</div>
                <div class="seat-num">19 A</div>
                <div class="proximity-scale" id="p-scale">
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div>
                </div>
                <div class="seat-label" style="margin-top: auto; font-size: 0.6em; opacity: 0.5;">Secure ATC Link v5.0</div>
            </div>

            <div class="main-ticket">
                <div class="header-bar">
                    <span class="icon">✈</span><h1>BOARDING BOARD</h1><span class="icon">✈</span>
                </div>

                <div class="content-area">
                    <div class="col-data">
                        <div class="data-group">
                            <div class="label">Ident / Voo</div>
                            <div id="callsign" class="value"></div>
                        </div>
                        <div class="data-group">
                            <div class="label">Distância da Base</div>
                            <div id="dist_body" class="value"></div>
                        </div>
                        <div class="data-group">
                            <div class="label">Altitude (MSL)</div>
                            <div id="alt" class="value"></div>
                        </div>
                    </div>

                    <div class="col-side">
                        <div style="text-align: center;">
                            <div class="label">Aeronave</div>
                            <div id="type_id" class="value" style="justify-content: center;">----</div>
                        </div>
                        <div id="compass">↑</div>
                        <a id="radar-link" href="#" target="_blank">
                            <div class="barcode" title="Clique para abrir no mapa"></div>
                        </a>
                    </div>
                </div>

                <div class="terminal-footer">
                    <div id="status-container"></div>
                </div>
            </div>
        </div>

        <script>
            // --- LÓGICA FRONT-END (REVISÃO 4/5: PERFORMANCE) ---
            let latAlvo = null, lonAlvo = null, currentTarget = null, step = 0;
            let weather = { temp: '--', sky: 'SCANNING', vis: '--' };
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->°%";

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                if (!container) return;
                const newText = String(newValue || "").toUpperCase();
                
                // Sincroniza número de slots
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); 
                    s.className = "letter-slot"; 
                    s.innerHTML = "&nbsp;"; 
                    container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { 
                    container.removeChild(container.lastChild); 
                }
                
                const slots = container.querySelectorAll('.letter-slot');
                
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar && targetChar !== " ") return;

                    const randomDelay = Math.floor(Math.random() * 250); 
                    const cyclesNeeded = 10 + Math.floor(Math.random() * 10);

                    setTimeout(() => {
                        let currentCycle = 0;
                        const interval = setInterval(() => {
                            slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                            slot.classList.add('flapping');
                            
                            if (++currentCycle >= cyclesNeeded) {
                                clearInterval(interval);
                                slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                                slot.classList.remove('flapping');
                            }
                        }, 50);
                    }, randomDelay);
                });
            }

            function updateProximityScale(dist) {
                const steps = document.querySelectorAll('.scale-step');
                const activeCount = Math.max(1, Math.min(8, Math.ceil(8 - (dist / 15))));
                steps.forEach((s, i) => {
                    if (i < activeCount) s.classList.add('active');
                    else s.classList.remove('active');
                });
            }

            async function geocodeAddress() {
                const input = document.getElementById('address-input');
                const query = input.value;
                if(!query) return;
                
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
                    const data = await res.json();
                    if(data.length > 0) {
                        latAlvo = parseFloat(data[0].lat); 
                        lonAlvo = parseFloat(data[0].lon);
                        document.getElementById('search-section').classList.add('hidden');
                        getWeather();
                        setInterval(executarBusca, 10000); // Busca a cada 10s
                        executarBusca();
                    }
                } catch(e) { alert("Erro na conexão com Nominatim."); }
            }

            async function getWeather() {
                if(!latAlvo) return;
                try {
                    const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latAlvo}&longitude=${lonAlvo}&current_weather=true&hourly=visibility`);
                    const data = await res.json();
                    weather.temp = Math.round(data.current_weather.temperature) + "°C";
                    const code = data.current_weather.weathercode;
                    weather.sky = code < 3 ? "CEU LIMPO" : "NUBLADO";
                    weather.vis = (data.hourly.visibility[0] / 1000).toFixed(1) + "KM";
                } catch(e) {}
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&_t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    const link = document.getElementById('radar-link');
                    if(data.found) {
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist.toFixed(1) + " KM");
                        updateProximityScale(data.dist);
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        link.href = `https://www.radarbox.com/@${data.lat},${data.lon},z12`;
                        link.classList.add('active');
                    } else {
                        currentTarget = null;
                        link.classList.remove('active');
                        updateWithEffect('callsign', 'PROCURANDO');
                        updateWithEffect('dist_body', '---');
                        updateWithEffect('alt', '---');
                    }
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SISTEMA PRONTO');
                updateWithEffect('status-container', '> AGUARDANDO LOCALIZACAO...');
                
                // Ciclo de Mensagens no Rodapé (REVISÃO 5/5: FLUXO DE DADOS)
                setInterval(() => {
                    let msg = "";
                    if(!currentTarget) {
                        const msgs = [
                            `> CONECTADO AO ATC LIVE`,
                            `> TEMPERATURA: ${weather.temp}`,
                            `> CEU: ${weather.sky}`,
                            `> VISIBILIDADE: ${weather.vis}`,
                            `> RASTREANDO AERONAVES...`
                        ];
                        msg = msgs[step % msgs.length];
                    } else {
                        const info = [
                            `> CONTATO POSITIVO: ${currentTarget.callsign}`,
                            `> VELOCIDADE: ${currentTarget.speed} KT`,
                            `> ROTA: ${currentTarget.origin} > ${currentTarget.dest}`,
                            `> SINAL: ESTAVEL`
                        ];
                        msg = info[step % info.length];
                    }
                    updateWithEffect('status-container', msg);
                    step++;
                }, 5000);

                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; 
                    lonAlvo = pos.coords.longitude;
                    document.getElementById('search-section').classList.add('hidden');
                    getWeather();
                    setInterval(executarBusca, 10000);
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
        res = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=8).json()
        
        if res.get('ac'):
            validos = [a for a in res['ac'] if 'lat' in a and (a.get('flight') or a.get('call'))]
            if not validos: return jsonify({"found": False})
            
            ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call')).strip(), 
                "dist": haversine(lat_u, lon_u, ac['lat'], ac['lon']), 
                "alt_ft": int(ac.get('alt_baro', 0)), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "type": ac.get('t', 'ACFT'), 
                "speed": ac.get('gs', 0),
                "lat": ac['lat'], 
                "lon": ac['lon'],
                "origin": ac.get('origin', 'N/A'), 
                "dest": ac.get('dest', 'N/A')
            })
    except Exception as e:
        print(f"Erro: {e}")
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)























