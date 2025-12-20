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
        <style>
            :root { --blue-bg: #2B6B8F; --text-gray: #888; --gold: #FFD700; }
            body { background: #E0E5EC; margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; }
            
            .boarding-pass {
                background: white; width: 95%; max-width: 800px;
                border-radius: 20px; overflow: hidden;
                box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                display: flex; flex-direction: column;
            }

            .main-ticket { display: flex; flex: 1; min-height: 320px; }

            /* Canhoto Esquerdo (Stub) */
            .stub { 
                background: var(--blue-bg); width: 30%; color: white; padding: 25px;
                border-right: 2px dashed rgba(255,255,255,0.3);
                display: flex; flex-direction: column; justify-content: space-between;
            }
            .seat-label { font-size: 0.8em; opacity: 0.8; }
            .seat-num { font-size: 5em; font-weight: bold; margin: 10px 0; }
            
            /* Quadradinhos de Proximidade */
            .proximity-bars { display: flex; gap: 4px; margin-top: 10px; }
            .bar { width: 12px; height: 12px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            .bar.active { background: white; box-shadow: 0 0 8px white; }

            /* Parte Principal */
            .info-area { flex: 1; display: flex; flex-direction: column; }
            .blue-header { background: var(--blue-bg); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
            .blue-header h2 { margin: 0; font-size: 1.2em; letter-spacing: 5px; font-weight: normal; }

            .white-content { padding: 30px; flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; position: relative; }
            .field { margin-bottom: 20px; }
            .label { color: var(--text-gray); font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { color: #222; font-size: 1.4em; font-weight: bold; }
            .value.highlight { color: #E6B100; font-size: 1.8em; }

            #compass { display: inline-block; transition: transform 0.6s ease; font-size: 1.5em; color: #E67E22; }

            /* Faixa Preta Inferior */
            .black-footer { 
                background: #000; padding: 12px 30px; 
                border-top: 4px solid var(--gold);
                min-height: 50px; display: flex; align-items: center;
            }
            .status-msg { 
                color: var(--gold) !important; font-family: monospace; 
                font-weight: bold; text-transform: uppercase; letter-spacing: 2px;
                display: block !important;
            }

            @media (max-width: 600px) {
                .main-ticket { flex-direction: column; }
                .stub { width: auto; border-right: none; border-bottom: 2px dashed #ccc; }
                .white-content { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="boarding-pass">
            <div class="main-ticket">
                <div class="stub">
                    <div>
                        <div class="seat-label">RADAR BASE<br>Seat:</div>
                        <div class="seat-num">19 A</div>
                        <div class="proximity-bars" id="proximity">
                            <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            <div class="bar"></div><div class="bar"></div>
                        </div>
                    </div>
                    <div style="font-size: 0.8em; opacity: 0.7;">ATC Secure</div>
                </div>

                <div class="info-area">
                    <div class="blue-header">
                        <span>✈</span>
                        <h2>BOARDING BOARD</h2>
                        <span>✈</span>
                    </div>
                    <div class="white-content">
                        <div>
                            <div class="field">
                                <div class="label">Ident / Callsign</div>
                                <div id="callsign" class="value highlight">READY</div>
                            </div>
                            <div class="field">
                                <div class="label">Aircraft Distance</div>
                                <div id="dist" class="value">---</div>
                            </div>
                            <div class="field">
                                <div class="label">Altitude (MSL)</div>
                                <div id="alt" class="value">---</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div class="field">
                                <div class="label">Type</div>
                                <div id="type" class="value">----</div>
                            </div>
                            <div class="field">
                                <div id="compass" class="value">↑</div>
                            </div>
                            <a id="map-link" target="_blank" style="display:inline-block; margin-top:10px; opacity:0.3;">
                                <svg id="barcode" style="width:120px; height:60px;"></svg>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="black-footer">
                <div id="status" class="status-msg">INITIALIZING RADAR SYSTEM...</div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <script>
            let latU, lonU;
            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latU = pos.coords.latitude; lonU = pos.coords.longitude;
                    setInterval(update, 8000); update();
                }, () => { document.getElementById('status').innerText = "ERROR: GPS DENIED"; });
            };

            function update() {
                if(!latU) return;
                fetch(`/api/data?lat=${latU}&lon=${lonU}&t=${Date.now()}`)
                .then(r => r.json()).then(data => {
                    const status = document.getElementById('status');
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('type').innerText = data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        status.innerText = "> TARGET ACQUIRED: " + data.callsign;

                        // Lógica dos quadradinhos (8 barras)
                        // Quanto menor a distância, mais barras acendem
                        let barsToLight = Math.max(1, Math.ceil((25 - data.dist) / 3.1));
                        const bars = document.querySelectorAll('.bar');
                        bars.forEach((b, i) => {
                            b.classList.toggle('active', i < barsToLight);
                        });

                        JsBarcode("#barcode", data.callsign, { format: "CODE128", displayValue: false, lineColor: "#222" });
                    } else {
                        status.innerText = "SCANNING AIRSPACE...";
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
            ac = sorted([a for a in r['ac'] if a.get('lat')], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                "alt_ft": int(ac.get('alt_baro', 0)), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN'), 
                "map_url": f"https://globe.adsbexchange.com/?lat={ac['lat']}&lon={ac['lon']}&zoom=11"
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
