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

const BRIEF_CACHE_DB = 'map-brief-geojson';
const BRIEF_CACHE_STORE = 'layers';
const BRIEF_CACHE_TTL_MS = 60 * 60 * 1000;
const GEO_LAYERS_CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const mapScriptElement = document.currentScript || document.querySelector('script[src*="/js/map"]');
const mapScriptVersion = (() => {
    if (!mapScriptElement?.src) return 'map.js';
    const scriptUrl = new URL(mapScriptElement.src, window.location.href);
    return `${scriptUrl.pathname}?v=${scriptUrl.searchParams.get('v') || ''}`;
})();

function openBriefGeoJsonCache() {
    if (!window.indexedDB) return Promise.reject(new Error('IndexedDB is unavailable'));

    return new Promise((resolve, reject) => {
        const request = window.indexedDB.open(BRIEF_CACHE_DB, 1);
        request.onupgradeneeded = () => {
            const database = request.result;
            if (!database.objectStoreNames.contains(BRIEF_CACHE_STORE)) {
                database.createObjectStore(BRIEF_CACHE_STORE, { keyPath: 'model_name' });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error || new Error('Unable to open IndexedDB'));
        request.onblocked = () => reject(new Error('Opening the IndexedDB cache was blocked'));
    });
}

async function readBriefGeoJsonCache(modelName) {
    const database = await openBriefGeoJsonCache();
    try {
        return await new Promise((resolve, reject) => {
            const transaction = database.transaction(BRIEF_CACHE_STORE, 'readonly');
            const request = transaction.objectStore(BRIEF_CACHE_STORE).get(modelName);
            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error || new Error('Unable to read IndexedDB cache'));
        });
    } finally {
        database.close();
    }
}

async function writeBriefGeoJsonCache(entry) {
    const database = await openBriefGeoJsonCache();
    try {
        await new Promise((resolve, reject) => {
            const transaction = database.transaction(BRIEF_CACHE_STORE, 'readwrite');
            transaction.objectStore(BRIEF_CACHE_STORE).put(entry);
            transaction.oncomplete = resolve;
            transaction.onerror = () => reject(transaction.error || new Error('Unable to write IndexedDB cache'));
            transaction.onabort = () => reject(transaction.error || new Error('IndexedDB cache write was aborted'));
        });
    } finally {
        database.close();
    }
}

function briefCacheValidatorMatches(cachedValidator, currentValidator) {
    return Boolean(
        cachedValidator && currentValidator &&
        cachedValidator.count === currentValidator.count &&
        cachedValidator.last_changed === currentValidator.last_changed
    );
}

function isBriefGeoJson(data) {
    return data && data.type === 'FeatureCollection' && Array.isArray(data.features);
}

async function getBriefGeoJson(layer, cacheMetadata) {
    const modelName = layer.model_name;
    const currentValidator = cacheMetadata?.layers?.[modelName];

    if (currentValidator) {
        try {
            const cached = await readBriefGeoJsonCache(modelName);
            const age = cached ? Date.now() - cached.cached_at : Infinity;
            if (
                cached && cached.script_version === mapScriptVersion &&
                age >= 0 && age < BRIEF_CACHE_TTL_MS &&
                briefCacheValidatorMatches(cached.validator, currentValidator) &&
                isBriefGeoJson(cached.geojson)
            ) {
                return cached.geojson;
            }
        } catch (error) {
            console.warn('Unable to read map data cache; loading from API instead.', error);
        }
    }

    const response = await fetchWithTimeout(`/api/brief/${modelName}/`);
    if (!response.ok) throw new Error(`Brief map API returned ${response.status} for ${modelName}`);
    const geojson = await response.json();
    if (!isBriefGeoJson(geojson)) throw new Error(`Invalid GeoJSON response for ${modelName}`);

    if (currentValidator) {
        try {
            await writeBriefGeoJsonCache({
                model_name: modelName,
                script_version: mapScriptVersion,
                validator: currentValidator,
                cached_at: Date.now(),
                geojson,
            });
        } catch (error) {
            console.warn('Unable to save map data cache; continuing without it.', error);
        }
    }

    return geojson;
}

