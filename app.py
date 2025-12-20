from flask import Flask, render_template_string, jsonify, request
import requests
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 25.0 

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
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Boarding Board Radar</title>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/flapper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/jquery.flapper.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>

        <style>
            :root { --blue: #2A6E91; --yellow: #FFD700; }
            body { background: #F0F2F5; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: sans-serif; overflow: hidden; }
            
            .search-bar { background: white; width: 90%; max-width: 850px; padding: 12px 20px; border-radius: 15px; display: flex; gap: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 30px; }
            .search-bar input { flex: 1; border: 1px solid #E0E0E0; padding: 12px; border-radius: 8px; outline: none; }
            .search-bar button { background: var(--blue); color: white; border: none; padding: 12px 25px; border-radius: 8px; font-weight: bold; cursor: pointer; }

            .ticket { background: white; width: 90%; max-width: 850px; height: 450px; border-radius: 30px; display: flex; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.12); position: relative; }
            
            .stub { background: var(--blue); width: 230px; padding: 35px 25px; color: white; display: flex; flex-direction: column; border-right: 2px dashed rgba(255,255,255,0.3); }
            .seat-num { font-size: 80px; font-weight: 800; margin: 10px 0; line-height: 1; }
            .dot-container { display: flex; gap: 5px; margin-top: 10px; }
            .dot { width: 14px; height: 14px; background: rgba(255,255,255,0.2); border-radius: 3px; }

            .main { flex: 1; display: flex; flex-direction: column; }
            .header-strip { background: var(--blue); color: white; padding: 18px 45px; display: flex; justify-content: space-between; align-items: center; }
            .header-strip h1 { margin: 0; font-size: 26px; letter-spacing: 12px; font-weight: 400; text-transform: uppercase; }

            .info-grid { padding: 40px 50px; display: flex; flex: 1; }
            .data-col { flex: 1.4; }
            .visual-col { flex: 1; border-left: 1px solid #F0F0F0; padding-left: 30px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; }

            .label { color: #999; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; }
            
            .flapper .digit { 
                background-color: #111 !important; 
                color: var(--yellow) !important; 
                border-radius: 3px !important; 
                border: 1px solid #333 !important;
            }

            #compass { font-size: 45px; color: #FF8C00; transition: transform 0.8s ease; }
            #barcode { width: 170px; height: 65px; }

            /* Footer com Texto Rotativo */
            .footer-black { background: #000; height: 75px; border-top: 5px solid var(--yellow); display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }
            .status-wrapper { width: 100%; text-align: center; position: relative; }
            .status-msg { 
                color: var(--yellow); font-family: 'Courier New', monospace; font-weight: bold; font-size: 18px; 
                text-transform: uppercase; position: absolute; width: 100%; left: 0; top: 50%; 
                transform: translateY(-50%); transition: opacity 1s, transform 1s; opacity: 0;
            }
            .status-msg.active { opacity: 1; transform: translateY(-50%) scale(1); }
        </style>
    </head>
    <body>

        <div class="search-bar">
            <input type="text" placeholder="Enter City or Location...">
            <button>CONNECT RADAR</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div style="font-size: 10px; font-weight: bold; opacity: 0.7;">RADAR BASE</div>
                <div style="font-size: 14px; margin-top: 10px;">Seat:</div>
                <div class="seat-num">19 A</div>
                <div class="dot-container">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
                <div style="margin-top: auto; font-size: 15px; opacity: 0.9;">ATC Secure</div>
            </div>

            <div class="main">
                <div class="header-strip">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>

                <div class="info-grid">
                    <div class="data-col">
                        <div class="label">Ident / Callsign</div>
                        <input id="flap_callsign" class="flap" />
                        <div class="label">Aircraft Distance</div>
                        <input id="flap_dist" class="flap" />
                        <div class="label">Altitude (MSL)</div>
                        <input id="flap_alt" class="flap" />
                    </div>
                    <div class="visual-col">
                        <div style="text-align: center;">
                            <div class="label">Aircraft Type</div>
                            <input id="flap_type" class="flap" />
                        </div>
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>

                <div class="footer-black">
                    <div class="status-wrapper">
                        <div id="msg1" class="status-msg active">SCANNING AIRSPACE...</div>
                        <div id="msg2" class="status-msg">TEMP: --°C | VIS: --KM</div>
                        <div id="msg3" class="status-msg">SKY: LOADING...</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const optCall = { width: 10, chars_preset: 'alphanum' };
            const optDist = { width: 10, chars_preset: 'num' };
            const optAlt = { width: 10, chars_preset: 'num' };
            const optType = { width: 8, chars_preset: 'alphanum' };

            const $fCall = $('#flap_callsign').flapper(optCall);
            const $fDist = $('#flap_dist').flapper(optDist);
            const $fAlt = $('#flap_alt').flapper(optAlt);
            const $fType = $('#flap_type').flapper(optType);

            let currentMsg = 1;
            let weatherData = { temp: "", vis: "", sky: "" };
            let flightFound = false;

            function rotateStatus() {
                if (flightFound) {
                    $('#msg1').addClass('active').siblings().removeClass('active');
                    return;
                }
                $(`#msg${currentMsg}`).removeClass('active');
                currentMsg = currentMsg === 3 ? 1 : currentMsg + 1;
                $(`#msg${currentMsg}`).addClass('active');
            }
            setInterval(rotateStatus, 4000);

            function update() {
                navigator.geolocation.getCurrentPosition(pos => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;

                    // Busca Clima
                    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,visibility,weather_code`)
                    .then(r => r.json()).then(w => {
                        const temp = Math.round(w.current.temperature_2m);
                        const vis = (w.current.visibility / 1000).toFixed(1);
                        document.getElementById('msg2').textContent = `TEMP: ${temp}°C | VISIB: ${vis}KM`;
                        document.getElementById('msg3').textContent = `SKY CONDITION: CLEAR OPS`;
                    });

                    // Busca Voo (Lógica Original)
                    fetch(`/api/data?lat=${lat}&lon=${lon}&t=` + Date.now())
                    .then(res => res.json()).then(data => {
                        if(data.found) {
                            flightFound = true;
                            $fCall.val(data.callsign).change();
                            $fDist.val(data.dist + "KM").change();
                            $fAlt.val(data.alt_ft + "FT").change();
                            $fType.val(data.type).change();
                            document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                            document.getElementById('msg1').textContent = "TARGET: " + data.callsign;
                            JsBarcode("#barcode", data.callsign, { format: "CODE128", width: 1.3, height: 40, displayValue: false, lineColor: "#2A6E91" });
                        } else {
                            flightFound = false;
                            document.getElementById('msg1').textContent = "SCANNING AIRSPACE...";
                        }
                    });
                });
            }

            setInterval(update, 8000);
            update();
        </script>
    </body>
    </html>
    ''')

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
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', ac.get('call', 'UNKN')).strip()[:10], 
                    "dist": str(round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)), 
                    "alt_ft": str(int(ac.get('alt_baro', 0))), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "type": ac.get('t', 'UNKN')[:8]
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
