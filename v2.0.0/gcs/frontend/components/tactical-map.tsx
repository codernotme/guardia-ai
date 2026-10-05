"use client";

import { useEffect, useRef, useState } from "react";
import type * as LType from "leaflet";
import { Button, Card, Chip } from "@heroui/react";
import { GcsTooltip } from "@/components/ui/gcs-tooltip";
import {
  Crosshair,
  Satellite,
  Maximize2,
  Minimize2,
  Plus,
  Minus,
  Navigation,
  Compass,
  Search,
  Bell,
  Download,
  Star,
  X,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Layers,
  Radio,
  Flame,
} from "lucide-react";

interface TacticalMapProps {
  lat: number;
  lon: number;
  heading: number;
  alt: number;
  speed: number;
  sats: number;
  fix: number;
  breadcrumbs: [number, number][];
  armed?: boolean;
  onAddWaypoint?: (lat: number, lon: number) => void;
  onOpenAutoSetup?: () => void;
  onToggleArm?: () => void;
}

const TILE_LAYERS = {
  satellite: {
    name: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>',
  },
  dark: {
    name: "Dark",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
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
  armed = false,
  onAddWaypoint,
  onOpenAutoSetup,
  onToggleArm,
}: TacticalMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const miniMapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const miniMapInstanceRef = useRef<any>(null);
  const droneMarkerRef = useRef<any>(null);
  const trailPolylineRef = useRef<any>(null);
  const tileLayerRef = useRef<any>(null);
  const LRef = useRef<any>(null);

  const [activeLayer, setActiveLayer] = useState<keyof typeof TILE_LAYERS>("satellite");
  const [autoCenter, setAutoCenter] = useState<boolean>(true);
  const [is3DMode, setIs3DMode] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  // Floating Inspection Card states
  const [showInspectionCard, setShowInspectionCard] = useState<boolean>(true);
  const [isSensorExpanded, setIsSensorExpanded] = useState<boolean>(true);
  const [isLogExpanded, setIsLogExpanded] = useState<boolean>(false);

  // Search input state
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Base coordinates (centered around drone or Stanfield test fields)
  const currentLat = lat && lat !== 0 ? lat : 28.6139;
  const currentLon = lon && lon !== 0 ? lon : 77.2090;

  // Initialize Leaflet Map (client-side only)
  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current) return;
    let isCancelled = false;

    import("leaflet").then((leafletModule) => {
      if (isCancelled || !mapContainerRef.current || mapInstanceRef.current) return;
      const L = (leafletModule.default || leafletModule) as any;
      LRef.current = L;

      if ((mapContainerRef.current as any)._leaflet_id) {
        delete (mapContainerRef.current as any)._leaflet_id;
      }

      const map = L.map(mapContainerRef.current, {
        center: [currentLat, currentLon],
        zoom: 17,
        zoomControl: false,
        attributionControl: false,
      });

      const tile = L.tileLayer(TILE_LAYERS[activeLayer].url, {
        maxZoom: 20,
        attribution: TILE_LAYERS[activeLayer].attribution,
      }).addTo(map);

      tileLayerRef.current = tile;

    // ── Polygon Sector 1 (Green Agricultural / Recon Field) ──
    const area1Coords: [number, number][] = [
      [currentLat - 0.0018, currentLon - 0.0022],
      [currentLat + 0.0015, currentLon - 0.0015],
      [currentLat + 0.0022, currentLon + 0.0012],
      [currentLat - 0.0012, currentLon + 0.0018],
    ];

    const area1Polygon = L.polygon(area1Coords, {
      color: "#10b981",
      weight: 2.5,
      fillColor: "#10b981",
      fillOpacity: 0.35,
      dashArray: "6, 6",
    }).addTo(map);

    // Area 1 Center HTML Badge
    const area1Center = area1Polygon.getBounds().getCenter();
    const area1Badge = L.divIcon({
      html: `
        <div class="flex flex-col items-center justify-center text-center pointer-events-none drop-shadow-md">
          <div class="w-7 h-7 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center text-white mb-0.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.343 9.343c5.857-5.857 15.355-5.857 21.213 0"></path></svg>
          </div>
          <span class="text-[11px] font-bold text-white tracking-wide">Area 1</span>
          <span class="text-[9px] text-white/80 font-medium">Active Monitoring</span>
        </div>
      `,
      className: "field-area-badge",
      iconSize: [120, 60],
      iconAnchor: [60, 30],
    });
    L.marker(area1Center, { icon: area1Badge, interactive: false }).addTo(map);

    // ── Polygon Sector 2 (Amber Monitoring Zone) ──
    const area2Coords: [number, number][] = [
      [currentLat + 0.0025, currentLon + 0.0028],
      [currentLat + 0.0042, currentLon + 0.0035],
      [currentLat + 0.0038, currentLon + 0.0062],
      [currentLat + 0.0022, currentLon + 0.0055],
    ];

    const area2Polygon = L.polygon(area2Coords, {
      color: "#f59e0b",
      weight: 2,
      fillColor: "#f59e0b",
      fillOpacity: 0.28,
      dashArray: "4, 4",
    }).addTo(map);

    const area2Center = area2Polygon.getBounds().getCenter();
    const area2Badge = L.divIcon({
      html: `
        <div class="flex flex-col items-center justify-center text-center pointer-events-none drop-shadow-md">
          <div class="w-7 h-7 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center text-white mb-0.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.343 9.343c5.857-5.857 15.355-5.857 21.213 0"></path></svg>
          </div>
          <span class="text-[11px] font-bold text-white tracking-wide">Area 2</span>
          <span class="text-[9px] text-white/80 font-medium">Active Monitoring</span>
        </div>
      `,
      className: "field-area-badge",
      iconSize: [120, 60],
      iconAnchor: [60, 30],
    });
    L.marker(area2Center, { icon: area2Badge, interactive: false }).addTo(map);

    // ── Drone Marker with Rotating Quadcopter SVG ──
    const droneHtml = `
      <div id="tactical-drone-marker" style="transform: rotate(${heading || 0}deg); transform-origin: center; transition: transform 0.15s linear;">
        <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Outer Pulsing Range Ring -->
          <circle cx="24" cy="24" r="22" stroke="#10b981" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.8"/>
          <!-- Drone Arms -->
          <line x1="12" y1="12" x2="36" y2="36" stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>
          <line x1="36" y1="12" x2="12" y2="36" stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>
          <!-- Rotors (Front Green / Back Red) -->
          <circle cx="12" cy="12" r="5.5" fill="#10b981" fill-opacity="0.4" stroke="#10b981" stroke-width="2"/>
          <circle cx="36" cy="12" r="5.5" fill="#10b981" fill-opacity="0.4" stroke="#10b981" stroke-width="2"/>
          <circle cx="12" cy="36" r="5.5" fill="#ef4444" fill-opacity="0.4" stroke="#ef4444" stroke-width="2"/>
          <circle cx="36" cy="36" r="5.5" fill="#ef4444" fill-opacity="0.4" stroke="#ef4444" stroke-width="2"/>
          <!-- Fuselage Body -->
          <circle cx="24" cy="24" r="8" fill="#111827" stroke="#10b981" stroke-width="2.5"/>
          <!-- Heading Vector Needle -->
          <polygon points="24,5 28,15 20,15" fill="#10b981"/>
        </svg>
      </div>
    `;

    const droneIcon = L.divIcon({
      html: droneHtml,
      className: "drone-leaflet-icon",
      iconSize: [46, 46],
      iconAnchor: [23, 23],
    });

    const marker = L.marker([currentLat, currentLon], { icon: droneIcon }).addTo(map);
    droneMarkerRef.current = marker;

    // Flight Path Trail
    const polyline = L.polyline([], {
      color: "#10b981",
      weight: 3,
      opacity: 0.9,
      dashArray: "5, 7",
    }).addTo(map);
    trailPolylineRef.current = polyline;

    // Waypoint click trigger
    map.on("click", (e: L.LeafletMouseEvent) => {
      if (onAddWaypoint) {
        onAddWaypoint(e.latlng.lat, e.latlng.lng);
      }
    });

      mapInstanceRef.current = map;

      // ── Inset Mini-Map Initialization ──
      if (miniMapContainerRef.current && !miniMapInstanceRef.current) {
        if ((miniMapContainerRef.current as any)._leaflet_id) {
          delete (miniMapContainerRef.current as any)._leaflet_id;
        }
        const miniMap = L.map(miniMapContainerRef.current, {
          center: [currentLat, currentLon],
          zoom: 14,
          zoomControl: false,
          attributionControl: false,
          dragging: false,
          scrollWheelZoom: false,
        });

        L.tileLayer(TILE_LAYERS.satellite.url, { maxZoom: 18 }).addTo(miniMap);
        L.rectangle(area1Polygon.getBounds(), { color: "#ffffff", weight: 1.5, fillOpacity: 0.15 }).addTo(miniMap);
        miniMapInstanceRef.current = miniMap;
      }
    });

    return () => {
      isCancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      if (miniMapInstanceRef.current) {
        miniMapInstanceRef.current.remove();
        miniMapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Layer when activeLayer changes
  useEffect(() => {
    if (!mapInstanceRef.current || !tileLayerRef.current || !LRef.current) return;
    const L = LRef.current;
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

    if (lat && lon && (lat !== 0 || lon !== 0)) {
      droneMarkerRef.current.setLatLng([lat, lon]);

      const el = document.getElementById("tactical-drone-marker");
      if (el) {
        el.style.transform = `rotate(${heading || 0}deg)`;
      }

      if (autoCenter) {
        mapInstanceRef.current.panTo([lat, lon], { animate: true, duration: 0.5 });
      }

      if (miniMapInstanceRef.current) {
        miniMapInstanceRef.current.panTo([lat, lon]);
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

  const handleZoomIn = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      mapContainerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div
      className={`relative w-full h-full min-h-[580px] rounded-3xl overflow-hidden border border-border shadow-md bg-[#0F1113] transition-all duration-300 ${
        is3DMode ? "perspective-[1000px] [transform:rotateX(15deg)]" : ""
      }`}
    >
      {/* Underlying Leaflet Map Canvas */}
      <div ref={mapContainerRef} className="w-full h-full min-h-[580px] z-0" />

      {/* ───────────────────────────────────────────────────────────
          Top Action & Search Header Bar (matching reference mockup)
         ─────────────────────────────────────────────────────────── */}
      <div className="absolute top-4 left-4 right-4 z-[1000] flex items-center justify-between gap-3 pointer-events-none">
        {/* Search Bar Input */}
        <div className="pointer-events-auto flex items-center bg-white dark:bg-[#1E2227] rounded-xl px-3 py-2 shadow-lg border border-border/80 w-72 sm:w-80 transition-all focus-within:ring-2 focus-within:ring-emerald-500">
          <Search className="w-4 h-4 text-muted mr-2.5 shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder='Type "/" to search waypoints, params...'
            className="w-full bg-transparent text-xs text-foreground placeholder:text-muted outline-none"
          />
        </div>

        {/* Right Action Cluster */}
        <div className="pointer-events-auto flex items-center gap-2">
          {/* Quick Arm / Disarm Action */}
          {onToggleArm && (
            <Button
              size="sm"
              variant={armed ? "danger" : "outline"}
              className={`h-9 font-semibold text-xs px-3 shadow-md rounded-xl ${
                armed
                  ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
                  : "bg-white dark:bg-[#1E2227] text-foreground border-border hover:bg-surface-secondary"
              }`}
              onPress={onToggleArm}
            >
              <Flame className="w-3.5 h-3.5 mr-1" />
              <span>{armed ? "DISARM" : "ARM"}</span>
            </Button>
          )}

          {/* ArduPilot Auto Setup Button */}
          {onOpenAutoSetup && (
            <Button
              size="sm"
              className="h-9 font-semibold text-xs px-3 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white shadow-md rounded-xl"
              onPress={onOpenAutoSetup}
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              <span>+ Auto Setup</span>
            </Button>
          )}

          {/* Export Button */}
          <Button
            size="sm"
            variant="ghost"
            className="h-9 font-semibold text-xs px-3 bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-md rounded-xl hover:bg-surface-secondary"
            onPress={() => alert("Exporting KML Survey Grid & MAVLink Telemetry...")}
          >
            <Download className="w-3.5 h-3.5 mr-1" />
            <span>Export</span>
          </Button>

          {/* Notification Bell */}
          <Button
            isIconOnly
            size="sm"
            variant="ghost"
            className="h-9 w-9 bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-md rounded-xl hover:bg-surface-secondary relative"
            aria-label="Alerts"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500" />
          </Button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────
          Floating Interactive Field / Drone Inspection Card
          (Faithfully reproduces the floating card from the screenshot)
         ─────────────────────────────────────────────────────────── */}
      {showInspectionCard && (
        <div className="absolute top-20 right-4 z-[1000] w-80 max-w-[calc(100vw-2rem)] animate-in fade-in slide-in-from-top-2 duration-300 pointer-events-auto">
          <Card className="bg-white dark:bg-[#1E2227] border border-border shadow-2xl rounded-2xl p-4 flex flex-col gap-3 backdrop-blur-md">
            {/* Header: Title + Star + Close */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <h3 className="font-bold text-sm text-foreground">
                  Area 1 : Rice Field
                </h3>
                <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              </div>
              <button
                onClick={() => setShowInspectionCard(false)}
                className="text-muted hover:text-foreground transition-colors p-1"
                aria-label="Close card"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Tag Code */}
            <span className="text-[11px] text-muted font-mono -mt-2">
              #23BC-12
            </span>

            {/* Dates / Mission Time */}
            <div className="grid grid-cols-2 text-xs py-1 border-y border-border/60">
              <div className="flex flex-col">
                <span className="text-muted text-[10px]">Planting date</span>
                <span className="font-semibold text-foreground">24 Aug 25</span>
              </div>
              <div className="flex flex-col">
                <span className="text-muted text-[10px]">Harvest date</span>
                <span className="font-semibold text-foreground">12 Nov 25</span>
              </div>
            </div>

            {/* Crop Health Bar */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted text-[11px]">Crop Health</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400 text-[11px]">Good</span>
              </div>
              <div className="w-full h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full w-[88%]" />
              </div>
            </div>

            {/* Accordion: Sensor Read */}
            <div className="border-t border-border/60 pt-2 flex flex-col">
              <button
                onClick={() => setIsSensorExpanded(!isSensorExpanded)}
                className="flex items-center justify-between text-xs font-semibold text-foreground py-1"
              >
                <span>Sensor Read</span>
                {isSensorExpanded ? (
                  <ChevronUp className="w-4 h-4 text-muted" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted" />
                )}
              </button>

              {isSensorExpanded && (
                <div className="grid grid-cols-2 gap-y-1.5 text-xs text-muted pt-1.5 pb-2 font-mono">
                  <span>Humidity</span>
                  <span className="text-right text-foreground font-semibold">15%</span>
                  <span>Temperature</span>
                  <span className="text-right text-foreground font-semibold">32°C</span>
                  <span>Soil Moisture</span>
                  <span className="text-right text-foreground font-semibold">42kPa</span>
                  <span>pH Level</span>
                  <span className="text-right text-foreground font-semibold">2.5</span>
                  <span>Drone Altitude</span>
                  <span className="text-right text-emerald-500 font-semibold">{alt.toFixed(1)}m</span>
                  <span>Groundspeed</span>
                  <span className="text-right text-foreground font-semibold">{speed.toFixed(1)}m/s</span>
                </div>
              )}
            </div>

            {/* Accordion: Sensor Log */}
            <div className="border-t border-border/60 pt-2 flex flex-col">
              <button
                onClick={() => setIsLogExpanded(!isLogExpanded)}
                className="flex items-center justify-between text-xs font-semibold text-foreground py-1"
              >
                <span>Sensor log</span>
                {isLogExpanded ? (
                  <ChevronUp className="w-4 h-4 text-muted" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted" />
                )}
              </button>

              {isLogExpanded && (
                <div className="text-[11px] text-muted font-mono pt-1 pb-1 flex flex-col gap-1">
                  <span>[09:14] EKF3 IMU0 optimal alignment</span>
                  <span>[09:20] Radio link: 1500us nominal</span>
                  <span>[09:24] Mission waypoint #4 reached</span>
                </div>
              )}
            </div>

            {/* Dark Embedded AI Insights Card */}
            <div className="p-3 bg-[#131518] text-white rounded-xl flex flex-col gap-1.5 shadow-inner border border-white/5">
              <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Insights</span>
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed">
                Keep soil moisture 40kPa and pH level under 2.6 to maximize the result.
                Autonomous flight corridor cleared with 0 geofence violations.
              </p>
            </div>
          </Card>
        </div>
      )}

      {/* Floating Toggle to re-open inspection card if closed */}
      {!showInspectionCard && (
        <div className="absolute top-20 right-4 z-[1000] pointer-events-auto">
          <Button
            size="sm"
            className="bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-lg rounded-xl text-xs font-semibold"
            onPress={() => setShowInspectionCard(true)}
          >
            <Layers className="w-3.5 h-3.5 mr-1 text-emerald-500" />
            <span>Show Sector Card</span>
          </Button>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────
          Floating Inset Mini-Map (bottom-left corner of the map)
         ─────────────────────────────────────────────────────────── */}
      <div className="absolute bottom-4 left-4 z-[1000] w-28 h-28 rounded-2xl overflow-hidden border-2 border-white/80 shadow-2xl pointer-events-auto bg-[#0F1113]">
        <div ref={miniMapContainerRef} className="w-full h-full" />
        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-[8px] font-mono text-white pointer-events-none">
          REGIONAL
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────
          Floating Map Controls Dock (bottom-right corner of the map)
         ─────────────────────────────────────────────────────────── */}
      <div className="absolute bottom-4 right-4 z-[1000] flex flex-col items-center gap-1.5 pointer-events-auto">
        {/* Fullscreen Button */}
        <GcsTooltip content={isFullscreen ? "Exit Fullscreen" : "Fullscreen Map"}>
          <button
            onClick={toggleFullscreen}
            className="w-9 h-9 rounded-xl bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-lg flex items-center justify-center hover:bg-surface-secondary transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </GcsTooltip>

        {/* Zoom In */}
        <GcsTooltip content="Zoom In">
          <button
            onClick={handleZoomIn}
            className="w-9 h-9 rounded-xl bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-lg flex items-center justify-center hover:bg-surface-secondary transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </GcsTooltip>

        {/* Zoom Out */}
        <GcsTooltip content="Zoom Out">
          <button
            onClick={handleZoomOut}
            className="w-9 h-9 rounded-xl bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-lg flex items-center justify-center hover:bg-surface-secondary transition-colors"
          >
            <Minus className="w-4 h-4" />
          </button>
        </GcsTooltip>

        {/* Recenter on Drone */}
        <GcsTooltip content="Center on Drone">
          <button
            onClick={handleCenterOnDrone}
            className="w-9 h-9 rounded-xl bg-white dark:bg-[#1E2227] text-foreground border border-border shadow-lg flex items-center justify-center hover:bg-surface-secondary transition-colors"
          >
            <Navigation className="w-4 h-4 text-emerald-500" />
          </button>
        </GcsTooltip>

        {/* 2D / 3D Tilt Toggle */}
        <GcsTooltip content={is3DMode ? "2D Flat View" : "3D Perspective View"}>
          <button
            onClick={() => setIs3DMode(!is3DMode)}
            className={`w-9 h-9 rounded-xl text-xs font-bold border border-border shadow-lg flex items-center justify-center transition-colors ${
              is3DMode
                ? "bg-emerald-500 text-white"
                : "bg-white dark:bg-[#1E2227] text-foreground hover:bg-surface-secondary"
            }`}
          >
            {is3DMode ? "3D" : "2D"}
          </button>
        </GcsTooltip>
      </div>
    </div>
  );
}