async function getGeoLayers(langCode) {
    const language = langCode || document.documentElement.lang || 'default';
    const cacheKey = `map-layers-v1:${mapScriptVersion}:${language}`;
    let cached = null;

    try {
        const parsed = JSON.parse(window.localStorage.getItem(cacheKey) || 'null');
        if (parsed && Array.isArray(parsed.layers) && Number.isFinite(parsed.cached_at)) cached = parsed;
        const age = cached ? Date.now() - cached.cached_at : Infinity;
        if (cached && age >= 0 && age < GEO_LAYERS_CACHE_TTL_MS) {
            return cached.layers;
        }
    } catch (error) {
        console.warn('Unable to read map layer metadata cache.', error);
    }

    const layersUrl = langCode
        ? `/api/get_layers/?lang=${encodeURIComponent(langCode)}`
        : '/api/get_layers/';
    try {
        const response = await fetchWithTimeout(layersUrl);
        if (!response.ok) throw new Error(`Layer API returned ${response.status}`);
        const layers = await response.json();
        if (!Array.isArray(layers)) throw new Error('Invalid layer metadata response');
        try {
            window.localStorage.setItem(cacheKey, JSON.stringify({ cached_at: Date.now(), layers }));
        } catch (error) {
            console.warn('Unable to save map layer metadata cache.', error);
        }
        return layers;
    } catch (error) {
        if (cached) {
            console.warn('Using previously cached layer metadata because the API is unavailable.', error);
            return cached.layers;
        }
        throw error;
    }
}

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
    attribution: 'Osnovni zemljevid: &copy; Sodelavci projekta <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> (ODbL)',
    referrerPolicy: 'strict-origin'
}).addTo(map);

var mtLayer = L.maptilerLayer({
    apiKey: api_key,
    style: L.MaptilerStyle.STREETS,
    language: 'sl'
});


var openTopoMapLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 17,
    attribution: '&copy; <a href="https://www.opentopomap.org/">OpenTopoMap</a> contributors (CC-BY-SA)'
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
var wmsInsUrl = 'https://ipi.eprostor.gov.si/wms-si-gurs-ins/wms?';
var rpeWmsUrl = 'https://ipi.eprostor.gov.si/wms-si-gurs-rpe/ows?';

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
// https://storitve.eprostor.gov.si/ows-ins-wms/oi/ows/ows?
var orthophotoLayer = L.tileLayer.wms(wmsUrl, {
    layers: 'SI.GURS.ZPDZ:PREGLEDNI_DOF',
    format: 'image/png',
    transparent: true,
    crs: L.CRS.EPSG3857,
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

const cadastralParcelsOverview = L.tileLayer.wms(wmsInsUrl, {
    layers: 'cp:CP.CadastralParcel',
    styles: 'CP.CadastralParcel.Default',
    format: 'image/png',
    transparent: true,
    version: '1.3.0',
    crs: L.CRS.EPSG3857,
    attribution: '© GURS'
});

const cadastralZoningOverview = L.tileLayer.wms(wmsInsUrl, {
    layers: 'cp:CP.CadastralZoning',
    styles: 'inspire_common:DEFAULT',
    format: 'image/png',
    transparent: true,
    opacity: 0.45,
    version: '1.3.0',
    crs: L.CRS.EPSG3857,
    attribution: '© GURS'
});

const localCommunityBoundaries = L.tileLayer.wms(rpeWmsUrl, {
    layers: 'SI.GURS.RPE:KRAJEVNE_SKUPNOSTI',
    styles: 'nep_rpe_kraj_skup',
    format: 'image/png',
    transparent: true,
    version: '1.3.0',
    crs: L.CRS.EPSG3857,
    attribution: '© GURS — Register prostorskih enot'
});

const localCommunityLabels = L.tileLayer.wms(rpeWmsUrl, {
    layers: 'SI.GURS.RPE:KRAJEVNE_SKUPNOSTI',
    styles: 'nep_rpe_kraj_skup_lbl',
    format: 'image/png',
    transparent: true,
    version: '1.3.0',
    crs: L.CRS.EPSG3857,
    attribution: '© GURS — Register prostorskih enot'
});

const localCommunitiesOverview = L.layerGroup([
    localCommunityBoundaries,
    localCommunityLabels
]);

const geographicalNamesOverview = L.tileLayer.wms(wmsInsUrl, {
    layers: 'gn:GN.GeographicalNames',
    styles: 'GN.GeographicalNames.Default',
    format: 'image/png',
    transparent: true,
    version: '1.3.0',
    crs: L.CRS.EPSG3857,
    attribution: '© GURS'
});


// TODO: use GL/Pixi canvas renderer for better performance or switch to openlayers/maplibre

var overlayMaps = {
    "GURS Orthophoto": orthophotoLayer,
    "GURS Lidar": lidar,
    "GURS Katastrske parcele": cadastralParcelsOverview,
    "GURS Katastrske občine": cadastralZoningOverview,
    "GURS Krajevne skupnosti": localCommunitiesOverview,
    "Register zemljepisnih imen": geographicalNamesOverview,
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

function addWmsFeatureInfoRequest(layer, serviceUrl, point) {
    const bounds = map.getBounds();
    const size = map.getSize();
    const southWest = map.options.crs.project(bounds.getSouthWest());
    const northEast = map.options.crs.project(bounds.getNorthEast());
    const params = new URLSearchParams({
        service: 'WMS',
        version: '1.3.0',
        request: 'GetFeatureInfo',
        layers: layer.wmsParams.layers,
        query_layers: layer.wmsParams.layers,
        styles: layer.wmsParams.styles || '',
        crs: 'EPSG:3857',
        bbox: [southWest.x, southWest.y, northEast.x, northEast.y].join(','),
        width: String(size.x),
        height: String(size.y),
        i: String(Math.round(point.x)),
        j: String(Math.round(point.y)),
        info_format: 'application/json',
        feature_count: '5'
    });

    return fetchWithTimeout(`${serviceUrl}${params.toString()}`);
}

function showWmsFeatureInfo(properties, point, fallbackName) {
    if (!properties || typeof properties !== 'object') return;

    const normalizedProperties = Object.entries(properties).filter(([, value]) =>
        value !== null && value !== undefined && String(value).trim() !== ''
    );
    const getKeyValue = (predicate) => normalizedProperties.find(([key]) => predicate(key.toLowerCase().replace(/[^a-z0-9]/g, '')))?.[1];
    const name = getFeatureDisplayName(properties, String(getKeyValue((key) => key.includes('ime') || key.includes('name') || key.includes('naziv')) || fallbackName));
    const code = getKeyValue((key) => key.includes('sifra') || key.includes('code') || key === 'id');
    const content = L.DomUtil.create('div');
    const title = L.DomUtil.create('strong', '', content);
    title.textContent = name;

    if (code !== undefined) {
        const codeLine = L.DomUtil.create('div', '', content);
        codeLine.textContent = `Šifra: ${code}`;
    }

    L.popup().setLatLng(point).setContent(content).openOn(map);
}

map.on('click', async function(event) {
    const queryLayers = [];
    if (map.hasLayer(localCommunitiesOverview)) {
        queryLayers.push({ layer: localCommunityBoundaries, serviceUrl: rpeWmsUrl, name: 'Krajevna skupnost' });
    }
    if (map.hasLayer(cadastralZoningOverview)) {
        queryLayers.push({ layer: cadastralZoningOverview, serviceUrl: wmsInsUrl, name: 'Katastrska občina' });
    }
    if (queryLayers.length === 0) return;

    for (const queryLayer of queryLayers) {
        try {
            const response = await addWmsFeatureInfoRequest(queryLayer.layer, queryLayer.serviceUrl, event.containerPoint);
            if (!response.ok) continue;
            const featureCollection = await response.json();
            const properties = featureCollection.features?.[0]?.properties;
            if (properties) {
                showWmsFeatureInfo(properties, event.latlng, queryLayer.name);
                return;
            }
        } catch (error) {
            console.warn(`Unable to query ${queryLayer.name} WMS feature info.`, error);
        }
    }
});


function renderDetailValue(value) {
    if (value === null || value === undefined) return '';
    if (typeof value !== 'string') return String(value);
    const looksLikeHtml = /<\/?[a-zA-Z][^>]*>/.test(value);
    if (looksLikeHtml) return value;
    return value.replace(/\r\n|\r|\n/g, '<br>');
}

function getFeatureDisplayName(properties, fallback = 'Izbrana točka') {
    if (!properties || typeof properties !== 'object') return fallback;

    const candidateKeys = [
        'name', 'Name', 'Ime', 'Naziv', 'name of the trail', 'Name of the trail',
        'Ime poti', 'Ime obhodnice', 'Ime poti', 'Path name', 'Trail name',
        'Name of the path', 'Obhodnica'
    ];

    for (const key of candidateKeys) {
        const value = properties[key];
        if (value !== null && value !== undefined && String(value).trim() !== '') {
            return String(value);
        }
    }

    const fallbackKey = Object.keys(properties).find((key) => {
        const normalized = String(key).toLowerCase();
        return normalized === 'name' || normalized === 'ime' || normalized.endsWith('name') || normalized.endsWith('ime') || normalized.includes('trail') || normalized.includes('path');
    });

    if (fallbackKey && properties[fallbackKey] !== null && properties[fallbackKey] !== undefined) {
        const value = properties[fallbackKey];
        if (String(value).trim() !== '') return String(value);
    }

    return fallback;
}

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

            var name = getFeatureDisplayName(properties, marker?.feature?.properties?.name || 'Izbrana točka');

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
                    .map(([key, value]) => `<strong>${key}:</strong> ${renderDetailValue(value)}`)
                    .join('<br>');

                // Update the point details in the sidebar (excluding image fields)
                pointDetails.innerHTML += details || "No details available for this point.";
            }

            // Fetch and render connected external entries (append after details)
            fetchConnectedEntries(layerName, id).then(renderConnectedEntries);

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
                    const langMatch = window.location.pathname.match(/^\/([a-z]{2}(?:-[A-Z]{2})?)\//);
                    const langPrefix = langMatch ? `/${langMatch[1]}` : '/sl';
                    const detailSegment = window.detailPathSegment || 'detail';
                    window.location.href = `${langPrefix}/${detailSegment}/${encodeURIComponent(layerName)}/${encodeURIComponent(id)}/`;
                };
            }
            
            // Switch to the details tab in the sidepanel
            switchSidepanelTab('mySidepanelLeft', 2);

        });
}

