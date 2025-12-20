from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

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
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Premium Pass</title>
        <style>
            :root { 
                --air-blue: #1a4a6e; 
                --warning-gold: #FFD700; 
                --bg-canvas: #e0e6ed; 
            }
            
            body { 
                background-color: var(--bg-canvas); margin: 0; padding: 0; 
                display: flex; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif;
            }

            .card { 
                background: white; width: 95%; max-width: 800px;
                border-radius: 15px; position: relative; 
                box-shadow: 0 30px 60px rgba(0,0,0,0.15); 
                display: flex; flex-direction: column; overflow: hidden;
                border: 1px solid rgba(0,0,0,0.1);
            }

            .ticket-main { display: flex; flex: 1; min-height: 250px; }

            .stub-side {
                width: 28%; background: var(--air-blue); color: white;
                padding: 30px 20px; display: flex; flex-direction: column;
                border-right: 2px dashed rgba(255,255,255,0.2);
            }

            .body-side { flex: 1; display: flex; flex-direction: column; }

            .header-strip { 
                background: var(--air-blue); padding: 15px 40px; 
                display: flex; justify-content: space-between; align-items: center; color: white;
            }
            .header-strip h1 { margin: 0; font-size: 1.2em; letter-spacing: 4px; font-weight: 300; }

            .info-grid { padding: 30px 40px; display: flex; justify-content: space-between; flex: 1; }
            
            .label { color: #999; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.6em; font-weight: 900; color: var(--air-blue); margin-bottom: 20px; }

            /* PAINEL INFERIOR PRETO COM LETRAS AMARELAS (FLAP) */
            .status-terminal { 
                background: #000; padding: 15px 40px; 
                border-top: 4px solid var(--warning-gold);
                min-height: 60px; display: flex; align-items: center;
                overflow: hidden;
            }

            .letter-slot {
                display: inline-block; background: #111; color: var(--warning-gold);
                font-family: 'Courier New', monospace; font-weight: 900; font-size: 1.1em;
                margin: 0 1px; padding: 2px 6px; border-radius: 3px;
                border: 1px solid #333; min-width: 0.7em; text-align: center;
            }

            .flapping { animation: flap-effect 0.07s infinite; }
            @keyframes flap-effect { 0% { transform: scaleY(1); } 50% { transform: scaleY(0.3); opacity: 0.5; } 100% { transform: scaleY(1); } }

            #compass { font-size: 2.5em; color: #ff9800; display: inline-block; transition: transform 1s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        </style>
    </head>
    <body>

        <div class="card">
            <div class="ticket-main">
                <div class="stub-side">
                    <div class="label" style="color:rgba(255,255,255,0.6)">Flight Sector</div>
                    <div style="font-size: 3.5em; font-weight: 900;">19A</div>
                    <div class="label" style="color:rgba(255,255,255,0.6); margin-top:auto;">Premium / ATC</div>
                </div>

                <div class="body-side">
                    <div class="header-strip">
                        <span>✈</span>
                        <h1>BOARDING BOARD</h1>
                        <span>✈</span>
                    </div>

                    <div class="info-grid">
                        <div style="flex: 2;">
                            <div class="label">Ident / Callsign</div>
                            <div id="callsign" class="value">SEARCHING</div>
                            <div class="label">Aircraft Distance</div>
                            <div id="dist_body" class="value">-- KM</div>
                            <div class="label">Altitude (MSL)</div>
                            <div id="alt" class="value">00000 FT</div>
                        </div>
                        <div style="flex: 1; text-align: center; border-left: 1px solid #eee; padding-left: 20px;">
                            <div class="label">Bearing</div>
                            <div id="compass">↑</div>
                            <div class="label" style="margin-top:20px">Type</div>
                            <div id="type_id" class="value">----</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="status-terminal">
                <div id="status-container"></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let step = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function updateFlapEffect(containerId, text) {
                const container = document.getElementById(containerId);
                const newText = text.toUpperCase();
                
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span"); s.className = "letter-slot"; s.innerHTML = "&nbsp;"; container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) { container.removeChild(container.lastChild); }

                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((char, i) => {
                    if (slots[i].innerText === char) return;
                    
                    let count = 0;
                    const iter = setInterval(() => {
                        slots[i].innerText = chars[Math.floor(Math.random() * chars.length)];
                        slots[i].classList.add('flapping');
                        if (++count > 10 + i) {
                            clearInterval(iter);
                            slots[i].innerText = char === " " ? "\u00A0" : char;
                            slots[i].classList.remove('flapping');
                        }
                    }, 50);
                });
            }

            window.onload = function() {
                updateFlapEffect('status-container', '> INITIALIZING RADAR...');
                
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(fetchData, 8000);
                    fetchData();
                });

                // Alternância de informações no painel amarelo
                setInterval(() => {
                    if(!currentTarget) {
                        const msgs = [
                            "> SCANNING AIRSPACE", 
                            "> GPS SIGNAL OK", 
                            "> TEMP: 24C / SKY: CLEAR",
                            "> VISIBILITY: 10KM+",
                            "> WAITING TARGET"
                        ];
                        updateFlapEffect('status-container', msgs[step % msgs.length]);
                    } else {
                        const info = [
                            `> TARGET: ${currentTarget.callsign}`,
                            `> SPEED: ${currentTarget.speed} KTS`,
                            `> TYPE: ${currentTarget.type}`,
                            `> PATH: ${currentTarget.origin} > ${currentTarget.dest}`
                        ];
                        updateFlapEffect('status-container', info[step % info.length]);
                    }
                    step++;
                }, 6000);
            };

            function fetchData() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(r => r.json()).then(data => {
                    if(data.found) {
                        currentTarget = data;
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('dist_body').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('type_id').innerText = data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
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
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                "alt_ft": int(ac.get('alt_baro', 0)), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "origin": ac.get('t_from', 'N/A').split(' ')[0],
                "dest": ac.get('t_to', 'N/A').split(' ')[0],
                "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0),
                "lat": ac['lat'], "lon": ac['lon']
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)
