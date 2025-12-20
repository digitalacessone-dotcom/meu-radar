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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Radar Boarding Pass</title>
        <style>
            :root { --air-blue: #2B7DA3; --text-gray: #555; --bg-main: #e0e5ec; }
            * { box-sizing: border-box; font-family: 'Helvetica Neue', Arial, sans-serif; }
            
            body { 
                background: var(--bg-main); margin: 0; padding: 20px;
                display: flex; align-items: center; justify-content: center; min-height: 100vh;
            }

            /* Container do Cartão */
            .boarding-pass {
                background: white; width: 100%; max-width: 800px;
                display: flex; border-radius: 15px; overflow: hidden;
                box-shadow: 10px 10px 20px rgba(0,0,0,0.1);
                position: relative;
            }

            /* Seção Esquerda (Canhoto/Stub) */
            .stub {
                background: #1e5d7b; color: white; width: 25%;
                padding: 20px; border-right: 2px dashed rgba(255,255,255,0.3);
                display: flex; flex-direction: column; justify-content: space-between;
            }
            .stub .label { color: rgba(255,255,255,0.7); font-size: 0.7em; text-transform: uppercase; }
            .stub .big-text { font-size: 3.5em; font-weight: bold; margin: 10px 0; }
            
            /* Seção Direita (Principal) */
            .main-ticket { width: 75%; padding: 0; display: flex; flex-direction: column; }
            
            .ticket-header { 
                background: var(--air-blue); color: white; padding: 15px 25px;
                display: flex; justify-content: space-between; align-items: center;
                font-weight: bold; letter-spacing: 2px;
            }

            .ticket-body { padding: 25px; flex-grow: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }

            .info-box { margin-bottom: 15px; }
            .label { color: #999; font-size: 0.75em; font-weight: bold; text-transform: uppercase; display: block; }
            .value { color: #222; font-size: 1.2em; font-weight: bold; }
            .highlight { color: #f39c12; font-size: 1.5em; }

            /* Código de Barras e Mapa */
            .barcode-area { 
                border-top: 1px solid #eee; padding: 15px 25px; 
                display: flex; justify-content: space-between; align-items: center;
                background: #fafafa;
            }
            .barcode-img { 
                height: 50px; width: 200px;
                background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 4px);
            }

            /* Status no Rodapé */
            .footer-status {
                background: #000; color: #FFD700; padding: 10px;
                text-align: center; font-family: monospace; font-size: 0.8em;
                text-transform: uppercase;
            }

            #compass { display: inline-block; transition: transform 0.6s ease; font-size: 1.5em; color: var(--air-blue); }

            @media (max-width: 600px) {
                .boarding-pass { flex-direction: column; }
                .stub { width: 100%; border-right: none; border-bottom: 2px dashed #ccc; }
                .main-ticket { width: 100%; }
                .ticket-body { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>

        <div class="boarding-pass">
            <div class="stub">
                <div>
                    <div class="label">Radar Base</div>
                    <div class="label">Seat:</div>
                    <div class="big-text">19 A</div>
                </div>
                <div>
                    <div id="signal-bars" style="letter-spacing:3px;">▯▯▯▯▯</div>
                    <div class="label" style="margin-top:10px;">ATC Secure</div>
                </div>
            </div>

            <div class="main-ticket">
                <div class="ticket-header">
                    <span>✈</span>
                    <span>BOARDING BOARD</span>
                    <span>✈</span>
                </div>

                <div class="ticket-body">
                    <div class="info-box">
                        <span class="label">Ident / Callsign</span>
                        <span id="callsign" class="value highlight">SEARCHING</span>
                    </div>
                    <div class="info-box">
                        <span class="label">Type</span>
                        <span id="type_ac" class="value">----</span>
                    </div>
                    <div class="info-box">
                        <span class="label">Aircraft Distance</span>
                        <span id="dist_body" class="value">--- KM</span>
                    </div>
                    <div class="info-box">
                        <span class="label">Bearing</span>
                        <span id="compass" class="value">↑</span>
                    </div>
                    <div class="info-box">
                        <span class="label">Altitude (MSL)</span>
                        <span id="alt" class="value">--- FT</span>
                    </div>
                    <div class="info-box">
                        <span class="label">Speed</span>
                        <span id="speed" class="value">--- KTS</span>
                    </div>
                </div>

                <a id="map-link" target="_blank" class="barcode-area" style="text-decoration:none;">
                    <div class="barcode-img"></div>
                    <div class="label" style="color:var(--air-blue)">TAP TO VIEW MAP</div>
                </a>

                <div class="footer-status" id="status">SCANNING AIRSPACE...</div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000);
                    executarBusca();
                });
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('type_ac').innerText = data.type;
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('dist_body').innerText = data.dist + " KM";
                        document.getElementById('speed').innerText = data.speed + " KTS";
                        
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        document.getElementById('status').innerText = "TARGET ACQUIRED: " + data.callsign;

                        let bars = Math.max(1, Math.ceil((25 - data.dist) / 5));
                        document.getElementById('signal-bars').innerText = "▮".repeat(bars) + "▯".repeat(5-bars);
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
                dist_km = haversine(lat_u, lon_u, ac['lat'], ac['lon'])
                
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(dist_km, 1), 
                    "alt_ft": int(ac.get('alt_baro', 0)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": f"https://globe.adsbexchange.com/?lat={ac['lat']}&lon={ac['lon']}&zoom=11",
                    "type": ac.get('t', 'UNKN'), 
                    "speed": ac.get('gs', 0)
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
