"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Button, Card, Chip } from "@heroui/react";
import { Crosshair, Satellite } from "lucide-react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";

interface TacticalMapProps {
  lat: number;
  lon: number;
  heading: number;
  alt: number;
  speed: number;
  sats: number;
  fix: number;
  breadcrumbs: [number, number][];
  onAddWaypoint?: (lat: number, lon: number) => void;
}

const TILE_LAYERS = {
  dark: {
    name: "Dark",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  },
  satellite: {
    name: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
  },
  streets: {
    name: "Streets",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
};

export default function TacticalMap({
  lat,
  lon,
  heading,
  alt,
  speed,
  sats,
  fix,
  breadcrumbs,
  onAddWaypoint,
}: TacticalMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const droneMarkerRef = useRef<L.Marker | null>(null);
  const trailPolylineRef = useRef<L.Polyline | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  const [activeLayer, setActiveLayer] = useState<keyof typeof TILE_LAYERS>("dark");
  const [autoCenter, setAutoCenter] = useState<boolean>(true);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialLat = lat && lat !== 0 ? lat : 28.6139;
    const initialLon = lon && lon !== 0 ? lon : 77.2090;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 17,
      zoomControl: false,
      attributionControl: false,
    });

    const tile = L.tileLayer(TILE_LAYERS[activeLayer].url, {
      maxZoom: 20,
      attribution: TILE_LAYERS[activeLayer].attribution,
    }).addTo(map);

    tileLayerRef.current = tile;

    // Custom Tactical Quadcopter SVG Icon with dynamic rotation
    const droneHtml = `
      <div id="tactical-drone-marker" style="transform: rotate(${heading || 0}deg); transform-origin: center; transition: transform 0.15s linear;">
        <svg width="42" height="42" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Outer Heading Ring -->
          <circle cx="24" cy="24" r="21" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.6"/>
          <!-- Drone Arms -->
          <line x1="12" y1="12" x2="36" y2="36" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="36" y1="12" x2="12" y2="36" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>
          <!-- Rotors -->
          <circle cx="12" cy="12" r="5" fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="1.5"/>
          <circle cx="36" cy="12" r="5" fill="var(--accent)" fill-opacity="0.25" stroke="var(--accent)" stroke-width="1.5"/>
          <circle cx="12" cy="36" r="5" fill="var(--danger)" fill-opacity="0.25" stroke="var(--danger)" stroke-width="1.5"/>
          <circle cx="36" cy="36" r="5" fill="var(--danger)" fill-opacity="0.25" stroke="var(--danger)" stroke-width="1.5"/>
          <!-- Center Body -->
          <circle cx="24" cy="24" r="7" fill="var(--surface)" stroke="var(--accent)" stroke-width="2"/>
          <!-- Forward Nose Needle -->
          <polygon points="24,6 27,15 21,15" fill="var(--accent)"/>
        </svg>
      </div>
    `;

    const droneIcon = L.divIcon({
      html: droneHtml,
      className: "drone-leaflet-icon",
      iconSize: [42, 42],
      iconAnchor: [21, 21],
    });

    const marker = L.marker([initialLat, initialLon], { icon: droneIcon }).addTo(map);
    droneMarkerRef.current = marker;

    // Flight Path Polyline
    const polyline = L.polyline([], {
      color: "var(--accent)",
      weight: 3,
      opacity: 0.85,
      dashArray: "4, 6",
    }).addTo(map);
    trailPolylineRef.current = polyline;

    // Click handler to drop waypoint
    map.on("click", (e: L.LeafletMouseEvent) => {
      if (onAddWaypoint) {
        onAddWaypoint(e.latlng.lat, e.latlng.lng);
      }
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Layer when activeLayer changes
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current) return;
    mapInstanceRef.current.removeLayer(tileLayerRef.current);
    const newTile = L.tileLayer(TILE_LAYERS[activeLayer].url, {
      maxZoom: 20,
      attribution: TILE_LAYERS[activeLayer].attribution,
    }).addTo(mapInstanceRef.current);
    tileLayerRef.current = newTile;
  }, [activeLayer]);

  // Update Position & Heading
  useEffect(() => {
    if (!mapInstanceRef.current || !droneMarkerRef.current) return;

    if (lat && lon && lat !== 0 && lon !== 0) {
      droneMarkerRef.current.setLatLng([lat, lon]);

      // Rotate icon element directly for ultra-smooth responsiveness
      const el = document.getElementById("tactical-drone-marker");
      if (el) {
        el.style.transform = `rotate(${heading || 0}deg)`;
      }

      if (autoCenter) {
        mapInstanceRef.current.panTo([lat, lon], { animate: true, duration: 0.5 });
      }
    }
  }, [lat, lon, heading, autoCenter]);

  // Update Trail Breadcrumbs
  useEffect(() => {
    if (!trailPolylineRef.current) return;
    if (breadcrumbs && breadcrumbs.length > 0) {
      trailPolylineRef.current.setLatLngs(breadcrumbs);
    }
  }, [breadcrumbs]);

  const handleCenterOnDrone = () => {
    if (mapInstanceRef.current && lat && lon) {
      mapInstanceRef.current.setView([lat, lon], 18, { animate: true });
      setAutoCenter(true);
    }
  };

  return (
    <div className="relative w-full h-full min-h-[480px] rounded-lg overflow-hidden border border-border bg-surface">
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full min-h-[480px] z-0" />

      {/* Top Floating Tactical HUD Bar */}
      <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        {/* GPS Coordinate & Satellite Pill */}
        <Card className="pointer-events-auto bg-background/85 backdrop-blur-md border border-accent/30 shadow-xl">
          <div className="flex items-center gap-2.5 px-3 py-2">
            <Satellite className="w-3.5 h-3.5 text-accent animate-pulse" />
            <span className="font-mono text-xs text-foreground tabular-nums">
              {lat ? lat.toFixed(6) : "0.000000"}°N, {lon ? lon.toFixed(6) : "0.000000"}°E
            </span>
            <Chip
              size="sm"
              variant="soft"
              color={fix >= 3 ? "success" : fix === 2 ? "warning" : "danger"}
              className="h-5 text-[10px] font-mono"
            >
              {sats} SAT | {fix >= 3 ? "3D" : fix === 2 ? "2D" : "NO"} FIX
            </Chip>
          </div>
        </Card>

        {/* Layer Selector & Controls */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <Card className="bg-background/85 backdrop-blur-md border border-border shadow-lg">
            <div className="flex p-1 gap-0.5">
              {(Object.keys(TILE_LAYERS) as (keyof typeof TILE_LAYERS)[]).map((key) => (
                <Button
                  key={key}
                  size="sm"
                  variant={activeLayer === key ? "primary" : "ghost"}
                  className="font-mono text-xs h-7 min-w-0 px-2.5"
                  onPress={() => setActiveLayer(key)}
                >
                  {TILE_LAYERS[key].name}
                </Button>
              ))}
            </div>
          </Card>

          <GcsTooltip content="Center view on drone">
            <Button
              size="sm"
              variant="outline"
              className="bg-background/85 backdrop-blur-md border border-border min-w-0 px-2 h-9"
              onPress={handleCenterOnDrone}
              aria-label="Center on Drone"
            >
              <Crosshair className="w-4 h-4" />
            </Button>
          </GcsTooltip>
        </div>
      </div>

      {/* Bottom Floating Altitude & Speed Tape */}
      <Card className="absolute bottom-3 left-3 z-[1000] pointer-events-none bg-background/90 backdrop-blur-md border border-border shadow-xl">
        <div className="flex items-center gap-4 px-4 py-2.5">
          <div className="flex flex-col">
            <span className="text-[10px] text-muted uppercase font-mono tracking-wider">Alt</span>
            <span className="font-mono text-sm font-bold text-accent">
              {alt.toFixed(2)} m
            </span>
            <span className="text-[9px] text-muted font-mono">({(alt * 3.28084).toFixed(1)} ft)</span>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex flex-col">
            <span className="text-[10px] text-muted uppercase font-mono tracking-wider">Speed</span>
            <span className="font-mono text-sm font-bold text-foreground">
              {speed.toFixed(1)} m/s
            </span>
            <span className="text-[9px] text-muted font-mono">({(speed * 3.6).toFixed(1)} km/h)</span>
          </div>
          <div className="w-px h-8 bg-border" />
          <div className="flex flex-col">
            <span className="text-[10px] text-muted uppercase font-mono tracking-wider">Heading</span>
            <span className="font-mono text-sm font-bold text-accent">
              {Math.round(heading || 0)}°
            </span>
          </div>
        </div>
      </Card>

      {/* Breadcrumb Point Count */}
      <div className="absolute bottom-3 right-3 z-[1000] pointer-events-none">
        <Chip size="sm" variant="soft" className="bg-background/85 backdrop-blur-md border border-border text-[10px] font-mono text-muted">
          Track: {breadcrumbs.length} pts
        </Chip>
      </div>
    </div>
  );
}
