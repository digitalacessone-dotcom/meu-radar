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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>ATC Radar Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Courier New', monospace; overflow: hidden;
            }

            .letter-slot {
                display: inline-block;
                min-width: 0.65em;
                text-align: center;
                position: relative;
                vertical-align: bottom;
            }

            .flapping { opacity: 0.6; transform: scaleY(0.7); filter: brightness(1.5); }

            #search-box { 
                display: none; width: 90%; max-width: 500px; background: rgba(255,255,255,0.1);
                padding: 10px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--warning-gold); gap: 8px; z-index: 100;
            }
            #search-box input { flex: 1; background: #000; border: 1px solid #444; padding: 10px; color: white; border-radius: 6px; }
            #search-box button { background: var(--warning-gold); color: #000; border: none; padding: 10px 15px; font-weight: 900; border-radius: 6px; }

            .card { 
                background: var(--air-blue); width: 95%; max-width: 620px;
                border-radius: 15px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); 
                overflow: hidden; transform: scale(0.96);
            }

            .notch { position: absolute; width: 30px; height: 30px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -15px; } .notch-right { right: -15px; }

            .header { 
                padding: 10px 0; 
                text-align: center; 
                color: white; 
                font-weight: 900; 
                font-size: 0.9em;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                letter-spacing: 1px;
            }
            .header span { font-size: 1.4em; }

            .white-area { 
                background: #fdfdfd; margin: 0 8px; position: relative; 
                display: flex; padding: 20px 15px; min-height: 220px; border-radius: 3px; 
            }

            .col-left { flex: 1.6; border-right: 1px dashed #ddd; padding-right: 15px; display: flex; flex-direction: column; justify-content: center; }
            .col-right { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 0.6em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.25em; font-weight: 900; color: var(--air-blue); margin-bottom: 10px; min-height: 1.2em; display: flex; flex-wrap: wrap; }
            
            #compass { display: inline-block; transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); color: var(--warning-gold); font-size: 1.3em; }
            
            .barcode { 
                height: 40px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); 
                width: 100%; margin: 5px 0; border: 1px solid #eee; 
            }

            /* RODAPÉ COM FAIXAS AMARELAS MAIS ESPESSAS */
            .footer { 
                padding: 0 0 12px 0; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                background: var(--air-blue);
            }
            .yellow-lines { 
                width: 100%; 
                height: 6px; /* Aumentado */
                border-top: 2px solid var(--warning-gold); /* Aumentado de 1px para 2px */
                border-bottom: 2px solid var(--warning-gold); /* Aumentado de 1px para 2px */
                margin-bottom: 6px;
            }
            
            .status-msg { 
                color: var(--warning-gold); font-size: 0.68em; font-weight: bold; 
                text-transform: uppercase; text-align: center; padding: 0 10px; 
                display: flex; justify-content: center; flex-wrap: wrap;
                min-height: 1.1em; letter-spacing: 0.5px;
            }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="CITY OR ZIP...">
            <button onclick="buscarEndereco()">GO</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header">
                <span>✈</span> BOARDING BOARD <span>✈</span>
            </div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value"></div></div>
                    <div><div class="label">AIRCRAFT DISTANCE</div><div id="dist_body" class="value"></div></div>
                    <div><div class="label">ALTITUDE (MSL)</div><div id="alt" class="value"></div></div>
                </div>
                <div class="col-right">
                    <div class="label">BEARING</div>
                    <div class="value"><span id="compass">↑</span></div>
                    <a id="map-link" style="text-decoration:none; width:100%;" target="_blank">
                        <div class="barcode"></div>
                    </a>
                    <div id="signal-bars" style="color:var(--air-blue); font-size:11px; font-weight:900;">[ ▯▯▯▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg"></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let statusIndex = 0;
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:- ";

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                const newText = String(newValue).toUpperCase();
                while (container.childNodes.length < newText.length) {
                    const s = document.createElement("span");
                    s.className = "letter-slot";
                    s.innerHTML = "&nbsp;";
                    container.appendChild(s);
                }
                while (container.childNodes.length > newText.length) {
                    container.removeChild(container.lastChild);
                }
                const slots = container.querySelectorAll('.letter-slot');
                newText.split('').forEach((targetChar, i) => {
                    const slot = slots[i];
                    if (slot.innerText === targetChar) return;
                    let cycles = 0;
                    const maxCycles = 10 + (i * 1);
                    const interval = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        slot.classList.add('flapping');
                        cycles++;
                        if (cycles >= maxCycles) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 40);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status', 'INITIALIZING...');
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
                
                setInterval(() => {
                    if(!currentTarget) {
                        const systemMsgs = [
                            "RADAR SWEEP ACTIVE",
                            "VISIBILITY: CAVOK (10KM+)",
                            "ATC TRANSCEIVER: ONLINE",
                            "TEMP: 22C / SKY: CLEAR SKY"
                        ];
                        updateWithEffect('status', systemMsgs[statusIndex % systemMsgs.length]);
                        statusIndex++;
                    } else {
                        const flightMsgs = [
                            `TARGET: ${currentTarget.callsign}`,
                            `PATH: ${currentTarget.origin} > ${currentTarget.dest}`,
                            `TYPE: ${currentTarget.type} / ${currentTarget.speed}KTS`
                        ];
                        updateWithEffect('status', flightMsgs[statusIndex % 3]);
                        statusIndex++;
                    }
                }, 4500);
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
                        currentTarget = data;
                        updateWithEffect('callsign', data.callsign);
                        updateWithEffect('alt', data.alt_ft.toLocaleString() + " FT");
                        updateWithEffect('dist_body', data.dist + " KM");
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                    } else {
                        if(currentTarget) {
                            updateWithEffect('callsign', "SEARCHING");
                            updateWithEffect('dist_body', "-- KM");
                            updateWithEffect('alt', "00000 FT");
                        }
                        currentTarget = null;
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
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, headers=headers, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                    "alt_ft": int(ac.get('alt_baro', 0)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": f"https://globe.adsbexchange.com/?lat={lat_u}&lon={lon_u}&zoom=11&hex={ac.get('hex')}",
                    "origin": ac.get('t_from', 'N/A').split(' ')[0],
                    "dest": ac.get('t_to', 'N/A').split(' ')[0],
                    "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0)
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)



