from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

RAIO_KM = 25.0 
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
        <link rel="manifest" href="data:application/manifest+json,{% raw %}{"name":"RadarPro","short_name":"Radar","display":"standalone","start_url":"/"}{% endraw %}">
        <title>Radar Pro</title>
        <style>
            body { background-color: #124076; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', Courier, monospace; }
            .search-container { display: none; background: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; gap: 5px; width: 90%; max-width: 500px; }
            input { flex: 1; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 16px; }
            button { background: #1A237E; color: white; border: none; padding: 10px 15px; border-radius: 5px; font-weight: bold; }
            
            .card { background: white; border-radius: 15px; display: flex; flex-direction: column; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #1A237E; overflow: hidden; width: 95%; max-width: 600px; }
            .header { background: #1A237E; color: white; padding: 12px; text-align: center; font-weight: bold; font-size: 1.5em; letter-spacing: 5px; }
            
            .main-content { display: flex; padding: 15px; min-height: 180px; }
            .data-section { flex: 2; border-right: 2px dashed #ccc; padding-right: 15px; display: flex; flex-direction: column; justify-content: space-around; }
            .side-section { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.3em; font-weight: bold; color: #1A237E; margin-bottom: 8px; }
            .value a { color: #1A237E; text-decoration: underline; text-decoration-color: #FFD700; }
            
            .barcode { width: 100%; height: 60px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 4px, #000 4px, #000 5px, transparent 5px, transparent 8px); margin: 10px 0; }
            
            .footer { background: #1A237E; color: #FFD700; padding: 10px; text-align: center; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }
            
            @media (max-width: 480px) {
                .main-content { flex-direction: column; padding: 20px; }
                .data-section { border-right: none; border-bottom: 2px dashed #ccc; padding-right: 0; padding-bottom: 15px; margin-bottom: 15px; }
                .side-section { padding-left: 0; }
                .barcode { height: 40px; }
            }
        </style>
    </head>
    <body onclick="ativarAlertas()">
        <div id="busca" class="search-container">
            <input type="text" id="endereco" placeholder="Digite Rua, Nº ou CEP...">
            <button onclick="buscarEndereco()">VIGIAR</button>
        </div>

        <div class="card">
            <div class="header">✈ BOARDING PASS ✈</div>
            <div class="main-content">
                <div class="data-section">
                    <div>
                        <div class="label">PASSENGER / CALLSIGN</div>
                        <div id="callsign" class="value">BUSCANDO...</div>
                    </div>
                    <div>
                        <div class="label">FROM / TO</div>
                        <div id="route" class="value">--- / ---</div>
                    </div>
                    <div>
                        <div class="label">ALTITUDE</div>
                        <div id="alt" class="value">--- FT</div>
                    </div>
                </div>
                <div class="side-section">
                    <div class="label">DISTANCE</div>
                    <div id="dist" class="value">--- KM</div>
                    <div class="barcode"></div>
                    <div style="font-size: 0.6em; color: #555;">SCAN ACTIVE: 25KM</div>
                </div>
            </div>
            <div id="status" class="footer">AGUARDANDO GPS...</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null;
            let detectadoAnteriormente = false;

            function ativarAlertas() {
                audioAlerta.play().then(() => { audioAlerta.pause(); audioAlerta.currentTime = 0; });
                if ("Notification" in window) { Notification.requestPermission(); }
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    document.getElementById('status').innerText = "VIGIANDO SUA POSIÇÃO";
                    iniciarRadar();
                }, (err) => {
                    document.getElementById('status').innerText = "GPS INDISPONÍVEL. USE O ENDEREÇO:";
                    document.getElementById('busca').style.display = "flex";
                }, { timeout: 8000 });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                if(!query) return;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('status').innerText = "VIGIANDO: " + query.substring(0,20).toUpperCase();
                    iniciarRadar();
                }
            }

            function iniciarRadar() {
                setInterval(executarBusca, 15000); 
                executarBusca();
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(res => res.json()).then(data => {
                    if(data.found) {
                        const mapsUrl = `https://www.google.com/maps?q=${data.lat},${data.lon}`;
                        document.getElementById('callsign').innerHTML = `<a href="${mapsUrl}" target="_blank">${data.callsign}</a>`;
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('alt').innerText = data.alt.toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        
                        if (!detectadoAnteriormente) {
                            audioAlerta.play();
                            if (Notification.permission === "granted") {
                                new Notification("Avião Detectado!", { body: `Voo ${data.callsign} a ${data.dist}km` });
                            }
                            detectadoAnteriormente = true;
                        }
                    } else {
                        document.getElementById('callsign').innerText = "BUSCANDO...";
                        document.getElementById('route').innerText = "--- / ---";
                        document.getElementById('alt').innerText = "--- FT";
                        document.getElementById('dist').innerText = "--- KM";
                        detectadoAnteriormente = false;
                    }
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_user = float(request.args.get('lat', 0))
    lon_user = float(request.args.get('lon', 0))
    try:
        r = requests.get(API_URL, timeout=10).json()
        for p in r.get('pilots', []):
            lat, lon = p.get('latitude'), p.get('longitude')
            if lat and lon:
                d = haversine(lat_user, lon_user, lat, lon)
                if d <= RAIO_KM:
                    f = p.get('flight_plan', {})
                    return jsonify({
                        "found": True, 
                        "callsign": p.get('callsign'),
                        "dep": f.get('departure', 'UNK'), 
                        "arr": f.get('arrival', 'UNK'),
                        "dist": round(d, 1), 
                        "alt": p.get('altitude', 0),
                        "lat": lat, "lon": lon
                    })
    except: pass
    return jsonify({"found": False})

