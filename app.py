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
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; }
            body { background-color: #0a192f; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; }
            
            .search-container { display: none; background: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid var(--warning-gold); width: 90%; max-width: 500px; }
            input { flex: 1; background: #000; border: 1px solid var(--air-blue); padding: 12px; color: var(--warning-gold); font-weight: bold; width: 70%; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; }

            .card { background: #fdfdfd; color: #1a1a1a; width: 95%; max-width: 600px; border-radius: 4px; position: relative; box-shadow: 0 20px 50px rgba(0,0,0,0.8); overflow: hidden; border-left: 15px solid var(--air-blue); }
            
            /* Cabeçalho com Aviões Maiores */
            .header { background: var(--air-blue); color: white; padding: 20px; text-align: center; font-weight: 900; letter-spacing: 2px; font-size: 1.2em; border-bottom: 2px dashed #ccc; display: flex; justify-content: center; align-items: center; gap: 25px; }
            .header span { font-size: 1.8em; } /* Aumenta o tamanho do avião */

            .main-content { display: flex; padding: 25px; min-height: 200px; }
            .data-section { flex: 2; border-right: 2px dashed #ddd; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-between; }
            .side-section { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #777; font-size: 0.65em; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
            .value { font-size: 1.5em; font-weight: 900; color: var(--air-blue); }
            
            .barcode { height: 50px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin-top: 15px; }
            
            /* Rodapé Azul com Letras Amarelas Girando */
            .footer { background: var(--air-blue); color: var(--warning-gold); padding: 15px; text-align: center; font-size: 0.9em; font-weight: bold; border-top: 2px solid rgba(255,215,0,0.3); min-height: 40px; letter-spacing: 2px; text-transform: uppercase; display: flex; align-items: center; justify-content: center; }
            
            @media (max-width: 480px) {
                .main-content { flex-direction: column; }
                .data-section { border-right: none; border-bottom: 2px dashed #ddd; padding-bottom: 20px; }
                .side-section { padding-top: 20px; }
            }
        </style>
    </head>
    <body onclick="ativarAlertas()">
        <div id="busca" class="search-container">
            <input type="text" id="endereco" placeholder="DIGITE LOCAL...">
            <button onclick="buscarEndereco()">VIGIAR</button>
        </div>

        <div class="card">
            <div class="header">
                <span>✈</span> FLIGHT MANIFEST <span>✈</span>
            </div>
            <div class="main-content">
                <div class="data-section">
                    <div>
                        <div class="label">IDENT / CALLSIGN</div>
                        <div id="callsign" class="value">---</div>
                    </div>
                    <div>
                        <div class="label">SECTOR: ORIGIN / DEST</div>
                        <div id="route" class="value">--- / ---</div>
                    </div>
                    <div>
                        <div class="label">PRESSURE ALTITUDE (FL)</div>
                        <div id="alt" class="value">00000 FT</div>
                    </div>
                </div>
                <div class="side-section">
                    <div class="label">RANGE</div>
                    <div id="dist" class="value">0.0 KM</div>
                    <div class="barcode"></div>
                </div>
            </div>
            <div id="status" class="footer">STB...</div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:- ";
            let latAlvo = null, lonAlvo = null;
            let targetLock = false;
            let systemTime = "--:--:--";
            let frasesVigia = ["RADAR ACTIVE", "SCANNING AIRSPACE", "SECTOR SECURED"];
            let frasesTarget = ["TARGET LOCKED", "TRACKING FLIGHT", "SIGNAL STABLE"];
            let indiceFrase = 0;

            function ativarAlertas() { audioAlerta.play().then(() => audioAlerta.pause()); }

            // Efeito Split-Flap de letras girando
            function splitFlapEffect(finalText) {
                const elem = document.getElementById('status');
                let iterations = 0;
                const interval = setInterval(() => {
                    elem.innerText = finalText.split('').map((char, index) => {
                        if (iterations > index + 3) return char;
                        return chars[Math.floor(Math.random() * chars.length)];
                    }).join('');
                    if (iterations > finalText.length + 5) {
                        elem.innerText = finalText;
                        clearInterval(interval);
                    }
                    iterations++;
                }, 40);
            }

            function rotacionar() {
                let lista = targetLock ? frasesTarget : frasesVigia;
                let msg = lista[indiceFrase % lista.length] + " " + systemTime;
                splitFlapEffect(msg);
                indiceFrase++;
                setTimeout(rotacionar, 6000);
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    systemTime = new Date().toLocaleTimeString();
                    rotacionar();
                    iniciarRadar();
                }, () => {
                    document.getElementById('busca').style.display = "flex";
                    rotacionar();
                });
            };

            function iniciarRadar() {
                setInterval(executarBusca, 15000); 
                executarBusca();
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    systemTime = new Date().toLocaleTimeString();
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('route').innerText = data.dep + " / " + data.arr;
                        document.getElementById('alt').innerText = data.alt.toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        if (!targetLock) audioAlerta.play();
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('route').innerText = "--- / ---";
                        document.getElementById('alt').innerText = "--- FT";
                        document.getElementById('dist').innerText = "--- KM";
                    }
                });
            }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    iniciarRadar();
                }
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
                    return jsonify({"found": True, "callsign": p.get('callsign'), "dep": f.get('departure', 'UNK'), "arr": f.get('arrival', 'UNK'), "dist": round(d, 1), "alt": p.get('altitude', 0)})
    except: pass
    return jsonify({"found": False})




