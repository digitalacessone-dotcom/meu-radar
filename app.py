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
            :root { --air-blue: #226488; --warning-gold: #FFD700; --bg-dark: #f0f4f7; }
            * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

            body { 
                background-color: var(--bg-dark); margin: 0; padding: 0; 
                display: flex; flex-direction: column; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif; overflow: hidden;
            }

            .card { 
                background: white; width: 95%; max-width: 850px;
                border-radius: 20px; position: relative; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1); 
                display: flex; overflow: hidden; border: 1px solid #ddd;
            }

            .left-stub {
                width: 25%; background: var(--air-blue); color: white;
                padding: 20px; display: flex; flex-direction: column;
                border-right: 2px dashed rgba(255,255,255,0.3); position: relative;
            }
            .left-stub .seat-num { font-size: 4em; font-weight: 900; margin-top: 20px; line-height: 1; }
            .left-stub .seat-label { font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }

            .main-ticket { flex: 1; display: flex; flex-direction: column; }

            .header-bar { 
                background: var(--air-blue); height: 80px; display: flex; 
                align-items: center; justify-content: space-between; padding: 0 40px; color: white;
            }
            .header-bar h1 { font-size: 1.5em; letter-spacing: 5px; margin: 0; }
            .plane-icon { font-size: 2em; opacity: 0.8; }

            .content-area { padding: 30px 50px; display: flex; flex: 1; background: white; }
            .col { display: flex; flex-direction: column; justify-content: space-around; }
            .col-data { flex: 2; border-right: 1px solid #eee; }
            .col-side { flex: 1; padding-left: 30px; align-items: center; }

            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); min-height: 1.2em; display: flex; }

            .terminal-footer { 
                background: #000; padding: 12px 40px; 
                border-top: 3px solid var(--warning-gold);
                min-height: 55px; display: flex; align-items: center;
            }

            .letter-slot { 
                display: inline-block; color: var(--warning-gold); 
                font-family: 'Courier New', monospace; font-weight: 900;
                min-width: 0.65em; text-align: center;
            }
            
            .flapping { animation: flap 0.07s infinite; }
            @keyframes flap { 50% { transform: scaleY(0.5); opacity: 0.5; } }

            #compass { font-size: 2.2em; transition: transform 0.8s ease; display: inline-block; color: #ff8c00; }
            
            /* ESTILO DO CÓDIGO DE BARRAS */
            #radar-link { 
                display: block; 
                text-decoration: none; 
                pointer-events: none; /* Desativado por padrão */
                transition: 0.5s;
                opacity: 0.2; /* Apagado por padrão */
            }

            .barcode { 
                width: 150px; height: 50px; 
                background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 5px); 
                margin-top: 20px; cursor: default;
            }

            /* Quando a aeronave é encontrada, essa classe é adicionada via JS */
            #radar-link.active {
                pointer-events: auto;
                opacity: 1;
            }
            #radar-link.active .barcode {
                cursor: pointer;
            }
            #radar-link.active:hover { transform: scale(1.05); }

        </style>
    </head>
    <body>

        <div class="card">
            <div class="left-stub">
                <div class="label" style="color: rgba(255,255,255,0.7)">Your Radar</div>
                <div class="seat-label">Seat Number:</div>
                <div class="seat-num">19 A</div>
                <div class="seat-label" style="margin-top: auto;">First Class / ATC</div>
            </div>

            <div class="main-ticket">
                <div class="header-bar">
                    <span class="plane-icon">✈</span>
                    <h1>BOARDING BOARD</h1>
                    <span class="plane-icon">✈</span>
                </div>

                <div class="content-area">
                    <div class="col col-data">
                        <div>
                            <div class="label">Ident / Callsign</div>
                            <div id="callsign" class="value"></div>
                        </div>
                        <div>
                            <div class="label">Aircraft Distance</div>
                            <div id="dist_body" class="value"></div>
                        </div>
                        <div>
                            <div class="label">Altitude (MSL)</div>
                            <div id="alt" class="value"></div>
                        </div>
                    </div>

                    <div class="col col-side">
                        <div class="label">Type</div>
                        <div id="type_id" class="value">----</div>
                        <div class="label" style="margin-top: 20px;">Bearing</div>
                        <div id="compass">↑</div>
                        
                        <a id="radar-link" href="javascript:void(0)" target="_blank">
                            <div class="barcode" title="VER NO RADARBOX"></div>
                        </a>
                    </div>
                </div>

                <div class="terminal-footer">
                    <div id="status-container"></div>
                </div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null;
            let currentTarget = null;
            let step = 0;
            const chars = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.:->";

            function updateWithEffect(id, newValue) {
                const container = document.getElementById(id);
                if (!container) return;
                const newText = String(newValue).toUpperCase();
                
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
                        if (++cycles >= 10 + i) {
                            clearInterval(interval);
                            slot.innerText = targetChar === " " ? "\u00A0" : targetChar;
                            slot.classList.remove('flapping');
                        }
                    }, 50);
                });
            }

            window.onload = function() {
                updateWithEffect('callsign', 'SEARCHING');
                updateWithEffect('status-container', '> INITIALIZING RADAR...');
                
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                });

                setInterval(() => {
                    if(!currentTarget) {
                        const msgs = ["> SCANNING AIRSPACE", "> GPS SIGNAL OK", "> TEMP: 24C / SKY: CLEAR", "> VISIBILITY: 10KM+", "> WAITING TARGET"];
                        updateWithEffect('status-container', msgs[step % msgs.length]);
                    } else {
                        const info = [
                            `> TARGET: ${currentTarget.callsign}`,
                            `> SPEED: ${currentTarget.speed} KTS`,
                            `> TYPE: ${currentTarget.type}`,
                            `> PATH: ${currentTarget.origin} > ${currentTarget.dest}`
                        ];
                        updateWithEffect('status-container', info[step % info.length]);
                    }
                    step++;
                }, 6000);
            };

            function iniciarRadar() { setInterval(executarBusca, 8000); executarBusca(); }

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
                        
                        // ATIVA O CLIQUE E O LINK
                        radarLink.classList.add('active');
                        radarLink.href = `https://www.radarbox.com/@${data.lat},${data.lon},z11`;
                    } else {
                        // DESATIVA CASO PERCA O SINAL
                        radarLink.classList.remove('active');
                        radarLink.href = "javascript:void(0)";
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