// Ensure floating search bar is visible by default
//document.getElementById('floating-search-bar').classList.add('visible');

// Fetch connected external entries for a given model/object
async function fetchConnectedEntries(model_name, object_id) {
    try {
        const url = `/api/get_connected_external_entries/?model_name=${encodeURIComponent(model_name)}&object_id=${encodeURIComponent(object_id)}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (err) {
        console.error('Error fetching connected entries:', err);
        return { connected_entries: [] };
    }
}

// Render connected entries list inside the point details panel
function normalizeWikidataId(value) {
    if (!value && value !== 0) return null;
    const text = String(value).trim();
    if (!text) return null;
    const match = text.match(/(?:https?:\/\/(?:www\.)?wikidata\.org\/wiki\/)?(q\d+)/i);
    if (!match) return null;
    return match[1].toUpperCase();
}

function buildWikipediaUrlForExternalProject(externalProject, externalId) {
    const project = String(externalProject || '').toLowerCase();
    if (!['wikidata', 'wikidata-item'].includes(project)) return '';
    const qid = normalizeWikidataId(externalId);
    if (!qid) return '';
    return `https://sl.wikipedia.org/wiki/Special:GoToLinkedPage/slwiki/${qid}`;
}

function renderConnectedEntries(data) {
    const pointDetails = document.getElementById('point-details');
    if (!pointDetails) return;

    // Remove previous list if any
    const previous = document.getElementById('connected-entries');
    if (previous) previous.remove();

    const container = document.createElement('div');
    container.id = 'connected-entries';
    container.className = 'connected-entries';

    const entries = data.connected_entries || [];
    if (entries.length === 0) {
        container.innerHTML = '<br /><h4>Povezani vnosi</h4><p>Ni povezanih vnosov.</p>';
    } else {
        let listHtml = '<br /><h4>Povezani vnosi</h4><ul style="padding-left:18px;">';
        listHtml += entries.flatMap(e => {
            const projectName = e.external_project_name || e.external_project || 'Zunanji vir';
            const externalId = e.external_id || '';
            const url = e.external_url || '';
            const additionalInfo = e.additional_info || '';
            const isMisc = e.external_project === 'misc';
            const wikipediaUrl = e.wikipedia_url || buildWikipediaUrlForExternalProject(e.external_project, externalId);

            const items = [];
            let label;
            if (isMisc) {
                label = `Druge povezave: ${additionalInfo || externalId || url}`;
            } else {
                const idWithAdditionalInfo = additionalInfo && externalId
                    ? `${externalId} (${additionalInfo})`
                    : (externalId || additionalInfo);
                label = `${projectName}: ${idWithAdditionalInfo}`;
            }

            if (url) {
                items.push(`<li><a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a></li>`);
            } else {
                items.push(`<li>${label}</li>`);
            }

            if (wikipediaUrl) {
                const wikipediaLabel = additionalInfo
                    ? `Članek na slovenski Wikipediji: ${additionalInfo}`
                    : 'Članek na slovenski Wikipediji';
                items.push(`<li><a href="${wikipediaUrl}" target="_blank" rel="noopener noreferrer">${wikipediaLabel}</a></li>`);
            }

            return items;
        }).join('');
        listHtml += '</ul>';
        container.innerHTML = listHtml;
    }

    pointDetails.appendChild(container);
}

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

// Fetch and render markers or line features for the layer. Returns the Leaflet layer added.
async function loadMarkersForLayer(layer_model_info, markerClusterGroup, cacheMetadata) {
    showLoadingCircle();
    let geojson;
    try {
        geojson = await getBriefGeoJson(layer_model_info, cacheMetadata);
    } finally {
        hideLoadingCircle();
    }
    console.log(`GeoJSON loaded for layer: ${layer_model_info.model_name}`);

    // Special handling for line-based layers such as trails and occupation borders.
    if (['okupacijskemeje', 'partisantrail'].includes(layer_model_info.model_name)) {
        const isTrail = layer_model_info.model_name === 'partisantrail';
        console.log(`Rendering line layer: ${layer_model_info.model_name}`);

        const lineLayer = L.geoJSON(geojson, {
            style: function(feature) {
                const c = feature.properties && feature.properties.color ? feature.properties.color : (isTrail ? '#2b7a78' : '#ff0000');
                return { color: c, weight: isTrail ? 4 : 3, opacity: 0.9 };
            },
            onEachFeature: function(feature, layer) {
                layer._layerName = layer_model_info.model_name;
                const featureName = getFeatureDisplayName(feature.properties, isTrail ? 'Izbrana obhodnica' : 'Izbrana meja');

                layer.on('click', function() {
                    if (!layer.getPopup()) {
                        layer.bindPopup(featureName);
                    }
                    layer.openPopup();
                    displayDetails(layer._layerName, feature.id);
                });
            }
        });
        lineLayer.addTo(map);
        return lineLayer;
    }

    // Default: point features rendered as markers (clustered)
    L.geoJSON(geojson, {
        pointToLayer: function(feature, latlng) {
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
                        icon = L.divIcon({ className: 'icon star-icon' });
                        if (feature.properties.status) {
                            switch (feature.properties.status) {
                                case 1:
                                    icon = L.divIcon({ className: 'icon star-icon red' });
                                    break;
                                case 3:
                                    icon = L.divIcon({ className: 'icon star-icon blue' });
                                    break;
                                case 2:
                                    icon = L.divIcon({ className: 'icon star-icon green' });
                                    break;
                            }
                        } else {
                            icon = L.divIcon({ className: 'icon star-icon red' });
                        }
                        break;
                    default:
                        icon = L.divIcon({ className: `icon ${layer_model_info.icon}` });
                        break;
                }
            }
            const marker = L.marker(latlng, { icon: icon });
            marker._layerName = layer_model_info.model_name;
            return marker;
        },
        onEachFeature: function(feature, layer) {
            layer.on('click', function(e) {
                const marker = e.target;
                const popupTitle = getFeatureDisplayName(feature.properties, 'Izbrana točka');
                if (!marker.getPopup()) {
                    marker.bindPopup(popupTitle);
                }
                marker.openPopup();
                displayDetails(marker._layerName, feature.id);
            });
        }
    }).addTo(markerClusterGroup);
    return markerClusterGroup;
}

