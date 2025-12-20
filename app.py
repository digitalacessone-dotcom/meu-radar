from flask import Flask, render_template_string, jsonify, request
import requests
import time
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
    # Gerador de versão para forçar o Safari a ignorar o cache
    v = int(time.time())
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <title>Boarding Board Radar v{v}</title>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/flapper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/jquery.flapper.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>

        <style>
            :root {{ 
                --sky-blue: #87CEEB; 
                --yellow-accent: #FFD700; 
            }}
            
            body {{ 
                background: #F0F4F7; margin: 0; display: flex; flex-direction: column; 
                align-items: center; justify-content: center; min-height: 100vh; 
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; 
                -webkit-font-smoothing: antialiased;
            }}
            
            #search-container {{ 
                background: white; width: 90%; max-width: 850px; padding: 12px 20px; 
                border-radius: 15px; display: none; gap: 15px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 30px;
                transition: opacity 0.8s ease, transform 0.8s ease; opacity: 1;
            }}
            #search-container.fade-out {{ opacity: 0; transform: translateY(-20px); pointer-events: none; }}
            #search-container input {{ flex: 1; border: 1px solid #E0E0E0; padding: 12px; border-radius: 8px; font-size: 16px; outline: none; }}
            #search-container button {{ background: var(--sky-blue); color: white; border: none; padding: 12px 25px; border-radius: 8px; font-weight: bold; cursor: pointer; }}

            .ticket {{ 
                background: white; width: 95%; max-width: 850px; height: 450px; 
                border-radius: 20px; display: flex; overflow: hidden; 
                box-shadow: 0 25px 50px rgba(0,0,0,0.1); position: relative; 
            }}
            
            .stub {{ 
                background: var(--sky-blue); width: 240px; padding: 35px 25px; 
                color: white; display: flex; flex-direction: column; 
                border-right: 2px dashed rgba(255,255,255,0.4); 
            }}
            .seat-num {{ font-size: 85px; font-weight: 900; margin: 10px 0; line-height: 1; letter-spacing: -2px; }}
            .dot-container {{ display: flex; gap: 6px; margin-top: 15px; }}
            .dot {{ width: 15px; height: 15px; background: rgba(255,255,255,0.3); border-radius: 3px; }}

            .main {{ flex: 1; display: flex; flex-direction: column; }}
            .header-strip {{ background: var(--sky-blue); color: white; padding: 18px 45px; display: flex; justify-content: space-between; align-items: center; }}
            .header-strip h1 {{ margin: 0; font-size: 24px; letter-spacing: 10px; font-weight: 400; text-transform: uppercase; }}

            .info-grid {{ padding: 40px 50px; display: flex; flex: 1; }}
            .data-col {{ flex: 1.4; }}
            .visual-col {{ flex: 1; border-left: 1px solid #F0F0F0; padding-left: 30px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; }}

            .label {{ color: #AAA; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 8px; }}
            
            /* Placar Split-Flap */
            .flapper .digit {{ 
                background-color: #1A1A1A !important; 
                color: var(--yellow-accent) !important; 
                border-radius: 4px !important; 
            }}

            #compass {{ font-size: 50px; color: #FF8C00; transition: transform 0.8s ease; }}
            #barcode {{ width: 180px; height: 70px; }}

            .footer-black {{ background: #000; height: 80px; border-top: 5px solid var(--yellow-accent); display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }}
            .status-wrapper {{ width: 100%; text-align: center; position: relative; height: 100%; }}
            .status-msg {{ 
                color: var(--yellow-accent); font-family: 'Courier New', Courier, monospace; 
                font-weight: bold; font-size: 18px; text-transform: uppercase; 
                position: absolute; width: 100%; left: 0; top: 50%; transform: translateY(-50%); 
                transition: opacity 0.8s; opacity: 0; 
            }}
            .status-msg.active {{ opacity: 1; }}

            @media (max-width: 600px) {{
                .ticket {{ height: auto; flex-direction: column; }}
                .stub {{ width: 100%; box-sizing: border-box; border-right: none; border-bottom: 2px dashed #ddd; }}
                .info-grid {{ flex-direction: column; padding: 20px; }}
                .visual-col {{ border-left: none; border-top: 1px solid #eee; padding: 20px 0; }}
            }}
        </style>
    </head>
    <body>

        <div id="search-container">
            <input type="text" id="address-input" placeholder="Digite Cidade ou CEP...">
            <button onclick="buscarManual()">CONNECT</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div style="font-size: 11px; font-weight: bold;">RADAR STATION</div>
                <div style="font-size: 14px; margin-top: 12px; font-weight: bold;">SEAT:</div>
                <div class="seat-num">19 A</div>
                <div class="dot-container">
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                    <div class="dot"></div><div class="dot"></div><div class="dot"></div><div class="dot"></div>
                </div>
                <div style="margin-top: auto; font-size: 16px; font-weight: bold;">ATC SECURE</div>
            </div>

            <div class="main">
                <div class="header-strip">
                    <span>✈</span><h1>BOARDING BOARD</h1><span>✈</span>
                </div>
                <div class="info-grid">
                    <div class="data-col">
                        <div class="label">Callsign</div>
                        <input id="flap_callsign" class="flap" />
                        <div class="label">Distance</div>
                        <input id="flap_dist" class="flap" />
                        <div class="label">Altitude</div>
                        <input id="flap_alt" class="flap" />
                    </div>
                    <div class="visual-col">
                        <div style="text-align: center;">
                            <div class="label">Type</div>
                            <input id="flap_type" class="flap" />
                        </div>
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>
                <div class="footer-black">
                    <div class="status-wrapper">
                        <div id="msg1" class="status-msg active">SCANNING...</div>
                        <div id="msg2" class="status-msg">CLIMA: --°C</div>
                        <div id="msg3" class="status-msg">METAR: VFR</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const optCall = {{ width: 10, chars_preset: 'alphanum' }};
            const optDist = {{ width: 10, chars_preset: 'num' }};
            const optAlt = {{ width: 10, chars_preset: 'num' }};
            const optType = {{ width: 8, chars_preset: 'alphanum' }};

            const $fCall = $('#flap_callsign').flapper(optCall);
            const $fDist = $('#flap_dist').flapper(optDist);
            const $fAlt = $('#flap_alt').flapper(optAlt);
            const $fType = $('#flap_type').flapper(optType);

            let lat, lon, flightFound = false, msgIdx = 1;

            setInterval(() => {{
                if (flightFound) return;
                $(`#msg${{msgIdx}}`).removeClass('active');
                msgIdx = msgIdx === 3 ? 1 : msgIdx + 1;
                $(`#msg${{msgIdx}}`).addClass('active');
            }}, 4000);

            function start(la, lo) {{
                lat = la; lon = lo;
                setInterval(fetchData, 8000);
                fetchData();
            }}

            function fetchData() {{
                fetch(`https://api.open-meteo.com/v1/forecast?latitude=${{lat}}&longitude=${{lon}}&current=temperature_2m`)
                .then(r => r.json()).then(w => {{
                    document.getElementById('msg2').textContent = `TEMP: ${{Math.round(w.current.temperature_2m)}}°C`;
                }});

                fetch(`/api/data?lat=${{lat}}&lon=${{lon}}&t=` + Date.now())
                .then(res => res.json()).then(data => {{
                    if(data.found) {{
                        flightFound = true;
                        $('#msg1').addClass('active').text("TARGET: " + data.callsign).siblings().removeClass('active');
                        $fCall.val(data.callsign).change();
                        $fDist.val(data.dist + "KM").change();
                        $fAlt.val(data.alt_ft + "FT").change();
                        $fType.val(data.type).change();
                        document.getElementById('compass').style.transform = `rotate(${{data.bearing}}deg)`;
                        JsBarcode("#barcode", data.callsign, {{ format: "CODE128", width: 1.4, height: 45, displayValue: false, lineColor: "#87CEEB" }});
                    }}
                }});
            }}

            function buscarManual() {{
                const q = document.getElementById('address-input').value;
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${{q}}`)
                .then(r => r.json()).then(res => {{
                    if(res.length > 0) {{
                        $('#search-container').addClass('fade-out');
                        setTimeout(() => $('#search-container').hide(), 1000);
                        start(res[0].lat, res[0].lon);
                    }}
                }});
            }}

            navigator.geolocation.getCurrentPosition(
                p => start(p.coords.latitude, p.coords.longitude),
                e => $('#search-container').css('display', 'flex')
            );
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{{lat_u}}/lon/{{lon_u}}/dist/{{RAIO_KM}}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            ac = sorted([a for a in r['ac'] if a.get('lat')], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({{
                "found": True, 
                "callsign": ac.get('flight', 'UNKN').strip()[:10], 
                "dist": str(round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)), 
                "alt_ft": str(int(ac.get('alt_baro', 0))), 
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                "type": ac.get('t', 'UNKN')[:8]
            }})
    except: pass
    return jsonify({{"found": False}})

if __name__ == '__main__':
    app.run(debug=True)
