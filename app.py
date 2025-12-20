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
        <title>Radar Boarding Pass</title>
        <style>
            :root { --blue: #4ba8cc; --dark-blue: #1e5d7b; --warning: #FFD700; }
            body { background: #d0e4f2; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; font-family: Arial, sans-serif; overflow: hidden; }
            
            .ticket {
                background: white; width: 90%; max-width: 700px;
                border-radius: 15px; display: flex; flex-direction: column;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2); overflow: hidden;
            }

            .ticket-top { display: flex; min-height: 280px; }

            /* Lado Esquerdo (Canhoto) */
            .stub { width: 30%; background: var(--dark-blue); color: white; padding: 20px; border-right: 2px dashed #ddd; display: flex; flex-direction: column; justify-content: space-between; }
            .seat { font-size: 4em; font-weight: bold; line-height: 1; margin: 10px 0; }

            /* Lado Direito (Principal) */
            .main { flex: 1; display: flex; flex-direction: column; }
            .header-strip { background: var(--blue); color: white; padding: 12px 25px; display: flex; justify-content: space-between; font-weight: bold; letter-spacing: 1px; }
            
            .content { padding: 20px 25px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; flex-grow: 1; }
            .label { color: var(--blue); font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { color: #333; font-size: 1.2em; font-weight: bold; margin-bottom: 8px; }

            /* Faixa Preta Inferior Estilo Radar */
            .footer-black { 
                background: #000; padding: 15px; 
                border-top: 3px solid var(--warning);
                display: flex; align-items: center; justify-content: center;
                min-height: 60px;
            }
            .status-text { 
                color: var(--warning) !important; 
                font-family: 'Courier New', monospace; 
                font-weight: bold; 
                font-size: 1em; 
                text-transform: uppercase;
                letter-spacing: 2px;
                text-align: center;
                animation: blink 1.5s infinite;
            }

            @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            #compass { display: inline-block; transition: transform 0.6s ease; font-size: 1.2em; color: #f39c12; }
            
            .barcode-area { border-top: 1px solid #eee; padding: 10px 25px; display: flex; justify-content: flex-end; }
            .barcode { height: 40px; width: 150px; background: repeating-linear-gradient(90deg, #333, #333 2px, transparent 2px, transparent 5px); }

            @media (max-width: 600px) {
                .ticket-top { flex-direction: column; }
                .stub { width: auto; border-right: none; border-bottom: 2px dashed #ddd; }
            }
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="ticket-top">
                <div class="stub">
                    <div>
                        <div class="label" style="color:rgba(255,255,255,0.7)">RADAR BASE</div>
                        <div class="seat">19 A</div>
                    </div>
                    <div style="font-size: 0.8em;">
                        <div id="sig">▯▯▯▯▯</div>
                        <div style="margin-top:5px; opacity:0.6">ATC SECURE</div>
                    </div>
                </div>

                <div class="main">
                    <div class="header-strip">
                        <span>✈ BOARDING PASS</span>
                        <span>AIR RADAR</span>
                    </div>
                    <div class="content">
                        <div>
                            <div class="label">Callsign</div>
                            <div id="callsign" class="value" style="color:var(--blue); font-size:1.5em;">SEARCHING</div>
                            <div class="label">Distance</div>
                            <div id="dist" class="value">--- KM</div>
                        </div>
                        <div>
                            <div class="label">Altitude</div>
                            <div id="alt" class="value">--- FT</div>
                            <div class="label">Bearing</div>
                            <div class="value"><span id="compass">↑</span></div>
                        </div>
                    </div>
                    <a id="map-link" target="_blank" style="text-decoration:none" class="barcode-area">
                        <div class="barcode"></div>
                    </a>
                </div>
            </div>
            
            <div class="footer-black">
                <div id="status" class="status-text">INITIALIZING SCANNER...</div>
            </div>
        </div>

        <script>
            let latU, lonU;
            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latU = pos.coords.latitude; lonU = pos.coords.longitude;
                    setInterval(fetchData, 8000); fetchData();
                }, () => { document.getElementById('status').innerText = "ERROR: GPS REQUIRED"; });
            };

            function fetchData() {
                if(!latU) return;
                fetch(`/api/data?lat=${latU}&lon=${lonU}&t=${Date.now()}`)
                .then(r => r.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        
                        // Atualiza texto amarelo na parte preta
                        document.getElementById('status').innerText = "> TARGET LOCKED: " + data.callsign;
                        
                        let b = Math.max(1, Math.ceil((25-data.dist)/5));
                        document.getElementById('sig').innerText = "▮".repeat(b) + "▯".repeat(5-b);
                    } else {
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
                "map_url": f"https://globe.adsbexchange.com/?lat={ac['lat']}&lon={ac['lon']}&zoom=11"
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
