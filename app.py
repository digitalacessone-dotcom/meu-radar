from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# Configurações de Radar Real-Time
RAIO_KM = 25.0  # Raio para avistamento visual a olho nu
API_OPENSKY = "https://opensky-network.org/api/states/all"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Visual Flight Radar 25KM</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; overflow: hidden; }
            
            /* Interface de Busca (aparece se o GPS falhar) */
            #search-box { display: none; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--warning-gold); width: 90%; max-width: 550px; gap: 10px; z-index: 100; }
            input { flex: 1; background: #000; border: 1px solid #333; padding: 12px; color: white; font-weight: bold; outline: none; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; }

            /* Bilhete Principal */
            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 25px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; transition: transform 0.3s ease; }
            
            /* Meias-luas laterais */
            .notch { position: absolute; width: 44px; height: 44px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -22px; } .notch-right { right: -22px; }

            /* Cabeçalho */
            .header { padding: 25px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 5px; font-size: 1.2em; }
            .header span { font-size: 2.2em; }

            /* Área do Manifesto */
            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 240px; border-radius: 2px; }
            .white-area::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; background-image: linear-gradient(to right, #ccc 40%, transparent 40%); background-size: 14px 100%; }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.7em; font-weight: 900; color: var(--air-blue); margin-bottom: 15px; }
            
            .barcode { height: 70px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 12px 0; }
            .scan-info { font-size: 9px; font-weight: 900; color: #444; letter-spacing: 1px; }

            /* Rodapé com Frases Rotativas */
            .footer { padding: 10px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 10px; border-top: 2.5px solid var(--warning-gold); border-bottom: 2.5px solid var(--warning-gold); margin-bottom: 20px; }
            .status-msg { color: var(--warning-gold); font-size: 0.9em; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; text-align: center; min-height: 20px; }

            /* SOLUÇÃO PARA CELULAR DEITADO (LANDSCAPE) */
            @media (max-height: 500px) and (orientation: landscape) {
                body { padding: 10px 0; }
                .card { transform: scale(0.75); margin: -40px 0; }
                .header { padding: 10px 0; }
                .white-area { min-height: 180px; padding: 15px 30px; }
                .footer { padding-bottom: 15px; }
                .yellow-lines { margin-bottom: 10px; }
            }
        </style>
    </head>
    <body onclick="audioAlerta.play().catch(()=>{})">
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="ENTER ZIP CODE OR CITY...">
            <button onclick="buscarEndereco()">ACTIVATE</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            
            <div class="header"><span>✈</span> FLIGHT MANIFEST / PASS <span>✈</span></div>
            
            <div class="white-area">
                <div class="col-left">
                    <div>
                        <div class="label">IDENTIFICATION / CALLSIGN</div>
                        <div id="callsign" class="value">SEARCHING</div>
                    </div>
                    <div>
                        <div class="label">AIRCRAFT REGISTRY</div>
                        <div id="origin" class="value">---</div>
                    </div>
                    <div>
                        <div class="label">PRESSURE ALTITUDE (FL)</div>
                        <div id="alt" class="value">00000 FT</div>
                    </div>
                </div>
                
                <div class="col-right">
                    <div class="label">RANGE TO TARGET</div>
                    <div id="dist" class="value">0.0 KM</div>
                    <div class="barcode"></div>
                    <div class="scan-info">VISUAL SCAN: 25KM</div>
                </div>
            </div>

            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">INITIALIZING RADAR...</div>
            </div>
        </div>

        <script>
            const audioAlerta = new Audio('https://www.soundjay.com/buttons/beep-07a.mp3');
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ";
            let latAlvo = null, lonAlvo = null;
            let targetLock = false;

            // Efeito Split-Flap para as letras girarem
            function splitFlap(text) {
                const el = document.getElementById('status');
                let i = 0;
                const inter = setInterval(() => {
                    el.innerText = text.split('').map((c, idx) => i > idx ? c : chars[Math.floor(Math.random()*chars.length)]).join('');
                    if(i++ > text.length) clearInterval(inter);
                }, 30);
            }

            // Tocar o bipe exatamente 5 vezes
            function alertBeepFiveTimes() {
                let count = 0;
                const interval = setInterval(() => {
                    audioAlerta.play().catch(() => {});
                    count++;
                    if (count >= 5) clearInterval(interval);
                }, 1000);
            }

            window.onload = function() {
                splitFlap("INITIALIZING RADAR...");
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => {
                    document.getElementById('search-box').style.display = "flex";
                });
            };

            function iniciarRadar() {
                executarBusca();
                setInterval(executarBusca, 10000); // Consulta a cada 10s
                
                // Reveza frases enquanto busca
                setInterval(() => {
                    if(!targetLock) {
                        const cycle = ["SCANNING LIVE AIRSPACE", "RADAR ACTIVE"];
                        splitFlap(cycle[Math.floor(Math.random() * cycle.length)]);
                    }
                }, 5000);
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('origin').innerText = data.origin;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        
                        if (!targetLock) { 
                            alertBeepFiveTimes(); 
                            splitFlap("TARGET LOCKED"); 
                        }
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('callsign').innerText = "SEARCHING";
                    }
                }).catch(() => {
                    const errors = ["SIGNAL LOST - RE-ESTABLISHING UPLINK", "DATA LINK FAILURE - RECONNECTING"];
                    splitFlap(errors[Math.floor(Math.random() * errors.length)]);
                });
            }

            async function buscarEndereco() {
                const query = document.getElementById('endereco').value;
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
                const data = await res.json();
                if(data.length > 0) {
                    latAlvo = parseFloat(data[0].lat); lonAlvo = parseFloat(data[0].lon);
                    document.getElementById('search-box').style.display = "none";
                    iniciarRadar();
                }
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    
    # Tentativa 1: ADS-B.LOL (API Direta e Rápida)
    try:
        r = requests.get(f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}", timeout=4).json()
        if r.get('ac'):
            best = r['ac'][0]
            d = haversine(lat_u, lon_u, best.get('lat'), best.get('lon'))
            return jsonify({"found": True, "callsign": best.get('flight', 'UNKN').strip(), "origin": "ADS-B LIVE", "dist": round(d, 1), "alt": best.get('alt_baro', 0) / 3.28})
    except: pass

    # Tentativa 2: OPENSKY NETWORK (Redundância)
    try:
        r = requests.get(API_OPENSKY, timeout=4).json()
        for s in r.get('states', []):
            if s[6] and s[5]:
                d = haversine(lat_u, lon_u, s[6], s[5])
                if d <= RAIO_KM:
                    return jsonify({"found": True, "callsign": s[1].strip() or "ACFT", "origin": s[2], "dist": round(d, 1), "alt": s[7] or 0})
    except: pass

    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)









