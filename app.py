from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# --- CONFIGURAÇÕES DO SERVIDOR ---
RAIO_KM = 120.0  
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]

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

# --- INTERFACE VISUAL (HTML/CSS/JS) ---
html_template = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Visual Radar Pro - Campos</title>
    <style>
        :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
        body { 
            background-color: var(--bg-dark); 
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            height: 100vh; margin: 0; font-family: 'Courier New', monospace; overflow: hidden; 
        }
        #search-box { 
            display: none; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 12px; 
            margin-bottom: 5px; border: 1px solid var(--warning-gold); width: 90%; max-width: 450px; gap: 10px; z-index: 100; 
        }
        input { flex: 1; background: #000; border: 1px solid #333; padding: 10px; color: white; outline: none; border-radius: 5px; font-family: inherit; }
        #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px; font-weight: 900; cursor: pointer; border-radius: 5px; }

        #scaler { height: 92vh; aspect-ratio: 4 / 5; display: flex; justify-content: center; align-items: center; }
        .card { background: var(--air-blue); width: 100%; height: 100%; border-radius: 4vh; position: relative; display: flex; flex-direction: column; box-shadow: 0 30px 60px rgba(0,0,0,0.7); }
        .notch { position: absolute; width: 6vh; height: 6vh; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
        .notch-left { left: -3vh; } .notch-right { right: -3vh; }

        .header { flex: 0.15; display: flex; justify-content: center; align-items: center; color: white; gap: 2.5vh; font-weight: 900; letter-spacing: 0.5vh; font-size: 2vh; }
        .plane-icon { font-size: 5vh; line-height: 0; }

        .white-area { flex: 0.65; background: #fdfdfd; margin: 0 1.5vh; position: relative; display: flex; padding: 2.5vh; border-radius: 2px; }
        .tear-line { position: absolute; right: 35%; top: 0; bottom: 0; border-right: 2px dashed #eee; z-index: 5; transition: 0.3s; }
        .tear-line.active { border-right-color: var(--warning-gold); box-shadow: -2px 0 15px var(--warning-gold); animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0.3; } }

        .stamp { position: absolute; top: 50%; left: 45%; transform: translate(-50%, -50%) rotate(-12deg) scale(5); border: 0.5vh double #d32f2f; color: #d32f2f; padding: 1vh 2vh; font-weight: 900; font-size: 3.5vh; opacity: 0; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); z-index: 10; pointer-events: none; }
        .stamp.visible { opacity: 0.25; transform: translate(-50%, -50%) rotate(-12deg) scale(1); }

        .col-left { flex: 1.8; border-right: 0.2vh dashed #eee; padding-right: 2vh; display: flex; flex-direction: column; justify-content: space-around; }
        .col-right { flex: 1; padding-left: 2vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
        .label { color: #999; font-size: 1.1vh; font-weight: 800; text-transform: uppercase; }
        .value { font-size: 2.8vh; font-weight: 900; color: var(--air-blue); margin-bottom: 1.5vh; }
        #compass { display: inline-block; transition: transform 0.5s ease; font-size: 3.5vh; color: var(--warning-gold); }
        .barcode { height: 6vh; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 1vh 0; }
        
        .footer { flex: 0.2; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--air-blue); padding-bottom: 1.5vh; }
        .yellow-lines { width: 100%; height: 1.1vh; border-top: 0.3vh solid var(--warning-gold); border-bottom: 0.3vh solid var(--warning-gold); margin-bottom: 1vh; }
        .status-msg { color: var(--warning-gold); font-size: 1.5vh; font-weight: bold; letter-spacing: 0.2vh; text-transform: uppercase; text-align: center; }
    </style>
</head>
<body onclick="audioAlerta.play().catch(()=>{})">
    <div id="search-box">
        <input type="text" id="endereco" placeholder="DIGITE A CIDADE...">
        <button onclick="buscarEndereco()">ATIVAR</button>
    </div>
    <div id="scaler">
        <div class="card">
            <div class="notch notch-left"></div><div class="notch notch-right"></div>
            <div class="header"><span class="plane-icon">✈</span><span>FLIGHT MANIFEST</span><span class="plane-icon">✈</span></div>
            <div class="white-area">
                <div class="tear-line" id="picote"></div>
                <div class="stamp" id="carimbo">VISUAL CONTACT</div>
                <div class="col-left">
                    <div><div class="label">IDENTIFICATION / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">ESTIMATED VISUAL (ETA)</div><div id="eta" class="value">-- MIN</div></div>
                    <div><div class="label">ALTITUDE / PRESSURE</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">RANGE & BEARING</div>
                    <div class="value"><span id="dist">0.0 KM</span> <div id="compass">↑</div></div>
                    <div class="barcode"></div>
                    <div id="clima" style="color:var(--air-blue); font-weight:bold; font-size:1.3vh;">--°C <br> VIS: -- KM</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">SCANNING AIRSPACE...</div>
            </div>
        </div>
    </div>
    <script>
        const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
        let latAlvo = null, lonAlvo = null, targetLock = false;
        window.onload = function() {
            const gpsWait = setTimeout(() => { if(!latAlvo) document.getElementById('search-box').style.display = "flex"; }, 4000);
            navigator.geolocation.getCurrentPosition(pos => {
                clearTimeout(gpsWait); latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude; iniciarRadar();
            }, () => { document.getElementById('search-box').style.display = "flex"; });
        };
        function iniciarRadar() { executarBusca(); setInterval(executarBusca, 10000); }
        function executarBusca() {
            if(!latAlvo) return;
            fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`).then(res => res.json()).then(data => {
                if(data.found) {
                    document.getElementById('callsign').innerText = data.callsign;
                    document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                    document.getElementById('dist').innerText = data.dist + " KM";
                    document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                    document.getElementById('clima').innerHTML = data.temp + "°C <br> VIS: " + data.vis + " KM";
                    document.getElementById('eta').innerText = (data.speed > 0 ? Math.round((data.dist / data.speed) * 60) : "--") + " MIN";
                    document.getElementById('carimbo').classList.add('visible');
                    if(data.dist < 15) document.getElementById('picote').classList.add('active');
                    document.getElementById('status').innerText = "TARGET ACQUIRED: " + data.callsign;
                    if(!targetLock) audioAlerta.play().catch(()=>{});
                    targetLock = true;
                } else {
                    targetLock = false;
                    document.getElementById('callsign').innerText = "SEARCHING";
                    document.getElementById('carimbo').classList.remove('visible');
                    document.getElementById('status').innerText = "SCANNING AIRSPACE...";
                }
            });
        }
        async function buscarEndereco() {
            const q = document.getElementById('endereco').value;
            const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${q}`);
            const data = await res.json();
            if(data.length > 0) { latAlvo = data[0].lat; lonAlvo = data[0].lon; document.getElementById('search-box').style.display = "none"; iniciarRadar(); }
        }
    </script>
</body>
</html>
'''

# --- ROTAS DO FLASK ---
@app.route('/')
def index():
    return render_template_string(html_template)

@app.route('/api/data')
def get_data():
    lat_u, lon_u = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    try:
        r = requests.get(f"https://api.adsb.one/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}", timeout=5).json()
        temp, vis = random.randint(26, 31), random.randint(12, 22)
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            dist = haversine(lat_u, lon_u, ac['lat'], ac['lon'])
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(dist, 1), "alt": ac.get('alt_baro', 0) / 3.28,
                "bearing": int(calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon'])),
                "speed": round(ac.get('gs', 0) * 1.852), "temp": temp, "vis": vis
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)




















