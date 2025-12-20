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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
        <title>Boarding Board Radar</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --main-blue: #2A6E91; --text-gray: #777; --warning-yellow: #FFD700; }
            body { background: #f0f2f5; margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; }
            
            .boarding-pass {
                background: white; width: 95%; max-width: 800px; height: 400px;
                border-radius: 25px; display: flex; overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1); position: relative;
            }

            /* Lado Esquerdo (Azul) */
            .side-panel { background: var(--main-blue); width: 25%; color: white; padding: 30px 20px; display: flex; flex-direction: column; border-right: 2px dashed rgba(255,255,255,0.3); }
            .side-label { font-size: 0.7em; opacity: 0.8; margin-bottom: 5px; }
            .seat-num { font-size: 5em; font-weight: bold; margin: 0; }
            .atc-secure { margin-top: auto; font-size: 0.9em; }

            /* Lado Direito (Branco) */
            .main-content { flex: 1; display: flex; flex-direction: column; }
            .top-bar { background: var(--main-blue); color: white; padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
            .top-bar h1 { margin: 0; font-size: 1.5em; letter-spacing: 8px; font-weight: normal; }

            .info-grid { padding: 30px 40px; display: grid; grid-template-columns: 1.5fr 1fr; flex: 1; }
            .data-label { color: var(--text-gray); font-size: 0.75em; font-weight: bold; margin-bottom: 5px; }
            .data-value { font-size: 1.8em; font-weight: bold; color: var(--warning-yellow); margin-bottom: 25px; font-family: 'Courier New', monospace; }
            .data-value.dark { color: var(--main-blue); font-size: 1.3em; }

            /* Rodapé Preto */
            .footer-black { background: #000; height: 60px; display: flex; align-items: center; justify-content: center; border-top: 4px solid var(--warning-yellow); }
            .status-msg { color: var(--warning-yellow); font-weight: bold; font-family: 'Courier New', monospace; font-size: 1.1em; }

            /* Bússola e Barcode */
            #compass { display: inline-block; font-size: 2em; transition: transform 0.6s ease; color: #ff8c00; }
            .barcode-area { text-align: right; }
            #barcode { width: 150px; height: 60px; }
            
            @media (max-width: 600px) {
                .boarding-pass { height: auto; flex-direction: column; }
                .side-panel { width: 100%; height: 150px; border-right: none; border-bottom: 2px dashed #ccc; }
                .info-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="boarding-pass">
            <div class="side-panel">
                <div class="side-label">RADAR BASE</div>
                <div class="side-label">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="atc-secure">ATC Secure</div>
            </div>

            <div class="main-content">
                <div class="top-bar">
                    <span>✈</span>
                    <h1>BOARDING BOARD</h1>
                    <span>✈</span>
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

                    <div class="right-data">
                        <div class="data-label">TYPE</div>
                        <div id="type" class="data-value dark">----</div>
                        
                        <div class="data-label">BEARING</div>
                        <div id="compass">↑</div>

                        <div class="barcode-area">
                            <svg id="barcode"></svg>
                        </div>
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
                    setInterval(executarBusca, 8000); 
                    executarBusca();
                }, () => { 
                    document.getElementById('status').textContent = "ERROR: ENABLE GPS"; 
                });
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=` + Date.now())
                .then(res => res.json())
                .then(data => {
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
                        document.getElementById('callsign').textContent = "SEARCHING";
                        document.getElementById('barcode').innerHTML = "";
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
                    "type": ac.get('t', 'UNKN'),
                    "speed": ac.get('gs', 0)
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
