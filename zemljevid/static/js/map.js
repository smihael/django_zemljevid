// Function to show/hide the loading circle
function showLoadingCircle() {
    const loadingCircle = document.getElementById('loading-circle');
    loadingCircle.style.display = 'block';
}

function hideLoadingCircle() {
    const loadingCircle = document.getElementById('loading-circle');
    loadingCircle.style.display = 'none';
}

// Add a timeout mechanism for the fetch response
const fetchWithTimeout = async (url, timeout = 5000) => {
    const controller = new AbortController();
    const signal = controller.signal;

    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, { signal });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        throw error;
    }
};

// Initialize the map
var map = L.map('map', {
    center: [defaultLat, defaultLng],
    zoom: 9,
    zoomControl: false,  
    attributionControl: true,
    contextmenu: true,
    contextmenuWidth: 140,
	contextmenuItems: [{
	    text: 'Prikaži koordinate',
	    callback: showCoordinates
	}, {
	    text: 'Centriraj',
	    callback: centerMap
	}, '-', {
	    text: '<span class="oi oi-zoom-in" style="font-size:16px;position:relative;top:2px;margin-left:4px;"></span> Približaj',
	    callback: zoomIn
	}, {
	    text: '<span class="oi oi-zoom-out" style="font-size:16px;position:relative;top:2px;margin-left:4px;"></span> Oddalji',
	    callback: zoomOut
	}]
});

//map.attributionControl.setPrefix('Poganja Leaflet, GeoDjango in PostGIS | &copy; Prostovoljci projekta <a href="/o-projektu">Partizanstvo na zemljevidu</a> (Slike: CC-BY-SA 4.0 z izjemami, podatki: CC 4.0)');
map.attributionControl.setPrefix('<a href="https://github.com/smihael/django_zemljevid">Django Zemljevid</a> | &copy; Prostovoljci projekta <a href="/o-projektu">Partizanstvo na zemljevidu</a> (Slike: CC-BY-SA 4.0 z izjemami, podatki: CC 4.0)');

const sidepanelLeft = L.control.sidepanel('mySidepanelLeft', {
    tabsPosition: 'left',
    panelPosition: 'left',
    tabsPosition: 'left',
    pushControls: true,
    darkMode: false,
    startTab: 1
}).addTo(map);

function switchSidepanelTab(panelId, tabIndex) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    // Open the panel if not already open
    if (panel.classList.contains('closed')) {
        panel.classList.remove('closed');
        panel.classList.add('opened');
    }

    const tabsLinks = panel.querySelectorAll('a.sidebar-tab-link');
    const tabsContents = panel.querySelectorAll('.sidepanel-tab-content');

    tabsLinks.forEach((tab, i) => {
        tab.classList.toggle('active', i === tabIndex);
    });

    tabsContents.forEach((content, i) => {
        content.classList.toggle('active', i === tabIndex);
    });
}



L.control.scale({
position: 'bottomright', 
metric: true,
imperial: false
}).addTo(map);

L.control.zoom({position: 'bottomright'}).addTo(map); 


// Add geolocation button above zoom controls
const GeolocateControl = L.Control.extend({
    options: { position: 'bottomright' },
    onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
        container.style.backgroundColor = 'white';
        container.style.width = '34px';
        container.style.height = '34px';
        container.style.display = 'flex';
        container.style.alignItems = 'center';
        container.style.justifyContent = 'center';
        container.style.cursor = 'pointer';
        container.title = 'Lociraj me';
        container.innerHTML = '<span style="font-size:20px;" aria-label="Geolociraj">📍</span>';
        container.onclick = function(e) {
            e.stopPropagation();
            map.locate({setView: true, watch: false});
        };
        return container;
    }
});
map.addControl(new GeolocateControl());

// Add OpenStreetMap tile layer
var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: 'Osnovni zemljevid: &copy; Sodelavci projekta <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

var mtLayer = L.maptilerLayer({
    apiKey: api_key,
    style: L.MaptilerStyle.STREETS,
    language: 'sl'
});


var openTopoMapLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 17,
    attribution: '&copy; <a href="https://www.opentopomap.org/">OpenTopoMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)'
});

osmLayer.on('tileerror', function() {
    // Remove OSM layer and switch to Maptiler
    if (map.hasLayer(osmLayer)) {
        map.removeLayer(osmLayer);
        map.addLayer(openTopoMapLayer);
    }
});


var wmsUrl = 'https://ipi.eprostor.gov.si/wms-si-gurs-dts/wms?';
//'https://ipi.eprostor.gov.si/gwc-si-gurs-dts/service/wms?'

const dpk250 = L.tileLayer.wms(wmsUrl, {
  layers: 'SI.GURS.DK:DPK250',
  format: 'image/png',
  transparent: true,
  version: '1.1.1',
  crs: L.CRS.EPSG3857,
  minZoom: 11,
  maxZoom: 14,
  attribution: '© GURS'
});

const dpk500 = L.tileLayer.wms(wmsUrl, {
  layers: 'SI.GURS.DK:DPK500',
  format: 'image/png',
  transparent: true,
  version: '1.1.1',
  crs: L.CRS.EPSG3857,
  minZoom: 9,
  maxZoom: 11,
  attribution: '© GURS'
});

const dtk50 = L.tileLayer.wms(wmsUrl, {
  layers: 'SI.GURS.DK:DTK50',
  format: 'image/png',
  transparent: true,
  version: '1.1.1',
  crs: L.CRS.EPSG3857,
  minZoom: 15,
  maxZoom: 18,
  //srs: 'EPSG:3794',
  attribution: '© GURS'
//  attribution: '© Geodetska uprava Republike Slovenije (GURS)'
});

// Add GURS Orthophoto WMS layer
var orthophotoLayer = L.tileLayer.wms('https://storitve.eprostor.gov.si/ows-ins-wms/oi/ows/ows?', {
    layers: 'OI.OrthoimageCoverage',
    format: 'image/png',
    transparent: true,
    version: '1.3.0',
    attribution: '© Geodetska uprava Republike Slovenije (GURS)'
});

const lidar = L.tileLayer.wms(wmsUrl, {
  layers: 'SI.GURS.ZPDZ:LIDAR',
  format: 'image/png',
  transparent: true,
  version: '1.1.1',
  crs: L.CRS.EPSG3857,
  attribution: '© GURS'
});


// TODO: use GL/Pixi canvas renderer for better performance or switch to openlayers/maplibre

var overlayMaps = {
    "GURS Orthophoto": orthophotoLayer,
    "GURS Lidar": lidar,
    //"GURS Topografska karta (1:50), na voljo samo pri primerni povečavi": gursWmsLayer,
    //'GURS DPK 1:500': dpk500,
    //'GURS DPK 1:250': dpk250,
    //'GURS DTK 1:50': dtk50
};

// Layer control to switch between OSM, Satellite imagery, and TopoMap
var baseMaps = {
    "OpenStreetMap (en)": osmLayer,
    "Maptiler (sl)": mtLayer,
    "OpenTopoMap (en)": openTopoMapLayer,
};

let layerControl; // Reference to the layer control

function updateLayerControl(baseMaps, overlayMaps) {
    if (layerControl) {
        map.removeControl(layerControl); // Remove the existing control
    }
    layerControl = L.control.layers(baseMaps, overlayMaps).addTo(map); // Add the updated control

    // Embed DPK/DTK toggle checkbox inside the base layers section
    setTimeout(() => {
        const baseLayersContainer = document.querySelector('.leaflet-control-layers-overlays');
        if (baseLayersContainer && !document.getElementById('dpkdtk-checkbox')) {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.style.marginTop = '8px';
            checkboxDiv.innerHTML = `
                <label style="cursor:pointer;">
                    <input type="checkbox" id="dpkdtk-checkbox" ${dpkdtkEnabled ? 'checked' : ''} /> GURS Državna pregledna karta 1:50, 1:250, 1:500
                </label>
            `;
            baseLayersContainer.appendChild(checkboxDiv);
            const dpkdtkCheckbox = document.getElementById('dpkdtk-checkbox');
            dpkdtkCheckbox.checked = dpkdtkEnabled;
            dpkdtkCheckbox.addEventListener('change', function() {
                dpkdtkEnabled = this.checked;
                map.fire('zoomend');
            });
        }
    }, 0);
}

