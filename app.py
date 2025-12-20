from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# --- CONFIGURAÇÕES DO RADAR ---
SEARCH_RADIUS = 150.0
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

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
        <style>
            :root { --air-blue: #226488; --gold: #FFD700; --bg: #f0f4f7; }
            body { background: var(--bg); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; margin: 0; }
            
            #search-section { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; gap: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            #search-section.hidden { display: none; }

            .card { background: white; width: 850px; border-radius: 20px; display: flex; overflow: hidden; box-shadow: 0 15px 30px rgba(0,0,0,0.1); border: 1px solid #ddd; }
            .left { width: 25%; background: var(--air-blue); color: white; padding: 30px; border-right: 2px dashed rgba(255,255,255,0.3); position: relative; }
            .right { flex: 1; display: flex; flex-direction: column; }
            
            .header { background: var(--air-blue); color: white; padding: 20px 40px; font-size: 1.5em; letter-spacing: 5px; text-align: center; font-weight: bold; }
            .content { padding: 30px 40px; display: flex; justify-content: space-between; flex: 1; }
            
            .label { color: #888; font-size: 0.75em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.8em; font-weight: 900; color: var(--air-blue); margin-bottom: 20px; font-family: monospace; }

            /* FAIXA PRETA - TEXTO EM INGLÊS FORÇADO */
            .footer { 
                background: black !important; 
                color: var(--gold) !important; 
                padding: 15px 40px; 
                font-family: 'Courier New', monospace; 
                font-size: 1.3em; 
                font-weight: bold;
                border-top: 4px solid var(--gold);
                min-height: 55px;
                display: flex;
                align-items: center;
                text-transform: uppercase;
            }
            
            #compass { font-size: 3.5em; color: #ff8c00; transition: transform 1s ease; }
            .scale { display: flex; gap: 5px; margin-top: 20px; }
            .dot { width: 12px; height: 12px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            .dot.active { background: white; box-shadow: 0 0 8px white; }
        </style>
    </head>
    <body>
        <div id="search-section">
            <input type="text" id="city" placeholder="Enter City...">
            <button onclick="start()">CONNECT</button>
        </div>

        <div class="card">
            <div class="left">
                <div class="label" style="color:#abd1e6">RADAR BASE</div>
                <div style="font-size: 4.5em; font-weight: 900; letter-spacing: -2px;">19 A</div>
                <div class="scale">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
            </div>
            <div class="right">
                <div class="header">BOARDING BOARD</div>
                <div class="content">
                    <div>
                        <div class="label">IDENT / CALLSIGN</div><div id="call" class="value">SEARCHING</div>
                        <div class="label">AIRCRAFT DISTANCE</div><div id="dist" class="value">---</div>
                        <div class="label">ALTITUDE (MSL)</div><div id="alt" class="value">---</div>
                    </div>
                    <div style="text-align:center; padding-right: 20px;">
                        <div class="label">BEARING</div>
                        <div id="compass">↑</div>
                        <div style="margin-top:20px; height:55px; width:130px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 6px); opacity:0.15;"></div>
                    </div>
                </div>
                <div class="footer" id="footer-text">> SYSTEM INITIALIZING...</div>
            </div>
        </div>

        <script>
            let lat, lon, step = 0;

            function updateFooter(text) {
                const el = document.getElementById('footer-text');
                if(el) el.innerHTML = "> " + text.toUpperCase();
            }

            async function start() {
                const q = document.getElementById('city').value;
                if(!q) return;
                try {
                    const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`);
                    const d = await r.json();
                    if(d.length > 0) {
                        lat = d[0].lat; lon = d[0].lon;
                        document.getElementById('search-section').classList.add('hidden');
                        updateFooter("RADAR CONNECTION ESTABLISHED");
                        setInterval(getData, 8000);
                        getData();
                    }
                } catch(e) { updateFooter("ERROR LOCATING COORDINATES"); }
            }

            async function getData() {
                if(!lat) return;
                try {
                    const res = await fetch(`/api/data?lat=${lat}&lon=${lon}`);
                    const data = await res.json();
                    if(data.found) {
                        document.getElementById('call').innerText = data.callsign;
                        document.getElementById('dist').innerText = data.dist.toFixed(1) + " KM";
                        document.getElementById('alt').innerText = data.alt.toLocaleString() + " FT";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        const dots = document.querySelectorAll('.dot');
                        const activeCount = Math.max(1, Math.min(8, Math.ceil(8 - (data.dist/20))));
                        dots.forEach((d, i) => i < activeCount ? d.classList.add('active') : d.classList.remove('active'));
                        
                        const msgs = [
                            `TARGET LOCKED: ${data.callsign}`,
                            `GROUND SPEED: ${data.speed} KTS`,
                            `SIGNAL STATUS: SECURE`
                        ];
                        updateFooter(msgs[step % msgs.length]);
                    } else {
                        updateFooter("SCANNING AIRSPACE...");
                    }
                    step++;
                } catch(e) { updateFooter("DATA LINK TIMEOUT"); }
            }

            window.onload = () => {
                navigator.geolocation.getCurrentPosition(p => {
                    lat = p.coords.latitude; lon = p.coords.longitude;
                    document.getElementById('search-section').classList.add('hidden');
                    updateFooter("GPS LOCATION SYNCED");
                    setInterval(getData, 8000);
                    getData();
                }, () => {
                    updateFooter("WAITING FOR MANUAL LOCATION INPUT");
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
        url = f"https://api.adsb.lol/v2/lat/{l1}/lon/{l2}/dist/{SEARCH_RADIUS}"
        r = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=10).json()
        if r.get('ac'):
            ac = sorted([a for a in r['ac'] if 'lat' in a], key=lambda x: haversine(l1, l2, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call') or "N/A").strip(),
                "dist": haversine(l1, l2, ac['lat'], ac['lon']),
                "alt": int(ac.get('alt_baro', 0)),
                "bearing": calculate_bearing(l1, l2, ac['lat'], ac['lon']),
                "speed": ac.get('gs', 0)
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

























