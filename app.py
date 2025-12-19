from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 50.0 

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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Radar Flight Pass</title>
        <style>
            :root { --air-blue: #1A237E; --warning-gold: #FFD700; --bg-dark: #0a192f; }
            body { background-color: var(--bg-dark); display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; font-family: 'Courier New', monospace; overflow: hidden; }
            
            .card { background: var(--air-blue); width: 95%; max-width: 650px; border-radius: 25px; position: relative; box-shadow: 0 30px 60px rgba(0,0,0,0.7); overflow: hidden; }
            .notch { position: absolute; width: 44px; height: 44px; background: var(--bg-dark); border-radius: 50%; top: 50%; transform: translateY(-50%); z-index: 20; }
            .notch-left { left: -22px; } .notch-right { right: -22px; }

            .header { padding: 25px 0; text-align: center; color: white; display: flex; justify-content: center; align-items: center; gap: 20px; font-weight: 900; letter-spacing: 5px; font-size: 1.2em; }
            .header span { font-size: 2.2em; }

            .white-area { background: #fdfdfd; margin: 0 12px; position: relative; display: flex; padding: 30px; min-height: 260px; border-radius: 2px; }
            .white-area::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; background-image: linear-gradient(to right, #ccc 40%, transparent 40%); background-size: 14px 100%; }

            .col-left { flex: 1.8; border-right: 2px dashed #eee; padding-right: 20px; display: flex; flex-direction: column; justify-content: space-around; }
            .col-right { flex: 1; padding-left: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
            
            .label { color: #999; font-size: 0.65em; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; }
            .value { font-size: 1.65em; font-weight: 900; color: var(--air-blue); margin-bottom: 12px; }
            
            #compass { display: inline-block; transition: transform 0.5s ease; font-size: 1.2em; color: var(--warning-gold); }
            
            .footer { padding: 10px 0 25px 0; display: flex; flex-direction: column; align-items: center; background: var(--air-blue); }
            .yellow-lines { width: 100%; height: 10px; border-top: 2.5px solid var(--warning-gold); border-bottom: 2.5px solid var(--warning-gold); margin-bottom: 20px; }
            .status-msg { color: var(--warning-gold); font-size: 0.85em; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; text-align: center; min-height: 20px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="notch notch-left"></div>
            <div class="notch notch-right"></div>
            <div class="header"><span>✈</span> FLIGHT MANIFEST <span>✈</span></div>
            <div class="white-area">
                <div class="col-left">
                    <div><div class="label">AIRCRAFT CALLSIGN</div><div id="callsign" class="value">SEARCHING</div></div>
                    <div><div class="label">PRESSURE ALTITUDE</div><div id="alt" class="value">00000 FT</div></div>
                </div>
                <div class="col-right">
                    <div class="label">BEARING</div>
                    <div id="compass">↑</div>
                    <div id="dist" class="value" style="margin-top:10px;">0.0 KM</div>
                </div>
            </div>

            <div class="footer">
                <div class="yellow-lines"></div>
                <div id="status" class="status-msg">INITIALIZING RADAR...</div>
            </div>
        </div>

        <script>
            let lat, lon;
            let targetLock = false;
            let weatherData = { temp: "--", vis: "--", desc: "STBY" };

            window.onload = function() {
                navigator.geolocation.getCurrentPosition(pos => {
                    lat = pos.coords.latitude; lon = pos.coords.longitude;
                    iniciarRadar();
                }, () => { lat = -21.76; lon = -41.33; iniciarRadar(); });
            };

            function iniciarRadar() {
                executarBusca();
                setInterval(executarBusca, 8000);
                
                let cycle = 0;
                setInterval(() => {
                    const bar = document.getElementById('status');
                    // Aqui entra a temperatura e visibilidade rotacionando junto com o resto
                    const msgs = targetLock ? 
                        ["TARGET LOCKED", "VISUAL CONTACT RECOMMENDED"] : 
                        ["SCANNING AIRSPACE", `TEMP: ${weatherData.temp}°C`, `VISIBILITY: ${weatherData.vis}KM`, `SKY: ${weatherData.desc}`];
                    
                    bar.innerText = msgs[cycle % msgs.length];
                    cycle++;
                }, 4000);
            }

            function executarBusca() {
                fetch(`/api/data?lat=${lat}&lon=${lon}`).then(res => res.json()).then(data => {
                    weatherData = data.weather;
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('alt').innerText = data.alt + " FT";
                        document.getElementById('dist').innerText = data.dist + " KM";
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        targetLock = true;
                    } else {
                        targetLock = false;
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
    l_lat, l_lon = float(request.args.get('lat')), float(request.args.get('lon'))
    
    # Clima
    weather = {"temp": "--", "vis": "--", "desc": "N/A"}
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={l_lat}&longitude={l_lon}&current=temperature_2m,visibility,weather_code"
        wr = requests.get(w_url, timeout=2).json()
        weather = {
            "temp": round(wr['current']['temperature_2m']),
            "vis": round(wr['current']['visibility']/1000, 1),
            "desc": "CLEAR" if wr['current']['weather_code'] == 0 else "CLOUDY" if wr['current']['weather_code'] < 50 else "RAINY"
        }
    except: pass

    # Radar
    try:
        url = f"https://api.adsb.one/v2/lat/{l_lat}/lon/{l_lon}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=4).json()
        if r.get('ac'):
            ac = sorted(r['ac'], key=lambda x: haversine(l_lat, l_lon, x.get('lat',0), x.get('lon',0)))[0]
            return jsonify({
                "found": True, "callsign": ac.get('flight', 'UNKN').strip(),
                "dist": round(haversine(l_lat, l_lon, ac['lat'], ac['lon']), 1),
                "alt": int(ac.get('alt_baro', 0)),
                "bearing": int(calculate_bearing(l_lat, l_lon, ac['lat'], ac['lon'])),
                "weather": weather
            })
    except: pass
    return jsonify({"found": False, "weather": weather})

if __name__ == '__main__':
    app.run(debug=True)













