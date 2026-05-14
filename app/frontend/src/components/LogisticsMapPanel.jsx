import { CircleMarker, MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { createAssetDivIcon } from "../utils/mapAssetIcons";

export function LogisticsMapPanel({
  mapView,
  onChangeMapView,
  selectedMapData,
  assetCounts,
}) {
  return (
    <article className="panel map-panel">
      <div className="map-header">
        <h3>Live Logistics Map</h3>
        <select value={mapView} onChange={(event) => onChangeMapView(event.target.value)}>
          <option value="airFreight">Global Air Freight</option>
          <option value="global">Global Shipping</option>
          <option value="regional">North America</option>
        </select>
      </div>
      <div className="map-viewport">
        <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom style={{ height: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {(selectedMapData.ports ?? []).map((port) => (
            <CircleMarker
              key={`${port.name}-${port.lat}-${port.lng}`}
              center={[port.lat, port.lng]}
              radius={7}
              pathOptions={{
                color: port.risk > 15 ? "#FF4757" : "#2ECC71",
                fillColor: port.risk > 15 ? "#FF4757" : "#2ECC71",
                fillOpacity: 0.8,
              }}
            >
              <Popup>
                <strong>{port.name}</strong>
                <br />
                Risk: {port.risk ?? 0}%
              </Popup>
            </CircleMarker>
          ))}
          {(selectedMapData.assets ?? []).map((asset, index) => {
            if (typeof asset.lat !== "number" || typeof asset.lng !== "number") {
              return null;
            }
            const fill =
              mapView === "airFreight"
                ? "#00E0FF"
                : mapView === "global"
                  ? "#FFC300"
                  : "#9D00FF";
            const icon = createAssetDivIcon(mapView, asset, { fill, stroke: "#10162a" });
            return (
              <Marker key={asset.id ?? `${asset.name}-${index}`} position={[asset.lat, asset.lng]} icon={icon}>
                <Popup>
                  <strong>{asset.name}</strong>
                  <br />
                  {asset.cargo ? `Cargo: ${asset.cargo}` : "Active asset"}
                  {asset.speed ? (
                    <>
                      <br />
                      Speed: {asset.speed}
                    </>
                  ) : null}
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
      <div className="muted map-counts">
        Assets (Air: {assetCounts.air} | Sea: {assetCounts.sea} | Land: {assetCounts.land})
      </div>
    </article>
  );
}
