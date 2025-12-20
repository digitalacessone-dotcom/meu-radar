from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configurações do Radar
RAIO_KM = 120.0 # Aumentado para garantir detecção em áreas menos densas
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
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
        <title>ATC Radar System</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background: var(--bg-dark); margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: monospace; overflow: hidden; }

            #search-box { display: none; width: 90%; max-width: 500px; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--warning-gold); gap: 8px; z-index: 100; }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 10px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 15px; font-weight: 900; border-radius: 6px; cursor: pointer; }

            .card { background: var(--air-blue); width: 95%; max-width: 620px; border-radius: 15px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden; }
            
            .header { padding: 15px; text-align: center; color: white; font-weight: 900; letter-spacing: 5px; font-size: 1.1em; }
            
            .white-area { background: #fdfdfd; margin: 0 10px; display: flex; padding: 25px 20px; border-radius: 4px; border: 1px solid #ccc; }
            .col-left { flex: 1.6; border-right: 1px dashed #ddd; }
            .col-right { flex: 1; padding-left: 20px; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: space-around; }

            .label { color: #888; font-size: 0.7em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.6em; font-weight: 900; color: var(--air-blue); margin-bottom: 15px; height: 1.2em; display: flex; align-items: center; }
            
            #compass { font-size: 3.5em; color: var(--warning-gold); transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275); }

            .footer { background: #000; border-top: 4px solid var(--warning-gold); padding: 12px 20px; width: 100%; min-height: 55px; display: flex; align-items: center; }
            #status-text { color: var(--warning-gold); font-weight: bold; font-size: 1em; text-transform: uppercase; letter-spacing: 1px; }

            /* Efeito de flap para os valores principais */
            .letter-slot { display: inline-block; min-width: 0.6em; text-align: center; }
            .flapping { animation: flap-anim 0.08s infinite; }
            @keyframes flap-anim { 0% { transform: scaleY(1); } 50% { transform: scaleY(0.1); } 100% { transform: scaleY(1); } }
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="endereco" placeholder="ENTER CITY OR ZIPCODE...">
            <button onclick="buscarEndereco()">CONNECT</button>
        </div>

        <div class="card">
            <div class="header">✈ BOARDING BOARD ✈</div>
            <div class="white-area">
                <div class="col-left">
                    <div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value"></div>
                    <div class="label">AIRCRAFT DISTANCE</div><div id="dist_body" class="value"></div>
                    <div class="label">ALTITUDE (MSL)</div><div id="alt" class="value"></div>
                </div>
                <div class="col-right">
                    <div class="label">TYPE</div><div id="type_id" class="value">----</div>
                    <div id="compass">↑</div>
                    <div style="height:40px; width:120px; background:repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); opacity:0.1;"></div>
                </div>
            </div>
            <div class="footer">
                <div id="status-text">> INITIALIZING RADAR SYSTEM...</div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, step = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function updateFooter(msg) {
                document.getElementById('status-text').textContent = "> " + msg.toUpperCase();
            }

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                container.innerHTML = "";
                newText.split('').forEach((char, i) => {
                    const span = document.createElement("span");
                    span.className = "letter-slot";
                    span.textContent = char === " " ? "\u00A0" : char;
                    container.appendChild(span);
                });
            }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=1`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); 
                    lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-box').style.display = "none";
                    iniciarRadar();
                }
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('type_id', data.type);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        const msgs = [
                            `TARGET LOCKED: ${data.callsign}`,
                            `GROUND SPEED: ${data.speed} KTS`,
                            `SQUAWK: ${data.squawk || '7000'}`
                        ];
                        updateFooter(msgs[step % msgs.length]);
                    } else {
                        updateWithEffect('callsign', 'SEARCHING');
                        updateFooter("SCANNING AIRSPACE...");
                    }
                    step++;
                });
            }

            function iniciarRadar() { setInterval(executarBusca, 8000); executarBusca(); }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; 
                    lonAlvo = pos.coords.longitude;
                    updateFooter("GPS CONNECTED");
                    iniciarRadar();
                }, () => { 
                    document.getElementById('search-box').style.display = "flex"; 
                    updateFooter("WAITING FOR LOCATION INPUT");
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
        r = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=8).json()
        if r.get('ac'):
            # Filtra aviões que têm posição lat/lon
            valid_ac = [a for a in r['ac'] if 'lat' in a]
            if not valid_ac: return jsonify({"found": False})
            
            ac = sorted(valid_ac, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call') or "N/A").strip(), 
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                "alt_ft": int(ac.get('alt_baro', 0)), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN'), 
                "speed": ac.get('gs', 0),
                "squawk": ac.get('squawk')
            })
    except Exception as e:
        print(f"API Error: {e}")
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
