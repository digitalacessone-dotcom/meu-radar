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
    body { background:#0a192f; margin:0; font-family:'Courier New', monospace; color:white; }
    .card { background:#1A237E; width:95%; max-width:720px; margin:20px auto; border-radius:20px; box-shadow:0 20px 50px rgba(0,0,0,0.8); overflow:hidden; }
    .header { padding:15px 0; text-align:center; color:white; font-weight:900; letter-spacing:3px; }
    .white-area { background:#fff; margin:0 10px 10px; padding:20px 15px; border-radius:4px; }
    .info { display:flex; gap:15px; flex-wrap:wrap; }
    .col-left { flex:1.4; border-right:1px dashed #ddd; padding-right:15px; min-width:260px; }
    .col-right { flex:1; padding-left:15px; text-align:center; display:flex; flex-direction:column; align-items:center; justify-content:space-around; min-width:220px; }
    .label { color:#888; font-size:0.65em; font-weight:800; text-transform:uppercase; }
    .value { font-size:1.1em; font-weight:900; color:#1A237E; margin-bottom:10px; }
    #compass { display:inline-block; transition:transform 0.6s ease; color:#ff8c00; font-size:1.5em; }
    #barcode { width:100%; max-width:160px; height:50px; display:block; }
    #map { height:340px; width:100%; border-radius:10px; margin-top:15px; }
    .footer { background:#000; padding:15px; min-height:80px; display:flex; align-items:center; justify-content:center; border-top:4px solid #FFD700; }
    .status-msg { color:#FFD700; font-weight:900; font-size:1.1em; text-transform:uppercase; text-align:center; text-shadow:1px 1px 2px rgba(0,0,0,0.8); }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">✈ ATC BOARDING PASS ✈</div>
    <div class="white-area">
      <div class="info">
        <div class="col-left">
          <div class="label">IDENT / CALLSIGN</div><div id="callsign" class="value">SEARCHING</div>
          <div class="label">FLIGHT PATH</div><div id="route" class="value">-- / --</div>
          <div class="label">TYPE / SPEED</div><div id="type_speed" class="value">-- / -- KTS</div>
          <div class="label">DISTANCE</div><div id="dist_body" class="value">-- KM</div>
        </div>
        <div class="col-right">
          <div class="label">ALTITUDE</div><div id="alt" class="value">00000 FT</div>
          <div class="label">BEARING</div><div class="value"><span id="compass">↑</span></div>
          <svg id="barcode"></svg>
        </div>
      </div>
      <div id="map"></div>
    </div>
    <div class="footer"><div id="status" class="status-msg">INITIALIZING RADAR...</div></div>
  </div>

  <script>
    let latUser, lonUser;
    let map, userMarker, planeMarker;

    function initMap(lat, lon) {
      map = L.map('map').setView([lat, lon], 8);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
      userMarker = L.marker([lat, lon], { title: 'Você' }).addTo(map);
    }

    function updatePlane(lat, lon, callsign) {
      if (planeMarker) map.removeLayer(planeMarker);
      planeMarker = L.marker([lat, lon], { title: callsign }).addTo(map);
      map.fitBounds(L.latLngBounds([userMarker.getLatLng(), planeMarker.getLatLng()]), { padding: [20, 20] });
    }

    function setStatus(msg) {
      document.getElementById('status').textContent = msg;
    }

    function executarBusca() {
      if (latUser == null || lonUser == null) return;
      fetch(`/api/data?lat=${latUser}&lon=${lonUser}&t=${Date.now()}`)
        .then(res => res.json())
        .then(data => {
          if (data.found) {
            document.getElementById('callsign').textContent = data.callsign;
            document.getElementById('route').textContent = `${data.origin} / ${data.dest}`;
            document.getElementById('type_speed').textContent = `${data.type} / ${data.speed} KTS`;
            document.getElementById('alt').textContent = `${Number(data.alt_ft).toLocaleString()} FT`;
            document.getElementById('dist_body').textContent = `${data.dist} KM`;
            document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
            JsBarcode("#barcode", data.callsign || "UNKNOWN", {
              format: "CODE128", width: 1.5, height: 40, displayValue: false, lineColor: "#1A237E"
            });
            updatePlane(data.lat, data.lon, data.callsign);
            setStatus(`TARGET ACQUIRED: ${data.callsign}`);
          } else {
            setStatus("SCANNING AIRSPACE...");
            document.getElementById('callsign').textContent = "SEARCHING";
            document.getElementById('barcode').innerHTML = "";
            if (planeMarker) map.removeLayer(planeMarker);
          }
        })
        .catch(err => {
          setStatus("DATA LINK ERROR");
          console.error(err);
        });
    }

    window.onload = function() {
      if (!('geolocation' in navigator)) {
        setStatus("LOCATION ERROR: NO GPS");
        return;
      }
      navigator.geolocation.getCurrentPosition(
        pos => {
          latUser = pos.coords.latitude;
          lonUser = pos.coords.longitude;
          initMap(latUser, lonUser);
          setInterval(executarBusca, 8000);
          executarBusca();
        },
        err => {
          setStatus("LOCATION ERROR: ENABLE GPS AND HTTPS");
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    };
  </script>
</body>
</html>
""")

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            validos
