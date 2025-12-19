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
            .search-container { display: none; background: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; gap: 5px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 90%; max-width: 500px; }
            input { flex: 1; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 16px; }
            button { background: #1A237E; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }
            .card { background: white; border-radius: 15px; display: flex; flex-direction: column; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #1A237E; overflow: hidden; width: 90%; max-width: 600px; }
            .header { background: #1A237E; color: white; padding: 10px; text-align: center; font-weight: bold; font-size: 1.5em; letter-spacing: 5px; }
            .main-content { display: flex; padding: 20px; }
            .data-section { flex: 2; border-right: 2px dashed #ccc; padding-right: 15px; }
            .side-section { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { font-size: 1.4em; font-weight: bold; color: #1A237E; margin-bottom: 10px; }
            .barcode { width: 100%; height: 50px; background: linear-gradient(90deg, #000 5%, transparent 5%, transparent 10%, #000 10%, #000 12%, transparent 12%, transparent 20%, #000 20%, #000 25%, transparent 25%, transparent 30%, #000 30%, #000 31%, transparent 31%, transparent 40%, #000 40%, #000 45%); background-size: 30px 100%; }
            .footer { background: #1A237E; color: #FFD700; padding: 8px; text-align: center; font-size: 0.8em; font-weight: bold; }
            @media (max-width: 500px) { .main-content { flex-direction: column; } .data-section { border-right: none; border-bottom: 2px dashed #ccc; padding-bottom: 15px; margin-bottom: 15px; } }
        </style>
    </head>
    <body onclick="pedirPermissao()">
        <div id="busca" class="search-container">
            <input type="text" id="endereco" placeholder="Digite Rua, Nº ou CEP...">
            <button onclick="buscarEndereco()">VIGIAR</button>
        </div>
        <div class="card">
            <div class="header">✈ BOARDING PASS ✈</div>
            <div class="main-content">
                <div class="data-section">
                    <div class="label">PASSENGER / CALLSIGN</div>
                    <div id="callsign" class="value">AGUARDANDO...</div>
                    <div class="label">FROM / TO</div>
                    <div id="route" class="value">--- / ---</div>
                </div>
                <div class="side-section">
                    <div class="label">DISTANCE</div>
                    <div id="dist" class="value">--- KM</div>
                    <div class="barcode"></div>
                </div>
            </div>
            <div id="status" class="footer">TOQUE NA TELA PARA ATIVAR ALERTAS</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null;
            let detectadoAnteriormente = false;

            function pedirPermissao() {
                // Ativa o som
                audioAlerta.play().then(() => { audioAlerta.pause(); audioAlerta.currentTime = 0; });
                
                // Pede permissão para notificações (essencial para tela bloqueada)
                if ("Notification" in window) {
                    Notification.requestPermission();
                }
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    document.getElementById('status').innerText = "VIGIANDO SUA POSIÇÃO";
                    setInterval(executarBusca, 20000); executarBusca();
                }, (err) => {
                    document.getElementById('status').innerText = "DIGITE O LOCAL:";
                    document.getElementById('busca').style.display = "flex";
                });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('status').innerText = "VIGIANDO: " + query.toUpperCase();
                    setInterval(executarBusca, 20000); executarBusca();
                }
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        
                        if (!detectadoAnteriormente) {
                            audioAlerta.play();
                            if (Notification.permission === "granted") {
                                new Notification("Avião Detectado!", { body: `Voo ${data.callsign} a ${data.dist}km`, icon: "/static/icon.png" });
                            }
                            detectadoAnteriormente = true;
                        }
                    } else {
                        document.getElementById('callsign').innerText = "BUSCANDO...";
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
                    return jsonify({"found": True, "callsign": p.get('callsign'), "dep": f.get('departure', 'UNK'), "arr": f.get('arrival', 'UNK'), "dist": round(d, 1)})
    except: pass
    return jsonify({"found": False})


