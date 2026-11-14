import type { ReferenceField, ReferenceMetadata } from "./api";
import type { Hover } from "./RouteMap";
import { COLOUR_RAMP, unitSymbol } from "./reference";

interface Props {
  meta: ReferenceMetadata;
  field: ReferenceField | null;
  dates: string[];
  date: string;
  onDateChange: (date: string) => void;
  hover: Hover | null;
}

/** Says exactly what the coloured layer is: source, date, units, scale and what it is not. */
export function Legend({ meta, field, dates, date, onDateChange, hover }: Props) {
  const unit = unitSymbol(meta.units);
  const { min, max } = meta.value_range;
  return (
    <section className="legend" aria-label="Temperature layer legend">
      <h2>Reference sea surface temperature</h2>
      <p className="legend-kind">
        <strong>Reference data, not a reconstruction.</strong> Historical analysed field from {meta.dataset}.
      </p>

      <label>
        Date (UTC day){" "}
        <select value={date} onChange={(event) => onDateChange(event.target.value)}>
          {dates.map((day) => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
        </select>
      </label>

      <div className="legend-scale">
        <div className="legend-bar" style={{ background: `linear-gradient(to right, ${COLOUR_RAMP.join(", ")})` }} />
        <div className="legend-ticks">
          <span>
            {min.toFixed(1)} {unit}
          </span>
          <span>{((min + max) / 2).toFixed(1)}</span>
          <span>
            {max.toFixed(1)} {unit}
          </span>
        </div>
        <p className="legend-note">
          Scale is fixed over {meta.data_period.start_date} to {meta.data_period.end_date}, so colours are comparable
          between dates. Grey areas have no value (land).
        </p>
      </div>

      <dl className="legend-facts">
        <dt>Showing</dt>
        <dd>{field ? `${field.date}, ${meta.long_name ?? meta.variable} (${meta.units})` : "Loading…"}</dd>
        <dt>This day</dt>
        <dd>
          {field && field.min !== null && field.max !== null
            ? `${field.min.toFixed(2)} to ${field.max.toFixed(2)} ${unit}; ${field.missing_count} cells without a value`
            : "–"}
        </dd>
        <dt>Grid</dt>
        <dd>
          {meta.grid.cell_size_degrees}° cells, {meta.grid.lat_count} × {meta.grid.lon_count}
        </dd>
        <dt>Under cursor</dt>
        <dd aria-live="off">
          {hover
            ? `${hover.sst.toFixed(2)} ${unit} at ${hover.lon.toFixed(3)}°E, ${hover.lat.toFixed(3)}°N`
            : "Move over the map"}
        </dd>
        <dt>Source</dt>
        <dd>
          <a href={meta.product_page} target="_blank" rel="noreferrer">
            NOAA NCEI product page
          </a>
          , retrieved {meta.retrieved_at_utc.slice(0, 10)}
        </dd>
      </dl>

      <ul className="legend-key">
        <li>
          <span className="key-line key-region" /> Scenario region
        </li>
        <li>
          <span className="key-line key-available" /> Extent of downloaded data
        </li>
        <li>
          <span className="key-line key-route" /> Route, numbered in visiting order
        </li>
      </ul>
    </section>
  );
}
