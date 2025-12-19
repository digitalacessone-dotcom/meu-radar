from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configurações
RAIO_KM = 100.0  # Aumentei o raio para facilitar testes iniciais

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
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #f0f4f7; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
            body { background-color: var(--bg-dark); margin: 0; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; overflow: hidden; }
            .card { background: white; width: 95%; max-width: 850px; border-radius: 20px; display: flex; overflow: hidden; border: 1px solid #ddd; box-shadow: 0 20px 40px rgba(0,0,0,0.1); position: relative; }
            .left-stub { width: 25%; background: var(--air-blue); color: white; padding: 20px; display: flex; flex-direction: column; border-right: 2px dashed rgba(255,255,255,0.3); }
            .seat-num { font-size: 4em; font-weight: 900; margin-top: 10px; }
            .main-ticket { flex: 1; display: flex; flex-direction: column; }
            .header-bar { background: var(--air-blue); height: 70px; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; color: white; }
            .header-bar h1 { font-size: 1.2em; letter-spacing: 5px; margin: 0; }
            .content-area { padding: 25px 40px; display: flex; flex: 1; }
            .col-data { flex: 2; border-right: 1px solid #eee; }
            .col-side { flex: 1; padding-left: 25px; text-align: center; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { font-size: 1.4em; font-weight: 900; color: var(--air-blue); margin-bottom: 15px; min-height: 1.2em; }
            .terminal-footer { background: #000; padding: 12px; border-top: 3px solid var(--warning-gold); min-height: 55px; display: flex; align-items: center; }
            .letter-slot { display: inline-block; color: var(--warning-gold); font-family: 'Courier New', monospace; font-weight: 900; min-width: 0.65em; text-align: center; }
            .flapping { animation: flap 0.07s infinite; }
            @keyframes flap { 50% { transform: scaleY(0.5); opacity: 0.5; } }
            #compass { font-size: 2.2em; transition: transform 0.8s ease; display: inline-block; color: #ff8c00; }
            #radar-link { display: block; text-decoration: none; pointer-events: none; transition: 0.5s; opacity: 0.2; }
            .barcode { width: 150px; height: 50px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); margin-top: 15px; margin-inline: auto; }
            #radar-link.active { pointer-events: auto; opacity: 1; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.7)">Your Radar</div>
                <div style="font-size: 0.8em;">Seat Number:</div>
                <div class="seat-num">19 A</div>
                <div style="margin-top: auto; font-size: 0.7em;">First Class / ATC</div>
            </div>
            <div class="main-ticket">
                <div class="header-bar"><span>✈</span><h1>BOARDING BOARD</h1><span>✈</span></div>
                <div class="content-area">
                    <div class="col-data">
                        <div class="label">Ident / Callsign</div><div id="callsign" class="value"></div>
                        <div class="label">Aircraft Distance</div><div id="dist_body" class="value"></div>
                        <div class="label">Altitude (MSL)</div><div id="alt" class="value"></div>
                    </div>
                    <div class="col-side">
                        <div class="label">Type</div><div id="type_id" class="value">----</div>
                        <div class="label">Bearing</div><div id="compass">↑</div>
                        <a id="radar-link" href="#" target="_blank"><div class="barcode"></div></a>
                    </div>
                </div>
                <div class="terminal-footer"><div id="status-container"></div></div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, currentTarget = null, step = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

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
                    if (slot.innerText === targetChar) return;
                    let cycles = 0;
                    const interval = setInterval(() => {
                        slot.innerText = chars[Math.floor(Math.random() * chars.length)];
                        slot.classList.add('flapping');
                        if (++cycles >= 8 + i) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 40);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status-container', '> INITIALIZING RADAR...');
                navigator.geolocation.getCurrentPosition(
                    pos => {
                        latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                        setInterval(executarBusca, 10000); executarBusca();
                    },
                    err => { updateWithEffect('status-container', '> ERROR: GPS DENIED'); }
                );

                setInterval(() => {
                    if(!currentTarget) {
                        const msgs = ["> SCANNING AIRSPACE", "> GPS SIGNAL OK", "> TEMP: 24C / SKY: CLEAR", "> WAITING TARGET"];
                        updateWithEffect('status-container', msgs[step % msgs.length]);
                    } else {
                        const info = [`> TARGET: ${currentTarget.callsign}`, `> SPEED: ${currentTarget.speed} KTS`, `> TYPE: ${currentTarget.type}`, `> PATH: ${currentTarget.origin} > ${currentTarget.dest}`];
                        updateWithEffect('status-container', info[step % info.length]);
                    }
                    step++;
                }, 6000);
            };

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
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        radarLink.classList.add('active');
                        radarLink.href = `https://www.radarbox.com/@${data.lat},${data.lon},z11`;
                    } else {
                        currentTarget = null;
                        radarLink.classList.remove('active');
                    }
                }).catch(e => console.error("Busca falhou:", e));
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
        # Tenta endpoint estável (V2)
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=8).json()
        
        if r.get('ac'):
            # Filtra apenas aeronaves que tenham localização válida
            valid_ac = [a for a in r['ac'] if 'lat' in a and 'lon' in a]
            if not valid_ac: return jsonify({"found": False})
            
            ac = sorted(valid_ac, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            
            return jsonify({
                "found": True, 
                "callsign": ac.get('flight', ac.get('call', 'N/A')).strip(), 
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                "alt_ft": int(ac.get('alt_baro', 0) if isinstance(ac.get('alt_baro'), (int, float)) else 0), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "origin": ac.get('t_from', '???'),
                "dest": ac.get('t_to', '???'),
                "type": ac.get('t', 'UNKN'), "speed": ac.get('gs', 0),
                "lat": ac['lat'], "lon": ac['lon']
            })
    except Exception as e:
        print(f"Erro na API: {e}")
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)














