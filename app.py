from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configuração do raio de alcance do radar
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
        <title>Radar Boarding Pass Pro</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); 
                margin: 0; padding: 0; 
                display: flex; align-items: center; justify-content: center; 
                min-height: 100vh;
                font-family: 'Courier New', monospace;
                overflow: hidden;
            }

            .card { 
                background: var(--air-blue); 
                width: 95%; max-width: 620px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden;
            }

            .header { padding: 15px 0; text-align: center; color: white; font-weight: 900; letter-spacing: 3px; }

            .white-area { 
                background: #fdfdfd; margin: 0 10px; display: flex; 
                padding: 20px 15px; min-height: 250px; border-radius: 4px; 
            }

            .col-left { flex: 1.6; border-right: 1px dashed #ddd; padding-right: 15px; }
            .col-right { flex: 1; padding-left: 15px; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: space-around; }
            
            .label { color: #888; font-size: 0.65em; font-weight: 800; text-transform: uppercase; }
            .value { font-size: 1.1em; font-weight: 900; color: var(--air-blue); margin-bottom: 10px; }
            
            #compass { display: inline-block; transition: transform 0.6s ease; color: #ff8c00; font-size: 1.5em; }
            
            .barcode-container { width: 100%; display: flex; justify-content: center; cursor: pointer; }
            #barcode { width: 100%; max-width: 150px; height: 50px; }

            /* Footer ajustado para iOS */
            .footer { 
                background: #000 !important; 
                padding: 15px; 
                min-height: 80px; 
                display: flex; 
                align-items: center; 
                justify-content: center;
                border-top: 4px solid var(--warning-gold);
            }
            .status-msg { 
                color: #FFD700 !important; 
                font-weight: 900; 
                font-size: 1.1em; 
                text-transform: uppercase;
                text-align: center;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8); /* Ajuda na leitura no iOS */
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">✈ ATC BOARDING PASS ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div>
                    <div class="label">FLIGHT PATH</div><div id="route" class="value">-- / --</div>
                    <div class="label">TYPE / SPEED</div><div id="type_speed" class="value">-- / -- KTS</div>
                    <div class="label">DISTANCE</div><div id="dist_body" class="value">-- KM</div>
                </div>
                <div class="col-right">
                    <div class="label">ALTITUDE</div><div id="alt" class="value">00000 FT</div>
                    <div class="label">BEARING</div><div class="value"><span id="compass">↑</span></div>
                    <a id="map-link" target="_blank" class="barcode-container">
                        <svg id="barcode"></svg>
                    </a>
                </div>
            </div>
            <div class="footer">
                <div id="status" class="status-msg">INITIALIZING RADAR...</div>
            </div>
        </div>

        <script>
            let latAlvo, lonAlvo;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000);
                    executarBusca();
                }, err => {
                    document.getElementById('status').textContent = "GPS ERROR: ENABLE LOCATION";
                });
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=` + Date.now())
                .then(res => res.json()).then(data => {
                    const statusElem = document.getElementById('status');
                    if(data.found) {
                        // Usando textContent para compatibilidade iOS
                        document.getElementById('callsign').textContent = data.callsign;
                        document.getElementById('route').textContent = data.origin + " / " + data.dest;
                        document.getElementById('type_speed').textContent = data.type + " / " + data.speed + " KTS";
                        document.getElementById('alt').textContent = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('dist_body').textContent = data.dist + " KM";
                        
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        statusElem.textContent = "TARGET ACQUIRED: " + data.callsign;

                        // Código de barras real
                        JsBarcode("#barcode", data.callsign, {
                            format: "CODE128", width: 1.5, height: 40, displayValue: false, lineColor: "#1A237E"
                        });
                    } else {
                        statusElem.textContent = "SCANNING AIRSPACE...";
                        document.getElementById('callsign').textContent = "SEARCHING";
                        document.getElementById('barcode').innerHTML = "";
                        document.getElementById('map-link').removeAttribute('href');
                    }
                }).catch(() => {
                    document.getElementById('status').textContent = "DATA LINK ERROR";
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
            validos = [a for a in r['ac'] if a.get('lat')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                
                # Link para mapa com local do usuário e do avião
                map_url = (f"https://globe.adsbexchange.com/?"
                           f"lat={ac['lat']}&lon={ac['lon']}&zoom=11"
                           f"&hex={ac.get('hex', '')}&sel={ac.get('hex', '')}"
                           f"&SiteLat={lat_u}&SiteLon={lon_u}")
                
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                    "alt_ft": int(ac.get('alt_baro', 0)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": map_url,
                    "origin": ac.get('t_from', 'N/A')[:3],
                    "dest": ac.get('t_to', 'N/A')[:3],
                    "type": ac.get('t', 'UNKN'),
                    "speed": ac.get('gs', 0)
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
