const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const copy = (value) => JSON.parse(JSON.stringify(value));
const setTypes = ["normal", "warmup", "failure", "dropset"];
const styles = `
  :host { display: block; color: var(--primary-text-color, #202830); font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
  * { box-sizing: border-box; }
  ha-card { display: block; overflow: hidden; background: var(--ha-card-background, var(--card-background-color, #fff)); border-radius: var(--ha-card-border-radius, 16px); border: 1px solid var(--divider-color, #dde3e7); }
  header, main, footer { padding: 24px; }
  header { display: flex; align-items: start; justify-content: space-between; gap: 16px; padding-bottom: 16px; }
  h1, h2, h3, p { margin: 0; }
  h1 { font-size: 24px; font-weight: 650; letter-spacing: -.5px; }
  h2 { font-size: 20px; margin-bottom: 12px; }
  h3 { font-size: 17px; }
  .eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 1.7px; text-transform: uppercase; color: var(--secondary-text-color, #64717b); margin-bottom: 8px; }
  .muted, .hint { color: var(--secondary-text-color, #64717b); font-size: 13px; line-height: 1.5; }
  .hint { margin-top: 8px; }
  .badge { display: inline-flex; border: 1px solid var(--divider-color, #dde3e7); border-radius: 20px; padding: 7px 10px; font-size: 12px; white-space: nowrap; }
  main { padding-top: 4px; }
  label { display: grid; gap: 7px; font-size: 13px; color: var(--secondary-text-color, #64717b); }
  input, select, button, textarea { font: inherit; }
  input:not([type=checkbox]), select, textarea { width: 100%; min-height: 46px; padding: 10px 12px; color: var(--primary-text-color, #202830); background: var(--secondary-background-color, #f3f6f8); border: 1px solid var(--divider-color, #dde3e7); border-radius: 9px; font-size: 16px; }
  textarea { min-height: 64px; resize: vertical; }
  button { min-height: 46px; border-radius: 10px; padding: 10px 16px; border: 1px solid var(--divider-color, #dde3e7); background: transparent; color: var(--primary-text-color, #202830); cursor: pointer; font-size: 14px; font-weight: 600; }
  button.primary { color: var(--text-primary-color, white); background: var(--primary-color, #167b74); border-color: var(--primary-color, #167b74); }
  button.danger { color: var(--error-color, #b63030); }
  button:disabled, input:disabled, select:disabled, textarea:disabled { opacity: .55; cursor: default; }
  button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible { outline: 3px solid var(--primary-color, #167b74); outline-offset: 2px; }
  .stack { display: grid; gap: 16px; }
  .row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
  .row > label { flex: 1; min-width: 160px; }
  .row.spread { justify-content: space-between; }
  .check { display: flex; flex-direction: row; align-items: center; gap: 10px; min-height: 46px; }
  input[type=checkbox] { width: 24px; height: 24px; accent-color: var(--primary-color, #167b74); cursor: pointer; }
  .intro { padding: 16px 0 22px; }
  .intro p { margin-top: 8px; max-width: 48ch; line-height: 1.6; }
  .exercise { border-top: 1px solid var(--divider-color, #dde3e7); padding-top: 20px; margin-top: 20px; }
  .exercise-head { margin-bottom: 14px; }
  .exercise-head button, .remove-set { font-size: 12px; min-height: 44px; padding: 8px 10px; }
  .sets { display: grid; gap: 8px; }
  .set { display: grid; grid-template-columns: 44px repeat(3, minmax(0, 1fr)) 44px; gap: 8px; align-items: end; border-radius: 10px; padding: 8px; background: var(--secondary-background-color, #f3f6f8); }
  .set.done { box-shadow: inset 3px 0 0 var(--primary-color, #167b74); }
  .set label { font-size: 11px; gap: 5px; }
  .set input:not([type=checkbox]), .set select { min-width: 0; padding: 8px; background: var(--ha-card-background, var(--card-background-color, #fff)); }
  .set .completion { align-self: stretch; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px; padding: 4px; }
  .set .set-type { grid-column: 2 / 4; }
  .set .optional { grid-column: 4 / 5; }
  .set .remove-set { grid-column: 5; grid-row: 1 / 3; align-self: center; padding: 8px; }
  .set .completion { grid-row: 1 / 3; }
  .exercise-actions { margin-top: 10px; }
  details { margin-top: 12px; }
  summary { cursor: pointer; min-height: 44px; display: flex; align-items: center; font-size: 13px; color: var(--secondary-text-color, #64717b); }
  .picker { margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--divider-color, #dde3e7); }
  footer { border-top: 1px solid var(--divider-color, #dde3e7); display: grid; gap: 12px; background: var(--ha-card-background, var(--card-background-color, #fff)); }
  .progress { height: 4px; background: var(--divider-color, #dde3e7); border-radius: 2px; overflow: hidden; }
  .progress > span { display: block; height: 100%; background: var(--primary-color, #167b74); transition: width .15s; }
  .notice { margin: 0 24px 16px; padding: 14px; border-radius: 10px; background: var(--secondary-background-color, #f3f6f8); line-height: 1.5; font-size: 14px; }
  .notice.error { border-left: 3px solid var(--error-color, #b63030); }
  .notice p + .row { margin-top: 12px; }
  .empty { padding: 24px 0; color: var(--secondary-text-color, #64717b); line-height: 1.6; }
  .finish-panel { border-top: 1px solid var(--divider-color, #dde3e7); padding-top: 18px; margin-top: 6px; }
  .finish-panel p { margin-bottom: 14px; line-height: 1.5; }
  .saved { color: var(--secondary-text-color, #64717b); font-size: 12px; }
  @media (max-width: 450px) {
    header, main, footer { padding-left: 16px; padding-right: 16px; }
    .notice { margin-left: 16px; margin-right: 16px; }
    h1 { font-size: 21px; }
    .set { grid-template-columns: 36px repeat(3, minmax(0, 1fr)); gap: 6px; padding: 8px 6px; }
    .set .remove-set { grid-column: 4; grid-row: 1; align-self: end; min-height: 46px; }
    .set .optional { grid-column: 4; }
    .set .set-type { grid-column: 2 / 4; }
    .set .completion { grid-row: 1 / 3; }
    .row.actions > button { flex: 1; }
  }
  @media (prefers-reduced-motion: reduce) { .progress > span { transition: none; } }
`;

class HevyWorkoutCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._epoch = 0;
    this._editVersion = 0;
    this._savedVersion = 0;
    this._board = null;
    this._draft = null;
    this._error = "";
    this._search = "";
    this._invalid = new Map();
    this._requestVersion = 0;
    this.shadowRoot.addEventListener("click", (event) => this._click(event));
    this.shadowRoot.addEventListener("input", (event) => this._input(event));
    this.shadowRoot.addEventListener("change", (event) => this._change(event));
  }

  static getConfigElement() { return document.createElement("hevy-workout-card-editor"); }
  static getStubConfig() { return { title: "Workout" }; }
  getCardSize() { return this._draft ? 9 : 4; }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Card configuration is required.");
    const previous = this._config.config_entry_id;
    this._config = { ...config };
    if (previous !== config.config_entry_id || !this._board) {
      this._reset(config.config_entry_id || "");
    }
    this._render();
    if (this.isConnected && this._hass) void this._load();
  }

  set hass(hass) {
    const connected = hass.connection?.connected ?? hass.connected ?? true;
    const connectionChanged = connected !== this._wasConnected;
    const reconnect = this._wasConnected === false && connected;
    const first = !this._hass;
    this._wasConnected = connected;
    this._hass = hass;
    if (!connected) clearTimeout(this._saveTimer);
    if (connectionChanged) this._render();
    if (this.isConnected && (first || reconnect || this._needsLoad)) void this._load();
  }

  connectedCallback() {
    this._needsLoad = true;
    this._render();
    if (this._hass) void this._load();
    clearInterval(this._poll);
    this._poll = setInterval(() => {
      if (!this._actionBusy && !this._saving && !this._dirty && !this._saveError) void this._load(true);
    }, 15000);
  }

  disconnectedCallback() {
    clearInterval(this._poll);
    clearTimeout(this._saveTimer);
    if (this._dirty && !this._saveError) void this._save();
    this._needsLoad = true;
  }

  get _dirty() { return this._editVersion !== this._savedVersion; }
  get _online() { return (this._hass?.connection?.connected ?? this._hass?.connected) !== false; }

  _reset(entry) {
    this._epoch += 1;
    this._entry = entry;
    this._actionBusy = false;
    this._board = null;
    this._draft = null;
    this._editVersion = 0;
    this._savedVersion = 0;
    this._saveError = false;
    this._conflict = false;
    this._error = "";
    this._confirm = "";
    this._invalid.clear();
    this._needsLoad = true;
    clearTimeout(this._saveTimer);
  }

  async _service(service, data = {}, entry = this._entry) {
    if (!this._online) throw new Error("Reconnect to Home Assistant before continuing.");
    if (service !== "get_workout_board") this._requestVersion += 1;
    const result = await this._hass.callWS({
      type: "call_service",
      domain: "hevy",
      service,
      service_data: { ...(entry ? { config_entry_id: entry } : {}), ...data },
      return_response: true,
    });
    return result.response;
  }

  async _load(quiet = false) {
    if (this._saving) { this._needsLoad = true; return; }
    if (!this._hass || (this._hass.connection?.connected ?? this._hass.connected) === false || this._loading === this._epoch) return;
    const epoch = this._epoch;
    const requestVersion = this._requestVersion;
    this._loading = epoch;
    this._needsLoad = false;
    try {
      const board = await this._service("get_workout_board");
      if (epoch !== this._epoch || requestVersion !== this._requestVersion) return;
      const oldRevision = this._draft?.revision;
      const oldId = this._draft?.id;
      const oldStatus = this._draft?.status;
      this._board = board;
      this._entry = board.config_entry_id || this._entry;
      if (!this._dirty && !this._saving) {
        this._draft = board.session ? copy(board.session) : null;
        this._conflict = false;
      } else if (board.session?.id !== oldId || board.session?.revision !== oldRevision) {
        this._conflict = true;
        this._saveError = true;
        this._error = "This workout changed on another screen. Your unsaved edits are still here. Load the saved session to continue.";
      }
      if (!quiet || oldRevision !== this._draft?.revision || oldId !== this._draft?.id || oldStatus !== this._draft?.status || this._conflict) this._render();
    } catch (error) {
      if (epoch !== this._epoch) return;
      this._error = this._message(error, "Could not load your workout. Check the Home Assistant connection.");
      if (!quiet) this._render();
    } finally {
      if (this._loading === epoch) this._loading = undefined;
    }
  }

  _message(error, fallback) {
    return typeof error?.message === "string" && error.message ? error.message : fallback;
  }

  _changed() {
    this._editVersion += 1;
    this._confirm = "";
    this._status();
    clearTimeout(this._saveTimer);
    if (!this._saveError) this._saveTimer = setTimeout(() => void this._save(), 450);
  }

  async _save() {
    clearTimeout(this._saveTimer);
    if (this._saving) return this._saving;
    if (!this._dirty || !this._draft || this._draft.status !== "active" || this._saveError || this._invalid.size) return;
    const epoch = this._epoch;
    const entry = this._entry;
    this._saving = (async () => {
      while (this._dirty && epoch === this._epoch && !this._saveError && !this._invalid.size) {
        const version = this._editVersion;
        const draft = copy(this._draft);
        try {
          const result = await this._service("update_workout", {
            session_id: draft.id,
            revision: draft.revision,
            title: draft.title,
            is_private: draft.is_private,
            exercises: draft.exercises,
          }, entry);
          if (epoch !== this._epoch) return;
          this._draft.revision = result.session.revision;
          this._board.session = copy(result.session);
          this._savedVersion = version;
          this._error = "";
        } catch (error) {
          if (epoch !== this._epoch) return;
          this._saveError = true;
          this._error = this._message(error, "Your latest edits could not be saved. Check your connection and retry saving.");
          this._renderError();
        }
      }
    })();
    this._status();
    try { await this._saving; } finally {
      this._saving = null;
      this._status();
    }
    if (this._saveError && epoch === this._epoch) await this._load(true);
  }

  async _action(service, data = {}) {
    if (this._actionBusy) return;
    this._actionBusy = true;
    this._error = "";
    const epoch = this._epoch;
    try {
      if (this._invalid.size) throw new Error("Check the highlighted values before continuing.");
      await this._save();
      if (epoch !== this._epoch) return;
      if (this._dirty || this._saveError) throw new Error("Save your changes or load the saved session before continuing.");
      this._render();
      const result = await this._service(service, {
        ...(this._draft ? { session_id: this._draft.id, revision: this._draft.revision } : {}),
        ...data,
      });
      if (epoch !== this._epoch) return;
      this._draft = result.session ? copy(result.session) : null;
      this._board.session = result.session;
      this._confirm = "";
      this._editVersion = 0;
      this._savedVersion = 0;
      await this._load(true);
    } catch (error) {
      if (epoch !== this._epoch) return;
      this._error = this._message(error, "The request could not be completed. Check the saved workout status before trying again.");
      this._confirm = "";
      await this._load(true);
    } finally {
      if (epoch === this._epoch) {
        this._actionBusy = false;
        this._render();
      }
    }
  }

  _input(event) {
    const target = event.target;
    if (target.dataset.action === "search") {
      this._search = target.value;
      this._renderOptions();
      return;
    }
    if (!this._online || !this._draft || this._draft.status !== "active" || this._actionBusy) return;
    const field = target.dataset.field;
    if (!field || target.type === "checkbox" || target.tagName === "SELECT") return;
    const key = `${field}:${target.dataset.exercise || ""}:${target.dataset.set || ""}`;
    if ((target.validity && !target.validity.valid) || (field === "title" && !target.value.trim())) {
      target.setAttribute("aria-invalid", "true");
      this._invalid.set(key, target.value);
      this._changed();
      return;
    }
    this._invalid.delete(key);
    target.removeAttribute("aria-invalid");
    if (field === "title") this._draft.title = target.value;
    else if (field === "notes") this._draft.exercises[Number(target.dataset.exercise)].notes = target.value;
    else {
      const set = this._draft.exercises[Number(target.dataset.exercise)].sets[Number(target.dataset.set)];
      if (target.value === "") delete set[field];
      else set[field] = Number(target.value);
    }
    this._changed();
  }

  _change(event) {
    const target = event.target;
    if (target.dataset.action === "account") { void this._switchAccount(target.value); return; }
    if (!this._online || !this._draft || this._draft.status !== "active" || this._actionBusy) return;
    const field = target.dataset.field;
    if (field === "is_private") this._draft.is_private = target.checked;
    else if (field === "completed" || field === "type" || field === "rpe") {
      const set = this._draft.exercises[Number(target.dataset.exercise)].sets[Number(target.dataset.set)];
      if (field === "completed" && target.checked && !["weight", "reps", "duration_seconds", "distance"].some((name) => set[name] != null)) {
        target.checked = false;
        this._error = "Enter a measurement before completing this set.";
        this._renderError();
        return;
      }
      if (field === "rpe") {
        if (target.value) set.rpe = Number(target.value);
        else delete set.rpe;
      } else set[field] = field === "completed" ? target.checked : target.value;
      if (field === "completed") target.closest(".set").classList.toggle("done", target.checked);
    } else return;
    this._changed();
  }

  async _switchAccount(entry) {
    if (this._actionBusy) return;
    await this._save();
    if (this._dirty || this._saveError) { this._render(); return; }
    this._reset(entry);
    this._render();
    await this._load();
  }

  _click(event) {
    const button = event.target.closest("button[data-action]");
    if (!this._online || !button || button.disabled || this._actionBusy) return;
    const action = button.dataset.action;
    if (this._invalid.size && !["load-saved", "reload-confirm", "dismiss", "refresh"].includes(action)) {
      this._error = "Check the highlighted values. Measurements must be between 0 and 1,000,000; reps and seconds must be whole numbers. The title cannot be empty.";
      this._renderError();
      return;
    }
    const exerciseIndex = Number(button.dataset.exercise);
    if (action === "refresh") { this._error = ""; void this._load(); }
    else if (action === "retry-save") { this._saveError = false; this._error = ""; this._renderError(); void this._save(); }
    else if (action === "load-saved") this._showConfirmation("reload");
    else if (action === "reload-confirm") {
      this._draft = this._board.session ? copy(this._board.session) : null;
      this._editVersion = 0;
      this._savedVersion = 0;
      this._saveError = false;
      this._conflict = false;
      this._invalid.clear();
      this._error = "";
      this._confirm = "";
      this._render();
      void this._load();
    }
    else if (action === "start") {
      const routine = this.shadowRoot.querySelector("[data-action=routine]").value;
      void this._action("start_workout", routine ? { routine_id: routine } : {});
    }
    else if (action === "add-exercise") {
      const id = this.shadowRoot.querySelector("[data-action=exercise]").value;
      const exercise = this._board.exercises.find((item) => item.id === id);
      if (!exercise || this._draft.exercises.length >= 100) return;
      this._draft.exercises.push({ exercise_template_id: id, name: exercise.title, sets: [{ type: "normal", completed: false }] });
      this._changed();
      this._render();
    }
    else if (action === "add-set") {
      const sets = this._draft.exercises[exerciseIndex].sets;
      if (sets.length >= 100) return;
      sets.push({ ...(sets.length ? copy(sets[sets.length - 1]) : { type: "normal" }), completed: false });
      this._changed();
      this._render();
    }
    else if (action === "remove-set") {
      if (this._draft.exercises[exerciseIndex].sets.length <= 1) return;
      this._draft.exercises[exerciseIndex].sets.splice(Number(button.dataset.set), 1);
      this._changed();
      this._render();
    }
    else if (action === "remove-exercise") {
      this._showConfirmation(`remove:${exerciseIndex}`);
    }
    else if (action === "remove-confirm") {
      this._draft.exercises.splice(exerciseIndex, 1);
      this._changed();
      this._render();
    }
    else if (["finish", "cancel", "retry", "discard"].includes(action)) this._showConfirmation(action);
    else if (action === "dismiss") { this._confirm = ""; this._render(); }
    else if (action === "finish-confirm") void this._action("finish_workout");
    else if (action === "cancel-confirm") void this._action("cancel_workout");
    else if (action === "retry-confirm") void this._action("resolve_workout", { resolution: "retry" });
    else if (action === "discard-confirm") void this._action("resolve_workout", { resolution: "discard" });
  }

  _showConfirmation(action) {
    this._confirm = action;
    this._render();
    const panel = this.shadowRoot.querySelector(".finish-panel");
    panel?.focus({ preventScroll: true });
    panel?.scrollIntoView?.({ block: "nearest", behavior: "instant" });
  }

  _ordered(items, favorites = []) {
    const ids = Array.isArray(favorites) ? favorites : [];
    return [...items].sort((a, b) => Number(ids.includes(b.id)) - Number(ids.includes(a.id)) || a.title.localeCompare(b.title));
  }

  _exerciseOptions() {
    const search = this._search.toLocaleLowerCase();
    const items = this._ordered(this._board?.exercises || [], this._config.exercise_ids).filter((item) => `${item.title} ${item.muscle_group || ""}`.toLocaleLowerCase().includes(search));
    return `<option value="">${items.length ? "Choose an exercise" : "No exercises found"}</option>${items.map((item) => `<option value="${escapeHTML(item.id)}">${escapeHTML(item.title)}</option>`).join("")}`;
  }

  _renderOptions() {
    const select = this.shadowRoot.querySelector("[data-action=exercise]");
    if (select) select.innerHTML = this._exerciseOptions();
  }

  _count() {
    const sets = this._draft?.exercises.flatMap((exercise) => exercise.sets) || [];
    return { total: sets.length, completed: sets.filter((set) => set.completed).length };
  }

  _status() {
    const status = this.shadowRoot.querySelector("[data-save-status]");
    if (status) status.textContent = !this._online ? "Offline. Reconnect to Home Assistant." : this._invalid.size ? "Check highlighted values" : this._saveError ? "Changes not saved" : this._saving || this._dirty ? "Saving changes..." : "Saved in Home Assistant";
    const { total, completed } = this._count();
    const count = this.shadowRoot.querySelector("[data-count]");
    if (count) count.textContent = `${completed} of ${total} sets completed`;
    const progress = this.shadowRoot.querySelector(".progress > span");
    if (progress) progress.style.width = `${total ? completed / total * 100 : 0}%`;
    const finish = this.shadowRoot.querySelector('[data-action="finish"]');
    if (finish) finish.disabled = !this._online || !completed || this._actionBusy || this._saveError || Boolean(this._invalid.size);
  }

  _renderError() {
    const region = this.shadowRoot.querySelector("[data-errors]");
    if (!region) return;
    region.innerHTML = this._error ? `<div class="notice error" role="alert"><p>${escapeHTML(this._error)}</p><div class="row">${this._saveError && !this._conflict ? '<button data-action="retry-save">Retry saving</button>' : ""}${this._saveError || this._invalid.size ? '<button data-action="load-saved">Load saved session</button>' : '<button data-action="refresh">Refresh status</button>'}</div></div>` : "";
  }

  _numeric(field, label, set, exercise, index, disabled) {
    const key = `${field}:${exercise}:${index}`;
    const value = this._invalid.has(key) ? this._invalid.get(key) : set[field] ?? "";
    if (field === "rpe") return `<label>RPE<select data-field="rpe" data-exercise="${exercise}" data-set="${index}" aria-label="RPE for set ${index + 1} of ${escapeHTML(this._draft.exercises[exercise].name)}" ${disabled}><option value="">None</option>${[6, 7, 7.5, 8, 8.5, 9, 9.5, 10].map((rpe) => `<option value="${rpe}" ${rpe === set.rpe ? "selected" : ""}>${rpe}</option>`).join("")}</select></label>`;
    const integer = field === "reps" || field === "duration_seconds";
    return `<label>${label}<input type="number" inputmode="${integer ? "numeric" : "decimal"}" min="0" max="1000000" ${this._invalid.has(key) ? 'aria-invalid="true"' : ""} step="${integer ? "1" : field === "rpe" ? "0.5" : "any"}" value="${escapeHTML(value)}" aria-label="${escapeHTML(label)} for set ${index + 1} of ${escapeHTML(this._draft.exercises[exercise].name)}" data-field="${field}" data-exercise="${exercise}" data-set="${index}" ${disabled}></label>`;
  }

  _exercise(exercise, index, disabled) {
    const metadata = this._board.exercises.find((item) => item.id === exercise.exercise_template_id);
    const kind = metadata?.type || "weight_reps";
    const duration = kind.includes("duration") || exercise.sets.some((set) => set.duration_seconds != null);
    const distance = kind.includes("distance") || exercise.sets.some((set) => set.distance != null);
    const weight = kind.includes("weight") || exercise.sets.some((set) => set.weight != null);
    const reps = kind.includes("reps") || exercise.sets.some((set) => set.reps != null) || (!duration && !distance);
    const fields = [];
    if (weight) fields.push(["weight", `Weight (${escapeHTML(this._draft.weight_unit)})`]);
    if (reps) fields.push(["reps", "Reps"]);
    if (duration) fields.push(["duration_seconds", "Time (sec)"]);
    if (distance) fields.push(["distance", `Distance (${escapeHTML(this._draft.distance_unit)})`]);
    return `<section class="exercise"><div class="row spread exercise-head"><h3>${escapeHTML(exercise.name)}</h3><button class="danger" data-action="remove-exercise" data-exercise="${index}" aria-label="Remove ${escapeHTML(exercise.name)}" ${disabled}>Remove</button></div><div class="sets">${exercise.sets.map((set, setIndex) => `<div class="set ${set.completed ? "done" : ""}"><label class="completion"><span>Set ${setIndex + 1}</span><input type="checkbox" data-field="completed" data-exercise="${index}" data-set="${setIndex}" aria-label="Complete set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${set.completed ? "checked" : ""} ${disabled}></label>${fields.map(([field, label]) => this._numeric(field, label, set, index, setIndex, disabled)).join("")}<label class="set-type">Set type<select data-field="type" data-exercise="${index}" data-set="${setIndex}" aria-label="Type for set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${disabled}>${setTypes.map((type) => `<option value="${type}" ${type === set.type ? "selected" : ""}>${type[0].toUpperCase() + type.slice(1)}</option>`).join("")}</select></label><div class="optional">${this._numeric("rpe", "RPE", set, index, setIndex, disabled)}</div><button class="remove-set danger" data-action="remove-set" data-exercise="${index}" data-set="${setIndex}" aria-label="Remove set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${disabled || (exercise.sets.length <= 1 ? "disabled" : "")}>×</button></div>`).join("")}</div><div class="exercise-actions"><button data-action="add-set" data-exercise="${index}" ${disabled}>+ Add set</button></div><details><summary>Exercise notes</summary><label>Notes<textarea data-field="notes" data-exercise="${index}" aria-label="Notes for ${escapeHTML(exercise.name)}" maxlength="2000" ${disabled}>${escapeHTML(exercise.notes || "")}</textarea></label></details></section>`;
  }

  _confirmation() {
    if (!this._confirm) return "";
    let title;
    let text;
    let action;
    let label;
    let extra = "";
    if (this._confirm === "finish") {
      title = "Finish this workout?";
      text = `${this._count().completed} completed sets will be sent to Hevy. Unchecked sets will be left out.`;
      action = "finish-confirm";
      label = "Finish and send to Hevy";
    } else if (this._confirm === "cancel") {
      title = this._draft?.status === "finished" ? "Start fresh?" : "Discard this session?";
      text = this._draft?.status === "finished" ? "Your workout stays in Hevy. This clears the session from your board." : "This removes the saved session from Home Assistant. It will not send a workout to Hevy.";
      action = "cancel-confirm";
      label = "Clear session";
    } else if (this._confirm === "retry") {
      title = "Check Hevy before retrying";
      text = "Open Hevy and check whether this workout was saved. Only unlock another submission if you have confirmed the workout is missing. Sending it again could create a duplicate.";
      action = "retry-confirm";
      label = "I checked Hevy. The workout is missing";
    } else if (this._confirm === "discard") {
      title = "Have you checked Hevy?";
      text = "Confirm the workout's status in Hevy first. Clearing this session will not delete a workout that reached Hevy.";
      action = "discard-confirm";
      label = "I checked Hevy. Clear this session";
    } else if (this._confirm === "reload") {
      title = "Replace your unsaved edits?";
      text = "Your unsaved edits will be discarded and the session saved in Home Assistant will be loaded.";
      action = "reload-confirm";
      label = "Discard edits and load saved session";
    } else if (this._confirm.startsWith("remove:")) {
      const index = Number(this._confirm.split(":")[1]);
      title = `Remove ${this._draft.exercises[index].name}?`;
      text = "This removes the exercise and all its sets from this session.";
      action = "remove-confirm";
      extra = `data-exercise="${index}"`;
      label = "Remove exercise";
    }
    return `<div class="finish-panel" tabindex="-1" role="region" aria-label="${escapeHTML(title)}"><h2>${escapeHTML(title)}</h2><p>${escapeHTML(text)}</p><div class="row actions"><button data-action="dismiss" ${this._actionBusy ? "disabled" : ""}>Go back</button><button class="primary" data-action="${action}" ${extra} ${this._actionBusy ? "disabled" : ""}>${escapeHTML(label)}</button></div></div>`;
  }

  _render() {
    const draft = this._draft;
    const busy = this._actionBusy || !this._online ? "disabled" : "";
    const disabled = this._actionBusy || !this._online || draft?.status !== "active" ? "disabled" : "";
    const accounts = this._board?.accounts || [];
    let content;
    let footer = "";
    if (!this._board) content = '<p class="empty" role="status">Loading your workout board...</p>';
    else if (!this._entry) content = '<p class="empty">Choose a Hevy account to open its workout board.</p>';
    else if (!draft) {
      content = `<div class="intro"><h2>Ready when you are.</h2><p class="muted">Choose a routine or start from scratch. Your progress is saved here as you train.</p></div><div class="stack"><label>Routine<select data-action="routine" ${busy}><option value="">Empty workout</option>${this._ordered(this._board.routines || [], this._config.routine_ids).map((routine) => `<option value="${escapeHTML(routine.id)}" ${routine.id === this._board.next_routine_id ? "selected" : ""}>${escapeHTML(routine.title)}</option>`).join("")}</select></label><button class="primary" data-action="start" ${busy}>${this._actionBusy ? "Starting..." : "Start workout"}</button></div>`;
    } else if (draft.status === "finished") {
      content = `<div class="intro"><p class="eyebrow">Workout complete</p><h2>${escapeHTML(draft.title)}</h2><p>Your completed sets have been sent to Hevy.</p>${draft.workout_id ? `<p class="muted">Workout ID: ${escapeHTML(draft.workout_id)}</p>` : ""}</div>`;
      footer = '<button class="primary" data-action="cancel">New workout</button>';
    } else if (draft.status === "uncertain") {
      content = `<div class="intro"><h2>Check your workout in Hevy</h2><p>Home Assistant could not confirm whether Hevy saved this workout. Your session is preserved. Check Hevy before choosing what to do next.</p></div><div class="row actions"><button data-action="discard" ${busy}>Clear checked session</button><button class="primary" data-action="retry" ${busy}>Workout is missing</button></div>`;
    } else if (draft.status === "submitting") {
      content = `<div class="intro" role="status"><h2>Sending your workout...</h2><p>Keep this session open. Its saved status will update automatically.</p></div>`;
    } else {
      content = `<div class="stack"><label>Workout title<input data-field="title" value="${escapeHTML(this._invalid.has("title::") ? this._invalid.get("title::") : draft.title)}" required maxlength="200" ${this._invalid.has("title::") ? 'aria-invalid="true"' : ""} ${disabled}></label><label class="check"><input type="checkbox" data-field="is_private" ${draft.is_private ? "checked" : ""} ${disabled}>Private workout</label></div>${draft.exercises.length ? draft.exercises.map((exercise, index) => this._exercise(exercise, index, disabled)).join("") : '<p class="empty">Add your first exercise below, then check off each set as you finish it.</p>'}<section class="picker stack"><h3>Add an exercise</h3><label>Search exercises<input data-action="search" type="search" value="${escapeHTML(this._search)}" placeholder="Name or muscle group" ${disabled}></label><label>Exercise<select data-action="exercise" ${disabled}>${this._exerciseOptions()}</select></label><button data-action="add-exercise" ${disabled}>+ Add exercise</button></section>`;
      footer = `<div class="row spread"><span class="muted" data-count></span><span class="saved" data-save-status role="status" aria-live="polite"></span></div><div class="progress" aria-hidden="true"><span></span></div><div class="row actions"><button class="danger" data-action="cancel" ${busy}>Discard session</button><button class="primary" data-action="finish" ${busy}>Finish workout</button></div>`;
    }
    this.shadowRoot.innerHTML = `<style>${styles}</style><ha-card><header><div><p class="eyebrow">Hevy · Workout board</p><h1>${escapeHTML(this._config.title || "Workout")}</h1></div>${draft ? `<span class="badge">${escapeHTML(({ active: "In progress", submitting: "Sending", uncertain: "Check Hevy", finished: "Finished" })[draft.status] || draft.status)}</span>` : ""}</header><div data-errors></div>${accounts.length > 1 ? `<div class="notice"><label>Hevy account<select data-action="account" ${busy}><option value="">Choose an account</option>${accounts.map((account) => `<option value="${escapeHTML(account.config_entry_id)}" ${account.config_entry_id === this._entry ? "selected" : ""}>${escapeHTML(account.title)}</option>`).join("")}</select></label></div>` : ""}<main>${content}</main>${footer || this._confirm ? `<footer>${footer}${this._confirmation()}</footer>` : ""}</ha-card>`;
    this._renderError();
    this._status();
  }
}

class HevyWorkoutCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this.shadowRoot.addEventListener("change", (event) => {
      const key = event.target.dataset.config;
      if (!key) return;
      const value = event.target.value.trim();
      this._config = { ...this._config };
      if (key.endsWith("_ids")) {
        const ids = value.split(",").map((id) => id.trim()).filter(Boolean);
        if (ids.length) this._config[key] = ids;
        else delete this._config[key];
      } else if (value) this._config[key] = value;
      else delete this._config[key];
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: { ...this._config } }, bubbles: true, composed: true }));
    });
  }

  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) { this._hass = hass; void this._accounts(); }

  async _accounts() {
    if (this._requested || !this._hass) return;
    this._requested = true;
    try {
      const result = await this._hass.callWS({ type: "call_service", domain: "hevy", service: "get_workout_board", service_data: {}, return_response: true });
      this._accountList = result.response.accounts;
      this._render();
    } catch { this._requested = false; }
  }

  _render() {
    const config = this._config;
    this.shadowRoot.innerHTML = `<style>${styles}</style><div class="stack"><label>Title<input data-config="title" value="${escapeHTML(config.title || "Workout")}"></label><label>Hevy account${this._accountList ? `<select data-config="config_entry_id"><option value="">Choose on the card</option>${this._accountList.map((account) => `<option value="${escapeHTML(account.config_entry_id)}" ${account.config_entry_id === config.config_entry_id ? "selected" : ""}>${escapeHTML(account.title)}</option>`).join("")}</select>` : `<input data-config="config_entry_id" value="${escapeHTML(config.config_entry_id || "")}" placeholder="Optional config entry ID">`}</label><label>Favorite routine IDs<input data-config="routine_ids" value="${escapeHTML((config.routine_ids || []).join(", "))}" placeholder="Comma-separated IDs"></label><label>Favorite exercise IDs<input data-config="exercise_ids" value="${escapeHTML((config.exercise_ids || []).join(", "))}" placeholder="Comma-separated IDs"></label><p class="hint">Favorites appear first in the pickers. Other routines and exercises remain available. Sessions are saved in Home Assistant for the selected account.</p></div>`;
  }
}

if (!customElements.get("hevy-workout-card")) customElements.define("hevy-workout-card", HevyWorkoutCard);
if (!customElements.get("hevy-workout-card-editor")) customElements.define("hevy-workout-card-editor", HevyWorkoutCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "hevy-workout-card")) window.customCards.push({ type: "hevy-workout-card", name: "Hevy Workout", description: "Log workouts with sessions saved in Home Assistant.", preview: true });
