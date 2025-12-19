from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

RAIO_KM = 100.0 # Raio maior para facilitar encontrar aviões
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Boarding Pass GPS</title>
        <style>
            body { background-color: #124076; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: sans-serif; }
            .card { width: 340px; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            .header { background: #1A237E; color: white; padding: 20px; text-align: center; font-weight: bold; font-size: 1.2em; }
            .content { padding: 20px; color: #333; }
            .label { color: #888; font-size: 0.8em; font-weight: bold; margin-top: 10px; }
            .value { font-size: 1.4em; font-weight: bold; color: #1A237E; margin-bottom: 15px; }
            .footer { background: #1A237E; color: #FFD700; padding: 12px; text-align: center; font-size: 0.8em; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">✈ BOARDING PASS (GPS)</div>
            <div class="content">
                <div class="label">PASSENGER / CALLSIGN</div>
                <div id="callsign" class="value">LOCALIZANDO...</div>
                <div class="label">FROM / TO</div>
                <div id="route" class="value">--- / ---</div>
                <div class="label">DISTANCE / ALTITUDE</div>
                <div id="info" class="value">--- KM / --- FT</div>
            </div>
            <div id="status" class="footer">AGUARDANDO GPS...</div>
        </div>
        <script>
            function update() {
                navigator.geolocation.getCurrentPosition(pos => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    fetch(`/api/data?lat=${lat}&lon=${lon}`).then(res => res.json()).then(data => {
                        if(data.found) {
                            document.getElementById('callsign').innerText = data.callsign;
                            document.getElementById('route').innerText = data.dep + " / " + data.arr;
                            document.getElementById('info').innerText = data.dist + " KM / " + data.alt + " FT";
                            document.getElementById('status').innerText = "AERONAVE PRÓXIMA!";
                        } else {
                            document.getElementById('status').innerText = "SEM VOOS EM 100KM";
                        }
                    });
                }, () => { document.getElementById('status').innerText = "ATIVE O GPS NO SAFARI"; });
            }
            setInterval(update, 30000);
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
