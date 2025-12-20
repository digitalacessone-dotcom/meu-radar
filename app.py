from flask import Flask, render_template_string, jsonify
import requests
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# Configurações do seu Radar (Campos dos Goytacazes)
LAT_ALVO, LON_ALVO = -21.759351, -41.329142 
RAIO_KM = 50.0
# Usando a API pública do ADSB.lol para dados reais mais abrangentes
API_URL = f"https://api.adsb.lol/v2/lat/{LAT_ALVO}/lon/{LON_ALVO}/dist/{RAIO_KM}"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tactical Radar Map</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root { --blue: #236589; --gold: #FFD700; }
            body { background-color: #0a192f; margin: 0; font-family: 'Courier New', monospace; color: white; overflow: hidden; }
            
            #container { display: flex; height: 100vh; }
            
            /* Lado do Ticket */
            #ticket-side { width: 350px; background: white; color: #333; display: flex; flex-direction: column; box-shadow: 5px 0 15px rgba(0,0,0,0.5); z-index: 1000; }
            .header { background: var(--blue); color: white; padding: 20px; text-align: center; font-weight: bold; font-size: 1.2em; }
            .content { padding: 20px; flex: 1; }
            .label { color: #888; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-top: 15px; }
            .value { font-size: 1.5em; font-weight: bold; color: var(--blue); }
            .footer { background: black; color: var(--gold); padding: 15px; font-weight: bold; border-top: 3px solid var(--gold); }

            /* Lado do Mapa */
            #map { flex: 1; background: #111; }
        </style>
    </head>
    <body>
        <div id="container">
            <div id="ticket-side">
                <div class="header">✈ LIVE TRACKING</div>
                <div class="content">
                    <div class="label">TARGET IDENT</div>
                    <div id="callsign" class="value">SEARCHING...</div>
                    
                    <div class="label">DISTANCE / ALTITUDE</div>
                    <div id="info" class="value">--- / ---</div>
                    
                    <div class="label">SQUAWK / TYPE</div>
                    <div id="extra" class="value">---- / ----</div>
                </div>
                <div class="footer" id="status">> RADAR ACTIVE</div>
            </div>
            
            <div id="map"></div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            // Posição do Radar (Sua casa)
            const baseLat = {{ base_lat }};
            const baseLon = {{ base_lon }};

            // Inicializa o Mapa (Estilo Escuro)
            const map = L.map('map').setView([baseLat, baseLon], 10);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(map);

            // Marcador da Base (Você)
            const baseIcon = L.circle([baseLat, baseLon], {
                color: '#FFD700', fillColor: '#FFD700', fillOpacity: 0.4, radius: 1000
            }).addTo(map).bindPopup("RADAR BASE (YOU)");

            // Marcador do Avião
            let planeMarker = L.marker([0, 0]).addTo(map);
            planeMarker.setOpacity(0); // Escondido no início

            function update() {
                fetch('/api/data').then(res => res.json()).then(data => {
                    if(data.found) {
                        document.getElementById('callsign').innerText = data.callsign;
                        document.getElementById('info').innerText = data.dist + "KM / " + data.alt + "FT";
                        document.getElementById('extra').innerText = data.squawk + " / " + data.type;
                        document.getElementById('status').innerText = "> TARGET ACQUIRED";

                        // Atualiza posição do avião no mapa
                        const planePos = [data.lat, data.lon];
                        planeMarker.setLatLng(planePos).setOpacity(1);
                        planeMarker.bindPopup("<b>" + data.callsign + "</b>").openPopup();
                        
                        // Ajusta o mapa para mostrar você e o avião
                        const bounds = L.latLngBounds([baseLat, baseLon], planePos);
                        map.fitBounds(bounds, {padding: [50, 50]});
                    } else {
                        document.getElementById('status').innerText = "> SCANNING AIRSPACE...";
                        planeMarker.setOpacity(0);
                    }
                });
            }

            setInterval(update, 5000); // Atualiza a cada 5 segundos
            update();
        </script>
    </body>
    </html>
    ''', base_lat=LAT_ALVO, base_lon=LON_ALVO)

@app.route('/api/data')
def get_data():
    try:
        # Usando ADSB.lol para dados reais de radar
        r = requests.get(API_URL, timeout=10).json()
        if r.get('ac'):
            # Pega o avião mais próximo
            ac = sorted(r['ac'], key=lambda x: haversine(LAT_ALVO, LON_ALVO, x['lat'], x['lon']))[0]
            d = haversine(LAT_ALVO, LON_ALVO, ac['lat'], ac['lon'])
            
            return jsonify({
                "found": True,
                "callsign": (ac.get('flight') or ac.get('call', 'UNKN')).strip(),
                "lat": ac['lat'],
                "lon": ac['lon'],
                "dist": round(d, 1),
                "alt": int(ac.get('alt_baro', 0)),
                "type": ac.get('t', 'UNKN'),
                "squawk": ac.get('squawk', '0000')
            })
    except Exception as e:
        print(f"Erro: {e}")
    return jsonify({"found": False})

if __name__ == "__main__":
    app.run(debug=True)
