from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 25.0
API_OPENSKY = "https://opensky-network.org/api/states/all"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calcula o ângulo para a bússola"""
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Smart Flight Ticket 25KM</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; overflow-x: hidden; }
            
            #search-box { display: none; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--warning-gold); width: 90%; max-width: 550px; gap: 10px; }
            input { flex: 1; background: #000; border: 1px solid #333; padding: 12px; color: white; font-weight: bold; outline: none; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; }

            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 25px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; }
            .notch { position: absolute; width: 44px; height: 44px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -22px; } .notch-right { right: -22px; }

            .header { padding: 25px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 5px; font-size: 1.2em; }
            .header span { font-size: 2.2em; }

            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 260px; border-radius: 2px; }
            .white-area::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; background-image: linear-gradient(to right, #ccc 40%, transparent 40%); background-size: 14px 100%; }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.6em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; }
            
            #compass { display: inline-block; transition: transform 0.5s ease; font-size: 1.2em; color: var(--warning-gold); }
            .signal-bar { font-size: 10px; color: #1A237E; font-weight: bold; margin-top: 5px; }

            .barcode { height: 60px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; }
            
            .footer { padding: 10px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 10px; border-top: 2.5px solid var(--warning-gold); border-bottom: 2.5px solid var(--warning-gold); margin-bottom: 20px; }
            .status-msg { color: var(--warning-gold); font-size: 0.9em; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; text-align: center; }

            @media (max-height: 500px) and (orientation: landscape) {
                .card { transform: scale(0.72); margin-top: -50px; }
                .white-area { min-height: 200px; padding: 15px 30px; }
            }
        </style>
    </head>
    <body onclick="audioAlerta.play().catch(()=>{})">
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="ENTER ZIP CODE OR CITY...">
            <button onclick="buscarEndereco()">ACTIVATE</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header"><span>✈</span> FLIGHT MANIFEST / PASS <span>✈</span></div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENTIFICATION / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">ETA TO VISUAL CONTACT</div><div id="eta" class="value">-- MIN</div></div>
                    <div><div class="label">PRESSURE ALTITUDE (FL)</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">RANGE & BEARING</div>
                    <div class="value"><span id="dist">0.0 KM</span> <span id="compass">↑</span></div>
                    <div class="barcode"></div>
                    <div id="signal" class="signal-bar">SIGNAL: [ ▯▯▯▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">SCANNING LIVE AIRSPACE...</div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ";
            let latAlvo = null, lonAlvo = null;
            let targetLock = false;

            function splitFlap(text) {
                const el = document.getElementById('status');
                let i = 0;
                const inter = setInterval(() => {
                    el.innerText = text.split('').map((c, idx) => i > idx ? c : chars[Math.floor(Math.random()*chars.length)]).join('');
                    if(i++ > text.length) clearInterval(inter);
                }, 30);
            }

            function alertBeepFiveTimes() {
                let count = 0;
                const interval = setInterval(() => {
                    audioAlerta.play().catch(() => {});
                    count++;
                    if (count >= 5) clearInterval(interval);
                }, 1000);
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
            };

            function iniciarRadar() {
                executarBusca();
                setInterval(executarBusca, 10000);
                setInterval(() => {
                    if(!targetLock) {
                        const cycle = ["SCANNING LIVE AIRSPACE", "RADAR ACTIVE"];
                        splitFlap(cycle[Math.floor(Math.random() * cycle.length)]);
                    }
                }, 5000);
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        // Cálculo de Sinal
                        let bars = Math.ceil((25 - data.dist) / 5);
                        document.getElementById('signal').innerText = "SIGNAL: [" + "▮".repeat(bars) + "▯".repeat(5-bars) + "]";
                        
                        // Cálculo ETA (Simplificado: distância / velocidade)
                        let eta = data.velocity > 0 ? Math.round((data.dist / (data.velocity * 3.6)) * 60) : "--";
                        document.getElementById('eta').innerText = eta + " MIN";

                        if (!targetLock) { alertBeepFiveTimes(); splitFlap("TARGET LOCKED"); }
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('eta').innerText = "-- MIN";
                        document.getElementById('signal').innerText = "SIGNAL: [ ▯▯▯▯▯ ]";
                        document.getElementById('compass').style.transform = `rotate(0deg)`;
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
    try:
        r = requests.get(API_OPENSKY, timeout=4).json()
        for s in r.get('states', []):
            if s[6] and s[5]:
                d = haversine(lat_u, lon_u, s[6], s[5])
                if d <= RAIO_KM:
                    b = calculate_bearing(lat_u, lon_u, s[6], s[5])
                    return jsonify({
                        "found": True, "callsign": s[1].strip() or "ACFT", 
                        "dist": round(d, 1), "alt": s[7] or 0, 
                        "bearing": b, "velocity": s[9] or 0
                    })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)








