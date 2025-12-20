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
        <title>Boarding Board Radar</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --main-blue: #2A6E91; --text-gray: #777; --warning-yellow: #FFD700; }
            body { background: #f0f2f5; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; }
            
            /* Barra de busca superior */
            .search-box {
                background: white; width: 90%; max-width: 850px; padding: 10px 20px;
                border-radius: 12px; display: flex; align-items: center; gap: 10px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 25px;
            }
            .search-box input { flex: 1; border: 1px solid #ddd; padding: 12px; border-radius: 8px; outline: none; }
            .search-box button { background: var(--main-blue); color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }

            /* Cartão de Embarque */
            .boarding-pass {
                background: white; width: 90%; max-width: 850px; height: 420px;
                border-radius: 25px; display: flex; overflow: hidden;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); position: relative;
            }

            /* Lateral Esquerda (Canhoto Azul) */
            .side-panel { background: var(--main-blue); width: 250px; color: white; padding: 30px 25px; display: flex; flex-direction: column; border-right: 2px dashed rgba(255,255,255,0.3); }
            .side-label { font-size: 0.7em; opacity: 0.8; margin-bottom: 5px; text-transform: uppercase; font-weight: bold; }
            .seat-num { font-size: 5.5em; font-weight: bold; margin: 15px 0; line-height: 1; }
            .dots { display: flex; gap: 4px; margin-bottom: auto; }
            .dot { width: 10px; height: 10px; background: rgba(255,255,255,0.2); border-radius: 2px; }

            /* Lado Direito (Conteúdo) */
            .main-content { flex: 1; display: flex; flex-direction: column; }
            .top-bar { background: var(--main-blue); color: white; padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
            .top-bar h1 { margin: 0; font-size: 1.6em; letter-spacing: 8px; font-weight: normal; }

            .info-grid { padding: 30px 45px; display: grid; grid-template-columns: 1.5fr 1fr; flex: 1; position: relative; }
            .data-label { color: var(--text-gray); font-size: 0.75em; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
            .data-value { font-size: 1.9em; font-weight: bold; color: var(--warning-yellow); margin-bottom: 25px; font-family: 'Courier New', monospace; }
            .data-value.dark { color: #333; font-size: 1.4em; }

            /* Divider Vertical */
            .divider { border-left: 1px solid #eee; height: 70%; position: absolute; left: 60%; top: 15%; }

            /* Bússola e Barcode */
            .right-visuals { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
            #compass { font-size: 2.5em; transition: transform 0.8s ease; color: #ff8c00; margin-bottom: 15px; }
            #barcode { width: 150px; height: 60px; }

            /* Rodapé Preto */
            .footer-black { background: #000; height: 60px; display: flex; align-items: center; justify-content: center; border-top: 4px solid var(--warning-yellow); }
            .status-msg { color: var(--warning-yellow); font-weight: bold; font-family: 'Courier New', monospace; font-size: 1.1em; text-transform: uppercase; }
            
            @media (max-width: 700px) {
                .boarding-pass { height: auto; flex-direction: column; }
                .side-panel { width: 100%; height: auto; border-right: none; border-bottom: 2px dashed #ccc; }
                .divider { display: none; }
                .info-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="search-box">
            <input type="text" placeholder="Enter City or Location...">
            <button>CONNECT RADAR</button>
        </div>

        <div class="boarding-pass">
            <div class="side-panel">
                <div class="side-label">Radar Base</div>
                <div class="side-label" style="margin-top:10px">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="dots">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div>
                </div>
                <div class="side-label" style="margin-top: auto;">ATC Secure</div>
            </div>

            <div class="main-content">
                <div class="top-bar">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>

                <div class="info-grid">
                    <div class="left-data">
                        <div class="data-label">IDENT / CALLSIGN</div>
                        <div id="callsign" class="data-value">READY</div>

                        <div class="data-label">AIRCRAFT DISTANCE</div>
                        <div id="dist_body" class="data-value dark">--- KM</div>

                        <div class="data-label">ALTITUDE (MSL)</div>
                        <div id="alt" class="data-value dark">--- FT</div>
                    </div>

                    <div class="divider"></div>

                    <div class="right-visuals">
                        <div class="data-label">TYPE</div>
                        <div id="type" class="data-value dark" style="margin-bottom:10px">----</div>
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>

                <div class="footer-black">
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
                        JsBarcode("#barcode", data.callsign, { format: "CODE128", width: 1.2, height: 40, displayValue: false, lineColor: "#2A6E91" });
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
