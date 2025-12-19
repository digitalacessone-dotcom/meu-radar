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
        <title>Radar Boarding Pass</title>
        <style>
            body { background-color: #124076; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', Courier, monospace; }
            .search-container { display: none; background: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; gap: 5px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); width: 90%; max-width: 500px; }
            input { flex: 1; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 16px; }
            button { background: #1A237E; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; }
            
            .card { background: white; border-radius: 15px; display: flex; flex-direction: column; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #1A237E; overflow: hidden; width: 90%; max-width: 600px; position: relative; }
            
            .header { background: #1A237E; color: white; padding: 10px; text-align: center; font-weight: bold; font-size: 1.5em; letter-spacing: 5px; }
            
            .main-content { display: flex; padding: 20px; }
            .data-section { flex: 2; border-right: 2px dashed #ccc; padding-right: 15px; }
            .side-section { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: space-between; align-items: center; }
            
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { font-size: 1.4em; font-weight: bold; color: #1A237E; margin-bottom: 10px; }
            .value a { color: #1A237E; text-decoration: none; border-bottom: 2px solid #FFD700; }
            
            /* Estilo do Código de Barras */
            .barcode { width: 100%; height: 50px; background: linear-gradient(90deg, #000 5%, transparent 5%, transparent 10%, #000 10%, #000 12%, transparent 12%, transparent 20%, #000 20%, #000 25%, transparent 25%, transparent 30%, #000 30%, #000 31%, transparent 31%, transparent 40%, #000 40%, #000 45%); background-size: 30px 100%; }
            
            .footer { background: #1A237E; color: #FFD700; padding: 8px; text-align: center; font-size: 0.8em; font-weight: bold; }
            
            @media (max-width: 500px) {
                .main-content { flex-direction: column; }
                .data-section { border-right: none; border-bottom: 2px dashed #ccc; padding-right: 0; padding-bottom: 15px; margin-bottom: 15px; }
                .side-section { padding-left: 0; }
            }
        </style>
    </head>
    <body onclick="ativarSom()">
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
                    <div class="label">ALTITUDE</div>
                    <div id="alt" class="value">--- FT</div>
                </div>
                <div class="side-section">
                    <div class="label">DISTANCE</div>
                    <div id="dist" class="value">--- KM</div>
                    <div class="barcode"></div>
                    <div style="font-size: 0.6em; margin-top: 5px;">25KM SCAN ACTIVE</div>
                </div>
            </div>
            <div id="status" class="footer">TENTANDO ACESSAR GPS...</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let somAtivado = false;
            let latAlvo = null, lonAlvo = null;
            let timerBusca = null;

            function ativarSom() { somAtivado = true; }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude;
                    lonAlvo = pos.coords.longitude;
                    document.getElementById('status').innerText = "VIGIANDO SUA POSIÇÃO (25KM)";
                    iniciarRadar();
                }, (err) => {
                    document.getElementById('status').innerText = "GPS INDISPONÍVEL. DIGITE O LOCAL:";
                    document.getElementById('busca').style.display = "flex";
                }, { timeout: 8000 });
            };

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                if(!query) return;
                try {
                    const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                    const data = await res.json();
                    if(data.length > 0) {
                        latAlvo = parseFloat(data[0].lat);
                        lonAlvo = parseFloat(data[0].lon);
                        document.getElementById('status').innerText = "VIGIANDO: " + query.toUpperCase();
                        iniciarRadar();
                    }
                } catch(e) { alert("Erro ao localizar endereço."); }
            }

            function iniciarRadar() {
                if(timerBusca) clearInterval(timerBusca);
                executarBusca();
                timerBusca = setInterval(executarBusca, 20000);
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}`).then(res => res.json()).then(data => {
                    if(data.found) {
                        // O Callsign vira um link para o Google Maps
                        const mapUrl = `https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lon}`;
                        document.getElementById('callsign').innerHTML = `<a href="${mapUrl}" target="_blank">${data.callsign}</a>`;
                        
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('alt').innerText = data.alt + " FT";
                        
                        if(somAtivado) audioAlerta.play();
                    } else {
                        document.getElementById('callsign').innerText = "BUSCANDO...";
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
                        "lat": lat,
                        "lon": lon
                    })
    except: pass
    return jsonify({"found": False})


