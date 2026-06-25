import { useMemo } from 'react';
import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';

// Fix leaflet default icon issue in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const CITIES = [
  { name: 'Mumbai, IN', lat: 19.0760, lng: 72.8777 },
  { name: 'Dubai, UAE', lat: 25.2048, lng: 55.2708 },
  { name: 'London, UK', lat: 51.5074, lng: -0.1278 },
  { name: 'Singapore, SG', lat: 1.3521, lng: 103.8198 },
  { name: 'New York, US', lat: 40.7128, lng: -74.0060 },
  { name: 'Hong Kong, HK', lat: 22.3193, lng: 114.1694 },
  { name: 'Frankfurt, DE', lat: 50.1109, lng: 8.6821 },
  { name: 'Zurich, CH', lat: 47.3769, lng: 8.5417 },
  { name: 'Cayman Islands', lat: 19.3133, lng: -81.2546 },
  { name: 'Panama City, PA', lat: 8.9824, lng: -79.5199 },
  { name: 'Cyprus', lat: 35.1264, lng: 33.4299 },
  { name: 'Seychelles', lat: -4.6796, lng: 55.4920 },
];

function getCityForNode(id) {
  let hash = 0;
  const str = String(id);
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return CITIES[Math.abs(hash) % CITIES.length];
}

const customIcon = new L.DivIcon({
  className: 'custom-div-icon',
  html: `<div style="background-color: #ef4444; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(239, 68, 68, 0.8);"></div>`,
  iconSize: [12, 12],
  iconAnchor: [6, 6]
});

const centerIcon = new L.DivIcon({
  className: 'custom-div-icon-center',
  html: `<div style="background-color: #f97316; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 15px rgba(249, 115, 22, 0.8);"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8]
});

export default function GeoMapView({ nodes, links, centerNodeId }) {
  const { mappedNodes, mappedLinks } = useMemo(() => {
    const mNodes = nodes.map(n => {
      const city = getCityForNode(n.id);
      return {
        ...n,
        lat: city.lat + (Math.random() - 0.5) * 0.1, // Add slight jitter so nodes in same city don't completely overlap
        lng: city.lng + (Math.random() - 0.5) * 0.1,
        city: city.name
      };
    });

    const nodeMap = new Map(mNodes.map(n => [n.id, n]));

    const mLinks = links.map(l => {
      const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
      const targetId = typeof l.target === 'object' ? l.target.id : l.target;
      const sNode = nodeMap.get(sourceId);
      const tNode = nodeMap.get(targetId);
      return {
        ...l,
        sNode,
        tNode
      };
    }).filter(l => l.sNode && l.tNode);

    return { mappedNodes: mNodes, mappedLinks: mLinks };
  }, [nodes, links]);

  if (!mappedNodes.length) {
    return (
      <div style={{ padding: '48px', textAlign: 'center', color: '#94a3b8' }}>
        No geographic data available.
      </div>
    );
  }

  return (
    <div style={{ height: '100%', width: '100%', position: 'relative' }}>
      <MapContainer 
        center={[20, 40]} 
        zoom={2} 
        style={{ height: '100%', width: '100%', background: '#0f172a' }}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        
        {mappedLinks.map((link, i) => (
          <Polyline 
            key={`link-${link.id}-${i}`}
            positions={[
              [link.sNode.lat, link.sNode.lng],
              [link.tNode.lat, link.tNode.lng]
            ]}
            color="#3b82f6"
            weight={link.amount > 100000 ? 3 : 1}
            opacity={0.4}
            dashArray={link.amount > 100000 ? "5, 10" : undefined}
          />
        ))}

        {mappedNodes.map(node => (
          <Marker 
            key={`node-${node.id}`} 
            position={[node.lat, node.lng]}
            icon={node.id === centerNodeId ? centerIcon : customIcon}
          >
            <Popup>
              <div style={{ minWidth: '180px' }}>
                <div style={{ fontWeight: 'bold', fontSize: '14px', borderBottom: '1px solid #e2e8f0', paddingBottom: '4px', marginBottom: '8px' }}>
                  {node.label}
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>
                  📍 {node.city}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span>Risk Score:</span>
                  <span style={{ fontWeight: 'bold', color: node.risk_score > 80 ? '#ef4444' : '#10b981' }}>
                    {Math.round(node.risk_score || 0)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span>Total Sent:</span>
                  <span style={{ fontWeight: 'bold' }}>₹{node.total_sent?.toLocaleString()}</span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
