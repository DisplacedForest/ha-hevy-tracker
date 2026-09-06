import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import { JSDOM } from "jsdom";

const source = await readFile(new URL("../../custom_components/hevy/frontend/hevy-workout-card.js", import.meta.url), "utf8");
const clone = (value) => JSON.parse(JSON.stringify(value));
const tick = () => new Promise((resolve) => setImmediate(resolve));
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const session = () => ({
  id: "session-1", revision: 1, status: "active", title: "Upper body", start_time: "2026-09-06T14:30:00Z", weight_unit: "kg", distance_unit: "km", is_private: true,
  exercises: [{ exercise_template_id: "bench", name: "Bench Press", sets: [{ type: "normal", weight: 60, reps: 8, completed: false }] }],
});
const board = (savedSession = session()) => ({
  accounts: [{ config_entry_id: "one", title: "Zach" }], config_entry_id: "one", weight_unit: "kg", distance_unit: "km", session: savedSession,
  next_routine_id: "upper",
  routines: [{ id: "upper", title: "Upper body", exercises: session().exercises }],
  exercises: [{ id: "bench", title: "Bench Press", type: "weight_reps", muscle_group: "chest" }, { id: "run", title: "Running", type: "distance_duration", muscle_group: "cardio" }],
});

async function setup(t, initial = board(), override) {
  const dom = new JSDOM("<!doctype html><body></body>", { runScripts: "dangerously", url: "https://ha.example/" });
  dom.window.eval(source);
  let state = clone(initial);
  const calls = [];
  const backend = async (request) => {
    calls.push(clone(request));
    if (override) {
      const result = await override(request, state);
      if (result !== undefined) return result;
    }
    const { service, service_data: data } = request;
    if (service === "get_workout_board") return { response: clone(state) };
    if (service === "update_workout") {
      if (data.revision !== state.session.revision) throw new Error("Session changed. Refresh before trying again.");
      state.session = { ...state.session, ...clone(data), revision: data.revision + 1 };
    } else if (service === "start_workout") state.session = session();
    else if (service === "finish_workout") state.session = { ...state.session, status: "finished", revision: state.session.revision + 1, workout_id: "hevy-123" };
    else if (service === "cancel_workout") state.session = null;
    else if (service === "resolve_workout") state.session = data.resolution === "retry" ? { ...state.session, status: "active", revision: state.session.revision + 1 } : null;
    return { response: clone({ session: state.session }) };
  };
  const card = dom.window.document.createElement("hevy-workout-card");
  card.setConfig({ type: "custom:hevy-workout-card", config_entry_id: "one" });
  card.hass = { callWS: backend, connected: true };
  dom.window.document.body.append(card);
  t.after(() => { card.remove(); dom.window.close(); });
  await tick();
  const input = (selector, value, eventName = "input") => {
    const element = card.shadowRoot.querySelector(selector);
    assert.ok(element, selector);
    if (element.type === "checkbox") element.checked = value;
    else element.value = String(value);
    element.dispatchEvent(new dom.window.Event(eventName, { bubbles: true }));
    return element;
  };
  const click = (action) => {
    const element = card.shadowRoot.querySelector(`[data-action="${action}"]`);
    assert.ok(element, action);
    element.click();
  };
  return { dom, card, calls, input, click, get state() { return state; }, set state(value) { state = value; } };
}

test("registers the native card and editor and escapes remote content", async (t) => {
  const initial = board();
  initial.session.title = '<img src=x onerror="alert(1)">';
  initial.session.exercises[0].name = "<script>bad()</script>";
  const { card, dom } = await setup(t, initial);
  assert.equal(dom.window.customCards[0].type, "hevy-workout-card");
  assert.equal(card.constructor.getConfigElement().tagName, "HEVY-WORKOUT-CARD-EDITOR");
  assert.equal(card.shadowRoot.querySelectorAll("script,img").length, 0);
  assert.equal(card.shadowRoot.querySelector("[data-field=title]").value, initial.session.title);
});

test("serializes changed drafts without replacing focused inputs or losing newer edits", async (t) => {
  const held = deferred();
  let updates = 0;
  const ctx = await setup(t, board(), async (request) => {
    if (request.service === "update_workout" && ++updates === 1) await held.promise;
  });
  const field = ctx.input("[data-field=weight]", 70);
  field.focus();
  const saving = ctx.card._save();
  await tick();
  ctx.input("[data-field=weight]", 75);
  held.resolve();
  await saving;
  const writes = ctx.calls.filter((call) => call.service === "update_workout");
  assert.equal(writes.length, 2);
  assert.equal(writes[0].service_data.exercises[0].sets[0].weight, 70);
  assert.equal(writes[1].service_data.exercises[0].sets[0].weight, 75);
  assert.equal(writes[1].service_data.revision, 2);
  assert.equal(ctx.card.shadowRoot.activeElement, field);
  assert.equal(ctx.card.shadowRoot.querySelector("[data-field=weight]"), field);
  assert.equal(ctx.card._dirty, false);
});

