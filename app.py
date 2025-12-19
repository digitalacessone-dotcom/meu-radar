from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Raio expandido para garantir captura em Campos/Litoral
RAIO_KM = 120.0 

# Lista de User-Agents para rotação (Camuflagem)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
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
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Manifesto de Voo Profissional</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #050b14; }
            body { 
                background-color: var(--bg-dark); display: flex; align-items: center; justify-content: center; 
                min-height: 100vh; margin: 0; font-family: 'Courier New', monospace;
                background-image: radial-gradient(circle at center, #1a2a44 0%, #050b14 100%);
            }

            /* DESIGN DO BILHETE FÍSICO */
            .card { 
                background: #fdfdfd; width: 95%; max-width: 650px; border-radius: 4px; 
                position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.8);
                overflow: hidden; background-image: url('https://www.transparenttextures.com/patterns/p6.png');
            }
            /* Efeito de dobra diagonal */
            .card::after { 
                content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                background: linear-gradient(135deg, rgba(255,255,255,0) 45%, rgba(0,0,0,0.06) 50%, rgba(255,255,255,0) 55%);
                pointer-events: none;
            }

            .blue-header { background: var(--air-blue); color: white; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
            .airline-info { font-size: 0.7em; font-weight: bold; letter-spacing: 1px; }

            .tear-line { border-right: 2px dashed #ccc; position: absolute; right: 30%; top: 0; bottom: 0; z-index: 5; }
            .tear-line.active { border-right-color: var(--warning-gold); box-shadow: -2px 0 10px var(--warning-gold); animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0.3; } }

            .white-area { display: flex; padding: 25px; min-height: 280px; position: relative; }
            .col-main { flex: 2; padding-right: 20px; }
            .col-stub { flex: 1; border-left: 1px solid #eee; padding-left: 20px; text-align: center; }

            /* CARIMBO DINÂMICO */
            .stamp {
                position: absolute; top: 50%; left: 40%; transform: translate(-50%, -50%) rotate(-15deg);
                border: 4px double #d32f2f; color: #d32f2f; padding: 10px 20px; font-weight: 900;
                font-size: 1.5em; border-radius: 10px; opacity: 0; transition: 0.5s;
                text-transform: uppercase; pointer-events: none; z-index: 10;
            }
            .stamp.visible { opacity: 0.4; animation: stamp-in 0.3s ease-out; }
            @keyframes stamp-in { from { transform: translate(-50%, -50%) rotate(-15deg) scale(2); opacity: 0; } }

            .label { color: #888; font-size: 0.65em; font-weight: 800; margin-bottom: 2px; }
            .value { font-size: 1.6em; font-weight: 900; color: #111; margin-bottom: 15px; }
            #compass { font-size: 1.5em; color: var(--air-blue); display: inline-block; transition: 0.5s; }
            
            .footer { background: #eee; padding: 10px; }
            .yellow-bar { background: var(--warning-gold); padding: 8px; text-align: center; font-weight: 900; font-size: 0.8em; color: #000; }

            .safety-tips { font-size: 0.55em; color: #666; margin-top: 15px; display: flex; gap: 8px; border-top: 1px solid #eee; padding-top: 10px; }
            .tip-icon { border: 1.2px solid #666; border-radius: 50%; width: 12px; height: 12px; display: inline-flex; align-items: center; justify-content: center; }
        </style>
    </head>
    <body>

        <div class="card">
            <div class="blue-header">
                <div class="airline-info">AIRSPACE MANIFEST / <span id="airline-name">SCANNING...</span></div>
                <div>✈</div>
            </div>

            <div class="white-area">
                <div class="stamp" id="main-stamp">VISUAL CONTACT</div>
                <div class="tear-line" id="tear"></div>

                <div class="col-main">
                    <div class="label">AIRCRAFT CALLSIGN</div>
                    <div id="callsign" class="value" style="font-size: 2.2em;">SEARCHING</div>
                    
                    <div style="display: flex; gap: 30px;">
                        <div><div class="label">ALTITUDE</div><div id="alt" class="value">---</div></div>
                        <div><div class="label">SPEED</div><div id="speed" class="value">---</div></div>
                    </div>
                    
                    <div class="safety-tips">
                        <span><span class="tip-icon">!</span> EYE PROTECTION</span>
                        <span><span class="tip-icon">!</span> TARGET TRACKING</span>
                    </div>
                </div>

                <div class="col-stub">
                    <div class="label">BEARING</div>
                    <div id="compass">↑</div>
                    <div id="dist" class="value" style="margin-top:10px;">0.0 KM</div>
                    <div class="label">ETA (MIN)</div>
                    <div id="eta" class="value" style="color:var(--air-blue)">--</div>
                </div>
            </div>

            <div class="footer">
                <div id="status-bar" class="yellow-bar">INITIALIZING RADAR UPLINK...</div>
            </div>
        </div>

        <script>
            let lat, lon;
            let targetLock = false;
            let flightData = null;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    lat = pos.coords.latitude; lon = pos.coords.longitude;
                    iniciarRadar();
                }, () => {
                    lat = -21.76; lon = -41.33; // Fallback Campos
                    iniciarRadar();
                });
            };

            function iniciarRadar() {
                setInterval(executarBusca, 7000);
                let cycle = 0;
                setInterval(() => {
                    const bar = document.getElementById('status-bar');
                    const msgs = targetLock ? [`TARGET: ${flightData.callsign}`, `RANGE: ${flightData.dist} KM`] : ["SCANNING CAMPOS AREA", "ADS-B NETWORK ACTIVE"];
                    bar.innerText = msgs[cycle % msgs.length];
                    cycle++;
                }, 3500);
            }

            function executarBusca() {
                fetch(`/api/data?lat=${lat}&lon=${lon}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        flightData = data;
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = data.alt + " FT";
                        document.getElementById('speed').innerText = data.speed + " KM/H";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('main-stamp').classList.add('visible');
                        if(data.dist < 20) document.getElementById('tear').classList.add('active');
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('main-stamp').classList.remove('visible');
                        document.getElementById('callsign').innerText = "SEARCHING";
                    }
                    // DEBUG SILENCIOSO NO CONSOLE (F12)
                    console.log("Debug:", data.debug_msg);
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    l_lat = float(request.args.get('lat', 0))
    l_lon = float(request.args.get('lon', 0))
    
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    debug_info = f"Scan em {l_lat}, {l_lon} | Raio {RAIO_KM}km"

    try:
        # API Principal com camuflagem
        url = f"https://api.adsb.one/v2/lat/{l_lat}/lon/{l_lon}/dist/{RAIO_KM}"
        r = requests.get(url, headers=headers, timeout=5).json()
        
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(l_lat, l_lon, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(l_lat, l_lon, ac['lat'], ac['lon']), 1),
                "alt": int(ac.get('alt_baro', 0)),
                "speed": int(ac.get('gs', 0) * 1.852),
                "bearing": int(calculate_bearing(l_lat, l_lon, ac['lat'], ac['lon'])),
                "debug_msg": debug_info + " | Sucesso!"
            })
    except Exception as e:
        debug_info += f" | Erro: {str(e)}"
    
    return jsonify({"found": False, "debug_msg": debug_info})

if __name__ == '__main__':
    app.run(debug=True)












