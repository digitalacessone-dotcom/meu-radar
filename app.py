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
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Boarding Pass</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root {
                --blue-main: #2A6E91;
                --text-gray: #888;
                --yellow-status: #FFD700;
            }
            body { 
                background: #eef1f4; 
                margin: 0; 
                display: flex; 
                flex-direction: column;
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                font-family: 'Helvetica Neue', Arial, sans-serif;
            }

            /* Container do Input superior */
            .search-container {
                width: 90%;
                max-width: 800px;
                background: white;
                padding: 10px 20px;
                border-radius: 12px;
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            }
            .search-container input {
                flex: 1;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            .search-container button {
                background: var(--blue-main);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                cursor: pointer;
            }

            /* Cartão de Embarque */
            .boarding-pass {
                width: 90%;
                max-width: 850px;
                background: white;
                border-radius: 25px;
                overflow: hidden;
                display: flex;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                position: relative;
            }

            /* Parte Esquerda (Canhoto Azul) */
            .left-stub {
                background: var(--blue-main);
                width: 28%;
                padding: 30px 20px;
                color: white;
                border-right: 2px dashed rgba(255,255,255,0.3);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }
            .stub-label { font-size: 10px; opacity: 0.8; text-transform: uppercase; font-weight: bold; }
            .seat-number { font-size: 70px; font-weight: bold; margin: 10px 0; }
            .dots { display: flex; gap: 5px; margin-bottom: 20px; }
            .dot { width: 12px; height: 12px; background: rgba(255,255,255,0.2); border-radius: 2px; }

            /* Parte Direita (Corpo Branco) */
            .right-main {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            .header-strip {
                background: var(--blue-main);
                color: white;
                padding: 15px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-strip h1 { 
                margin: 0; 
                font-size: 24px; 
                letter-spacing: 6px; 
                font-weight: normal; 
                text-transform: uppercase;
            }

            .info-grid {
                padding: 30px 45px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                flex: 1;
            }
            .data-block { margin-bottom: 20px; }
            .label { color: var(--text-gray); font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { 
                font-size: 26px; 
                font-weight: bold; 
                color: var(--yellow-status); 
                font-family: 'Courier New', monospace;
            }
            .value-dark { color: #333; font-size: 20px; }

            /* Bússola e Barcode */
            .visual-section {
                border-left: 1px solid #eee;
                padding-left: 30px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            #compass { font-size: 40px; color: #f39c12; transition: transform 0.8s ease; margin-bottom: 15px; }
            #barcode { width: 180px; height: 60px; }

            /* Footer Preto */
            .footer-status {
                background: #000;
                height: 65px;
                border-top: 4px solid var(--yellow-status);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .status-msg {
                color: var(--yellow-status);
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 18px;
                text-transform: uppercase;
            }

            @media (max-width: 600px) {
                .boarding-pass { flex-direction: column; }
                .left-stub { width: auto; height: 150px; border-right: none; border-bottom: 2px dashed #ccc; }
                .info-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>

        <div class="search-container">
            <input type="text" placeholder="Enter City or Location...">
            <button>CONNECT RADAR</button>
        </div>

        <div class="boarding-pass">
            <div class="left-stub">
                <div>
                    <div class="stub-label">Radar Base</div>
                    <div class="stub-label">Seat:</div>
                    <div class="seat-number">19 A</div>
                    <div class="dots">
                        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    </div>
                </div>
                <div class="stub-label">ATC Secure</div>
            </div>

            <div class="right-main">
                <div class="header-strip">
                    <span>✈</span>
                    <h1>Boarding Board</h1>
                    <span>✈</span>
                </div>

                <div class="info-grid">
                    <div class="data-container">
                        <div class="data-block">
                            <div class="label">Ident / Callsign</div>
                            <div id="callsign" class="value">READY</div>
                        </div>
                        <div class="data-block">
                            <div class="label">Aircraft Distance</div>
                            <div id="dist_body" class="value value-dark">--- KM</div>
                        </div>
                        <div class="data-block">
                            <div class="label">Altitude (MSL)</div>
                            <div id="alt" class="value value-dark">--- FT</div>
                        </div>
                    </div>

                    <div class="visual-section">
                        <div class="data-block" style="text-align: center;">
                            <div class="label">Type</div>
                            <div id="type" class="value value-dark">----</div>
                        </div>
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>

                <div class="footer-status">
                    <div id="status" class="status-msg">INITIALIZING RADAR...</div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo, lonAlvo;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000); executarBusca();
                }, () => { 
                    document.getElementById('status').textContent = "ERROR: ENABLE GPS"; 
                });
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=` + Date.now())
                .then(res => res.json()).then(data => {
                    const statusElem = document.getElementById('status');
                    if(data.found) {
                        document.getElementById('callsign').textContent = data.callsign;
                        document.getElementById('dist_body').textContent = data.dist + " KM";
                        document.getElementById('alt').textContent = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('type').textContent = data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        statusElem.textContent = "TARGET ACQUIRED: " + data.callsign;

                        JsBarcode("#barcode", data.callsign, {
                            format: "CODE128", width: 1.2, height: 40, displayValue: false, lineColor: "#2A6E91"
                        });
                    } else {
                        statusElem.textContent = "SCANNING AIRSPACE...";
                        document.getElementById('callsign').textContent = "READY";
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
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=5).json()
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
                    "type": ac.get('t', 'UNKN')
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
