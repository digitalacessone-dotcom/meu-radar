from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

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
        <title>Visual Radar Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            
            * { box-sizing: border-box; }
            
            body { 
                background-color: var(--bg-dark); 
                margin: 0; padding: 0;
                display: flex; flex-direction: column; 
                height: 100vh; width: 100vw;
                font-family: 'Courier New', monospace; 
                overflow: hidden; 
            }
            
            /* Box de busca flutuante no topo */
            #search-box { 
                display: none; background: rgba(0,0,0,0.8); padding: 10px; 
                border-bottom: 2px solid var(--warning-gold); width: 100%; gap: 10px; z-index: 100;
            }
            input { flex: 1; background: #222; border: 1px solid #444; padding: 10px; color: white; border-radius: 4px; }
            #search-box button { background: var(--warning-gold); border: none; padding: 10px 15px; font-weight: 900; border-radius: 4px; }

            /* Container principal que ocupa tudo */
            .main-container {
                flex: 1;
                display: flex;
                padding: 10px;
                align-items: center;
                justify-content: center;
            }

            .card { 
                background: var(--air-blue); 
                width: 100%; 
                height: 100%;
                max-width: 500px;
                border-radius: 20px; 
                position: relative; 
                display: flex; 
                flex-direction: column; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.5);
                overflow: hidden;
            }

            /* Picotes laterais */
            .notch { position: absolute; width: 30px; height: 30px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 5; }
            .notch-left { left: -15px; } .notch-right { right: -15px; }

            /* Header adaptável */
            .header { 
                padding: 15px; 
                display: flex; justify-content: center; align-items: center; 
                color: white; gap: 15px; font-weight: 900; 
                text-align: center; font-size: 14px;
            }
            .plane-icon { font-size: 32px; }

            /* Área branca estica para preencher o espaço */
            .white-area { 
                flex: 1; 
                background: #fdfdfd; 
                margin: 0 10px; 
                position: relative; 
                display: flex; 
                padding: 15px; 
                border-radius: 4px;
            }
            
            .stamp { 
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-12deg);
                border: 3px double #d32f2f; color: #d32f2f; padding: 5px 10px; 
                font-weight: 900; font-size: 24px; opacity: 0; transition: 0.3s; z-index: 10; pointer-events: none;
            }
            .stamp.visible { opacity: 0.25; }

            .col-left { flex: 1.6; border-right: 1px dashed #ddd; padding-right: 10px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 10px; display: flex; flex-direction: column; justify-content: space-around; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 9px; font-weight: 800; text-transform: uppercase; }
            .value { font-size: 18px; font-weight: 900; color: var(--air-blue); }
            
            #compass { font-size: 28px; color: var(--warning-gold); transition: 0.5s; display: block; }
            .barcode { height: 40px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 80%; }
            
            /* Rodapé fixo embaixo */
            .footer { padding-bottom: 15px; display: flex; flex-direction: column; align-items: center; }
            .yellow-lines { width: 100%; height: 8px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin: 10px 0; }
            .status-msg { color: var(--warning-gold); font-size: 12px; font-weight: bold; text-align: center; min-height: 15px; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CIDADE...">
            <button onclick="buscarEndereco()">OK</button>
        </div>

        <div class="main-container">
            <div class="card">
                <div class="notch notch-left"></div>
                <div class="notch notch-right"></div>
                <div class="header">
                    <span class="plane-icon">✈</span> 
                    <span>FLIGHT MANIFEST</span> 
                    <span class="plane-icon">✈</span>
                </div>
                <div class="white-area">
                    <div class="stamp" id="carimbo">VISUAL CONTACT</div>
                    <div class="col-left">
                        <div><div class="label">CALLSIGN</div><div id="callsign" class="value">SEARCH...</div></div>
                        <div><div class="label">EST. ETA</div><div id="eta" class="value">-- MIN</div></div>
                        <div><div class="label">ALTITUDE</div><div id="alt" class="value">00000 FT</div></div>
                    </div>
                    <div class="col-right">
                        <div class="label">RANGE/BEARING</div>
                        <div class="value"><span id="dist">0.0</span><small>KM</small></div>
                        <span id="compass">↑</span>
                        <div class="barcode"></div>
                        <div id="signal" style="color:var(--air-blue); font-weight:bold; font-size: 10px;">[ ▯▯▯▯▯ ]</div>
                    </div>
                </div>
                <div class="footer">
                    <div class="yellow-lines"></div>
                    <div id="status" class="status-msg">INITIALIZING...</div>
                </div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null, targetLock = false;
            let weatherData = { temp: "--", vis: "--", desc: "SCAN" };

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude; iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
            };

            function iniciarRadar() {
                executarBusca();
                setInterval(executarBusca, 10000);
                let msgIdx = 0;
                setInterval(() => {
                    const statusEl = document.getElementById('status');
                    const msgs = targetLock ? 
                        ["TARGET LOCKED", "VISIBILITY: "+weatherData.vis+"KM", "TEMP: "+weatherData.temp+"°C"] :
                        ["SCANNING AIRSPACE", "RADAR ACTIVE", "WEATHER: "+weatherData.desc];
                    statusEl.innerText = msgs[msgIdx % msgs.length];
                    msgIdx++;
                }, 3000);
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    weatherData = data.weather;
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('carimbo').classList.add('visible');
                        if(!targetLock) audioAlerta.play().catch(()=>{});
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('carimbo').classList.remove('visible');
                    }
                });
            }

            async function buscarEndereco() {
                const q = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${q}`);
                const data = await res.json();
                if(data.length > 0) { 
                    latAlvo = data[0].lat; lonAlvo = data[0].lon; 
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
    lat_u, lon_u = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    weather = {"temp": "--", "vis": "--", "desc": "N/A"}
    try:
        wr = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat_u}&longitude={lon_u}&current=temperature_2m,visibility,weather_code", timeout=2).json()
        weather = {"temp": round(wr['current']['temperature_2m']), "vis": round(wr['current']['visibility']/1000, 1), "desc": "CLEAR" if wr['current']['weather_code']==0 else "CLOUDY"}
    except: pass
    try:
        r = requests.get(f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}", timeout=3).json()
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({"found": True, "callsign": ac.get('flight', 'UNKN').strip(), "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), "alt": ac.get('alt_baro', 0)/3.28, "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']), "speed": round(ac.get('gs', 0)*1.852), "weather": weather})
    except: pass
    return jsonify({"found": False, "weather": weather})

if __name__ == '__main__':
    app.run(debug=True)






















