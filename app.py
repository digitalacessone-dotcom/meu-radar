from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 120.0 
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X)"]

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
            
            body { 
                background-color: var(--bg-dark); 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                margin: 0; 
                font-family: 'Courier New', monospace; 
                overflow: hidden; 
            }
            
            /* CONTENT WRAPPER PARA ESCALA */
            #scaler {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                transition: transform 0.3s ease;
            }

            .card { 
                background: var(--air-blue); 
                width: 92%; 
                max-width: 600px; 
                border-radius: 25px; 
                position: relative; 
                box-shadow: 0 30px 60px rgba(0,0,0,0.7); 
                overflow: hidden; 
            }

            /* AJUSTE PARA TELA DEITADA (LANDSCAPE) */
            @media (orientation: landscape) and (max-height: 500px) {
                #scaler { transform: scale(0.85); } /* Diminui o bilhete para caber na altura */
                .header { padding: 10px 0 !important; }
                .white-area { padding: 15px 30px !important; min-height: 180px !important; }
                .footer { padding-bottom: 10px !important; }
            }

            .notch { position: absolute; width: 40px; height: 40px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -20px; } .notch-right { right: -20px; }

            .header { padding: 25px 0; text-align: center; color: white; font-weight: 900; letter-spacing: 5px; font-size: 1.1em; }
            
            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 250px; border-radius: 2px; }
            
            .tear-line { position: absolute; right: 35%; top: 0; bottom: 0; border-right: 2px dashed #eee; z-index: 5; }
            .tear-line.active { border-right-color: var(--warning-gold); animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0.2; } }

            .stamp { 
                position: absolute; top: 50%; left: 35%; transform: translate(-50%, -50%) rotate(-15deg) scale(4); 
                border: 4px double #d32f2f; color: #d32f2f; padding: 8px 15px; font-weight: 900; font-size: 1.6em; 
                opacity: 0; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); z-index: 10; pointer-events: none;
            }
            .stamp.visible { opacity: 0.35; transform: translate(-50%, -50%) rotate(-15deg) scale(1); }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.6em; font-weight: 800; text-transform: uppercase; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); margin-bottom: 10px; }
            
            #compass { display: inline-block; transition: transform 0.5s ease; font-size: 1.2em; color: var(--warning-gold); }
            .barcode { height: 50px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 80%; margin-top: 10px; }
            
            .footer { padding: 10px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 8px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 15px; }
            .status-msg { color: var(--warning-gold); font-size: 0.8em; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; }
        </style>
    </head>
    <body onclick="audioAlerta.play().catch(()=>{})">
        <div id="scaler">
            <div class="card">
                <div class="notch notch-left"></div>
                <div class="notch notch-right"></div>
                <div class="header">✈ FLIGHT MANIFEST ✈</div>
                
                <div class="white-area">
                    <div class="tear-line" id="picote"></div>
                    <div class="stamp" id="carimbo">VISUAL CONTACT</div>
                    
                    <div class="col-left">
                        <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                        <div><div class="label">ALTITUDE (FL)</div><div id="alt" class="value">00000 FT</div></div>
                    </div>
                    <div class="col-right">
                        <div class="label">BEARING</div>
                        <div id="compass">↑</div>
                        <div id="dist" class="value" style="margin-top:5px;">0.0 KM</div>
                        <div class="barcode"></div>
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
            let latAlvo, lonAlvo, targetLock = false;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000);
                }, () => { latAlvo = -21.76; lonAlvo = -41.33; setInterval(executarBusca, 8000); });
            };

            function executarBusca() {
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = data.alt + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('status').innerText = "TARGET ACQUIRED";
                        document.getElementById('carimbo').classList.add('visible');
                        
                        if(data.dist < 15) document.getElementById('picote').classList.add('active');
                        else document.getElementById('picote').classList.remove('active');

                        if(!targetLock) audioAlerta.play().catch(()=>{});
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('carimbo').classList.remove('visible');
                        document.getElementById('picote').classList.remove('active');
                        document.getElementById('status').innerText = "SCANNING AIRSPACE...";
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u, lon_u = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        r = requests.get(f"https://api.adsb.one/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}", headers=headers, timeout=5).json()
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1),
                "alt": int(ac.get('alt_baro', 0)),
                "bearing": int(calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']))
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)


















