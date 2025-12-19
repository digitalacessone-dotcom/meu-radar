from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Mechanical Split-Flap Radar</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Courier New', monospace; overflow: hidden;
            }

            /* CONTAINER DO PAINEL MECÂNICO */
            .flap-container {
                display: flex;
                flex-wrap: wrap;
                gap: 2px;
            }

            .slot {
                width: 0.7em;
                height: 1.2em;
                background: #111;
                color: white;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 3px;
                overflow: hidden;
                border-bottom: 1px solid #333;
            }

            /* ANIMAÇÃO DE QUEDA DA PALHETA */
            .flap-anim {
                animation: flipDown 0.15s steps(2) infinite;
            }

            @keyframes flipDown {
                0% { transform: translateY(-100%); }
                100% { transform: translateY(100%); }
            }

            #search-box { 
                display: none; width: 90%; max-width: 500px; background: rgba(255,255,255,0.1);
                padding: 10px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--warning-gold); gap: 8px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 10px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 15px; font-weight: 900; border-radius: 6px; }

            .card { 
                background: var(--air-blue); width: 95%; max-width: 620px;
                border-radius: 20px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden; transform: scale(0.96);
            }

            .notch { position: absolute; width: 40px; height: 40px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -20px; } .notch-right { right: -20px; }

            .header { padding: 15px 0; text-align: center; color: white; font-weight: 900; letter-spacing: 3px; font-size: 1.1em; }

            .white-area { 
                background: #fdfdfd; margin: 0 10px; position: relative; 
                display: flex; padding: 25px 15px; min-height: 240px; border-radius: 4px; 
            }

            .col-left { flex: 1.6; border-right: 1px dashed #ddd; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 5px; }
            .value { margin-bottom: 15px; min-height: 1.2em; color: var(--air-blue); }
            
            #compass { display: inline-block; transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); color: var(--warning-gold); font-size: 1.4em; }
            
            .barcode { 
                height: 50px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); 
                width: 100%; margin: 8px 0 4px 0; border: 1px solid #eee; 
            }

            .footer { padding: 10px 0 20px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); min-height: 110px; }
            .yellow-lines { width: 100%; height: 6px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 12px; }
            
            .status-msg { color: var(--warning-gold); min-height: 1.5em; }
            
            /* Ajuste de cor para o texto no ticket vs rodapé */
            .value .slot { background: var(--air-blue); color: white; }
            .status-msg .slot { background: #000; color: var(--warning-gold); border: 1px solid #222; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CITY OR ZIP...">
            <button onclick="buscarEndereco()">GO</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header">✈ ATC BOARDING BOARD ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div class="label">IDENT / CALLSIGN</div>
                    <div id="callsign" class="value flap-container"></div>
                    
                    <div class="label">AIRCRAFT DISTANCE</div>
                    <div id="dist_body" class="value flap-container"></div>
                    
                    <div class="label">ALTITUDE (MSL)</div>
                    <div id="alt" class="value flap-container"></div>
                </div>
                <div class="col-right">
                    <div class="label">BEARING</div>
                    <div class="value"><span id="compass">↑</span></div>
                    <a id="map-link" style="text-decoration:none; width:100%;" target="_blank">
                        <div class="barcode"></div>
                    </a>
                    <div id="signal-bars" style="color:var(--air-blue); font-size:12px; font-weight:900;">[ ▮▮▮▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg flap-container"></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let statusIndex = 0;
            const alphabet = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            const systemMsgs = [
                "RADAR SWEEP ACTIVE: 25KM",
                "VISIBILITY: CAVOK",
                "ATC TRANSCEIVER: ONLINE",
                "TEMP: 24C / QNH: 1013"
            ];

            // FUNÇÃO MOTOR DO SPLIT-FLAP REAL
            function updateSplitFlap(id, newText) {
                const container = document.getElementById(id);
                newText = String(newText).toUpperCase();
                
                // Garantir que temos slots suficientes
                while (container.children.length < newText.length) {
                    const slot = document.createElement('div');
                    slot.className = 'slot';
                    slot.innerHTML = '<span>&nbsp;</span>';
                    container.appendChild(slot);
                }
                while (container.children.length > newText.length) {
                    container.removeChild(container.lastChild);
                }

                Array.from(container.children).forEach((slot, i) => {
                    const targetChar = newText[i] || " ";
                    const currentSpan = slot.querySelector('span');
                    const currentChar = currentSpan.innerText;

                    if (currentChar !== targetChar) {
                        let step = alphabet.indexOf(currentChar);
                        if (step === -1) step = 0;
                        
                        // Inicia animação de "giro" mecânico
                        currentSpan.classList.add('flap-anim');
                        
                        const timer = setInterval(() => {
                            step = (step + 1) % alphabet.length;
                            currentSpan.innerText = alphabet[step];
                            
                            if (alphabet[step] === targetChar) {
                                clearInterval(timer);
                                currentSpan.classList.remove('flap-anim');
                            }
                        }, 40 + (i * 10)); // Atraso progressivo para efeito cascata
                    }
                });
            }

            window.onload = function() {
                updateSplitFlap('callsign', 'SEARCHING');
                updateSplitFlap('status', 'INITIALIZING SYSTEM');

                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
                
                setInterval(() => {
                    if(!currentTarget) {
                        updateSplitFlap('status', systemMsgs[statusIndex]);
                        statusIndex = (statusIndex + 1) % systemMsgs.length;
                    } else {
                        const flightMsgs = [
                            `TARGET: ${currentTarget.callsign}`,
                            `PATH: ${currentTarget.origin} > ${currentTarget.dest}`,
                            `TYPE: ${currentTarget.type} / ${currentTarget.speed}KTS`
                        ];
                        updateSplitFlap('status', flightMsgs[statusIndex % 3]);
                        statusIndex++;
                    }
                }, 6000);
            };

            function iniciarRadar() {
                setInterval(executarBusca, 8000);
                executarBusca();
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        currentTarget = data;
                        updateSplitFlap('callsign', data.callsign);
                        updateSplitFlap('alt', data.alt_ft + " FT");
                        updateSplitFlap('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                    } else {
                        if(currentTarget) {
                            updateSplitFlap('callsign', "SEARCHING");
                            updateSplitFlap('dist_body', "00.0 KM");
                        }
                        currentTarget = null;
                    }
                });
            }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-box').style.display = "none";
                    iniciarRadar();
                }
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, headers=headers, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                    "alt_ft": int(ac.get('alt_baro', 0)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": f"https://globe.adsbexchange.com/?lat={lat_u}&lon={lon_u}&zoom=11&hex={ac.get('hex')}",
                    "origin": ac.get('t_from', 'N/A').split(' ')[0],
                    "dest": ac.get('t_to', 'N/A').split(' ')[0],
                    "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0)
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)




