const MAP_LAYER_ORDER = [
    'partisanmemorial',
    'croatianpartisanmemorial',
    'partisantrail',
    'osamosvojitvenaobelezja',
    'partisanpointswithoutmemorial',
    'partisannaming',
    'okupacijskemeje',
    'othermemorials',
];

const MAP_LAYER_DISPLAY_NAMES = {
    partisanmemorial: 'Spomeniki (SLO)',
    croatianpartisanmemorial: 'Spomeniki (HR)',
    osamosvojitvenaobelezja: 'Osamosvojitev',
};

function getLayerDisplayName(layer) {
    return MAP_LAYER_DISPLAY_NAMES[layer.model_name] || layer.verbose_name_plural;
}

// Fetch model names and dynamically create marker layers
async function processGeoLayers() {
    const langMatch = window.location.pathname.match(/^\/([a-z]{2}(?:-[A-Z]{2})?)\//);
    const langCode = langMatch ? langMatch[1] : '';
    const [layers, cacheMetadata] = await Promise.all([
        getGeoLayers(langCode),
        fetchWithTimeout('/api/cache_metadata/')
            .then(response => {
                if (!response.ok) throw new Error(`Cache metadata API returned ${response.status}`);
                return response.json();
            })
            .catch(error => {
                console.warn('Map cache validation is unavailable; loading brief data directly.', error);
                return null;
            }),
    ]);

    const filterContainer = document.getElementById('filter-container');
    const layerOrder = new Map(MAP_LAYER_ORDER.map((modelName, index) => [modelName, index]));
    const orderedLayers = layers
        .map((layer, originalIndex) => ({ layer, originalIndex }))
        .sort((left, right) => {
            const leftOrder = layerOrder.get(left.layer.model_name) ?? Number.MAX_SAFE_INTEGER;
            const rightOrder = layerOrder.get(right.layer.model_name) ?? Number.MAX_SAFE_INTEGER;
            return leftOrder - rightOrder || left.originalIndex - right.originalIndex;
        })
        .map(({ layer }) => layer);

    const loadPromises = orderedLayers.map(async layer => {
        let createdLayer;
        const lineLayerModels = new Set(['okupacijskemeje', 'partisantrail']);
        const isLineLayer = lineLayerModels.has(layer.model_name);
        const displayName = getLayerDisplayName(layer);

        if (isLineLayer) {
            // Directly load and add line layer (not clustered)
            createdLayer = await loadMarkersForLayer(layer, null, cacheMetadata);
            createdLayer.addTo(map);
        } else {
            const markerClusterGroup = L.markerClusterGroup({
                chunkedLoading: true,
                disableClusteringAtZoom: 12,
                name: displayName,
            });
            createdLayer = await loadMarkersForLayer(layer, markerClusterGroup, cacheMetadata);
            markerClusterGroup.addTo(map);
        }

        return { layer, createdLayer, displayName };
    });

    const loadedLayers = await Promise.all(loadPromises);
    geoLayers = loadedLayers.map(({ createdLayer }) => createdLayer);

    // Build filter UI in the configured order, not in request-completion order.
    for (const { createdLayer, displayName } of loadedLayers) {
        const filterOption = document.createElement('div');
        filterOption.className = 'filter-option';
        const label = document.createElement('label');
        label.textContent = displayName;
        filterOption.appendChild(label);
        filterOption.classList.add('enabled');
        filterOption.title = 'Kliknite za skritje sloja';

        filterOption.addEventListener('click', function() {
            if (filterOption.classList.contains('enabled')) {
                map.removeLayer(createdLayer);
                filterOption.classList.remove('enabled');
                filterOption.title = 'Kliknite za prikaz sloja';
            } else {
                map.addLayer(createdLayer);
                filterOption.classList.add('enabled');
                filterOption.title = 'Kliknite za skritje sloja';
            }
        });

        filterContainer.appendChild(filterOption);
    }

    updateLayerControl(baseMaps, overlayMaps);
}

// Call the function to fetch model names and initialize layers
let geoLayers = [];

function normalizeSidebarSearchText(value) {
    return String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[đĐ]/g, 'd')
        .replace(/[-‐‑‒–—―−]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

function filterSidebarSearchData(query, records) {
    const normalizedQuery = normalizeSidebarSearchText(query);
    if (!normalizedQuery) return {};

    const matches = {};
    for (const [name, record] of Object.entries(records)) {
        if (normalizeSidebarSearchText(name).includes(normalizedQuery)) {
            matches[name] = record;
        }
    }
    return matches;
}

processGeoLayers().then(() => {
    L.control.search({
        layer: L.layerGroup(geoLayers),
        initial: false,
        casesensitive: false,
        collapsed: false,
        container: 'searchbox',
        zoom: 17,
        position: 'topright',
        propertyName: 'name',
        filterData: filterSidebarSearchData,
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