test("loads a saved session after a new card attaches", async (t) => {
  const first = await setup(t);
  first.input("[data-field=reps]", 12);
  first.input("[data-field=completed]", true, "change");
  await first.card._save();
  const second = await setup(t, first.state);
  assert.equal(second.card.shadowRoot.querySelector("[data-field=reps]").value, "12");
  assert.equal(second.card.shadowRoot.querySelector("[data-field=completed]").checked, true);
});

test("requires finish confirmation, flushes edits, and sends only one finish request", async (t) => {
  const ctx = await setup(t);
  ctx.input("[data-field=weight]", 80);
  ctx.input("[data-field=completed]", true, "change");
  ctx.click("finish");
  assert.equal(ctx.calls.some((call) => call.service === "finish_workout"), false);
  assert.match(ctx.card.shadowRoot.textContent, /1 completed sets will be sent/);
  ctx.click("finish-confirm");
  ctx.click("finish-confirm");
  await tick();
  await tick();
  const writes = ctx.calls.filter((call) => call.service !== "get_workout_board");
  assert.deepEqual(writes.map((call) => call.service), ["update_workout", "finish_workout"]);
  assert.equal(writes[1].service_data.revision, 2);
  assert.equal(ctx.card._draft.status, "finished");
  assert.match(ctx.card.shadowRoot.textContent, /hevy-123/);
});

test("keeps edits after save conflict and requires confirmation before discarding them", async (t) => {
  const ctx = await setup(t);
  ctx.input("[data-field=weight]", 75);
  ctx.state.session.revision = 2;
  ctx.state.session.exercises[0].sets[0].weight = 90;
  await ctx.card._save();
  assert.equal(ctx.card._draft.exercises[0].sets[0].weight, 75);
  assert.equal(ctx.card._conflict, true);
  assert.equal(ctx.card.shadowRoot.querySelector("[data-action=retry-save]"), null);
  ctx.click("load-saved");
  assert.equal(ctx.card._draft.exercises[0].sets[0].weight, 75);
  ctx.click("reload-confirm");
  await tick();
  assert.equal(ctx.card._draft.exercises[0].sets[0].weight, 90);
  assert.equal(ctx.card._dirty, false);
});

test("does not retry a finish after an uncertain network outcome", async (t) => {
  const initial = board();
  initial.session.exercises[0].sets[0].completed = true;
  const ctx = await setup(t, initial, async (request, state) => {
    if (request.service === "finish_workout") {
      state.session.status = "uncertain";
      state.session.revision += 1;
      throw new Error("Connection interrupted");
    }
  });
  ctx.click("finish");
  ctx.click("finish-confirm");
  await tick();
  await tick();
  assert.equal(ctx.card._draft.status, "uncertain");
  await ctx.card._load();
  assert.equal(ctx.calls.filter((call) => call.service === "finish_workout").length, 1);
  ctx.click("retry");
  assert.match(ctx.card.shadowRoot.textContent, /I checked Hevy. The workout is missing/);
  assert.equal(ctx.calls.some((call) => call.service === "resolve_workout"), false);
  ctx.click("retry-confirm");
  await tick();
  assert.equal(ctx.card._draft.status, "active");
  assert.equal(ctx.calls.filter((call) => call.service === "finish_workout").length, 1);
});

test("ignores a previous account's delayed board response", async (t) => {
  const stale = deferred();
  let count = 0;
  const ctx = await setup(t, board(), async (request) => {
    if (request.service === "get_workout_board" && ++count === 2) return stale.promise;
  });
  const old = ctx.card._load();
  const next = board();
  next.config_entry_id = "two";
  next.session.title = "Second account";
  ctx.state = next;
  await ctx.card._switchAccount("two");
  stale.resolve({ response: board() });
  await old;
  assert.equal(ctx.card._entry, "two");
  assert.equal(ctx.card._draft.title, "Second account");
});

test("does not regress a session when a pre-save poll completes after saving", async (t) => {
  const stale = deferred();
  let count = 0;
  const ctx = await setup(t, board(), async (request) => {
    if (request.service === "get_workout_board" && ++count === 2) return stale.promise;
  });
  const old = ctx.card._load();
  ctx.input("[data-field=weight]", 99);
  await ctx.card._save();
  stale.resolve({ response: board() });
  await old;
  assert.equal(ctx.card._draft.revision, 2);
  assert.equal(ctx.card._draft.exercises[0].sets[0].weight, 99);
});

test("starts the suggested routine and supports timed and distance exercises", async (t) => {
  const ctx = await setup(t, board(null));
  ctx.click("start");
  await tick();
  assert.equal(ctx.calls.find((call) => call.service === "start_workout").service_data.routine_id, "upper");
  ctx.input("[data-action=search]", "cardio");
  assert.equal(ctx.card.shadowRoot.querySelectorAll("[data-action=exercise] option").length, 2);
  ctx.input("[data-action=exercise]", "run", "change");
  ctx.click("add-exercise");
  ctx.input("[data-field=duration_seconds]", 600);
  ctx.input("[data-field=distance]", 1.5);
  await ctx.card._save();
  assert.equal(ctx.state.session.exercises[1].sets[0].duration_seconds, 600);
  assert.equal(ctx.state.session.exercises[1].sets[0].distance, 1.5);
});

