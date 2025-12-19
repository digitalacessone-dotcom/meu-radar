from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 80.0

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

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

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass</title>
        <style>
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #f0f4f7; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif; overflow: hidden;
            }

            /* BARRA DE PESQUISA COM TRANSIÇÃO */
            #search-section {
                background: #fff; padding: 15px 25px; border-radius: 12px;
                margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                display: flex; gap: 10px; align-items: center; border: 1px solid #ddd;
                width: 95%; max-width: 850px; z-index: 100;
                transition: all 0.5s ease;
                opacity: 1; transform: translateY(0);
            }
            #search-section.hidden {
                opacity: 0; transform: translateY(-20px); pointer-events: none; margin-bottom: -60px;
            }

            #search-section input { border: 1px solid #ccc; padding: 10px; border-radius: 6px; flex: 1; font-size: 0.9em; outline: none; }
            #search-section button { background: var(--air-blue); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }

            /* BOTÃO RE-CONFIG DISCRETO */
            #reconfig-btn {
                position: absolute; top: 10px; right: 10px; font-size: 0.6em; color: #aaa; cursor: pointer; text-decoration: underline; z-index: 50;
            }

            .card { 
                background: white; width: 95%; max-width: 850px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
                display: flex; overflow: hidden; border: 1px solid #ddd;
                transition: transform 0.5s ease;
            }

            .left-stub {
                width: 25%; background: var(--air-blue); color: white;
                padding: 20px; display: flex; flex-direction: column;
                border-right: 2px dashed rgba(255,255,255,0.3);
            }
            .left-stub .seat-num { font-size: 4em; font-weight: 900; margin-top: 20px; line-height: 1; }
            .left-stub .seat-label { font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }

            .main-ticket { flex: 1; display: flex; flex-direction: column; }
            .header-bar { background: var(--air-blue); height: 80px; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; color: white; }
            .header-bar h1 { font-size: 1.5em; letter-spacing: 5px; margin: 0; }
            
            .content-area { padding: 30px 50px; display: flex; flex: 1; background: white; }
            .col-data { flex: 2; border-right: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; }
            .col-side { flex: 1; padding-left: 30px; align-items: center; display: flex; flex-direction: column; justify-content: space-around; }

            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); min-height: 1.2em; display: flex; }

            .terminal-footer { background: #000; padding: 12px 40px; border-top: 3px solid var(--warning-gold); min-height: 55px; display: flex; align-items: center; }
            .letter-slot { display: inline-block; color: var(--warning-gold); font-family: 'Courier New', monospace; font-weight: 900; min-width: 0.65em; text-align: center; }
            
            .flapping { animation: flap 0.07s infinite; }
            @keyframes flap { 50% { transform: scaleY(0.5); opacity: 0.5; } }

            #compass { font-size: 2.5em; transition: transform 0.8s ease; display: inline-block; color: #ff8c00; }
            
            #radar-link { display: block; text-decoration: none; pointer-events: none; transition: 0.4s all ease; opacity: 0.1; }
            .barcode { width: 150px; height: 55px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); margin-top: 10px; }
            
            #radar-link.active { pointer-events: auto !important; opacity: 1 !important; cursor: pointer !important; }
            #radar-link.active:hover { transform: scale(1.1); }
        </style>
    </head>
    <body>

        <div id="search-section">
            <input type="text" id="address-input" placeholder="Digite endereço, cidade ou CEP para iniciar...">
            <button onclick="geocodeAddress()">CONECTAR</button>
        </div>

        <div id="reconfig-btn" onclick="toggleSearch()">[ CHANGE LOCATION ]</div>

        <div class="card">
            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.7)">Radar Base</div>
                <div class="seat-label">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="seat-label" style="margin-top: auto;">Secure Tunnel</div>
            </div>

            <div class="main-ticket">
                <div class="header-bar">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>

                <div class="content-area">
                    <div class="col-data">
                        <div><div class="label">Ident / Callsign</div><div id="callsign" class="value"></div></div>
                        <div><div class="label">Aircraft Distance</div><div id="dist_body" class="value"></div></div>
                        <div><div class="label">Altitude (MSL)</div><div id="alt" class="value"></div></div>
                    </div>

                    <div class="col-side">
                        <div style="text-align: center;">
                            <div class="label">Type</div>
                            <div id="type_id" class="value">----</div>
                        </div>
                        <div id="compass">↑</div>
                        <a id="radar-link" href="#" target="_blank">
                            <div class="barcode"></div>
                        </a>
                    </div>
                </div>

                <div class="terminal-footer">
                    <div id="status-container"></div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, currentTarget = null, step = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function toggleSearch() {
                document.getElementById('search-section').classList.remove('hidden');
            }

            async function geocodeAddress() {
                const query = document.getElementById('address-input').value;
                if(!query) return;
                updateWithEffect('status-container', '> GEO-SEARCHING...');
                try {
                    const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
                    const data = await response.json();
                    if(data.length > 0) {
                        latAlvo = parseFloat(data[0].lat);
                        lonAlvo = parseFloat(data[0].lon);
                        
                        // ESCONDE A BARRA AO CONECTAR
                        document.getElementById('search-section').classList.add('hidden');
                        
                        updateWithEffect('status-container', '> LOCATION LOCKED');
                        executarBusca();
                        // Inicia o loop de busca se ainda não começou
                        if(!window.searchLoop) window.searchLoop = setInterval(executarBusca, 12000);
                    }
                } catch(e) { updateWithEffect('status-container', '> GEO-ERROR'); }
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                if (!container) return;
                const newText = String(newValue || "").toUpperCase();
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); s.className = "letter-slot"; s.innerHTML = "&nbsp;"; container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { container.removeChild(container.lastChild); }
                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;
                    let cycles = 0;
                    const interval = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        slot.classList.add('flapping');
                        if (++cycles >= 10 + i) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 45);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status-container', '> WAITING CONNECTION...');
                
                // Se o navegador já tiver GPS permitido, esconde a barra automaticamente
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    document.getElementById('search-section').classList.add('hidden');
                    executarBusca();
                    window.searchLoop = setInterval(executarBusca, 12000);
                });

                setInterval(() => {
                    if(!currentTarget) {
                        const msgs = ["> SCANNING AIRSPACE", "> NETWORK SECURE", "> WAITING TARGET"];
                        updateWithEffect('status-container', msgs[step % msgs.length]);
                    } else {
                        const info = [`> TARGET: ${currentTarget.callsign}`, `> SPD: ${currentTarget.speed} KT`, `> ALT: ${currentTarget.alt_ft} FT` ];
                        updateWithEffect('status-container', info[step % info.length]);
                    }
                    step++;
                }, 6000);
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    const radarLink = document.getElementById('radar-link');
                    if(data.found) {
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        radarLink.href = `https://www.radarbox.com/@${data.lat},${data.lon},z12`;
                        radarLink.classList.add('active');
                    } else {
                        currentTarget = null;
                        radarLink.classList.remove('active');
                        updateWithEffect('callsign', 'SEARCHING');
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Accept': 'application/json', 'Referer': 'https://adsb.lol/'}
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, headers=headers, timeout=10).json()
        if r.get('ac'):
            valid_ac = [a for a in r['ac'] if 'lat' in a and 'lon' in a]
            if valid_ac:
                ac = sorted(valid_ac, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'N/A')).strip(), 
                    "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                    "alt_ft": int(ac.get('alt_baro', 0) if isinstance(ac.get('alt_baro'), (int, float)) else 0), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0),
                    "lat": ac['lat'], "lon": ac['lon']
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)















