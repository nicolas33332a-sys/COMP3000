import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, createScenario, getReferenceField, getReferenceMetadata, getScenario, listScenarios } from "./api";
import type { Problem, ReferenceField, ReferenceMetadata } from "./api";
import { exampleScenario } from "./exampleScenario";
import { datesInPeriod, draftFromInput, draftToInput, emptyDraft, toNumber } from "./form";
import type { ScenarioDraft } from "./form";
import { Legend } from "./Legend";
import { RouteMap } from "./RouteMap";
import type { Hover } from "./RouteMap";
import type { Scenario } from "./scenario";
import { ScenarioForm } from "./ScenarioForm";
import { ScenarioDetails } from "./ScenarioDetails";

const describe = (error: unknown) => (error instanceof Error ? error.message : "Something unexpected went wrong.");

export function App() {
  // Reference data (what the coloured layer shows).
  const [meta, setMeta] = useState<ReferenceMetadata | null>(null);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [field, setField] = useState<ReferenceField | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);

  // Saved scenarios, always as loaded from the server.
  const [scenarios, setScenarios] = useState<Scenario[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // The new-scenario form.
  const [draft, setDraft] = useState<ScenarioDraft>(() => emptyDraft());
  const [problems, setProblems] = useState<Problem[]>([]);
  const [failure, setFailure] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reloadList = useCallback(async () => {
    try {
      setScenarios(await listScenarios());
      setListError(null);
    } catch (error) {
      setListError(describe(error));
    }
  }, []);

  const loadReference = useCallback(async () => {
    try {
      const loaded = await getReferenceMetadata();
      setMeta(loaded);
      setReferenceError(null);
      setDate((current) => current || (loaded.dates[0] ?? ""));
      // Start an untouched form from the area and dates that actually have data.
      setDraft((current) => (current.west === "" && current.name === "" ? emptyDraft(loaded) : current));
    } catch (error) {
      setReferenceError(describe(error));
    }
  }, []);

  useEffect(() => {
    void reloadList();
    void loadReference();
  }, [reloadList, loadReference]);

  // The dates offered: all available ones, or only the scenario's period when one is open.
  const dates = useMemo(() => datesInPeriod(meta?.dates ?? [], selected), [meta, selected]);
  useEffect(() => {
    if (dates.length > 0 && !dates.includes(date)) setDate(dates[0]);
  }, [dates, date]);

  const [fieldAttempt, setFieldAttempt] = useState(0);
  useEffect(() => {
    if (!date) return;
    let cancelled = false;
    getReferenceField(date)
      .then((loaded) => {
        if (!cancelled) {
          setField(loaded);
          setReferenceError(null);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setField(null);
          setReferenceError(describe(error));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [date, fieldAttempt]);

  const retryReference = () => {
    void loadReference();
    setFieldAttempt((attempt) => attempt + 1);
  };

  const save = async () => {
    setSaving(true);
    setProblems([]);
    setFailure(null);
    setNotice(null);
    try {
      const created = await createScenario(draftToInput(draft));
      // Show the copy read back from the server, not the form's own values.
      const reloaded = await getScenario(created.id);
      await reloadList();
      setSelected(reloaded);
      setNotice("Saved. This is the copy loaded back from the server.");
      if (meta) setDraft(emptyDraft(meta));
    } catch (error) {
      if (error instanceof ApiError && error.problems.length > 0) setProblems(error.problems);
      else setFailure(describe(error));
    } finally {
      setSaving(false);
    }
  };

  const open = async (id: string) => {
    setNotice(null);
    try {
      setSelected(await getScenario(id));
      setListError(null);
    } catch (error) {
      setListError(describe(error));
    }
  };

  // What the map draws: the open saved scenario, or the form as it is being typed.
  const shown = selected
    ? { region: selected.region, waypoints: selected.waypoints }
    : {
        region: { west: toNumber(draft.west), south: toNumber(draft.south), east: toNumber(draft.east), north: toNumber(draft.north) },
        waypoints: draft.waypoints.map((point) => ({ lon: toNumber(point.lon), lat: toNumber(point.lat) })),
      };

  const addWaypointFromMap = (lon: number, lat: number) =>
    setDraft((current) => ({
      ...current,
      waypoints: [...current.waypoints, { lon: lon.toFixed(3), lat: lat.toFixed(3) }],
    }));

  return (
    <div className="layout">
      <aside className="panel">
        <h1>MarineScope</h1>

        <section aria-label="Saved scenarios">
          <h2>Saved scenarios</h2>
          {listError && (
            <div className="alert" role="alert">
              {listError}{" "}
              <button type="button" onClick={() => void reloadList()}>
                Try again
              </button>
            </div>
          )}
          {scenarios === null && !listError && <p>Loading…</p>}
          {scenarios?.length === 0 && <p>None yet. Create one below.</p>}
          {scenarios && scenarios.length > 0 && (
            <ul className="scenario-list">
              {scenarios.map((scenario) => (
                <li key={scenario.id}>
                  <button
                    type="button"
                    className={selected?.id === scenario.id ? "current" : undefined}
                    aria-current={selected?.id === scenario.id}
                    onClick={() => void open(scenario.id)}
                  >
                    <strong>{scenario.name}</strong>
                    <small>
                      {scenario.waypoints.length} waypoints · saved {scenario.created_at.slice(0, 16).replace("T", " ")} UTC
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {selected ? (
          <section aria-label="Saved scenario">
            {notice && (
              <p className="notice" role="status">
                {notice}
              </p>
            )}
            <ScenarioDetails scenario={selected} />
            <button
              type="button"
              className="primary"
              onClick={() => {
                setSelected(null);
                setNotice(null);
              }}
            >
              New scenario
            </button>
          </section>
        ) : (
          <section>
            <h2>New scenario</h2>
            <ScenarioForm
              draft={draft}
              onChange={setDraft}
              onSubmit={() => void save()}
              onUseExample={() => setDraft(draftFromInput(exampleScenario))}
              saving={saving}
              problems={problems}
              failure={failure}
            />
          </section>
        )}
      </aside>

      <main className="map-column">
        {referenceError && (
          <div className="alert" role="alert">
            <strong>Temperature layer unavailable.</strong> {referenceError}{" "}
            <button type="button" onClick={retryReference}>
              Try again
            </button>
          </div>
        )}
        <RouteMap
          available={meta?.region ?? null}
          region={shown.region}
          waypoints={shown.waypoints}
          field={field}
          cellSizeDegrees={meta?.grid.cell_size_degrees ?? 0.25}
          valueRange={meta?.value_range ?? null}
          onPick={selected ? undefined : addWaypointFromMap}
          onHover={setHover}
        />
        {meta && <Legend meta={meta} field={field} dates={dates} date={date} onDateChange={setDate} hover={hover} />}
      </main>
    </div>
  );
}
