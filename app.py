from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configuração do Radar (Aumentado para detectar mais aviões)
RAIO_KM = 100.0 

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
        <title>Boarding Board Radar</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --main-blue: #236589; --yellow-text: #FFD700; }
            body { 
                background: #e0e0e0; 
                margin: 0; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                font-family: Arial, sans-serif;
            }

            /* Container principal seguindo as fotos */
            .ticket {
                width: 900px;
                background: white;
                border-radius: 20px;
                display: flex;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }

            /* Parte Esquerda (Azul) */
            .side-panel {
                width: 210px;
                background: var(--main-blue);
                color: white;
                padding: 20px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                border-right: 2px dashed rgba(255,255,255,0.3);
            }
            .radar-base { font-size: 10px; font-weight: bold; opacity: 0.8; }
            .seat-label { font-size: 14px; margin-top: 5px; }
            .seat-number { font-size: 80px; font-weight: 900; margin-top: -5px; }
            .atc-secure { font-size: 14px; opacity: 0.9; }

            /* Parte Direita (Conteúdo) */
            .main-panel { flex: 1; display: flex; flex-direction: column; }
            .blue-header { 
                background: var(--main-blue); 
                color: white; 
                padding: 15px; 
                text-align: center; 
                font-weight: bold; 
                font-size: 24px; 
                letter-spacing: 10px;
                display: flex;
                justify-content: space-around;
                align-items: center;
            }

            .info-grid { 
                padding: 30px 40px; 
                display: flex; 
                justify-content: space-between; 
                flex: 1; 
                background: white;
            }
            
            .label { color: #8c8c8c; font-size: 10px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 28px; font-weight: bold; color: var(--yellow-text); min-height: 35px; font-family: 'Courier New', monospace; }
            .data-blue { color: var(--main-blue); font-size: 22px; }

            /* Estilo do Código de Barras e Bússola */
            .visual-data { text-align: center; width: 180px; border-left: 1px solid #f0f0f0; padding-left: 20px; }
            #compass { font-size: 40px; color: #f39c12; transition: transform 0.8s; margin: 10px 0; }
            
            .barcode-box { margin-top: 15px; cursor: pointer; transition: opacity 0.2s; }
            .barcode-box:hover { opacity: 0.7; }
            #barcode { width: 140px; height: 60px; }

            /* Faixa Preta Inferior */
            .footer-black { 
                background: black; 
                height: 55px; 
                margin-top: auto; 
                display: flex; 
                align-items: center; 
                padding: 0 25px;
                border-top: 4px solid var(--yellow-text);
            }
            #status-text { color: var(--yellow-text); font-family: 'Courier New', monospace; font-weight: bold; font-size: 16px; }

            #search-ui { position: fixed; top: 20px; z-index: 100; background: white; padding: 10px; border-radius: 8px; display: flex; gap: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            #search-ui input { border: 1px solid #ccc; padding: 8px; border-radius: 4px; }
            #search-ui button { background: var(--main-blue); color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>

        <div id="search-ui">
            <input type="text" id="city" placeholder="CITY NAME OR ZIP...">
            <button onclick="manualStart()">CONNECT RADAR</button>
        </div>

        <div class="ticket">
            <div class="side-panel">
                <div>
                    <div class="radar-base">RADAR BASE</div>
                    <div class="seat-label">Seat:</div>
                    <div class="seat-number">19 A</div>
                    <div style="display:flex; gap:3px; margin-top:10px;">
                        <div style="width:12px; height:12px; background:rgba(255,255,255,0.2);"></div>
                        <div style="width:12px; height:12px; background:rgba(255,255,255,0.2);"></div>
                        <div style="width:12px; height:12px; background:rgba(255,255,255,0.2);"></div>
                    </div>
                </div>
                <div class="atc-secure">ATC Secure</div>
            </div>

            <div class="main-panel">
                <div class="blue-header">
                    <span>✈</span> BOARDING BOARD <span>✈</span>
                </div>
                
                <div class="info-grid">
                    <div style="flex: 1;">
                        <div class="label">IDENT / CALLSIGN</div>
                        <div id="call" class="value">SEARCHING</div>
                        
                        <div class="label">AIRCRAFT DISTANCE</div>
                        <div id="dist" class="value" style="color:#d4d4d4">---</div>
                        
                        <div class="label">ALTITUDE (MSL)</div>
                        <div id="alt" class="value" style="color:#d4d4d4">---</div>
                    </div>

                    <div class="visual-data">
                        <div class="label">TYPE</div>
                        <div id="type" class="data-blue">----</div>
                        
                        <div id="compass">↑</div>
                        
                        <a id="map-link" target="_blank" class="barcode-link">
                            <div class="barcode-box">
                                <svg id="barcode"></svg>
                            </div>
                        </a>
                    </div>
                </div>

                <div class="footer-black">
                    <div id="status-text">> INITIALIZING RADAR...</div>
                </div>
            </div>
        </div>

        <script>
            let userLat = null, userLon = null, step = 0;

            function updateFooter(msg) {
                document.getElementById('status-text').textContent = "> " + msg.toUpperCase();
            }

            async function manualStart() {
                const city = document.getElementById('city').value;
                const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${city}&limit=1`);
                const d = await r.json();
                if(d.length > 0) {
                    userLat = d[0].lat; userLon = d[0].lon;
                    document.getElementById('search-ui').style.display = 'none';
                    initRadar();
                }
            }

            function initRadar() {
                setInterval(fetchData, 7000);
                fetchData();
            }

            async function fetchData() {
                if(!userLat) return;
                try {
                    const response = await fetch(`/api/data?lat=${userLat}&lon=${userLon}`);
                    const data = await response.json();

                    if(data.found) {
                        // Atualiza Campos
                        document.getElementById('call').textContent = data.callsign;
                        document.getElementById('dist').textContent = data.dist.toFixed(1) + " KM";
                        document.getElementById('alt').textContent = data.alt.toLocaleString() + " FT";
                        document.getElementById('type').textContent = "...." + data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;

                        // Cores de ativo
                        document.getElementById('dist').style.color = '#236589';
                        document.getElementById('alt').style.color = '#236589';

                        // Código de Barras Clicável
                        const link = document.getElementById('map-link');
                        link.href = `https://www.flightradar24.com/${data.callsign}`;
                        
                        JsBarcode("#barcode", data.callsign, {
                            format: "CODE128",
                            width: 1.5,
                            height: 45,
                            displayValue: false,
                            lineColor: "#236589"
                        });

                        // Mensagens na Faixa Preta (Inglês)
                        const msgs = [
                            `TARGET LOCKED: ${data.callsign}`,
                            `GROUND SPEED: ${data.speed} KTS`,
                            `SQUAWK: ${data.squawk || '7000'}`,
                            `DATA SYNCED WITH BASE 19A`
                        ];
                        updateFooter(msgs[step % msgs.length]);
                    } else {
                        updateFooter("SCANNING AIRSPACE...");
                        document.getElementById('call').textContent = "SEARCHING";
                        document.getElementById('barcode').innerHTML = "";
                    }
                    step++;
                } catch(e) { updateFooter("LINK ERROR - RETRYING"); }
            }

            window.onload = () => {
                navigator.geolocation.getCurrentPosition(p => {
                    userLat = p.coords.latitude; userLon = p.coords.longitude;
                    document.getElementById('search-ui').style.display = 'none';
                    updateFooter("GPS CONNECTED");
                    initRadar();
                }, () => { updateFooter("MANUAL LOCATION REQUIRED"); });
            };
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat = float(request.args.get('lat', 0))
    lon = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=8).json()
        if r.get('ac'):
            valid = [a for a in r['ac'] if 'lat' in a]
            if not valid: return jsonify({"found": False})
            ac = sorted(valid, key=lambda x: haversine(lat, lon, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call') or "UNKN").strip(),
                "dist": haversine(lat, lon, ac['lat'], ac['lon']),
                "alt": int(ac.get('alt_baro', 0)),
                "bearing": calculate_bearing(lat, lon, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN'),
                "speed": ac.get('gs', 0),
                "squawk": ac.get('squawk')
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
