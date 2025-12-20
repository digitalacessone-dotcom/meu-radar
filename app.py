from flask import Flask, render_template_string, jsonify, request
import requests
import random
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 80.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    y = sin(radians(lon2 - lon1)) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(radians(lat2)) * cos(radians(lon2 - lon1))
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Flight Radar Ticket</title>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --air-blue: #226488; --gold: #FFD700; }
            body { background: #0a192f; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: 'Courier New', monospace; margin: 0; }
            
            #search-box { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; gap: 10px; border: 1px solid var(--gold); }
            #search-box input { background: #000; border: 1px solid #444; padding: 10px; color: white; border-radius: 5px; }
            #search-box button { background: var(--gold); border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 5px; }

            .card { background: #fdfdfd; width: 850px; border-radius: 20px; display: flex; overflow: hidden; box-shadow: 0 15px 30px rgba(0,0,0,0.5); }
            .left { width: 25%; background: var(--air-blue); color: white; padding: 30px; border-right: 2px dashed rgba(0,0,0,0.1); display: flex; flex-direction: column; justify-content: space-between; }
            .right { flex: 1; display: flex; flex-direction: column; }
            
            .header { background: var(--air-blue); color: white; padding: 15px; font-size: 1.5em; letter-spacing: 5px; text-align: center; font-weight: bold; }
            .content { padding: 30px 40px; display: flex; justify-content: space-between; flex: 1; position: relative; }
            
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .value { font-size: 2.2em; font-weight: 900; color: var(--air-blue); margin-bottom: 20px; }
            .ident { color: #ccac00; }

            .footer { background: black; border-top: 4px solid var(--gold); height: 60px; display: flex; align-items: center; padding: 0 30px; }
            #status-msg { color: var(--gold); font-size: 1.1em; font-weight: bold; text-transform: uppercase; }
            
            #compass { font-size: 3.5em; color: #ff8c00; transition: transform 1s ease; }

            /* ESTILO DO CÓDIGO DE BARRAS */
            .barcode-area { margin-top: 20px; text-align: center; }
            #map-link { text-decoration: none; display: block; }
            #barcode { width: 100%; max-width: 160px; height: 60px; background: transparent; }
            
            /* Efeito visual para indicar que é clicável */
            .clickable-active { cursor: pointer; transition: opacity 0.2s; }
            .clickable-active:hover { opacity: 0.7; }
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="city" placeholder="ENTER CITY NAME...">
            <button onclick="start()">CONNECT</button>
        </div>

        <div class="card">
            <div class="left">
                <div>
                    <div class="label" style="color:#abd1e6">RADAR BASE</div>
                    <div style="font-size: 4.5em; font-weight: 900;">19 A</div>
                </div>
                <div style="font-size: 0.8em; opacity: 0.8; font-weight: bold;">ATC SECURE</div>
            </div>
            <div class="right">
                <div class="header">BOARDING BOARD</div>
                <div class="content">
                    <div>
                        <div class="label">IDENT / CALLSIGN</div><div id="call" class="value ident">SEARCHING</div>
                        <div class="label">AIRCRAFT DISTANCE</div><div id="dist" class="value">---</div>
                        <div class="label">ALTITUDE (MSL)</div><div id="alt" class="value">---</div>
                    </div>
                    <div style="text-align:center; min-width: 180px;">
                        <div class="label">BEARING</div>
                        <div id="compass">↑</div>
                        <div class="label" style="margin-top:10px">TYPE</div><div id="type" style="font-weight:bold; color:var(--air-blue)">----</div>
                        
                        <div class="barcode-area">
                            <a id="map-link" target="_blank">
                                <svg id="barcode"></svg>
                            </a>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <div id="status-msg">> STANDBY: GPS SEARCHING</div>
                </div>
            </div>
        </div>

        <script>
            let lat, lon;

            function updateFooter(txt) {
                document.getElementById('status-msg').textContent = "> " + txt.toUpperCase();
            }

            async function start() {
                const q = document.getElementById('city').value;
                const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`);
                const d = await r.json();
                if(d.length > 0) {
                    lat = d[0].lat; lon = d[0].lon;
                    document.getElementById('search-box').style.display = 'none';
                    updateFooter("LOCATION SYNCED");
                    setInterval(getData, 8000);
                    getData();
                }
            }

            async function getData() {
                if(!lat) return;
                try {
                    const res = await fetch(`/api/data?lat=${lat}&lon=${lon}`);
                    const data = await res.json();
                    
                    if(data.found) {
                        document.getElementById('call').textContent = data.callsign;
                        document.getElementById('dist').textContent = data.dist.toFixed(1) + " KM";
                        document.getElementById('alt').textContent = data.alt.toLocaleString() + " FT";
                        document.getElementById('type').textContent = data.type;
                        document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                        
                        // CONFIGURA O CÓDIGO DE BARRAS CLICÁVEL
                        const link = document.getElementById('map-link');
                        link.href = `https://www.flightradar24.com/${data.callsign}`;
                        link.classList.add('clickable-active');
                        
                        JsBarcode("#barcode", data.callsign, {
                            format: "CODE128",
                            width: 2,
                            height: 50,
                            displayValue: false,
                            lineColor: "#226488"
                        });

                        updateFooter(`LOCKED: ${data.callsign} | SPD: ${data.speed} KTS`);
                    } else {
                        updateFooter("SCANNING AIRSPACE...");
                        document.getElementById('map-link').removeAttribute('href');
                        document.getElementById('map-link').classList.remove('clickable-active');
                        document.getElementById('barcode').innerHTML = ""; // Limpa barcode se não houver avião
                    }
                } catch(e) { updateFooter("DATA LINK ERROR"); }
            }

            window.onload = () => {
                navigator.geolocation.getCurrentPosition(p => {
                    lat = p.coords.latitude; lon = p.coords.longitude;
                    document.getElementById('search-box').style.display = 'none';
                    updateFooter("GPS CONNECTED");
                    setInterval(getData, 8000);
                    getData();
                }, () => { updateFooter("WAITING FOR MANUAL INPUT"); });
            };
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    l1 = float(request.args.get('lat', 0)); l2 = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{l1}/lon/{l2}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=10).json()
        if r.get('ac'):
            # Pega o avião mais próximo com posição válida
            valid = [a for a in r['ac'] if 'lat' in a]
            if not valid: return jsonify({"found": False})
            ac = sorted(valid, key=lambda x: haversine(l1, l2, x['lat'], x['lon']))[0]
            
            return jsonify({
                "found": True, 
                "callsign": (ac.get('flight') or ac.get('call') or "UNKN").strip(),
                "dist": haversine(l1, l2, ac['lat'], ac['lon']),
                "alt": int(ac.get('alt_baro', 0)),
                "bearing": calculate_bearing(l1, l2, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN'),
                "speed": ac.get('gs', 0)
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
