from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

# Raio aumentado para 100km para garantir que pegue o tráfego da costa de Campos
RAIO_KM = 100.0 

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
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Manifest - Campos</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #050b14; }
            body { background-color: var(--bg-dark); display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; }
            .card { background: #fdfdfd; width: 95%; max-width: 600px; border-radius: 15px; overflow: hidden; position: relative; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
            .header { background: var(--air-blue); color: white; padding: 15px; text-align: center; font-weight: bold; letter-spacing: 2px; }
            .content { display: flex; padding: 20px; min-height: 250px; position: relative; }
            .main-info { flex: 2; border-right: 1px dashed #ccc; }
            .side-info { flex: 1; padding-left: 20px; text-align: center; }
            .label { color: #888; font-size: 0.7em; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 1.8em; font-weight: 900; color: var(--air-blue); margin-bottom: 15px; }
            .footer { background: var(--air-blue); padding: 10px; border-top: 4px solid var(--warning-gold); }
            .status { color: var(--warning-gold); text-align: center; font-size: 0.8em; font-weight: bold; }
            .stamp { position: absolute; top: 40%; left: 30%; border: 4px solid #d32f2f; color: #d32f2f; padding: 5px 15px; font-weight: 900; transform: rotate(-15deg); opacity: 0; transition: 0.5s; }
            .stamp.show { opacity: 0.4; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">LIVE RADAR MANIFEST</div>
            <div class="content">
                <div class="stamp" id="stamp">TARGET LOCKED</div>
                <div class="main-info">
                    <div class="label">Identification / Callsign</div>
                    <div id="callsign" class="value">SEARCHING</div>
                    <div class="label">Altitude (Baro)</div>
                    <div id="alt" class="value">00000 FT</div>
                    <div class="label">Ground Speed</div>
                    <div id="speed" class="value">--- KM/H</div>
                </div>
                <div class="side-info">
                    <div class="label">Range</div>
                    <div id="dist" class="value">0.0 KM</div>
                    <div class="label">Bearing</div>
                    <div id="bearing" class="value">0°</div>
                </div>
            </div>
            <div class="footer">
                <div id="status" class="status">CONNECTING TO CAMPOS UPLINK...</div>
            </div>
        </div>

        <script>
            let lat, lon;

            function updateRadar() {
                if(!lat) return;
                fetch(`/api/data?lat=${lat}&lon=${lon}`)
                .then(res => res.json())
                .then(data => {
                    const statusEl = document.getElementById('status');
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = data.alt + " FT";
                        document.getElementById('speed').innerText = data.speed + " KM/H";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('bearing').innerText = data.bearing + "°";
                        document.getElementById('stamp').classList.add('show');
                        statusEl.innerText = "TRACKING: " + data.callsign + " via " + data.source;
                    } else {
                        document.getElementById('callsign').innerText = "SEARCHING";
                        document.getElementById('stamp').classList.remove('show');
                        statusEl.innerText = "SCANNING CAMPOS AIRSPACE... (NO TARGETS)";
                    }
                })
                .catch(e => {
                    document.getElementById('status').innerText = "API CONNECTION ERROR - RETRYING";
                });
            }

            navigator.geolocation.getCurrentPosition(pos => {
                lat = pos.coords.latitude;
                lon = pos.coords.longitude;
                setInterval(updateRadar, 5000);
            }, () => {
                // Fallback para Campos caso GPS falhe
                lat = -21.76; lon = -41.33;
                setInterval(updateRadar, 5000);
            });
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat'))
    lon_u = float(request.args.get('lon'))
    
    # API 1: ADS-B Exchange (Alternativa mais robusta)
    try:
        url = f"https://opendata.adsbexchange.com/virtualradar/AircraftList.json?lat={lat_u}&lng={lon_u}&fDstL=0&fDstU={RAIO_KM}"
        # Se a API Exchange for instável, usamos o proxy da ADSB.lol que é o mais rápido hoje
        url_alt = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        
        r = requests.get(url_alt, timeout=5).json()
        if r.get('ac'):
            # Pega o avião mais próximo
            ac = sorted(r['ac'], key=lambda x: haversine(lat_u, lon_u, x.get('lat',0), x.get('lon',0)))[0]
            
            return jsonify({
                "found": True,
                "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1),
                "alt": int(ac.get('alt_baro', 0)),
                "speed": int(ac.get('gs', 0) * 1.852),
                "bearing": int(calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon'])),
                "source": "ADSB-LOL"
            })
    except Exception as e:
        print(f"Erro: {e}")
        
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True)













