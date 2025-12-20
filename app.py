from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
RAIO_KM = 80.0
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass</title>
        <style>
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #f0f4f7; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif; overflow: hidden;
            }

            #search-section {
                background: #fff; padding: 15px 25px; border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                display: flex; gap: 10px; align-items: center; border: 1px solid #ddd;
                width: 95%; max-width: 850px; z-index: 100;
                max-height: 200px; opacity: 1; margin-bottom: 20px; overflow: hidden;
                transition: all 0.8s ease;
            }

            #search-section.hidden { max-height: 0; opacity: 0; margin-bottom: 0; padding: 0; border: 0; pointer-events: none; }
            #search-section input { border: 1px solid #ccc; padding: 10px; border-radius: 6px; flex: 1; outline: none; }
            #search-section button { background: var(--air-blue); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }

            .card { 
                background: white; width: 95%; max-width: 850px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
                display: flex; overflow: hidden; border: 1px solid #ddd;
            }

            .left-stub {
                width: 25%; background: var(--air-blue); color: white;
                padding: 20px; display: flex; flex-direction: column;
                border-right: 2px dashed rgba(255,255,255,0.3);
            }

            .seat-num { font-size: 4em; font-weight: 900; margin-top: 10px; line-height: 1; }
            
            .proximity-scale {
                display: flex; gap: 4px; margin-top: 15px;
                width: 100%; justify-content: flex-start;
            }
            .scale-step {
                width: 12px; height: 12px;
                background: rgba(255,255,255,0.2); 
                border-radius: 2px; transition: all 0.4s ease;
            }
            .scale-step.active { background: #ffffff; box-shadow: 0 0 5px rgba(255,255,255,0.8); }

            .main-ticket { flex: 1; display: flex; flex-direction: column; }
            .header-bar { 
                background: var(--air-blue); height: 80px; display: flex; 
                align-items: center; justify-content: space-between; padding: 0 40px; color: white;
            }
            .header-bar h1 { font-size: 1.5em; letter-spacing: 5px; margin: 0; }

            .content-area { padding: 30px 50px; display: flex; flex: 1; background: white; }
            .col-data { flex: 2; border-right: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; }
            .col-side { flex: 1; padding-left: 30px; align-items: center; display: flex; flex-direction: column; justify-content: space-around; }

            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); min-height: 1.2em; display: flex; }

            .terminal-footer { 
                background: #000; padding: 12px 40px; border-top: 3px solid var(--warning-gold);
                min-height: 55px; display: flex; align-items: center;
            }

            .letter-slot { 
                display: inline-block; color: var(--warning-gold); 
                font-family: 'Courier New', monospace; font-weight: 900; 
                min-width: 0.65em; text-align: center;
            }
            .flapping { animation: flap 0.08s infinite; }
            @keyframes flap { 50% { transform: scaleY(0.1); opacity: 0.3; } }

            #compass { font-size: 2.5em; transition: transform 0.8s ease; display: inline-block; color: #ff8c00; }
            #radar-link { display: block; text-decoration: none; pointer-events: none; transition: 0.4s; opacity: 0.1; }
            #radar-link.active { pointer-events: auto !important; opacity: 1 !important; cursor: pointer !important; }
            .barcode { width: 150px; height: 55px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); margin-top: 10px; }
        </style>
    </head>
    <body>

        <div id="search-section">
            <input type="text" id="address-input" placeholder="Enter City or Location...">
            <button onclick="geocodeAddress()">CONNECT RADAR</button>
        </div>

        <div class="card">
            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.7)">Radar Base</div>
                <div class="seat-label">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="proximity-scale" id="p-scale">
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div><div class="scale-step"></div>
                    <div class="scale-step"></div><div class="scale-step"></div>
                </div>
                <div class="seat-label" style="margin-top: auto;">ATC Secure</div>
            </div>

            <div class="main-ticket">
                <div class="header-bar">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>

                <div class="content-area">
                    <div class="col-data">
                        <div><div class="label">Ident / Callsign</div><div id="callsign" class="value"></div></div>
                        <div><div class="label">Aircraft Distance</div><div id="dist_body" class="value"></div></div>
                        <div><div class="label">Altitude (MSL)</div><div id="alt" class="value"></div></div>
                    </div>

                    <div class="col-side">
                        <div style="text-align: center;"><div class="label">Type</div><div id="type_id" class="value">----</div></div>
                        <div id="compass">↑</div>
                        <a id="radar-link" href="#" target="_blank"><div class="barcode"></div></a>
                    </div>
                </div>

                <div class="terminal-footer">
                    <div id="status-container"></div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, currentTarget = null, step = 0;
            let weather = { temp: '--', sky: 'SCANNING' };
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->°%";

            function updateProximityScale(dist) {
                const steps = document.querySelectorAll('.scale-step');
                const activeCount = Math.max(1, Math.min(8, Math.ceil(8 - (dist / 10))));
                steps.forEach((s, i) => {
                    if (i < activeCount) s.classList.add('active');
                    else s.classList.remove('active');
                });
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                if (!container) return;
                const newText = String(newValue || "").toUpperCase();
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); s.className = "letter-slot"; s.innerHTML = "&nbsp;"; container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { container.removeChild(container.lastChild); }
                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar && targetChar !== " ") return;
                    const randomDelay = Math.floor(Math.random() * 200); 
                    const randomDuration = 10 + Math.floor(Math.random() * 15);
                    setTimeout(() => {
                        let cycles = 0;
                        const interval = setInterval(() => {
                            slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                            slot.classList.add('flapping');
                            if (++cycles >= randomDuration) {
                                clearInterval(interval);
                                slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                                slot.classList.remove('flapping');
                            }
                        }, 50);
                    }, randomDelay);
                });
            }

            async function geocodeAddress() {
                const query = document.getElementById('address-input').value;
                if(!query) return;
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
                    const data = await res.json();
                    if(data.length > 0) {
                        latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                        document.getElementById('search-section').classList.add('hidden');
                        getWeather();
                        if(!window.searchLoop) window.searchLoop = setInterval(executarBusca, 12000);
                        executarBusca();
                    }
                } catch(e) { }
            }

            async function getWeather() {
                if(!latAlvo) return;
                try {
                    const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latAlvo}&longitude=${lonAlvo}&current_weather=true`);
                    const data = await res.json();
                    weather.temp = Math.round(data.current_weather.temperature) + "°C";
                    weather.sky = data.current_weather.weathercode < 3 ? "CLEAR SKY" : "CLOUDY";
                } catch(e) {}
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    const radarLink = document.getElementById('radar-link');
                    if(data.found) {
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        updateProximityScale(data.dist);
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        radarLink.href = `https://www.radarbox.com/@${data.lat},${data.lon},z12`;
                        radarLink.classList.add('active');
                    } else {
                        currentTarget = null;
                        radarLink.classList.remove('active');
                        updateWithEffect('callsign', 'SEARCHING');
                        updateWithEffect('dist_body', '---');
                        updateWithEffect('alt', '---');
                        document.querySelectorAll('.scale-step').forEach(s => s.classList.remove('active'));
                    }
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'READY');
                
                setInterval(() => {
                    if(!currentTarget) {
                        const msgs = [`> CONNECTING SERVER...`,`> LOCAL TEMP: ${weather.temp}`,`> SKY: ${weather.sky}`,`> SCANNING AIRSPACE...` ];
                        updateWithEffect('status-container', msgs[step % msgs.length]);
                    } else {
                        const info = [`> TARGET LOCKED: ${currentTarget.callsign}`,`> SPEED: ${currentTarget.speed} KT`,`> ROUTE: ${currentTarget.origin} -> ${currentTarget.dest}`,`> POSITION: STABLE` ];
                        updateWithEffect('status-container', info[step % info.length]);
                    }
                    step++;
                }, 5000);

                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    document.getElementById('search-section').classList.add('hidden');
                    getWeather();
                    window.searchLoop = setInterval(executarBusca, 12000);
                    executarBusca();
                });
            };
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
        r = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=10).json()
        if r.get('ac'):
            ac = sorted([a for a in r['ac'] if 'lat' in a], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": ac.get('flight', ac.get('call', 'N/A')).strip(), 
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                "alt_ft": int(ac.get('alt_baro', 0) if isinstance(ac.get('alt_baro'), (int, float)) else 0), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0),
                "lat": ac['lat'], "lon": ac['lon'],
                "origin": ac.get('origin', 'N/A'), "dest": ac.get('destination', 'N/A')
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




















