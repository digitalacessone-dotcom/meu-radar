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
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
        <title>First Class Radar Pass</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { 
                --airline-blue: #1e4d6b; 
                --accent-gold: #c5a059; 
                --text-dark: #2c3e50;
                --bg-light: #e0e4e8;
            }
            
            body { 
                background: var(--bg-light); margin: 0; 
                display: flex; align-items: center; justify-content: center; 
                min-height: 100vh; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }

            /* Container Principal Estilo Cartão */
            .ticket {
                background: white; width: 95%; max-width: 750px;
                border-radius: 15px; display: flex; flex-direction: column;
                box-shadow: 0 15px 35px rgba(0,0,0,0.15); overflow: hidden;
            }

            /* Faixa Superior Azul */
            .ticket-header {
                background: var(--airline-blue); color: white;
                padding: 15px 30px; display: flex; justify-content: space-between; align-items: center;
            }
            .ticket-header h2 { margin: 0; font-weight: 300; letter-spacing: 4px; font-size: 1.2em; }
            .class-label { font-size: 0.8em; border: 1px solid white; padding: 2px 10px; border-radius: 20px; }

            /* Área Central Branca */
            .ticket-body { display: flex; min-height: 280px; }

            /* Stub Lateral (Canhoto) */
            .ticket-stub {
                width: 25%; background: #f9f9f9; padding: 25px;
                border-right: 2px dashed #ddd; display: flex; flex-direction: column; justify-content: center;
            }
            .stub-info { margin-bottom: 20px; }
            .stub-label { font-size: 0.6em; color: #999; text-transform: uppercase; font-weight: bold; }
            .stub-value { font-size: 1.5em; font-weight: bold; color: var(--airline-blue); }

            /* Conteúdo Principal */
            .ticket-main { flex: 1; padding: 25px 40px; position: relative; }
            
            .flight-info { display: flex; justify-content: space-between; margin-bottom: 30px; }
            .info-box { display: flex; flex-direction: column; }
            .label { font-size: 0.65em; color: #888; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.2em; font-weight: 700; color: var(--text-dark); }
            .value-alt { color: var(--accent-gold); font-family: 'Courier New', Courier, monospace; font-size: 1.4em; }

            /* Bússola e Elementos Visuais */
            .visuals { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
            #compass { font-size: 2.5em; transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1); color: var(--accent-gold); }
            #barcode { width: 160px; height: 50px; }

            /* Rodapé Preto com Letras Amarelas (Elegante) */
            .ticket-footer {
                background: #111; padding: 12px; 
                border-top: 4px solid var(--accent-gold);
                display: flex; align-items: center; justify-content: center;
            }
            .status-msg { 
                color: #FFD700; font-family: 'Courier New', monospace; 
                font-weight: bold; letter-spacing: 1px; font-size: 0.95em;
                text-transform: uppercase;
            }

            /* Decoração do Avião no Fundo */
            .airplane-bg {
                position: absolute; right: 10%; top: 40%; 
                font-size: 8em; color: rgba(0,0,0,0.03); transform: rotate(-45deg); pointer-events: none;
            }

            @media (max-width: 650px) {
                .ticket-body { flex-direction: column; }
                .ticket-stub { width: 100%; border-right: none; border-bottom: 2px dashed #ddd; padding: 15px 25px; }
                .airplane-bg { display: none; }
            }
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="ticket-header">
                <h2>RADAR BOARDING PASS</h2>
                <span class="class-label">FIRST CLASS</span>
            </div>

            <div class="ticket-body">
                <div class="ticket-stub">
                    <div class="stub-info">
                        <div class="stub-label">Radar Base</div>
                        <div class="stub-value">19 A</div>
                    </div>
                    <div class="stub-info">
                        <div class="stub-label">System</div>
                        <div class="stub-value" style="font-size: 1em;">SKY-SCAN v2</div>
                    </div>
                </div>

                <div class="ticket-main">
                    <div class="airplane-bg">✈</div>
                    
                    <div class="flight-info">
                        <div class="info-box">
                            <span class="label">Identification / Flight</span>
                            <span id="callsign" class="value-alt">SEARCHING</span>
                        </div>
                        <div class="info-box" style="text-align: right;">
                            <span class="label">Aircraft Type</span>
                            <span id="type" class="value">----</span>
                        </div>
                    </div>

                    <div class="flight-info">
                        <div class="info-box">
                            <span class="label">Distance</span>
                            <span id="dist_body" class="value">-- KM</span>
                        </div>
                        <div class="info-box">
                            <span class="label">Altitude</span>
                            <span id="alt" class="value">00000 FT</span>
                        </div>
                        <div class="info-box" style="text-align: right;">
                            <span class="label">Direction</span>
                            <div id="compass">↑</div>
                        </div>
                    </div>

                    <div class="visuals">
                        <div class="info-box">
                            <span class="label">Secure Auth</span>
                            <svg id="barcode"></svg>
                        </div>
                    </div>
                </div>
            </div>

            <div class="ticket-footer">
                <div id="status" class="status-msg">INITIALIZING RADAR...</div>
            </div>
        </div>

        <script>
            let latAlvo, lonAlvo;

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    setInterval(executarBusca, 8000); executarBusca();
                }, () => { 
                    document.getElementById('status').textContent = "SYSTEM ERROR: GPS REQUIRED"; 
                });
            };

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=` + Date.now())
                .then(res => res.json()).then(data => {
                    const statusElem = document.getElementById('status');
                    if(data.found) {
                        document.getElementById('callsign').textContent = data.callsign;
                        document.getElementById('dist_body').textContent = data.dist + " KM";
                        document.getElementById('alt').textContent = data.alt_ft.toLocaleString() + " FT";
                        document.getElementById('type').textContent = data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        statusElem.textContent = "TARGET ACQUIRED: " + data.callsign;

                        JsBarcode("#barcode", data.callsign, {
                            format: "CODE128", width: 1.2, height: 40, displayValue: false, lineColor: "#1e4d6b"
                        });
                    } else {
                        statusElem.textContent = "SCANNING LOCAL AIRSPACE...";
                        document.getElementById('callsign').textContent = "SEARCHING";
                        document.getElementById('barcode').innerHTML = "";
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
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1), 
                    "alt_ft": int(ac.get('alt_baro', 0)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "type": ac.get('t', 'UNKN')
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