// Update the call to L.control.layers
updateLayerControl(baseMaps, overlayMaps);


function displayDetails(layerName, id, marker = null) {
    // Fetch the details of the selected marker, parse the response, and update the sidebar
    fetch(`/api/full/${layerName}/${id}`)
        .then(response => response.json())
        .then(data => {
            var properties = data.properties;

            // Serialize the map's state into URL parameters
            const url = new URL(window.location);
            url.searchParams.set('layer', layerName);
            url.searchParams.set('id', id);
            window.history.replaceState({}, '', url.toString());

            // get property name (key starts with Ime)
            var name = properties['Ime'] || properties['Name'] || marker?.feature?.properties?.name || 'Izbrana točka';

            // Update the sidebar title with the layer name
            const sidebarTitle = document.getElementById('sidebar-title');
            if (sidebarTitle) {
                sidebarTitle.textContent = name;
            }

            //slike
            fetchImagesJson(layerName, id).then(renderGallery);

            // Find point-details container and append gallery
            const pointDetails = document.getElementById('point-details');
            if (pointDetails) {
                pointDetails.innerHTML = ''; // Clear previous content

                // Filter out null values and those in imageKeys
                var filteredProperties = Object.entries(properties)
                    .filter(([key, value]) => !key.startsWith('Slika') && value !== null);

                // Map and join the filtered properties
                var details = filteredProperties
                    .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
                    .join('<br>');

                // Update the point details in the sidebar (excluding image fields)
                pointDetails.innerHTML += details || "No details available for this point.";
            }

            let sidebarButtons = document.getElementById('sidebar-buttons');
            sidebarButtons.style.display = 'flex'; // Show the sidebar buttons
            const locirajButton = document.querySelector('button[aria-label="Lociraj"]');
            const priblizajButton = document.querySelector('button[aria-label="Približaj in centiraj"]');
            const detailsButton = document.querySelector('button[aria-label="Odpri podrobnosti"]');

            if (locirajButton) {
                locirajButton.onclick = function () {
                    L.popup()
                        .setLatLng([data.geometry.coordinates[1], data.geometry.coordinates[0]])
                        .setContent(name)
                        .openOn(map);
                };
            }

            if (priblizajButton) {
                priblizajButton.onclick = function () {
                    map.setView([data.geometry.coordinates[1], data.geometry.coordinates[0]], 19);
                };
            }

            if (detailsButton) {
                detailsButton.onclick = function () {
                    window.location.href = '/admin/zemljevid/' + layerName + '/' + id + '/change/';
                };
            }
            
            // Switch to the details tab in the sidepanel
            switchSidepanelTab('mySidepanelLeft', 2);

        });
}

// Ensure floating search bar is visible by default
//document.getElementById('floating-search-bar').classList.add('visible');


function updateMapUrl() {
    // Get current map view and layers
    const zoom = map.getZoom();
    const center = map.getCenter();
    const layers = [];
  
    // Check if each layer is active
    if (map.hasLayer(orthophotoLayer)) layers.push('orthophoto');
    //if (map.hasLayer(gursWmsLayer)) layers.push('gurs');
    //if (map.hasLayer(layerGroup)) layers.push('markers');

    // Serialize the map's state into URL parameters
    const url = new URL(window.location);
    url.searchParams.set('zoom', zoom);
    url.searchParams.set('lat', center.lat);
    url.searchParams.set('lng', center.lng);
    url.searchParams.set('layers', layers.join(','));
  
    // Update the browser's URL without reloading the page
    window.history.replaceState({}, '', url.toString());
}
  
function applyMapSettingsFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
  
    // Get parameters from URL
    const zoom = parseInt(urlParams.get('zoom')) || 9;  // Default zoom level
    const lat = parseFloat(urlParams.get('lat')) || defaultLat; // Default latitude
    const lng = parseFloat(urlParams.get('lng')) || defaultLng; // Default longitude
    const layers = (urlParams.get('layers') || '').split(',');
    const layer = urlParams.get('layer') || ''; // Get the layer from URL, if any
    const id = urlParams.get('id') || ''; // Get the ID from URL, if any
  
    // If a layer and ID are specified, display details for that point
    if (layer && id) {
        displayDetails(layer, id); 
    }
    

    // Set the map's view based on URL parameters
    map.setView([lat, lng], zoom);
  
    // Add the appropriate layers based on URL parameters
    if (layers.includes('orthophoto')) map.addLayer(orthophotoLayer);
    //if (layers.includes('gurs')) map.addLayer(gursWmsLayer);
    //if (layers.includes('markers')) map.addLayer(layerGroup);

    //TODO: markers
}
  
// Apply map settings when the page loads
window.onload = applyMapSettingsFromUrl;

map.on('moveend', updateMapUrl);
map.on('baselayerchange', updateMapUrl);
map.on('overlayadd', updateMapUrl);
map.on('overlayremove', updateMapUrl);

let dpkdtkEnabled = false; // Global flag for DPK/DTK toggle

map.on('zoomend', () => {
  const z = map.getZoom();

  if (dpkdtkEnabled) {
    if (z >= dpk500.options.minZoom && z <= dpk500.options.maxZoom) {
      if (!map.hasLayer(dpk500)) map.addLayer(dpk500);
    } else {
      map.removeLayer(dpk500);
    }

    if (z >= dpk250.options.minZoom && z <= dpk250.options.maxZoom) {
      if (!map.hasLayer(dpk250)) map.addLayer(dpk250);
    } else {
      map.removeLayer(dpk250);
    }

    if (z >= dtk50.options.minZoom && z <= dtk50.options.maxZoom) {
      if (!map.hasLayer(dtk50)) map.addLayer(dtk50);
    } else {
      map.removeLayer(dtk50);
    }
  } else {
    map.removeLayer(dpk500);
    map.removeLayer(dpk250);
    map.removeLayer(dtk50);
  }
});

// Fetch and render markers for the layer
async function loadMarkersForLayer(layer_model_info,markerClusterGroup) {
    showLoadingCircle();
    const markersUrl = `/api/brief/${layer_model_info.model_name}/`;
    const response = await fetchWithTimeout(markersUrl);
    const geojson = await response.json();
    hideLoadingCircle();
    console.log(`Markers loaded for layer: ${layer_model_info.model_name}`);

    // Add markers to the layer
    L.geoJSON(geojson, {
        pointToLayer: function (feature, latlng) {
            let icon = L.Icon.Default.prototype; 

            if (layer_model_info.icon !== null) {
                switch (layer_model_info.icon) {
                    case 'hospital':
                        icon = L.icon({
                            iconUrl: '/static/images/bolnisnica.svg',
                            iconSize: [20, 20]
                        });
                        break;

                    case 'star-icon':
                        icon = L.divIcon({
                            className: 'icon star-icon'
                        });

                        if (feature.properties.status) {
                            switch (feature.properties.status) {
                                case 1:
                                    icon = L.divIcon({
                                        className: 'icon star-icon red'
                                    });
                                    break;
                                case 3:
                                    icon = L.divIcon({
                                        className: 'icon star-icon blue'
                                    });
                                    break;
                                case 2:
                                    icon = L.divIcon({
                                        className: 'icon star-icon green'
                                    });
                                    break;
                            }
                        } else {
                            // Default to red if no status is set
                            icon = L.divIcon({
                                className: 'icon star-icon red'
                            });
                        }
                        break;
                
                    default:
                        icon = L.divIcon({
                            className: `icon ${layer_model_info.icon}`,
                        });
                        break;                
                }
            }

            marker = L.marker(latlng, { icon: icon });
            marker._layerName = layer_model_info.model_name;

            return marker;
        },
        onEachFeature: function (feature, layer) {

            layer.on('click', function (e) {
                var marker = e.target;
                if (!marker.getPopup()) {
                marker.bindPopup(feature.properties.name || 'Izbrana točka');
                }
                marker.openPopup();
       
                displayDetails(marker._layerName, feature.id);
            });
        }
    }).addTo(markerClusterGroup);
}

