# No app.py, altere apenas a parte da busca no script para incluir este console.log de teste
# Ou substitua tudo para garantir:

from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

RAIO_KM = 25.0 
# Usando a URL de dados detalhados para garantir que não escape nada
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
        <title>Radar Pro</title>
        <style>
            body { background-color: #124076; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', Courier, monospace; }
            .search-container { display: flex; background: white; padding: 10px; border-radius: 10px; margin-bottom: 20px; gap: 5px; width: 90%; max-width: 500px; }
            input { flex: 1; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 16px; }
            button { background: #1A237E; color: white; border: none; padding: 10px 15px; border-radius: 5px; font-weight: bold; }
            .card { background: white; border-radius: 15px; display: flex; flex-direction: column; box-shadow: 0 15px 35px rgba(0,0,0,0.6); border: 2px solid #1A237E; overflow: hidden; width: 95%; max-width: 600px; }
            .header { background: #1A237E; color: white; padding: 12px; text-align: center; font-weight: bold; font-size: 1.5em; letter-spacing: 5px; }
            .main-content { display: flex; padding: 15px; min-height: 180px; }
            .data-section { flex: 2; border-right: 2px dashed #ccc; padding-right: 15px; display: flex; flex-direction: column; justify-content: space-around; }
            .side-section { flex: 1; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
            .value { font-size: 1.3em; font-weight: bold; color: #1A237E; margin-bottom: 8px; }
            .barcode { width: 100%; height: 60px; background: repeating-linear-gradient(90deg, #000, #000 2px, transparent 2px, transparent 4px, #000 4px, #000 5px, transparent 5px, transparent 8px); margin: 10px 0; }
            .footer { background: #1A237E; color: #FFD700; padding: 10px; text-align: center; font-size: 0.8em; font-weight: bold; }
            @media (max-width: 480px) { .main-content { flex-direction: column; } .data-section { border-right: none; border-bottom: 2px dashed #ccc; padding-bottom: 15px; margin-bottom: 15px; } }
        </style>
    </head>
    <body onclick="ativarAlertas()">
        <div class="search-container">
            <input type="text" id="endereco" placeholder="Digite CEP ou Rua...">
            <button onclick="buscarEndereco()">VIGIAR</button>
        </div>
        <div class="card">
            <div class="header">✈ BOARDING PASS ✈</div>
            <div class="main-content">
                <div class="data-section">
                    <div><div class="label">CALLSIGN</div><div id="callsign" class="value">BUSCANDO...</div></div>
                    <div><div class="label">ROUTE</div><div id="route" class="value">--- / ---</div></div>
                    <div><div class="label">ALTITUDE</div><div id="alt" class="value">--- FT</div></div>
                </div>
                <div class="side-section">
                    <div class="label">DISTANCE</div><div id="dist" class="value">--- KM</div>
                    <div class="barcode"></div>
                </div>
            </div>
            <div id="status" class="footer">INICIANDO SISTEMA...</div>
        </div>
        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            let latAlvo = null, lonAlvo = null;

            function ativarAlertas() { audioAlerta.play().then(() => { audioAlerta.pause(); }); }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('status').innerText = "VIGIANDO: " + query.toUpperCase();
                    executarBusca();
                }
            }

            function executarBusca() {
                if(!latAlvo) return;
                // Adicionamos um timestamp para evitar que o navegador use dados antigos (cache)
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${new Date().getTime()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('alt').innerText = data.alt + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        audioAlerta.play();
                    } else {
                        document.getElementById('callsign').innerText = "VIGIA ATIVA";
                        document.getElementById('status').innerText = "BUSCA REALIZADA EM: " + new Date().toLocaleTimeString();
                    }
                });
            }
            setInterval(executarBusca, 15000);
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
        # Se não houver voos na área, o programa continua buscando
        for p in r.get('pilots', []):
            lat, lon = p.get('latitude'), p.get('longitude')
            if lat and lon:
                d = haversine(lat_user, lon_user, lat, lon)
                if d <= RAIO_KM:
                    f = p.get('flight_plan', {})
                    return jsonify({"found": True, "callsign": p.get('callsign'), "dep": f.get('departure', 'UNK'), "arr": f.get('arrival', 'UNK'), "dist": round(d, 1), "alt": p.get('altitude', 0)})
    except: pass
    return jsonify({"found": False})

