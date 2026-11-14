import { Map as MapLibreMap, Marker, NavigationControl, setWorkerUrl } from "maplibre-gl";
import type { Feature, FeatureCollection, GeoJSON, Polygon } from "geojson";
import type { GeoJSONSource, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import type { ReferenceField } from "./api";
import { colourStops, fieldToCells } from "./reference";
import type { RegionBounds, Waypoint } from "./scenario";
import { toLonLat } from "./scenario";

// MapLibre draws in a web worker; with a bundler it has to be told where that file is.
// "?worker&url" makes Vite build it as a worker. A plain "?url" import does not work in
// development: Vite then injects its page-only client code into the worker, which stops
// it silently and leaves the map blank.
setWorkerUrl(workerUrl);

// Everything MarineScope needs (grid, region, route) is drawn from our own data.
// The coastline comes from MapLibre's free demo tiles and is only for orientation:
// if it cannot be downloaded the map still works, just without the outline.
const STYLE: StyleSpecification = {
  version: 8,
  sources: {
    basemap: { type: "vector", url: "https://demotiles.maplibre.org/tiles/tiles.json" },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#eef1f4" } },
    { id: "land", type: "fill", source: "basemap", "source-layer": "countries", paint: { "fill-color": "#d9d5c9" } },
  ],
};

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

function boxFeature(box: RegionBounds): Feature<Polygon> {
  const { west, south, east, north } = box;
  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]], // [lon, lat]
    },
  };
}

function isValidBox(box: RegionBounds | null): box is RegionBounds {
  return (
    box !== null &&
    [box.west, box.south, box.east, box.north].every(Number.isFinite) &&
    box.west < box.east &&
    box.south < box.north &&
    box.south >= -90 &&
    box.north <= 90
  );
}

function isOnEarth(point: Waypoint): boolean {
  return Number.isFinite(point.lon) && Number.isFinite(point.lat) && Math.abs(point.lon) <= 180 && Math.abs(point.lat) <= 90;
}

export interface Hover {
  lon: number;
  lat: number;
  sst: number;
}

interface Props {
  /** The area that reference data exists for (dashed outline). */
  available: RegionBounds | null;
  /** The scenario's own region (solid outline). */
  region: RegionBounds | null;
  /** Route in visiting order. Points that are not valid coordinates are skipped. */
  waypoints: Waypoint[];
  field: ReferenceField | null;
  cellSizeDegrees: number;
  valueRange: { min: number; max: number } | null;
  /** When set, clicking the map reports the clicked position (used to add waypoints). */
  onPick?: (lon: number, lat: number) => void;
  onHover?: (hover: Hover | null) => void;
}

export function RouteMap({ available, region, waypoints, field, cellSizeDegrees, valueRange, onPick, onHover }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const [ready, setReady] = useState(false);

  // Latest callbacks, so the map's event handlers (registered once) never go stale.
  const onPickRef = useRef(onPick);
  const onHoverRef = useRef(onHover);
  onPickRef.current = onPick;
  onHoverRef.current = onHover;

  useEffect(() => {
    const map = new MapLibreMap({
      container: container.current!,
      style: STYLE,
      center: [-10, 48],
      zoom: 4,
      dragRotate: false,
      attributionControl: { compact: false, customAttribution: "Temperature: NOAA OISST v2.1 · Coastline: MapLibre demo tiles" },
    });
    map.addControl(new NavigationControl({ showCompass: false }));
    mapRef.current = map;
    // Development only: lets the map be inspected from the browser console.
    if (import.meta.env.DEV) (window as unknown as { marinescopeMap?: MapLibreMap }).marinescopeMap = map;

    map.on("load", () => {
      for (const id of ["cells", "available", "region", "route"]) {
        map.addSource(id, { type: "geojson", data: EMPTY });
      }
      // Bottom to top: temperature cells, coastline, boxes, route.
      map.addLayer({ id: "cells", type: "fill", source: "cells", paint: { "fill-color": "#888", "fill-opacity": 0.9 } });
      map.addLayer({
        id: "coastline", type: "line", source: "basemap", "source-layer": "countries",
        paint: { "line-color": "#333", "line-width": 1 },
      });
      map.addLayer({
        id: "available", type: "line", source: "available",
        paint: { "line-color": "#333", "line-width": 1.5, "line-dasharray": [3, 3] },
      });
      map.addLayer({ id: "region", type: "line", source: "region", paint: { "line-color": "#c2185b", "line-width": 2 } });
      map.addLayer({ id: "route-casing", type: "line", source: "route", paint: { "line-color": "#000", "line-width": 5 } });
      map.addLayer({ id: "route", type: "line", source: "route", paint: { "line-color": "#fff", "line-width": 2.5 } });

      map.on("click", (event) => onPickRef.current?.(event.lngLat.lng, event.lngLat.lat));
      map.on("mousemove", "cells", (event) => {
        const properties = event.features?.[0]?.properties;
        if (properties) onHoverRef.current?.({ lon: properties.lon, lat: properties.lat, sst: properties.sst });
      });
      map.on("mouseleave", "cells", () => onHoverRef.current?.(null));
      setReady(true);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const setData = (id: string, data: GeoJSON) => (mapRef.current?.getSource(id) as GeoJSONSource | undefined)?.setData(data);

  // Temperature cells and their colour scale.
  useEffect(() => {
    if (!ready) return;
    setData("cells", field ? fieldToCells(field, cellSizeDegrees) : EMPTY);
    if (valueRange) {
      mapRef.current!.setPaintProperty("cells", "fill-color", [
        "interpolate", ["linear"], ["get", "sst"],
        ...colourStops(valueRange.min, valueRange.max).flat(),
      ]);
    }
  }, [ready, field, cellSizeDegrees, valueRange]);

  // Outlines. Fit the view to the scenario region, or to the available data when there is none.
  const regionKey = isValidBox(region) ? JSON.stringify(region) : "";
  const availableKey = isValidBox(available) ? JSON.stringify(available) : "";
  useEffect(() => {
    if (!ready) return;
    setData("available", isValidBox(available) ? boxFeature(available) : EMPTY);
    setData("region", isValidBox(region) ? boxFeature(region) : EMPTY);
    const view = isValidBox(region) ? region : isValidBox(available) ? available : null;
    if (view) {
      mapRef.current!.fitBounds([[view.west, view.south], [view.east, view.north]], { padding: 30, duration: 0 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, regionKey, availableKey]);

  // Route line and numbered waypoint markers, in visiting order.
  const routeKey = JSON.stringify(waypoints);
  useEffect(() => {
    if (!ready) return;
    const valid = waypoints.map((point, index) => ({ point, number: index + 1 })).filter(({ point }) => isOnEarth(point));
    setData(
      "route",
      valid.length >= 2
        ? { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: valid.map(({ point }) => toLonLat(point)) } }
        : EMPTY,
    );
    markers.current.forEach((marker) => marker.remove());
    markers.current = valid.map(({ point, number }) => {
      const element = document.createElement("div");
      element.className = "waypoint-marker";
      element.textContent = String(number);
      element.title = `Waypoint ${number}: longitude ${point.lon}, latitude ${point.lat}`;
      return new Marker({ element }).setLngLat(toLonLat(point)).addTo(mapRef.current!);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, routeKey]);

  return (
    <div
      ref={container}
      className={onPick ? "map map-picking" : "map"}
      role="application"
      aria-label="Map of the survey region, route and reference sea surface temperature"
    />
  );
}
