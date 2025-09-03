"""
Map Generator Service

Creates interactive Singapore maps with lightning strike markers.
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    logger.warning("Folium not available - maps will not be generated")
    FOLIUM_AVAILABLE = False


class MapGenerator:
    """Generates interactive maps showing lightning strikes in Singapore."""
    
    def __init__(self):
        self.singapore_center = [1.3521, 103.8198]
        self.singapore_bounds = {
            "lat_min": 0.95,
            "lat_max": 1.75, 
            "lon_min": 103.27,
            "lon_max": 104.52,
        }
    
    def create_singapore_map(self, coordinates: List[Dict]) -> str:
        """
        Create an interactive map of Singapore with lightning strikes.
        
        Args:
            coordinates: List of lightning coordinate dictionaries
            
        Returns:
            str: HTML content of the generated map
        """
        if not FOLIUM_AVAILABLE:
            return self._create_fallback_map_html(coordinates)
        
        try:
            # Create base map
            lightning_map = folium.Map(
                location=self.singapore_center,
                zoom_start=11,
                tiles='OpenStreetMap'
            )
            
            # Add Singapore boundary rectangle
            folium.Rectangle(
                bounds=[[self.singapore_bounds['lat_min'], self.singapore_bounds['lon_min']],
                        [self.singapore_bounds['lat_max'], self.singapore_bounds['lon_max']]],
                color='blue',
                fill=False,
                weight=2,
                popup='Singapore Boundary'
            ).add_to(lightning_map)
            
            # Add lightning markers if data exists
            if coordinates:
                for coord in coordinates:
                    # Different colors for different lightning types
                    color = 'red' if coord['type'] == 'G' else 'orange'
                    icon_symbol = '⚡' if coord['type'] == 'G' else '☁️'
                    
                    # Create popup text
                    popup_text = f"""
                    <b>Lightning Strike</b><br>
                    Type: {coord['type']} ({coord['description']})<br>
                    Time: {coord['datetime']}<br>
                    Coordinates: {coord['latitude']:.4f}, {coord['longitude']:.4f}
                    """
                    
                    # Add marker
                    folium.Marker(
                        location=[coord['latitude'], coord['longitude']],
                        popup=folium.Popup(popup_text, max_width=300),
                        tooltip=f"{icon_symbol} {coord['type']} - {coord['datetime']}",
                        icon=folium.Icon(color=color, icon='flash', prefix='fa')
                    ).add_to(lightning_map)
            
            # Add marker for Singapore center
            folium.Marker(
                location=self.singapore_center,
                popup='Singapore Center',
                tooltip='Singapore Center',
                icon=folium.Icon(color='green', icon='home', prefix='fa')
            ).add_to(lightning_map)
            
            # Generate HTML
            return lightning_map._repr_html_()
            
        except Exception as e:
            logger.error(f"Error creating map: {e}")
            return self._create_fallback_map_html(coordinates)
    
    def _create_fallback_map_html(self, coordinates: List[Dict]) -> str:
        """
        Create a fallback HTML map when Folium is not available.
        """
        # Simple HTML map using OpenStreetMap
        markers_js = ""
        if coordinates:
            markers_data = []
            for coord in coordinates:
                markers_data.append({
                    'lat': coord['latitude'],
                    'lng': coord['longitude'],
                    'type': coord['type'],
                    'description': coord['description'],
                    'datetime': coord['datetime']
                })
            
            markers_js = f"var lightningMarkers = {str(markers_data).replace("'", '"')};"
        else:
            markers_js = "var lightningMarkers = [];"
        
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Singapore Lightning Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <style>
                #map {{ height: 600px; width: 100%; }}
                .info {{ 
                    padding: 10px; 
                    background: white; 
                    margin-bottom: 10px; 
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body>
            <div class="info">
                <h3>Singapore Lightning Detection Map</h3>
                <p>Showing {len(coordinates)} lightning strikes. Red markers = Ground strikes, Orange markers = Cloud-to-cloud strikes.</p>
            </div>
            <div id="map"></div>
            
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script>
                // Initialize map centered on Singapore
                var map = L.map('map').setView([{self.singapore_center[0]}, {self.singapore_center[1]}], 11);
                
                // Add OpenStreetMap tiles
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(map);
                
                // Add Singapore boundary rectangle
                var singaporeBounds = [
                    [{self.singapore_bounds['lat_min']}, {self.singapore_bounds['lon_min']}],
                    [{self.singapore_bounds['lat_max']}, {self.singapore_bounds['lon_max']}]
                ];
                L.rectangle(singaporeBounds, {{color: 'blue', weight: 2, fill: false}}).addTo(map)
                    .bindPopup('Singapore Boundary');
                
                // Add Singapore center marker
                L.marker([{self.singapore_center[0]}, {self.singapore_center[1]}])
                    .addTo(map)
                    .bindPopup('Singapore Center')
                    .openPopup();
                
                // Lightning data
                {markers_js}
                
                // Add lightning markers
                lightningMarkers.forEach(function(strike) {{
                    var icon = strike.type === 'G' ? '⚡' : '☁️';
                    var color = strike.type === 'G' ? 'red' : 'orange';
                    
                    var marker = L.marker([strike.lat, strike.lng])
                        .addTo(map)
                        .bindPopup(`
                            <b>Lightning Strike</b><br>
                            Type: ${{strike.type}} (${{strike.description}})<br>
                            Time: ${{strike.datetime}}<br>
                            Coordinates: ${{strike.lat.toFixed(4)}}, ${{strike.lng.toFixed(4)}}
                        `);
                }});
                
                // Auto-fit map if there are lightning strikes
                if (lightningMarkers.length > 0) {{
                    var group = new L.featureGroup(lightningMarkers.map(strike => 
                        L.marker([strike.lat, strike.lng])
                    ));
                    map.fitBounds(group.getBounds().pad(0.1));
                }}
            </script>
        </body>
        </html>
        """
        
        return fallback_html


# Create global instance
map_generator = MapGenerator()