// Fetch model names and dynamically create marker layers
async function processGeoLayers() {
    
    const response = await fetch('/api/get_layers/');
    const layers = await response.json();

    // Add filter options to the navbar
    const filterContainer = document.getElementById('filter-container');

    layers.forEach(layer => {

        // Create marker layer for each model
        const markerClusterGroup = L.markerClusterGroup({
            chunkedLoading: true,
            disableClusteringAtZoom: 12,
            name: layer.verbose_name_plural,
        });

        console.log(`Loading markers for layer: ${layer.model_name}`);
        loadMarkersForLayer(layer, markerClusterGroup);

        // Add the layer to the overlay maps
        //overlayMaps[layer.model_name] = markerClusterGroup;
        markerClusterGroup.addTo(map); 
        geoLayers.push(markerClusterGroup)


        const filterOption = document.createElement('div');
        filterOption.className = 'filter-option';
        filterOption.innerHTML = `
            <label>${layer.verbose_name_plural}</label>
        `;

        // Initially enable the layer
        filterOption.classList.add('enabled');
        filterOption.title = 'Kliknite za skritje sloja';

        // Add click event to toggle layer visibility
        filterOption.addEventListener('click', function () {
            if (filterOption.classList.contains('enabled')) {
                //map.removeLayer(overlayMaps[layer.model_name]);
                map.removeLayer(markerClusterGroup);
                filterOption.classList.remove('enabled');
                filterOption.title = 'Kliknite za prikaz sloja';
            } else {
                //map.addLayer(overlayMaps[layer.model_name]);
                map.addLayer(markerClusterGroup);
                filterOption.classList.add('enabled');
                filterOption.title = 'Kliknite za skritje sloja';
            }
        });

        filterContainer.appendChild(filterOption);


        
    });

    // Update the layer control with the new layers
    updateLayerControl(baseMaps, overlayMaps);
    

}

// Call the function to fetch model names and initialize layers
let geoLayers = [];
processGeoLayers().then(() => {
    L.control.search({
        layer: L.layerGroup(geoLayers),
        initial: false,
        collapsed: false,
        container: 'searchbox',
        zoom: 17,
        position: 'topright',
        propertyName: 'name',
        buildTip: function(text, val) {
            var type = val.layer.feature?.properties?.amenity || '';
            return '<a href="#" class="'+type+'">'+text+'<b>'+type+'</b></a>';
        }
    }).addTo(map);
});


// Dynamically set --navbar-height CSS variable based on actual navbar height
function setNavbarHeightVar() {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        document.documentElement.style.setProperty('--navbar-height', navbar.offsetHeight + 'px');
    }
}
window.addEventListener('DOMContentLoaded', setNavbarHeightVar);
window.addEventListener('resize', setNavbarHeightVar);



function showCoordinates (e) {
    textContent = `Lat: ${e.latlng.lat.toFixed(6)}, Lng: ${e.latlng.lng.toFixed(6)}`;
    // Display coordinates in a popup or console
    alert(`Lat: ${e.latlng.lat.toFixed(6)}, Lng: ${e.latlng.lng.toFixed(6)}`);
    // copy to clipboard
    navigator.clipboard.writeText(textContent).then(() => {
        console.log('Coordinates copied to clipboard:', textContent);
    }).catch(err => {
        console.error('Failed to copy coordinates: ', err);
    });
}

function centerMap (e) {
	map.panTo(e.latlng);
}

function zoomIn (e) {
	map.zoomIn();
}

function zoomOut (e) {
	map.zoomOut();
}


