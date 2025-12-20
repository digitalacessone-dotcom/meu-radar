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
    return render_template_string(open("template_leaflet.html", encoding="utf-8").read())

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
