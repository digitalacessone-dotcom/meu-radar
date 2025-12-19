from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# Configurações do Radar
RAIO_KM = 100.0 
API_URL = "https://api.vatsim.net/v2/fed/flights"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Radar Pro GPS</title>
        <style>
            body { 
                background-color: #124076; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                margin: 0; 
                font-family: 'Courier New', Courier, monospace; 
            }
            .card { 
                background: white; 
                border-radius: 15px; 
                display: flex;
                flex-direction: column;
                box-shadow: 0 15px 35px rgba(0,0,0,0.6);
                border: 2px solid #1A237E;
                overflow: hidden;
                transition: all 0.4s ease;
            }
            /* MODO DEITADO (PAISAGEM) */
            @media screen and (orientation: landscape) {
                .card { width: 600px; height: 260px; }
                .main-content { display: flex; flex: 1; padding: 15px; }
                .data-section { flex: 2; border-right: 2px dashed #ccc; padding-right: 15px; }
                .side-section { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; }
            }
            /* MODO EM PÉ (RETRATO) */
            @media screen and (orientation: portrait) {
                .card { width: 90%; height: auto; max-width: 350px; }
                .main-content { display: block; padding: 20px; }
                .data-section { border-right: none; border-bottom: 2px dashed #ccc; padding-bottom: 15px; margin-bottom: 15px; }
                .side-section { padding-left: 0; }
            }
            .header { background: #1A237E; color: white; padding: 10px; text-align: center; font-weight: bold; font-size: 1.5em; letter-spacing: 5px; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { font-size: 1.4em; font-weight: bold; color: #1A237E; margin-bottom: 10px; }
            .footer { background: #1A237E; color: #FFD700; padding: 8px; text-align: center; font-size: 0.9em; font-weight: bold; }
        </style>
    </head>
    <body onclick="ativarSom()">
        <div class="card">
            <div class="header">✈ BOARDING PASS ✈</div>
            <div class="main-content">
                <div class="data-section">
                    <div class="label">PASSENGER / CALLSIGN</div>
                    <div id="callsign" class="value">BUSCANDO...</div>
                    <div class="label">FROM / TO</div>
                    <div id="route" class="value">--- / ---</div>
                </div>
                <div class="side-section">
                    <div class="label">DISTANCE</div>
                    <div id="dist" class="value">--- KM</div>
                    <div class="label">ALTITUDE</div>
                    <div id="alt" class="value">--- FT</div>
                </div>
            </div>
            <div id="status" class="footer">STATUS: AGUARDANDO GPS...</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let somAtivado = false;
            let detectadoAnteriormente = false;

            function ativarSom() {
                if(!somAtivado) {
                    audioAlerta.play().then(() => {
                        audioAlerta.pause();
                        audioAlerta.currentTime = 0;
                        somAtivado = true;
                        console.log("Som desbloqueado");
                    });
                }
            }

            function update() {
                navigator.geolocation.getCurrentPosition(pos => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    fetch(`/api/data?lat=${lat}&lon=${lon}`).then(res => res.json()).then(data => {
                        if(data.found) {
                            document.getElementById('callsign').innerText = data.callsign;
                            document.getElementById('route').innerText = data.dep + " / " + data.arr;
                            document.getElementById('dist').innerText = data.dist + " KM";
                            document.getElementById('alt').innerText = data.alt + " FT";
                            document.getElementById('status').innerText = "AERONAVE DETECTADA!";
                            
                            if (!detectadoAnteriormente && somAtivado) {
                                audioAlerta.play();
                                detectadoAnteriormente = true;
                            }
                        } else {
                            document.getElementById('status').innerText = "BUSCANDO EM 100KM...";
                            detectadoAnteriormente = false;
                        }
                    });
                }, (err) => {
                    document.getElementById('status').innerText = "ERRO: ATIVE O GPS NO SAFARI";
                }, { enableHighAccuracy: false, timeout: 5000, maximumAge: 0 });
            }

            setInterval(update, 20000);
            update();
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_user = float(request.args.get('lat', 0))
    lon_user = float(request.args.get('lon', 0))
    if lat_user == 0: return jsonify({"found": False})
    try:
        r = requests.get(API_URL, timeout=10).json()
        for p in r.get('pilots', []):
            lat, lon = p.get('latitude'), p.get('longitude')
            if lat and lon:
                d = haversine(lat_user, lon_user, lat, lon)
                if d <= RAIO_KM:
                    f = p.get('flight_plan', {})
                    return jsonify({
                        "found": True, "callsign": p.get('callsign'),
                        "dep": f.get('departure', 'UNK'), "arr": f.get('arrival', 'UNK'),
                        "dist": round(d, 1), "alt": p.get('altitude', 0)
                    })
    except: pass
    return jsonify({"found": False})


