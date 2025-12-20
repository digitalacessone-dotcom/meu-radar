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
        <title>Boarding Pass Radar</title>
        <style>
            body { background: #d0e4f2; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; font-family: Arial, sans-serif; }
            
            .ticket {
                background: white; width: 750px; height: 300px;
                border-radius: 20px; display: flex; overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            }

            /* Lateral Esquerda */
            .left-side { width: 220px; background: #4ba8cc; padding: 20px; color: white; border-right: 2px dashed #ddd; display: flex; flex-direction: column; justify-content: space-between; }
            .seat-num { font-size: 5em; font-weight: bold; margin-top: 10px; }
            .flight-info-left { font-size: 0.9em; margin-bottom: 5px; }

            /* Lado Direito Principal */
            .right-side { flex: 1; display: flex; flex-direction: column; }
            .top-bar { background: #4ba8cc; height: 60px; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; color: white; font-weight: bold; letter-spacing: 2px; }
            .top-bar img { height: 25px; filter: brightness(0) invert(1); }

            .main-content { padding: 25px 35px; display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; flex: 1; position: relative; }
            .label { color: #4ba8cc; font-size: 0.75em; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; }
            .value { color: #333; font-size: 1.3em; font-weight: bold; margin-bottom: 15px; }

            .barcode-section { display: flex; justify-content: flex-end; align-items: flex-end; padding-right: 35px; padding-bottom: 20px; }
            .barcode-line { height: 60px; width: 180px; background: repeating-linear-gradient(90deg, #333, #333 1px, transparent 1px, transparent 4px, #333 4px, #333 5px); }

            #status-bar { background: #000; color: #FFD700; text-align: center; font-size: 0.7em; padding: 4px; font-family: monospace; }
            #compass { display: inline-block; transition: transform 0.6s ease; font-size: 1.5em; color: #f39c12; }

            @media (max-width: 600px) {
                .ticket { width: 95%; height: auto; flex-direction: column; border-radius: 10px; }
                .left-side { width: auto; height: 150px; border-right: none; border-bottom: 2px dashed #ddd; }
            }
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="left-side">
                <div>
                    <div style="font-size: 0.7em; opacity: 0.8;">RADAR BASE</div>
                    <div class="seat-num">19 A</div>
                </div>
                <div class="flight-info-left">
                    <div>SCANNING: 25KM</div>
                    <div id="signal">▯▯▯▯▯</div>
                </div>
            </div>

            <div class="right-side">
                <div class="top-bar">
                    <span>✈ AIR RADAR</span>
                    <span style="font-size: 1.2em;">BOARDING PASS</span>
                    <span>✈</span>
                </div>

                <div class="main-content">
                    <div>
                        <div class="label">IDENT / CALLSIGN</div>
                        <div id="callsign" class="value" style="font-size: 1.8em; color: #4ba8cc;">SEARCHING</div>
                        
                        <div class="label">AIRCRAFT DISTANCE</div>
                        <div id="dist" class="value">--- KM</div>

                        <div class="label">ALTITUDE (MSL)</div>
                        <div id="alt" class="value">--- FT</div>
                    </div>
                    <div>
                        <div class="label">TYPE</div>
                        <div id="type" class="value">----</div>

                        <div class="label">BEARING</div>
                        <div class="value"><span id="compass">↑</span></div>
                        
                        <div class="label">SPEED</div>
                        <div id="speed" class="value">--- KTS</div>
                    </div>
                </div>

                <div class="barcode-section">
                    <a id="map-link" target="_blank" style="text-decoration: none;">
                        <div class="barcode-line"></div>
                        <div style="font-size: 0.6em; color: #999; text-align: center; margin-top: 5px;">VIEW LIVE MAP</div>
                    </a>
                </div>
                <div id="status-bar">SYSTEM INITIALIZING...</div>
            </div>
        </div>

        <script>
            let latU, lonU;
            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latU = pos.coords.latitude; lonU = pos.coords.longitude;
                    setInterval(update, 8000); update();
                });
            };

            function update() {
                if(!latU) return;
                fetch(`/api/data?lat=${latU}&lon=${lonU}&t=${Date.now()}`)
                .then(r => r.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('type').innerText = data.type;
                        document.getElementById('speed').innerText = data.speed + " KTS";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        document.getElementById('status-bar').innerText = "RADAR: TARGET LOCKED " + data.callsign;
                        
                        let b = Math.max(1, Math.ceil((25-data.dist)/5));
                        document.getElementById('signal').innerText = "▮".repeat(b) + "▯".repeat(5-b);
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
                "speed": ac.get('gs', 0),
                "map_url": f"https://globe.adsbexchange.com/?lat={ac['lat']}&lon={ac['lon']}&zoom=11"
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
