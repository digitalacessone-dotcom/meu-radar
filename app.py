from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configurações de Busca
RADIUS = 150.0
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def get_bearing(lat1, lon1, lat2, lon2):
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
        <title>Flight Radar Ticket</title>
        <style>
            body { background: #e0e6ed; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: Arial, sans-serif; margin: 0; }
            
            #search { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
            button { background: #226488; color: #fff; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }

            .ticket { background: #fff; width: 800px; display: flex; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
            
            .left-side { background: #226488; color: #fff; width: 220px; padding: 25px; border-right: 2px dashed #ccc; }
            .right-side { flex: 1; display: flex; flex-direction: column; }
            
            .header { background: #226488; color: #fff; padding: 15px; text-align: center; font-weight: bold; letter-spacing: 4px; font-size: 1.2em; }
            .main-content { padding: 25px; display: flex; justify-content: space-between; flex: 1; }
            
            .label { color: #888; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 3px; }
            .data-val { font-size: 28px; font-weight: bold; color: #226488; margin-bottom: 15px; font-family: 'Courier New', monospace; }

            .black-bar { 
                background: #000; 
                color: #FFD700; 
                padding: 12px 25px; 
                font-family: 'Courier New', monospace; 
                font-weight: bold; 
                border-top: 3px solid #FFD700;
                min-height: 25px;
                font-size: 1.1em;
            }

            #compass { font-size: 50px; color: #ff8c00; transition: 1s ease; }
            .dots { display: flex; gap: 4px; margin-top: 15px; }
            .dot { width: 10px; height: 10px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            .dot.on { background: #fff; box-shadow: 0 0 5px #fff; }
        </style>
    </head>
    <body>

        <div id="search">
            <input type="text" id="city" placeholder="City Name...">
            <button onclick="init()">CONNECT</button>
        </div>

        <div class="ticket">
            <div class="left-side">
                <div class="label" style="color:#abd1e6">RADAR BASE</div>
                <div style="font-size: 60px; font-weight: 900;">19 A</div>
                <div class="dots">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
            </div>
            <div class="right-side">
                <div class="header">BOARDING BOARD</div>
                <div class="main-content">
                    <div>
                        <div class="label">IDENT / CALLSIGN</div><div id="call" class="data-val">SEARCHING</div>
                        <div class="label">DISTANCE</div><div id="dist" class="data-val">---</div>
                        <div class="label">ALTITUDE (MSL)</div><div id="alt" class="data-val">---</div>
                    </div>
                    <div style="text-align: center; padding-right: 30px;">
                        <div class="label">BEARING</div>
                        <div id="compass">↑</div>
                    </div>
                </div>
                <div class="black-bar" id="status-bar">> READY TO SCAN</div>
            </div>
        </div>

        <script>
            let userLat, userLon;

            async function init() {
                const city = document.getElementById('city').value;
                if(!city) return;
                const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${city}&limit=1`);
                const d = await r.json();
                if(d.length > 0) {
                    userLat = d[0].lat; userLon = d[0].lon;
                    document.getElementById('search').style.display = 'none';
                    document.getElementById('status-bar').innerText = "> LOCATION SYNCED";
                    setInterval(fetchData, 7000);
                    fetchData();
                }
            }

            async function fetchData() {
                try {
                    const res = await fetch(`/api/air?lat=${userLat}&lon=${userLon}`);
                    const data = await res.json();
                    
                    if(data.found) {
                        document.getElementById('call').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.distance.toFixed(1) + " KM";
                        document.getElementById('alt').innerText = data.altitude.toLocaleString() + " FT";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('status-bar').innerText = `> LOCKED: ${data.callsign} | SPD: ${data.speed} KTS`;
                        
                        const dots = document.querySelectorAll('.dot');
                        const active = Math.max(1, Math.min(8, Math.ceil(8 - (data.distance/20))));
                        dots.forEach((dot, i) => i < active ? dot.classList.add('on') : dot.classList.remove('on'));
                    } else {
                        document.getElementById('status-bar').innerText = "> SCANNING AIRSPACE...";
                    }
                } catch(e) {
                    document.getElementById('status-bar').innerText = "> DATA LINK ERROR";
                }
            }

            window.onload = () => {
                navigator.geolocation.getCurrentPosition(p => {
                    userLat = p.coords.latitude; userLon = p.coords.longitude;
                    document.getElementById('search').style.display = 'none';
                    document.getElementById('status-bar').innerText = "> GPS CONNECTED";
                    setInterval(fetchData, 7000);
                    fetchData();
                }, () => {
                    document.getElementById('status-bar').innerText = "> WAITING FOR INPUT";
                });
            };
        </script>
    </body>
    </html>
    ''')

@app.route('/api/air')
def api_air():
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        url = f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{RADIUS}"
        r = requests.get(url, headers=HEADERS, timeout=10).json()
        
        if r.get('ac'):
            # Pega o avião mais próximo
            ac = sorted([a for a in r['ac'] if 'lat' in a], key=lambda x: get_distance(lat, lon, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True,
                "callsign": (ac.get('flight') or ac.get('call') or "UNKNOWN").strip(),
                "distance": get_distance(lat, lon, ac['lat'], ac['lon']),
                "altitude": int(ac.get('alt_baro', 0)),
                "bearing": get_bearing(lat, lon, ac['lat'], ac['lon']),
                "speed": ac.get('gs', 0)
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

























