// Turning the reference temperature grid into map shapes and colours.
//
// The API sends cell centres. Each cell is drawn as a square reaching half a
// cell either side of its centre, so the picture shows the real 0.25-degree
// resolution instead of a smoothed image that would suggest more detail.

import type { FeatureCollection, Polygon } from "geojson";
import type { ReferenceField } from "./api";
import { toLonLat } from "./scenario";

export interface CellProperties {
  sst: number;
  lon: number;
  lat: number;
}

export type CellCollection = FeatureCollection<Polygon, CellProperties>;

/** One square per cell that has a value. Cells with no value (land) are left out. */
export function fieldToCells(field: ReferenceField, cellSizeDegrees: number): CellCollection {
  const half = cellSizeDegrees / 2;
  const features: CellCollection["features"] = [];
  field.lat.forEach((lat, i) => {
    field.lon.forEach((lon, j) => {
      const sst = field.values[i][j]; // values[i][j] is at lat[i], lon[j]
      if (sst === null) return;
      const corner = (dLon: number, dLat: number) => toLonLat({ lon: lon + dLon, lat: lat + dLat });
      features.push({
        type: "Feature",
        properties: { sst, lon, lat },
        geometry: {
          type: "Polygon",
          coordinates: [[corner(-half, -half), corner(half, -half), corner(half, half), corner(-half, half), corner(-half, -half)]],
        },
      });
    });
  });
  return { type: "FeatureCollection", features };
}

/** Viridis: perceptually even and readable with common colour-vision deficiencies. */
export const COLOUR_RAMP = ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];

/** Evenly spaced [value, colour] stops from min to max, for the map and the legend alike. */
export function colourStops(min: number, max: number): [number, string][] {
  const span = max > min ? max - min : 1; // a flat field still needs increasing stops
  return COLOUR_RAMP.map((colour, index) => [min + (span * index) / (COLOUR_RAMP.length - 1), colour]);
}

/** "Celsius" (the source's wording) -> "°C" for labels; anything else is shown unchanged. */
export function unitSymbol(units: string | null): string {
  if (units === null) return "";
  return units.toLowerCase() === "celsius" ? "°C" : units;
}
