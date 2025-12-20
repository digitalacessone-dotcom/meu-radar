from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 125.0  # raio de alcance do radar

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
    return render_template_string("""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar Interativo</title>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <style>
        body {
            margin: 0;
            font-family: sans-serif;
            background: #0a192f;
            color: white;
        }
        .card {
            max-width: 700px;
            margin: 20px auto;
            background: #1A237E;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0,0,0,0.6);
        }
        .header {
            background: #1A237E;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 1.5em;
            font-weight: bold;
        }
        .content {
            background: white;
            color: #1A237E;
            padding: 20px;
        }
        .label {
            font-size: 0.8em;
            color: #888;
            text-transform: uppercase;
            font-weight: bold;
        }
        .value {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        #map {
            height: 300px;
            width: 100%;
            margin-top: 15px;
            border-radius: 10px;
        }
        .footer {
            background: #000;
            color: #FFD700;
            text-align: center;
            padding: 15px;
            font-weight: bold;
            font-size: 1.1em;
            border-top: 4px solid #FFD700;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">✈ Radar Interativo ✈</div>
        <div class="content">
            <div class="label">Callsign</div>
            <div id="callsign" class="value">--</div>
            <div class="label">Origem / Destino</div>
            <div id="route" class="value">-- / --</div>
            <div class="label">Tipo / Velocidade</div>
            <div id="type_speed" class="value">-- / -- KTS</div>
            <div class="label">Altitude</div>
            <div id="alt" class="value">-- FT</div>
            <div class="label">Distância</div>
            <div id="dist_body" class="value">-- KM</div>
            <div class="label">Rumo</div>
            <div id="bearing" class="value">--°</div>
            <svg id="barcode"></svg>
            <div id="map"></div>
        </div>
        <div class="footer" id="status">INICIALIZANDO RADAR...</div>
    </div>

    <script>
        let latAlvo, lonAlvo;
        let map, userMarker, planeMarker;

        window.onload = function() {
            navigator.geolocation.getCurrentPosition(pos => {
                latAlvo = pos.coords.latitude;
                lonAlvo = pos.coords.longitude;
                initMap(latAlvo, lonAlvo);
                setInterval(executarBusca, 8000);
                executarBusca();
            }, () => {
                document.getElementById('status').textContent = "ERRO DE LOCALIZAÇÃO";
            });
        };

        function initMap(lat, lon) {
            map = L.map('map').setView([lat, lon], 8);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            userMarker = L.marker([lat, lon], {title: "Você"}).addTo(map);
        }

        function updatePlane(lat, lon, callsign) {
            if (planeMarker) map.removeLayer(planeMarker);
            planeMarker = L.marker([lat, lon], {title: callsign}).addTo(map);
            map.fitBounds(L.latLngBounds([userMarker.getLatLng(), planeMarker.getLatLng()]));
        }

        function executarBusca() {
            if (!latAlvo) return;
            fetch(`/api/data?lat=${latAlvo}&lon=${lonAlvo}&t=` + Date.now())
            .then(res => res.json())
            .then(data => {
                const statusElem = document.getElementById('status');
                if (data.found) {
                    document.getElementById('callsign').textContent = data.callsign;
                    document.getElementById('route').textContent = data.origin + " / " + data.dest;
                    document.getElementById('type_speed').textContent = data.type + " / " + data.speed + " KTS";
                    document.getElementById('alt').textContent = data.alt_ft + " FT";
                    document.getElementById('dist_body').textContent = data.dist + " KM";
                    document.getElementById('bearing').textContent = data.bearing + "°";
                    JsBarcode("#barcode", data.callsign, {
                        format: "CODE128", width: 1.5, height: 40, displayValue: false, lineColor: "#1A237E"
                    });
                    updatePlane(data.lat, data.lon, data.callsign);
                    statusElem.textContent = "ALVO IDENTIFICADO: " + data.callsign;
                } else {
                    statusElem.textContent = "ESCANEANDO O CÉU...";
                    document.getElementById('callsign').textContent = "--";
                    document.getElementById('barcode').innerHTML = "";
                    if (planeMarker) map.removeLayer(planeMarker);
                }
            })
            .catch(err => {
                document.getElementById('status').textContent = "ERRO DE CONEXÃO";
                console.error("Erro:", err);
            });
        }
    </script>
</body>
</html>
""")  # fim do render_template_string

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat') and a.get('lon')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                dist = round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)
                bearing = round(calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']), 2)
                return jsonify({
                    "found": True,
                    "callsign": ac.get("flight", "UNKNOWN"),
                    "origin": ac.get("r", "--"),
                    "dest": ac.get("d", "--"),
                    "type": ac.get("t", "--"),
                    "speed": ac.get("spd", 0),
                    "alt_ft": ac.get("alt_baro", 0),
                    "dist": dist,
                    "bearing": bearing,
                    "lat": ac['lat'],
                    "lon": ac['lon']
                })
    except Exception as e:
        print("Erro na API:", e)
    return jsonify({"found": False})