test("invalid measurements cannot be saved or submitted with stale values", async (t) => {
  const ctx = await setup(t);
  ctx.input("[data-field=completed]", true, "change");
  ctx.input("[data-field=reps]", 8.5);
  await ctx.card._save();
  assert.equal(ctx.calls.some((call) => call.service === "update_workout"), false);
  assert.equal(ctx.card.shadowRoot.querySelector("[data-action=finish]").disabled, true);
  assert.equal(ctx.card.shadowRoot.querySelector("[data-field=reps]").getAttribute("aria-invalid"), "true");
  ctx.input("[data-field=reps]", 9);
  await ctx.card._save();
  assert.equal(ctx.state.session.exercises[0].sets[0].reps, 9);
});

test("disconnect stops polling and reconnect refreshes the saved session", async (t) => {
  const ctx = await setup(t);
  ctx.card.remove();
  const before = ctx.calls.length;
  ctx.state.session.revision = 4;
  ctx.state.session.title = "Updated elsewhere";
  ctx.dom.window.document.body.append(ctx.card);
  await tick();
  assert.equal(ctx.calls.length, before + 1);
  assert.equal(ctx.card._draft.title, "Updated elsewhere");
});

test("visual editor emits account and favorites configuration", async (t) => {
  const { dom } = await setup(t);
  const editor = dom.window.document.createElement("hevy-workout-card-editor");
  editor.setConfig({ type: "custom:hevy-workout-card" });
  let detail;
  editor.addEventListener("config-changed", (event) => { detail = event.detail; });
  const field = editor.shadowRoot.querySelector("[data-config=exercise_ids]");
  field.value = "bench, run, ";
  field.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
  assert.deepEqual(Array.from(detail.config.exercise_ids), ["bench", "run"]);
  assert.equal(detail.config.type, "custom:hevy-workout-card");
});

test("requires an explicit account when several accounts are available", async (t) => {
  const initial = board(null);
  initial.accounts.push({ config_entry_id: "two", title: "Second account" });
  delete initial.config_entry_id;
  const ctx = await setup(t, initial);
  ctx.card.setConfig({ type: "custom:hevy-workout-card" });
  await tick();
  assert.equal(ctx.card.shadowRoot.querySelector("[data-action=start]"), null);
  assert.match(ctx.card.shadowRoot.textContent, /Choose a Hevy account/);
});

test("does not automatically retry a failed save and preserves the local draft", async (t) => {
  const ctx = await setup(t, board(), async (request) => {
    if (request.service === "update_workout") throw new Error("Offline");
  });
  ctx.input("[data-field=weight]", 100);
  await ctx.card._save();
  ctx.input("[data-field=reps]", 10);
  await ctx.card._save();
  assert.equal(ctx.card._draft.exercises[0].sets[0].weight, 100);
  assert.equal(ctx.card._draft.exercises[0].sets[0].reps, 10);
  assert.equal(ctx.calls.filter((call) => call.service === "update_workout").length, 1);
  assert.equal(ctx.card._dirty, true);
});

test("reads durable completion when a finish response is lost", async (t) => {
  const initial = board();
  initial.session.exercises[0].sets[0].completed = true;
  const ctx = await setup(t, initial, async (request, state) => {
    if (request.service === "finish_workout") {
      state.session.status = "finished";
      state.session.workout_id = "saved-despite-timeout";
      state.session.revision += 1;
      throw new Error("Response lost");
    }
  });
  ctx.click("finish");
  ctx.click("finish-confirm");
  await tick();
  assert.equal(ctx.card._draft.status, "finished");
  assert.match(ctx.card.shadowRoot.textContent, /saved-despite-timeout/);
  assert.equal(ctx.calls.filter((call) => call.service === "finish_workout").length, 1);
});

test("empty sets cannot be marked completed", async (t) => {
  const ctx = await setup(t);
  ctx.input("[data-action=exercise]", "run", "change");
  ctx.click("add-exercise");
  const checkbox = ctx.input('[data-field=completed][data-exercise="1"]', true, "change");
  assert.equal(checkbox.checked, false);
  assert.equal(ctx.card._draft.exercises[1].sets[0].completed, false);
  assert.match(ctx.card.shadowRoot.textContent, /Enter a measurement/);
});

test("refreshes after Home Assistant connection reconnects", async (t) => {
  const ctx = await setup(t);
  const before = ctx.calls.length;
  const connection = { connected: false };
  ctx.card.hass = { ...ctx.card._hass, connection };
  ctx.state.session.title = "Connection recovered";
  ctx.state.session.revision += 1;
  connection.connected = true;
  ctx.card.hass = { ...ctx.card._hass, connection };
  await tick();
  assert.equal(ctx.calls.length, before + 1);
  assert.equal(ctx.card._draft.title, "Connection recovered");
});
