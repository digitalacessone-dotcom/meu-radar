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
            :root { --blue: #2A6E91; --yellow: #FFD700; --text-gray: #999; }
            body { background: #f4f7f9; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; }
            
            /* Barra de busca superior separada */
            .search-header {
                background: white; width: 90%; max-width: 850px; padding: 12px 20px;
                border-radius: 12px; display: flex; gap: 10px; margin-bottom: 25px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05); align-items: center;
            }
            .search-header input { flex: 1; border: 1px solid #ddd; padding: 12px; border-radius: 8px; outline: none; }
            .search-header button { background: var(--blue); color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; }

            /* Estrutura do Cartão */
            .ticket {
                background: white; width: 90%; max-width: 850px; height: 420px;
                border-radius: 25px; display: flex; overflow: hidden;
                box-shadow: 0 20px 50px rgba(0,0,0,0.1);
            }

            /* Canhoto Azul */
            .stub {
                background: var(--blue); width: 220px; color: white; padding: 30px;
                display: flex; flex-direction: column; border-right: 2px dashed rgba(255,255,255,0.3);
            }
            .stub-label { font-size: 0.7em; opacity: 0.7; font-weight: bold; text-transform: uppercase; }
            .seat-num { font-size: 5.5em; font-weight: bold; margin: 10px 0; }
            .dot-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 10px; }
            .dot { width: 12px; height: 12px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            .atc-text { margin-top: auto; font-size: 1em; opacity: 0.9; }

            /* Corpo Principal */
            .main { flex: 1; display: flex; flex-direction: column; }
            .top-strip { background: var(--blue); color: white; padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; }
            .top-strip h1 { margin: 0; font-size: 1.6em; letter-spacing: 10px; font-weight: 300; }

            .info-area { padding: 30px 45px; display: flex; flex: 1; }
            .data-col { flex: 1.5; }
            .visual-col { flex: 1; border-left: 1px solid #eee; display: flex; flex-direction: column; align-items: center; justify-content: space-around; padding-left: 20px; }

            .label { color: var(--text-gray); font-size: 0.7em; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
            .value-y { color: var(--yellow); font-size: 2em; font-weight: bold; font-family: 'Courier New', monospace; margin-bottom: 25px; }
            .value-d { color: #333; font-size: 1.3em; font-weight: bold; margin-bottom: 25px; }

            #compass { font-size: 2.5em; transition: transform 0.6s ease; color: #ff8c00; }
            #barcode { width: 160px; height: 60px; }

            /* Rodapé Preto e Amarelo */
            .footer { background: #000; height: 65px; border-top: 4px solid var(--yellow); display: flex; align-items: center; justify-content: center; }
            .status { color: var(--yellow); font-family: 'Courier New', monospace; font-weight: bold; font-size: 1.1em; text-transform: uppercase; }

            @media (max-width: 600px) {
                .ticket { flex-direction: column; height: auto; }
                .stub { width: auto; border-right: none; border-bottom: 2px dashed #ddd; }
                .info-area { flex-direction: column; }
                .visual-col { border-left: none; border-top: 1px solid #eee; padding: 20px 0; }
            }
        </style>
    </head>
    <body>
        <div class="search-header">
            <input type="text" placeholder="Enter City or Location...">
            <button>CONNECT RADAR</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div class="stub-label">Radar Base</div>
                <div class="stub-label" style="margin-top:10px">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="dot-grid">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
                <div class="atc-text">ATC Secure</div>
            </div>

            <div class="main">
                <div class="top-strip">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>
                <div class="info-area">
                    <div class="data-col">
                        <div class="label">Ident / Callsign</div>
                        <div id="callsign" class="value-y">READY</div>
                        <div class="label">Aircraft Distance</div>
                        <div id="dist_body" class="value-d">--- KM</div>
                        <div class="label">Altitude (MSL)</div>
                        <div id="alt" class="value-d">--- FT</div>
                    </div>
                    <div class="visual-col">
                        <div class="label">Type</div>
                        <div id="type" class="value-d" style="margin-bottom:10px">----</div>
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>
                <div class="footer">
                    <div id="status" class="status">INITIALIZING RADAR...</div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo, lonAlvo;
            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000); executarBusca();
                }, () => { document.getElementById('status').textContent = "ERROR: ENABLE GPS"; });
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
