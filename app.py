from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Terminal</title>
        <style>
            :root { --blue: #1A237E; --gold: #FFD700; }
            body { background: #0a192f; margin: 0; padding: 10px; font-family: 'Courier New', monospace; color: white; display: flex; flex-direction: column; align-items: center; }

            .ticket { background: #fdfdfd; width: 100%; max-width: 600px; border-radius: 10px; overflow: hidden; color: #1A237E; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-top: 20px; }
            .blue-top { background: var(--blue); color: white; padding: 15px; text-align: center; font-weight: bold; letter-spacing: 3px; }
            
            .main-info { padding: 20px; display: flex; justify-content: space-between; border-bottom: 2px dashed #ccc; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; }
            .val { font-size: 1.5em; font-weight: 900; margin-bottom: 10px; }

            /* A FAIXA PRETA REESTRUTURADA */
            .black-bar-container { background: var(--blue); padding-bottom: 10px; width: 100%; }
            .yellow-strip { height: 4px; background: var(--gold); margin-bottom: 5px; }
            
            .black-bar { 
                background: #000000 !important; 
                margin: 0 10px; 
                height: 50px; 
                display: flex; 
                align-items: center; 
                justify-content: center;
                border: 1px solid #333;
                box-sizing: border-box;
            }
            
            #status-display { 
                color: #FFD700 !important; 
                font-weight: 900; 
                font-size: 1.1em; 
                text-transform: uppercase;
                display: block !important;
                visibility: visible !important;
                text-align: center;
            }

            #compass { font-size: 3em; color: orange; transition: transform 0.5s; }
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="blue-top">BOARDING BOARD</div>
            <div class="main-info">
                <div>
                    <div class="label">IDENT / CALLSIGN</div><div id="call" class="val">WAITING</div>
                    <div class="label">DISTANCE</div><div id="dist" class="val">---</div>
                    <div class="label">ALTITUDE</div><div id="alt" class="val">---</div>
                </div>
                <div style="text-align: center;">
                    <div class="label">BEARING</div>
                    <div id="compass">↑</div>
                </div>
            </div>
            <div class="black-bar-container">
                <div class="yellow-strip"></div>
                <div class="black-bar">
                    <span id="status-display">SYSTEM ONLINE</span>
                </div>
            </div>
        </div>

        <script>
            let lat, lon, target = null;

            function logStatus(msg) {
                document.getElementById('status-display').innerText = "> " + msg.toUpperCase();
            }

            async function updateRadar() {
                if(!lat) return;
                try {
                    const r = await fetch(`/api/data?lat=${lat}&lon=${lon}`);
                    const data = await r.json();
                    if(data.found) {
                        target = data;
                        document.getElementById('call').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt_ft + " FT";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        logStatus(`LOCKED: ${data.callsign} | SPD: ${data.speed} KTS`);
                    } else {
                        logStatus("SCANNING AIRSPACE...");
                    }
                } catch(e) { logStatus("CONNECTION ERROR"); }
            }

            window.onload = () => {
                navigator.geolocation.getCurrentPosition(p => {
                    lat = p.coords.latitude; lon = p.coords.longitude;
                    logStatus("GPS CONNECTED");
                    setInterval(updateRadar, 7000);
                    updateRadar();
                }, () => {
                    logStatus("ERROR: GPS REQUIRED");
                });
            };
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    l1 = float(request.args.get('lat', 0)); l2 = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{l1}/lon/{l2}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            ac = sorted([a for a in r['ac'] if 'lat' in a], key=lambda x: haversine(l1, l2, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', ac.get('call', 'N/A')).strip(),
                "dist": round(haversine(l1, l2, ac['lat'], ac['lon']), 1),
                "alt_ft": int(ac.get('alt_baro', 0)), "bearing": calculate_bearing(l1, l2, ac['lat'], ac['lon']),
                "speed": ac.get('gs', 0)
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
