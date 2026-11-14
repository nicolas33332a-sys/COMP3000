import type { Scenario } from "./scenario";

/** Read-only view of a scenario exactly as the server returned it. */
export function ScenarioDetails({ scenario }: { scenario: Scenario }) {
  const { region, data_period, vessel, sampling } = scenario;
  return (
    <>
      <h2>{scenario.name}</h2>
      <dl className="details">
        <dt>Region</dt>
        <dd>
          west {region.west}, south {region.south}, east {region.east}, north {region.north}
        </dd>
        <dt>Data period</dt>
        <dd>
          {data_period.start_date} to {data_period.end_date} (UTC days)
        </dd>
        <dt>Vessel</dt>
        <dd>
          {vessel.name}, {vessel.speed_knots} knots
        </dd>
        <dt>Departure</dt>
        <dd>{vessel.departure_time.slice(0, 16).replace("T", " ")} UTC</dd>
        <dt>Sampling</dt>
        <dd>
          every {sampling.interval_minutes} min, noise {sampling.noise_std_c ?? 0} °C, seed {sampling.random_seed ?? 0}
        </dd>
        <dt>Saved</dt>
        <dd>{scenario.created_at.slice(0, 19).replace("T", " ")} UTC</dd>
        <dt>ID</dt>
        <dd>
          <code>{scenario.id}</code>
        </dd>
      </dl>
      <table className="waypoints">
        <caption>Waypoints in visiting order</caption>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Longitude (°E)</th>
            <th scope="col">Latitude (°N)</th>
          </tr>
        </thead>
        <tbody>
          {scenario.waypoints.map((point, index) => (
            <tr key={index}>
              <th scope="row">{index + 1}</th>
              <td>{point.lon}</td>
              <td>{point.lat}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
