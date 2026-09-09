const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const copy = (value) => JSON.parse(JSON.stringify(value));
const setTypes = ["normal", "warmup", "failure", "dropset"];
const boardOptions = {
  show_header: [true, "Show board header"],
  show_intro: [false, "Show intro text"],
  show_exercise_notes: [true, "Show exercise notes"],
  show_add_exercise: [true, "Show Add an exercise section"],
  show_empty_workout: [true, "Show Empty workout in routine picker"],
  show_remove_exercise: [true, "Show exercise Remove button"],
  show_set_type: [true, "Show set type"],
  show_rpe: [true, "Show RPE"],
  show_private_workout: [true, "Show Private workout control"],
  default_private_workout: [false, "Make new workouts private by default"],
  collapse_completed_sets: [false, "Collapse completed sets"],
  show_account_stats: [false, "Show selected account stats"],
};
const styles = `
  :host { display: block; color: var(--primary-text-color, #202830); font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
  * { box-sizing: border-box; }
  ha-card { display: block; overflow: hidden; background: var(--ha-card-background, var(--card-background-color, #fff)); border-radius: var(--ha-card-border-radius, 16px); border: 1px solid var(--divider-color, #dde3e7); }
  header, main, footer { padding: 24px; }
  header { display: flex; align-items: start; justify-content: space-between; gap: 16px; padding-bottom: 16px; }
  h1, h2, h3, p { margin: 0; }
  h1 { font-size: 20px; font-weight: 650; letter-spacing: -.5px; overflow-wrap: anywhere; }
  h2 { font-size: 20px; margin-bottom: 12px; }
  h3 { font-size: 17px; }
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
  .exercise:first-child { border-top: 0; padding-top: 0; margin-top: 0; }
  .workout-title { font-size: 17px; margin: 0; overflow-wrap: anywhere; }
  main > .stack + .exercise { margin-top: 16px; padding-top: 16px; }
  .picker-intro, .success { margin-bottom: 16px; overflow-wrap: anywhere; }
  .success { font-size: 14px; line-height: 1.5; }
  .without-header { padding-top: 20px; }
  .account-picker, .account-identity { margin: 0 24px 16px; }
  .exercise-head { margin-bottom: 14px; }
  .exercise-head button, .remove-set { font-size: 12px; min-height: 44px; padding: 8px 10px; }
  .sets { display: grid; gap: 8px; }
  .set { display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px; gap: 8px; align-items: center; border-radius: 10px; padding: 8px; background: var(--secondary-background-color, #f3f6f8); }
  .set-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .set.collapsed { grid-template-columns: 44px minmax(0, 1fr); }
  .set-summary { text-align: left; border: 0; display: grid; gap: 4px; overflow-wrap: anywhere; }
  .set-summary .hint { margin: 0; }
  .collapse-set { grid-column: 1 / -1; }
  .account-name { margin-top: 8px; overflow-wrap: anywhere; }
  .account-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0 24px 20px; padding: 14px; border: 1px solid var(--divider-color, #dde3e7); border-radius: 10px; }
  .account-stats dt { font-size: 12px; color: var(--secondary-text-color, #64717b); }
  .account-stats dd { margin: 6px 0 0; font-size: 20px; font-weight: 600; }
  .account-stats dd.muted { font-size: 13px; overflow-wrap: anywhere; }
  .settings { border: 0; border-top: 1px solid var(--divider-color, #dde3e7); padding: 16px 0 0; margin: 0; min-width: 0; }
  .settings legend { font-size: 16px; font-weight: 600; padding: 0 8px 0 0; }
  .set.done { box-shadow: inset 3px 0 0 var(--primary-color, #167b74); }
  .set label { font-size: 11px; gap: 5px; }
  .set input:not([type=checkbox]), .set select { min-width: 0; padding: 8px; background: var(--ha-card-background, var(--card-background-color, #fff)); }
  .set .completion { align-self: stretch; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px; padding: 4px; }
  .set .remove-set { padding: 8px; }
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
    .account-picker, .account-identity { margin-left: 16px; margin-right: 16px; }
    .set { grid-template-columns: 32px minmax(0, 1fr) 32px; gap: 6px; padding: 8px 6px; }
    .set.collapsed { grid-template-columns: 32px minmax(0, 1fr); }
    .set .remove-set { min-height: 46px; }
    .account-stats { margin-left: 16px; margin-right: 16px; }
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
    this._expandedSets = new Set();
    this._requestVersion = 0;
    this.shadowRoot.addEventListener("click", (event) => this._click(event));
    this.shadowRoot.addEventListener("input", (event) => this._input(event));
    this.shadowRoot.addEventListener("change", (event) => this._change(event));
  }

  static getConfigElement() { return document.createElement("hevy-workout-card-editor"); }
  static getStubConfig() { return { title: "Workout" }; }
  getCardSize() { return this._draft && this._draft.status !== "finished" ? 9 : 4; }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Card configuration is required.");
    for (const key of Object.keys(boardOptions)) {
      if (config[key] !== undefined && typeof config[key] !== "boolean") throw new Error(`${boardOptions[key][1]} must be true or false.`);
    }
    if (config.workout_title !== undefined && !["editable", "readonly", "hidden"].includes(config.workout_title)) throw new Error("Workout title must be editable, readonly, or hidden.");
    if (config.intro_text !== undefined && typeof config.intro_text !== "string") throw new Error("Intro text must be text.");
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
  _option(key) { return this._config[key] ?? boardOptions[key][0]; }

  _accountTitle() {
    return this._board?.accounts?.find((account) => account.config_entry_id === this._entry)?.title || "Hevy account";
  }

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
    this._routineId = undefined;
    this._invalid.clear();
    this._expandedSets.clear();
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
      const oldRoutines = JSON.stringify([this._board?.routines, this._board?.next_routine_id]);
      this._board = board;
      this._entry = board.config_entry_id || this._entry;
      if (!this._dirty && !this._saving) {
        this._draft = board.session ? copy(board.session) : null;
        if (oldId !== this._draft?.id) this._expandedSets.clear();
        this._conflict = false;
      } else if (board.session?.id !== oldId || board.session?.revision !== oldRevision) {
        this._conflict = true;
        this._saveError = true;
        this._error = "This workout changed on another screen. Your unsaved edits are still here. Load the saved session to continue.";
      }
      const pickerChanged = (!this._draft || this._draft.status === "finished") && oldRoutines !== JSON.stringify([board.routines, board.next_routine_id]);
      if (!quiet || pickerChanged || oldRevision !== this._draft?.revision || oldId !== this._draft?.id || oldStatus !== this._draft?.status || this._conflict) this._render();
      else this._renderStats();
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
        ...(this._draft && service !== "start_workout" ? { session_id: this._draft.id, revision: this._draft.revision } : {}),
        ...data,
      });
      if (epoch !== this._epoch) return;
      this._draft = result.session ? copy(result.session) : null;
      this._board.session = result.session;
      this._confirm = "";
      this._editVersion = 0;
      this._savedVersion = 0;
      if (service === "start_workout") this._routineId = undefined;
      await this._load(true);
    } catch (error) {
      if (epoch !== this._epoch) return;
      this._error = this._message(error, "The request could not be completed. Check the saved workout status before trying again.");
      this._confirm = "";
      await this._load(true);
      if (service === "finish_workout" && this._draft?.status === "finished") this._error = "";
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
    if (target.dataset.action === "routine") { this._routineId = target.value; return; }
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
      if (field === "completed") {
        const key = `${target.dataset.exercise}:${target.dataset.set}`;
        this._expandedSets.delete(key);
        this._renderSet(Number(target.dataset.exercise), Number(target.dataset.set));
        this.shadowRoot.querySelector(`[data-field="completed"][data-exercise="${target.dataset.exercise}"][data-set="${target.dataset.set}"]`)?.focus({ preventScroll: true });
      }
    } else return;
    this._changed();
  }

  async _switchAccount(entry) {
    if (this._actionBusy) return;
    this._actionBusy = true;
    this._render();
    await this._save();
    if (this._dirty || this._saveError) { this._actionBusy = false; this._render(); return; }
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
      if ((!routine && !this._option("show_empty_workout")) || (routine && !this._board.routines?.some((item) => item.id === routine))) {
        this._error = "Choose an available routine before starting.";
        this._renderError();
        return;
      }
      void this._action("start_workout", { ...(routine ? { routine_id: routine } : {}), is_private: this._option("default_private_workout") });
    }
    else if (action === "add-exercise") {
      if (!this._option("show_add_exercise")) return;
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
      this._expandedSets.clear();
      this._changed();
      this._render();
    }
    else if (action === "remove-exercise") {
      if (!this._option("show_remove_exercise")) return;
      this._showConfirmation(`remove:${exerciseIndex}`);
    }
    else if (action === "remove-confirm") {
      if (!this._option("show_remove_exercise")) return;
      this._draft.exercises.splice(exerciseIndex, 1);
      this._expandedSets.clear();
      this._changed();
      this._render();
    }
    else if (action === "expand-set" || action === "collapse-set") {
      const setIndex = Number(button.dataset.set);
      const key = `${exerciseIndex}:${setIndex}`;
      if (action === "expand-set") this._expandedSets.add(key);
      else this._expandedSets.delete(key);
      this._renderSet(exerciseIndex, setIndex);
      this.shadowRoot.querySelector(`[data-field="completed"][data-exercise="${exerciseIndex}"][data-set="${setIndex}"]`)?.focus({ preventScroll: true });
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
    requestAnimationFrame(() => {
      if (!panel?.isConnected) return;
      panel.focus({ preventScroll: true });
      panel.scrollIntoView?.({ block: "nearest", behavior: "instant" });
    });
  }

  _ordered(items, favorites = []) {
    const ids = Array.isArray(favorites) ? favorites : [];
    return [...items].sort((a, b) => Number(ids.includes(b.id)) - Number(ids.includes(a.id)) || a.title.localeCompare(b.title));
  }

  _routinePicker(busy) {
    const routines = this._ordered(this._board.routines || [], this._config.routine_ids);
    const showEmpty = this._option("show_empty_workout");
    if (!routines.some((routine) => routine.id === this._routineId) && !(this._routineId === "" && showEmpty)) {
      this._routineId = routines.find((routine) => routine.id === this._board.next_routine_id)?.id ?? (showEmpty ? "" : routines[0]?.id);
    }
    const unavailable = !showEmpty && !routines.length;
    const intro = this._option("show_intro") ? `<p class="muted picker-intro">${escapeHTML(this._config.intro_text || "Choose a routine.")}</p>` : "";
    const success = this._draft?.status === "finished" ? `<p class="success" role="status">${escapeHTML(this._draft.title)} was sent to ${escapeHTML(this._accountTitle())}.</p>` : "";
    return `${success}${intro}<div class="stack"><label>Routine<select data-action="routine" ${busy || (unavailable ? "disabled" : "")}>${showEmpty ? `<option value="" ${this._routineId === "" ? "selected" : ""}>Empty workout</option>` : ""}${unavailable ? '<option value="">No routines available</option>' : ""}${routines.map((routine) => `<option value="${escapeHTML(routine.id)}" ${routine.id === this._routineId ? "selected" : ""}>${escapeHTML(routine.title)}</option>`).join("")}</select></label>${unavailable ? '<p class="muted">Create a routine in Hevy and refresh, or enable Empty workout in this card\'s settings.</p><button data-action="refresh" ' + busy + '>Refresh routines</button>' : ""}<button class="primary" data-action="start" ${busy || (unavailable ? "disabled" : "")}>${this._actionBusy ? "Starting..." : "Start workout"}</button></div>`;
  }

  _workoutFields(disabled) {
    const invalid = this._invalid.has("title::");
    const mode = invalid ? "editable" : this._config.workout_title || "editable";
    const title = mode === "editable" ? `<label>Workout title<input data-field="title" value="${escapeHTML(invalid ? this._invalid.get("title::") : this._draft.title)}" required maxlength="200" ${invalid ? 'aria-invalid="true"' : ""} ${disabled}></label>` : mode === "readonly" ? `<h2 class="workout-title">${escapeHTML(this._draft.title)}</h2>` : "";
    const privacy = this._option("show_private_workout") ? `<label class="check"><input type="checkbox" data-field="is_private" ${this._draft.is_private ? "checked" : ""} ${disabled}>Private workout</label>` : "";
    return title || privacy ? `<div class="stack">${title}${privacy}</div>` : "";
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

  _measurementFields(exercise) {
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
    return fields;
  }

  _set(exercise, index, setIndex, disabled) {
    const set = exercise.sets[setIndex];
    const key = `${index}:${setIndex}`;
    const invalid = [...this._invalid.keys()].some((field) => field.endsWith(`:${key}`));
    const collapsible = this._option("collapse_completed_sets") && set.completed && !invalid;
    const collapsed = collapsible && !this._expandedSets.has(key);
    const completion = `<label class="completion"><span>Set ${setIndex + 1}</span><input type="checkbox" data-field="completed" data-exercise="${index}" data-set="${setIndex}" aria-label="Complete set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${set.completed ? "checked" : ""} ${disabled}></label>`;
    if (collapsed) {
      const measurements = [["weight", this._draft.weight_unit], ["reps", "reps"], ["duration_seconds", "sec"], ["distance", this._draft.distance_unit]].filter(([field]) => set[field] != null).map(([field, unit]) => `${set[field]} ${unit}`).join(" · ");
      return `<div class="set done collapsed" data-set-row="${key}">${completion}<button class="set-summary" data-action="expand-set" data-exercise="${index}" data-set="${setIndex}" aria-expanded="false" aria-label="Show details for set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${disabled}><span>${escapeHTML(measurements)}</span><span class="hint">Show details</span></button></div>`;
    }
    const type = this._option("show_set_type") ? `<label>Set type<select data-field="type" data-exercise="${index}" data-set="${setIndex}" aria-label="Type for set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${disabled}>${setTypes.map((type) => `<option value="${type}" ${type === set.type ? "selected" : ""}>${type[0].toUpperCase() + type.slice(1)}</option>`).join("")}</select></label>` : "";
    const rpe = this._option("show_rpe") ? this._numeric("rpe", "RPE", set, index, setIndex, disabled) : "";
    const collapse = collapsible ? `<button class="collapse-set" data-action="collapse-set" data-exercise="${index}" data-set="${setIndex}" aria-expanded="true" ${disabled}>Hide details</button>` : "";
    return `<div class="set ${set.completed ? "done" : ""}" data-set-row="${key}">${completion}<div class="set-fields">${this._measurementFields(exercise).map(([field, label]) => this._numeric(field, label, set, index, setIndex, disabled)).join("")}${type}${rpe}${collapse}</div><button class="remove-set danger" data-action="remove-set" data-exercise="${index}" data-set="${setIndex}" aria-label="Remove set ${setIndex + 1} of ${escapeHTML(exercise.name)}" ${disabled || (exercise.sets.length <= 1 ? "disabled" : "")}>×</button></div>`;
  }

  _renderSet(index, setIndex) {
    const row = this.shadowRoot.querySelector(`[data-set-row="${index}:${setIndex}"]`);
    const exercise = this._draft?.exercises[index];
    if (row && exercise?.sets[setIndex]) {
      const disabled = this._actionBusy || !this._online || this._draft.status !== "active" ? "disabled" : "";
      row.outerHTML = this._set(exercise, index, setIndex, disabled);
    }
  }

  _exercise(exercise, index, disabled) {
    const remove = this._option("show_remove_exercise") ? `<button class="danger" data-action="remove-exercise" data-exercise="${index}" aria-label="Remove ${escapeHTML(exercise.name)}" ${disabled}>Remove</button>` : "";
    const invalidNotes = this._invalid.has(`notes:${index}:`);
    const notes = this._option("show_exercise_notes") || invalidNotes ? `<details ${invalidNotes ? "open" : ""}><summary>Exercise notes</summary><label>Notes<textarea data-field="notes" data-exercise="${index}" aria-label="Notes for ${escapeHTML(exercise.name)}" maxlength="2000" ${invalidNotes ? 'aria-invalid="true"' : ""} ${disabled}>${escapeHTML(invalidNotes ? this._invalid.get(`notes:${index}:`) : exercise.notes || "")}</textarea></label></details>` : "";
    return `<section class="exercise"><div class="row spread exercise-head"><h3>${escapeHTML(exercise.name)}</h3>${remove}</div><div class="sets">${exercise.sets.map((_, setIndex) => this._set(exercise, index, setIndex, disabled)).join("")}</div><div class="exercise-actions"><button data-action="add-set" data-exercise="${index}" ${disabled}>+ Add set</button></div>${notes}</section>`;
  }

  _renderStats() {
    const region = this.shadowRoot.querySelector("[data-account-stats]");
    if (!region) return;
    const stats = this._board?.stats || {};
    region.innerHTML = [["workout_count", "Total workouts"], ["weekly_workout_count", "Last 7 days"], ["current_streak", "Streak (days)"]].map(([key, label]) => {
      const available = typeof stats[key] === "number" && Number.isFinite(stats[key]);
      return `<div><dt>${label}</dt><dd class="${available ? "" : "muted"}">${available ? escapeHTML(stats[key]) : "Unavailable"}</dd></div>`;
    }).join("");
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
      text = `${this._count().completed} completed ${this._count().completed === 1 ? "set" : "sets"} will be sent to ${this._accountTitle()} as a ${this._draft.is_private ? "private" : "public"} workout. Unchecked sets will be left out.`;
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
    else if (!draft || draft.status === "finished") {
      content = this._routinePicker(busy);
    } else if (draft.status === "uncertain") {
      content = `<div class="intro"><h2>Check your workout in Hevy</h2><p>Home Assistant could not confirm whether Hevy saved this workout. Your session is preserved. Check Hevy before choosing what to do next.</p></div><div class="row actions"><button data-action="discard" ${busy}>Clear checked session</button><button class="primary" data-action="retry" ${busy}>Workout is missing</button></div>`;
    } else if (draft.status === "submitting") {
      content = `<div class="intro" role="status"><h2>Sending your workout...</h2><p>Keep this session open. Its saved status will update automatically.</p></div>`;
    } else {
      const picker = this._option("show_add_exercise") ? `<section class="picker stack"><h3>Add an exercise</h3><label>Search exercises<input data-action="search" type="search" value="${escapeHTML(this._search)}" placeholder="Name or muscle group" ${disabled}></label><label>Exercise<select data-action="exercise" ${disabled}>${this._exerciseOptions()}</select></label><button data-action="add-exercise" ${disabled}>+ Add exercise</button></section>` : "";
      const empty = this._option("show_add_exercise") ? "Add an exercise to begin." : "This workout has no exercises. Enable Add an exercise in this card's settings, or discard this session and choose a routine.";
      content = `${this._workoutFields(disabled)}${draft.exercises.length ? draft.exercises.map((exercise, index) => this._exercise(exercise, index, disabled)).join("") : `<p class="empty">${empty}</p>`}${picker}`;
      footer = `<div class="row spread"><span class="muted" data-count></span><span class="saved" data-save-status role="status" aria-live="polite"></span></div><div class="progress" aria-hidden="true"><span></span></div><div class="row actions"><button class="danger" data-action="cancel" ${busy}>Discard session</button><button class="primary" data-action="finish" ${busy}>Finish workout</button></div>`;
    }
    const accountName = this._entry && this._board && accounts.length <= 1 ? `<p class="muted account-name">${escapeHTML(this._accountTitle())}</p>` : "";
    const header = this._option("show_header") ? `<header><div><h1>${escapeHTML(this._config.title || "Workout")}</h1>${accountName}</div>${draft && draft.status !== "finished" ? `<span class="badge">${escapeHTML(({ active: "In progress", submitting: "Sending", uncertain: "Check Hevy" })[draft.status] || draft.status)}</span>` : ""}</header>` : accountName ? `<div class="account-identity">${accountName}</div>` : "";
    this.shadowRoot.innerHTML = `<style>${styles}</style><ha-card class="${this._option("show_header") ? "" : "without-header"}">${header}<div data-errors></div>${accounts.length > 1 ? `<div class="account-picker"><label>Who is working out?<select data-action="account" ${busy}><option value="">Choose an account</option>${accounts.map((account) => `<option value="${escapeHTML(account.config_entry_id)}" ${account.config_entry_id === this._entry ? "selected" : ""}>${escapeHTML(account.title)}</option>`).join("")}</select></label></div>` : ""}${this._option("show_account_stats") && this._entry ? `<dl class="account-stats" data-account-stats aria-label="Stats for ${escapeHTML(this._accountTitle())}"></dl>` : ""}<main>${content}</main>${footer || this._confirm ? `<footer>${footer}${this._confirmation()}</footer>` : ""}</ha-card>`;
    this._renderError();
    this._status();
    this._renderStats();
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
      const value = event.target.type === "checkbox" ? event.target.checked : event.target.value.trim();
      this._config = { ...this._config };
      if (key in boardOptions) this._config[key] = value;
      else if (key.endsWith("_ids")) {
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
    this.shadowRoot.innerHTML = `<style>${styles}</style><div class="stack"><label>Board title<input data-config="title" value="${escapeHTML(config.title || "Workout")}"></label><label>Intro text<input data-config="intro_text" value="${escapeHTML(config.intro_text || "Choose a routine.")}"></label><label>Hevy account${this._accountList ? `<select data-config="config_entry_id"><option value="">Choose on the card</option>${this._accountList.map((account) => `<option value="${escapeHTML(account.config_entry_id)}" ${account.config_entry_id === config.config_entry_id ? "selected" : ""}>${escapeHTML(account.title)}</option>`).join("")}</select>` : `<input data-config="config_entry_id" value="${escapeHTML(config.config_entry_id || "")}" placeholder="Optional config entry ID">`}</label><label>Favorite routine IDs<input data-config="routine_ids" value="${escapeHTML((config.routine_ids || []).join(", "))}" placeholder="Comma-separated IDs"></label><label>Favorite exercise IDs<input data-config="exercise_ids" value="${escapeHTML((config.exercise_ids || []).join(", "))}" placeholder="Comma-separated IDs"></label><p class="hint">Favorites appear first in the pickers. Other routines and exercises remain available. Sessions are saved in Home Assistant for the selected account.</p><fieldset class="settings"><legend>Board display</legend><label>Workout title<select data-config="workout_title">${[["editable", "Editable input"], ["readonly", "Text only"], ["hidden", "Hidden"]].map(([value, label]) => `<option value="${value}" ${(config.workout_title || "editable") === value ? "selected" : ""}>${label}</option>`).join("")}</select></label>${Object.entries(boardOptions).map(([key, [fallback, label]]) => `<label class="check"><input type="checkbox" data-config="${key}" ${(config[key] ?? fallback) ? "checked" : ""}>${label}</label>`).join("")}<p class="hint">The privacy default applies when starting a new workout. Saved sessions keep their privacy setting. Hidden values are preserved. Invalid edits stay visible until corrected or the saved session is loaded.</p></fieldset></div>`;
  }
}

if (!customElements.get("hevy-workout-card")) customElements.define("hevy-workout-card", HevyWorkoutCard);
if (!customElements.get("hevy-workout-card-editor")) customElements.define("hevy-workout-card-editor", HevyWorkoutCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "hevy-workout-card")) window.customCards.push({ type: "hevy-workout-card", name: "Hevy Workout", description: "Log workouts with sessions saved in Home Assistant.", preview: true });
