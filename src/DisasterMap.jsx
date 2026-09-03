import { Circle, MapContainer, Marker, Popup, TileLayer, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const markerIcon = new L.Icon({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function DisasterMap({ externalData, riskScore }) {
  const location = externalData?.location;
  const center = location
    ? [location.latitude, location.longitude]
    : [21.2514, 81.6296];
  const earthquakes = externalData?.operational?.earthquakes ?? [];
  const features = externalData?.landslide_features ?? {};
  const sources = externalData?.sources ?? {};
  const resolvedAddress = sources.geocoding?.data?.results?.[0]?.formatted_address;
  const dynamicRisk = Number(riskScore ?? externalData?.operational?.risk?.score ?? 0);
  const dynamicLevel = dynamicRisk >= 80 ? "CRITICAL" : dynamicRisk >= 60 ? "HIGH" : dynamicRisk >= 35 ? "MODERATE" : "LOW";

  return (
    <div className="real-map">
      <MapContainer
        key={`${center[0]}-${center[1]}`}
        center={center}
        zoom={location ? 9 : 13}
        scrollWheelZoom
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        <TileLayer
          attribution="Labels © Esri"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
          pane="overlayPane"
        />

        {location && (
          <Circle center={center} radius={22000} pathOptions={{ color: "#ff3d64", fillColor: "#ff3d64", fillOpacity: 0.2 }}>
            <Tooltip permanent direction="center" className="map-risk-label">FUSION ZONE · {dynamicLevel}</Tooltip>
            <Popup>
              <strong>LIVE DATA-FUSION ZONE</strong><br />
              {resolvedAddress ?? `${center[0].toFixed(4)}, ${center[1].toFixed(4)}`}<br />
              Landslide risk: {dynamicRisk.toFixed(1)}/100<br />
              Rainfall: {Number(features.rainfall_mm ?? 0).toFixed(1)} mm<br />
              River level: {features.water_level != null ? `${Number(features.water_level).toFixed(2)} m` : "Unavailable"}<br />
              Elevation: {features.terrain?.elevation_m != null ? `${Number(features.terrain.elevation_m).toFixed(0)} m` : "Unavailable"}<br />
              Official alerts: {features.official_alert_count ?? 0}<br />
              Satellite scenes: {features.satellite_scene_count ?? 0}
            </Popup>
          </Circle>
        )}

        {earthquakes.filter((event) => event.latitude != null && event.longitude != null).map((event) => (
          <Circle
            key={event.id ?? `${event.latitude}-${event.longitude}`}
            center={[event.latitude, event.longitude]}
            radius={Math.max(3500, Number(event.magnitude ?? 0) * 4500)}
            pathOptions={{ color: "#f59e0b", fillColor: "#f59e0b", fillOpacity: 0.3 }}
          >
            <Tooltip>USGS M{event.magnitude ?? "--"}</Tooltip>
            <Popup><strong>USGS Earthquake</strong><br />Magnitude: {event.magnitude ?? "--"}<br />{event.place ?? "Location unavailable"}</Popup>
          </Circle>
        ))}

        {!location && <Circle center={[21.255, 81.635]} radius={900} pathOptions={{ color: "#ff3d64", fillColor: "#ff3d64", fillOpacity: 0.28 }}>
          <Tooltip permanent direction="center" className="map-risk-label">ZONE A · CRITICAL</Tooltip>
          <Popup><strong>ZONE A — CRITICAL</strong><br />Flood probability: 87%<br />People at risk: 1,248</Popup>
        </Circle>}
        {!location && <Circle center={[21.245, 81.62]} radius={650} pathOptions={{ color: "#ff9e2c", fillColor: "#ff9e2c", fillOpacity: 0.28 }}>
          <Tooltip permanent direction="center" className="map-risk-label">ZONE B · HIGH</Tooltip>
          <Popup><strong>ZONE B — HIGH</strong><br />Flood probability: 68%</Popup>
        </Circle>}
        {!location && <Circle center={[21.26, 81.615]} radius={500} pathOptions={{ color: "#ffe44d", fillColor: "#ffe44d", fillOpacity: 0.24 }}>
          <Tooltip permanent direction="center" className="map-risk-label">ZONE C · MODERATE</Tooltip>
          <Popup><strong>ZONE C — MODERATE</strong><br />Flood probability: 42%</Popup>
        </Circle>}

        {!location && <><Marker position={[21.2505, 81.625]} icon={markerIcon}>
          <Tooltip permanent direction="right" offset={[12, 0]} className="map-place-label">🏥 Government Hospital</Tooltip>
          <Popup><strong>Government Hospital</strong><br />Available beds: 47</Popup>
        </Marker>
        <Marker position={[21.257, 81.632]} icon={markerIcon}>
          <Tooltip permanent direction="right" offset={[12, 0]} className="map-place-label">🚑 Rescue Team 02</Tooltip>
          <Popup><strong>Rescue Team 02</strong><br />Status: AVAILABLE</Popup>
        </Marker>
        <Marker position={[21.242, 81.63]} icon={markerIcon}>
          <Tooltip permanent direction="right" offset={[12, 0]} className="map-place-label">🏠 Emergency Shelter</Tooltip>
          <Popup><strong>Emergency Shelter</strong><br />Capacity: 500</Popup>
        </Marker></>}
      </MapContainer>
    </div>
  );
}

export default DisasterMap;
