from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Configurações de Radar
RAIO_KM = 150.0 

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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Radar Boarding Pass Pro</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; overflow: hidden; }
            
            #search-box { display: none; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--warning-gold); width: 90%; max-width: 550px; gap: 10px; z-index: 100; }
            input { flex: 1; background: #000; border: 1px solid #333; padding: 12px; color: white; font-weight: bold; outline: none; }
            button { background: var(--warning-gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; }

            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 25px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; }
            .notch { position: absolute; width: 44px; height: 44px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -22px; } .notch-right { right: -22px; }

            .header { padding: 25px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 5px; font-size: 1.2em; }
            .header span { font-size: 3.5em; line-height: 0; }

            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 260px; border-radius: 2px; }
            .white-area::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; background-image: linear-gradient(to right, #ccc 40%, transparent 40%); background-size: 14px 100%; }

            .stamp { position: absolute; top: 50%; left: 45%; transform: translate(-50%, -50%) rotate(-12deg) scale(5); border: 4px double #d32f2f; color: #d32f2f; padding: 10px 20px; font-weight: 900; font-size: 2.2em; opacity: 0; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); z-index: 10; pointer-events: none; text-align: center; line-height: 1; }
            .stamp.visible { opacity: 0.25; transform: translate(-50%, -50%) rotate(-12deg) scale(1); }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.65em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; }
            
            #compass { display: inline-block; transition: transform 0.5s ease; font-size: 1.2em; color: var(--warning-gold); }
            
            /* CÓDIGO DE BARRAS CLICÁVEL */
            .barcode-link { text-decoration: none; width: 100%; display: block; cursor: pointer; transition: transform 0.2s; }
            .barcode-link:active { transform: scale(0.95); }
            .barcode { height: 65px; background: repeating-linear-gradient(90deg, #000, #000 1px, transparent 1px, transparent 3px, #000 3px, #000 4px); width: 100%; margin: 10px 0; border: 1px solid #eee; }
            
            .footer { padding: 10px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 10px; border-top: 2.5px solid var(--warning-gold); border-bottom: 2.5px solid var(--warning-gold); margin-bottom: 20px; }
            .status-msg { color: var(--warning-gold); font-size: 0.80em; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; text-align: center; min-height: 20px; padding: 0 10px; }
        </style>
    </head>
    <body>
        
        <div id="search-box">
            <input type="text" id="endereco" placeholder="ENTER ZIP CODE OR CITY...">
            <button onclick="buscarEndereco()">ACTIVATE</button>
        </div>

        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header"><span>✈</span> BOARDING PASS <span>✈</span></div>
            <div class="white-area">
                <div class="stamp" id="carimbo">VISUAL CONTACT</div>
                <div class="col-left">
                    <div><div class="label">IDENTIFICATION / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">ESTIMATED VISUAL (ETA)</div><div id="eta" class="value">-- MIN</div></div>
                    <div><div class="label">PRESSURE ALTITUDE (FL)</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">RANGE & BEARING</div>
                    <div class="value"><span id="dist">0.0 KM</span> <span id="compass">↑</span></div>
                    
                    <a id="map-link" class="barcode-link" target="_blank">
                        <div class="barcode"></div>
                    </a>
                    
                    <div class="label" style="font-size: 8px;">SIGNAL INTENSITY</div>
                    <div id="signal" style="color:var(--air-blue); font-weight:bold;">[ ▯▯▯▯▯ ]</div>
                </div>
            </div>
            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">INITIALIZING RADAR...</div>
            </div>
        </div>

        <script>
            let latAlvo = null, lonAlvo = null, targetLock = false, flightData = null;
            let weatherData = { temp: "--", vis: "--" };
            let currentMsgIndex = 0;

            function splitFlap(text) {
                const el = document.getElementById('status');
                let i = 0;
                const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ";
                const inter = setInterval(() => {
                    el.innerText = text.split('').map((c, idx) => i > idx ? c : chars[Math.floor(Math.random()*chars.length)]).join('');
                    if(i++ > text.length) clearInterval(inter);
                }, 20);
            }

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    latAlvo = pos.coords.latitude; lonAlvo = pos.coords.longitude;
                    iniciarRadar();
                }, () => { document.getElementById('search-box').style.display = "flex"; });
            };

            function iniciarRadar() {
                executarBusca();
                setInterval(executarBusca, 10000);
                setInterval(() => {
                    const searchMsgs = !targetLock ? 
                        ["SCANNING AIRSPACE", "RADAR ACTIVE", `TEMP: ${weatherData.temp} C`, `VISIBILITY: ${weatherData.vis} KM`] :
                        ["TARGET LOCKED", `CALLSIGN: ${flightData.callsign}`, "TAP BARCODE FOR LIVE MAP", "VISUAL CONTACT ACTIVE"];
                    currentMsgIndex = (currentMsgIndex + 1) % searchMsgs.length;
                    splitFlap(searchMsgs[currentMsgIndex]);
                }, 4500);
            }

            function executarBusca() {
                if(!latAlvo) return;
                fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=${Date.now()}`)
                .then(res => res.json()).then(data => {
                    if(data.weather) weatherData = data.weather;
                    if(data.found) {
                        flightData = data;
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = Math.round(data.alt * 3.28).toLocaleString() + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        document.getElementById('map-link').href = data.map_url;
                        document.getElementById('carimbo').classList.add('visible');
                        targetLock = true;
                    } else {
                        targetLock = false;
                        document.getElementById('carimbo').classList.remove('visible');
                        document.getElementById('callsign').innerText = "SEARCHING";
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    weather = {"temp": "--", "vis": "--"}
    try:
        wr = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat_u}&longitude={lon_u}&current=temperature_2m,visibility", timeout=2).json()
        if 'current' in wr:
            weather['temp'] = round(wr['current']['temperature_2m'])
            weather['vis'] = round(wr['current']['visibility'] / 1000, 1)
    except: pass

    # Tenta obter dados do radar
    url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
    try:
        r = requests.get(url, headers=headers, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                dist_km = haversine(lat_u, lon_u, ac['lat'], ac['lon'])
                
                # LINK ADS-B EXCHANGE: Foca na aeronave (hex) e mostra sua base (SiteLat/Lon)
                icao_hex = ac.get('hex', '')
                map_url = f"https://globe.adsbexchange.com/?lat={lat_u}&lon={lon_u}&zoom=9&hex={icao_hex}&SiteLat={lat_u}&SiteLon={lon_u}"
                
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip(), 
                    "dist": round(dist_km, 1), 
                    "alt": (ac.get('alt_baro') or ac.get('alt_geom') or 0) / 3.28, 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "map_url": map_url,
                    "weather": weather
                })
    except: pass

    return jsonify({"found": False, "weather": weather})

if __name__ == '__main__':
    app.run(debug=True)





























