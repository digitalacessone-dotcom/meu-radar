from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Visual Radar Pro - Campos</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; }
            
            #search-box { display: none; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--warning-gold); width: 90%; max-width: 600px; gap: 10px; }
            input { flex: 1; background: #000; border: 1px solid #333; padding: 12px; color: white; border-radius: 5px; outline: none; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: bold; cursor: pointer; border-radius: 5px; }

            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 25px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; padding-bottom: 20px; }
            
            /* AVIÕES LATERAIS GRANDES */
            .header { padding: 25px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 3px; }
            .plane-icon { font-size: 3em; line-height: 0; }

            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 280px; border-radius: 2px; }
            
            .stamp { position: absolute; top: 50%; left: 45%; transform: translate(-50%, -50%) rotate(-12deg) scale(5); border: 4px double #d32f2f; color: #d32f2f; padding: 10px 20px; font-weight: 900; font-size: 1.8em; opacity: 0; transition: 0.4s; pointer-events: none; }
            .stamp.visible { opacity: 0.25; transform: translate(-50%, -50%) rotate(-12deg) scale(1); }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.7em; font-weight: 800; text-transform: uppercase; }
            .value { font-size: 1.7em; font-weight: 900; color: var(--air-blue); margin-bottom: 10px; }
            
            #compass { display: inline-block; transition: 0.5s; font-size: 1.5em; color: var(--warning-gold); }
            .barcode { height: 60px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; }
            .status-msg { color: var(--warning-gold); text-align: center; font-weight: bold; margin-top: 15px; font-size: 0.9em; text-transform: uppercase; }
        </style>
    </head>
    <body onclick="audioAlerta.play().catch(()=>{})">
        <div id="search-box">
            <input type="text" id="endereco" placeholder="DIGITE CIDADE OU COORDENADAS...">
            <button onclick="buscarEndereco()">ATIVAR RADAR</button>
        </div>

        <div class="card">
            <div class="header">
                <span class="plane-icon">✈</span> 
                <span>FLIGHT MANIFEST</span> 
                <span class="plane-icon">✈</span>
            </div>
            <div class="white-area">
                <div class="stamp" id="carimbo">VISUAL CONTACT</div>
                <div class="col-left">
                    <div><div class="label">CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">ETA</div><div id="eta" class="value">-- MIN</div></div>
                    <div><div class="label">ALTITUDE</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">RANGE/BEARING</div>
                    <div class="value"><span id="dist">0.0 KM</span> <span id="compass">↑</span></div>
                    <div class="barcode"></div>
                    <div id="status" class="status-msg">SCANNING...</div>
                </div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude; iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
            };

            function iniciarRadar() { executarBusca(); setInterval(executarBusca, 10000); }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('status').innerText = "TARGET LOCKED";
                        document.getElementById('carimbo').classList.add('visible');
                    } else {
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('status').innerText = "SCANNING...";
                        document.getElementById('carimbo').classList.remove('visible');
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
    ''')

@app.route('/api/data')
def get_data():
    lat_u, lon_u = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    try:
        r = requests.get(f"https://api.adsb.one/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}", timeout=5).json()
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1),
                "alt": ac.get('alt_baro', 0) / 3.28,
                "bearing": int(calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon'])),
                "speed": round(ac.get('gs', 0) * 1.852)
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)




















