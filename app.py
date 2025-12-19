from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# CONFIGURAÇÃO DE RAIO: 25KM
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Radar Boarding Pass - iPhone 15 Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); 
                margin: 0; padding: 0; 
                display: flex; flex-direction: column;
                align-items: center; justify-content: center; 
                min-height: 100vh;
                font-family: 'Courier New', monospace;
                overflow: hidden;
            }

            #search-box { 
                display: none; 
                width: 90%; max-width: 500px;
                background: rgba(255,255,255,0.1);
                padding: 10px; border-radius: 12px;
                margin-bottom: 15px; border: 1px solid var(--warning-gold);
                gap: 8px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 10px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 15px; font-weight: 900; border-radius: 6px; }

            .card { 
                background: var(--air-blue); 
                width: 95%; max-width: 620px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden;
                transform: scale(0.96);
            }

            .notch { position: absolute; width: 40px; height: 40px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -20px; } .notch-right { right: -20px; }

            .header { padding: 15px 0; text-align: center; color: white; font-weight: 900; letter-spacing: 3px; font-size: 1.1em; }

            .white-area { 
                background: #fdfdfd; margin: 0 10px; position: relative; 
                display: flex; padding: 25px 15px; min-height: 240px; border-radius: 4px; 
            }

            .col-left { flex: 1.6; border-right: 1px dashed #ddd; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.3em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; }
            
            #compass { display: inline-block; transition: transform 0.6s ease; color: var(--warning-gold); font-size: 1.2em; }
            
            .barcode { 
                height: 55px; 
                background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); 
                width: 100%; margin: 8px 0 4px 0; border: 1px solid #eee; 
            }

            .signal-area { width: 100%; text-align: center; }
            #signal-text { font-size: 8px; color: #888; font-weight: bold; margin-bottom: 2px; display: block; }
            #signal-bars { color: var(--air-blue); font-weight: 900; font-size: 12px; letter-spacing: 2px; }
            
            .footer { padding: 10px 0 20px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 6px; border-top: 2px solid var(--warning-gold); border-bottom: 2px solid var(--warning-gold); margin-bottom: 15px; }
            .status-msg { color: var(--warning-gold); font-size: 0.75em; font-weight: bold; text-transform: uppercase; text-align: center; padding: 0 10px; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="ENTER CITY OR ZIP CODE...">
            <button onclick="buscarEndereco()">ACTIVATE</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header">✈ BOARDING PASS ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">ACTIVE RADAR RANGE</div><div class="value">25 KM</div></div>
                    <div><div class="label">ALTITUDE (MSL)</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">RANGE / BEARING</div>
                    <div class="value"><span id="dist">0.0 KM</span> <span id="compass">↑</span></div>
                    
                    <a id="map-link" style="text-decoration:none; width:100%;" target="_blank">
                        <div class="barcode"></div>
                    </a>

                    <div class="signal-area">
                        <span id="signal-text">SIGNAL INTENSITY</span>
                        <div id="signal-bars">[ ▯▯▯▯▯ ]</div>
                    </div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">SCANNING AIRSPACE (25KM)...</div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
            };

            function iniciarRadar() {
                setInterval(executarBusca, 8000);
                executarBusca();
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
                        document.getElementById('map-link').href = data.map_url;
                        document.getElementById('status').innerText = "TARGET ACQUIRED: " + data.callsign;

                        let bars = Math.max(1, Math.ceil((25 - data.dist) / 5));
                        document.getElementById('signal-bars').innerText = "[" + "▮".repeat(bars) + "▯".repeat(5-bars) + "]";
                    } else {
                        document.getElementById('status').innerText = "RADAR SWEEP ACTIVE (25KM)...";
                        document.getElementById('signal-bars').innerText = "[ ▯▯▯▯▯ ]";
                        document.getElementById('callsign').innerText = "SEARCHING";
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
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, headers=headers, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                dist_km = haversine(lat_u, lon_u, ac['lat'], ac['lon'])
                
                # Link otimizado com foco e seleção
                map_url = (f"https://globe.adsbexchange.com/?"
                           f"lat={lat_u}&lon={lon_u}&zoom=11"
                           f"&hex={ac.get('hex', '')}"
                           f"&sel={ac.get('hex', '')}"
                           f"&SiteLat={lat_u}&SiteLon={lon_u}")
                
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(dist_km, 1), 
                    "alt": (ac.get('alt_baro') or ac.get('alt_geom') or 0) / 3.28, 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": map_url
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)






























