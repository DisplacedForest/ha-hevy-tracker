from __future__ import annotations

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import CoreState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util.file import WriteError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hevy.api import HevyApiError
from custom_components.hevy.const import CONF_API_KEY, DOMAIN
from custom_components.hevy.session_services import register_session_services
from custom_components.hevy.workout_session import WorkoutSession


@pytest.fixture(autouse=True)
def storage_directory(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)


@pytest.fixture
async def session_manager(hass, imperial_coordinator):
    coordinator = imperial_coordinator
    coordinator._exercise_templates = {
        "t1": {"title": "Bench Press", "type": "weight_reps"},
        "t3": {"title": "Running", "type": "distance_duration"},
        "t5": {"title": "Hip Openers", "type": "duration"},
    }
    await coordinator.fetch_routines()
    coordinator.client.create_workout = AsyncMock(return_value={"id": "saved-1"})
    coordinator.async_request_refresh = AsyncMock()
    manager = WorkoutSession(hass, "entry-one", coordinator)
    await manager.load()
    return manager


async def completed(manager):
    draft = await manager.start("r1", None)
    draft["exercises"][0]["sets"][0]["completed"] = True
    draft["exercises"][0]["sets"][0]["weight"] = 135
    draft["exercises"][1]["sets"][0]["completed"] = True
    return await manager.update(draft["id"], draft["revision"], draft)


async def test_saved_draft_restores_checked_sets_after_restart(hass, session_manager):
    draft = await completed(session_manager)
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    assert reopened.snapshot() == draft
    assert reopened.snapshot()["exercises"][0]["sets"][0]["completed"]


async def test_restart_during_submission_requires_recovery(hass, session_manager):
    draft = await completed(session_manager)
    draft["status"] = "submitting"
    await session_manager._save(draft)
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    recovered = reopened.snapshot()
    assert recovered["status"] == "uncertain"
    assert recovered["revision"] == draft["revision"] + 1
    with pytest.raises(ServiceValidationError):
        await reopened.finish(recovered["id"], recovered["revision"])
    session_manager.coordinator.client.create_workout.assert_not_called()


async def test_duplicate_finish_sends_once_and_returns_receipt(session_manager):
    draft = await completed(session_manager)
    results = await asyncio.gather(
        session_manager.finish(draft["id"], draft["revision"]),
        session_manager.finish(draft["id"], draft["revision"]),
    )
    assert results[0] == results[1]
    assert results[0]["status"] == "finished"
    assert results[0]["workout_id"] == "saved-1"
    session_manager.coordinator.client.create_workout.assert_awaited_once()


async def test_finish_only_sends_checked_sets_and_converts_frozen_units(
    session_manager,
):
    draft = await completed(session_manager)
    session_manager.coordinator.unit_system = "metric"
    await session_manager.finish(draft["id"], draft["revision"])
    payload = session_manager.coordinator.client.create_workout.call_args.args[0][
        "workout"
    ]
    assert len(payload["exercises"]) == 2
    assert len(payload["exercises"][0]["sets"]) == 1
    assert payload["exercises"][0]["sets"][0]["weight_kg"] == pytest.approx(61.24)
    assert payload["exercises"][1]["sets"][0]["distance_meters"] == pytest.approx(
        4989, abs=2
    )
    assert payload["start_time"] == draft["start_time"]


async def test_metric_session_keeps_metric_measurements(hass, metric_coordinator):
    metric_coordinator._exercise_templates = {"t1": {"title": "Bench Press"}}
    metric_coordinator.client.create_workout = AsyncMock(return_value={"id": "metric"})
    metric_coordinator.async_request_refresh = AsyncMock()
    manager = WorkoutSession(hass, "metric", metric_coordinator)
    draft = await manager.start(None, "Metric workout")
    draft["exercises"] = [
        {
            "exercise_template_id": "t1",
            "name": "ignored",
            "sets": [{"weight": 20.5, "reps": 8, "distance": 2.5, "completed": True}],
        }
    ]
    draft = await manager.update(draft["id"], draft["revision"], draft)
    assert draft["exercises"][0]["name"] == "Bench Press"
    await manager.finish(draft["id"], draft["revision"])
    item = metric_coordinator.client.create_workout.call_args.args[0]["workout"][
        "exercises"
    ][0]["sets"][0]
    assert item["weight_kg"] == 20.5
    assert item["distance_meters"] == 2500


async def test_stale_update_cannot_overwrite_another_device(session_manager):
    draft = await completed(session_manager)
    changed = deepcopy(draft)
    changed["title"] = "Changed elsewhere"
    latest = await session_manager.update(draft["id"], draft["revision"], changed)
    with pytest.raises(ServiceValidationError, match="another device"):
        await session_manager.update(draft["id"], draft["revision"], draft)
    assert session_manager.snapshot() == latest


@pytest.mark.parametrize(
    "field,value",
    [
        ("weight", float("nan")),
        ("weight", float("inf")),
        ("weight", -1),
        ("weight", True),
        ("weight", "20"),
        ("weight", 1000001),
        ("reps", 2.5),
        ("reps", False),
        ("duration_seconds", 0.5),
        ("rpe", 8.2),
    ],
)
async def test_bad_measurements_do_not_replace_saved_draft(
    session_manager, field, value
):
    draft = await completed(session_manager)
    original = deepcopy(draft)
    draft["exercises"][0]["sets"][0][field] = value
    with pytest.raises(ServiceValidationError):
        await session_manager.update(draft["id"], draft["revision"], draft)
    assert session_manager.snapshot() == original


async def test_blank_sets_can_be_drafted_but_not_checked(session_manager):
    draft = await session_manager.start("r2", None)
    assert draft["exercises"][0]["sets"] == [{"type": "normal", "completed": False}]
    draft["exercises"][0]["sets"][0]["completed"] = True
    with pytest.raises(ServiceValidationError, match="measurement"):
        await session_manager.update(draft["id"], draft["revision"], draft)


async def test_zero_completed_sets_never_calls_hevy(session_manager):
    draft = await session_manager.start("r1", None)
    with pytest.raises(ServiceValidationError, match="at least one"):
        await session_manager.finish(draft["id"], draft["revision"])
    session_manager.coordinator.client.create_workout.assert_not_called()
    assert session_manager.snapshot()["status"] == "active"


@pytest.mark.parametrize("response", [{}, {"workout": []}, {"id": None}, {"id": 42}])
async def test_unconfirmed_response_never_automatically_retries(
    session_manager, response
):
    draft = await completed(session_manager)
    session_manager.coordinator.client.create_workout.return_value = response
    with pytest.raises(HomeAssistantError, match="Check Hevy"):
        await session_manager.finish(draft["id"], draft["revision"])
    uncertain = session_manager.snapshot()
    assert uncertain["status"] == "uncertain"
    with pytest.raises(ServiceValidationError):
        await session_manager.finish(uncertain["id"], uncertain["revision"])
    session_manager.coordinator.client.create_workout.assert_awaited_once()


async def test_timeout_preserves_draft_and_requires_explicit_resolution(
    session_manager,
):
    draft = await completed(session_manager)
    session_manager.coordinator.client.create_workout.side_effect = HevyApiError(
        "timeout"
    )
    with pytest.raises(HomeAssistantError):
        await session_manager.finish(draft["id"], draft["revision"])
    uncertain = session_manager.snapshot()
    assert uncertain["exercises"] == draft["exercises"]
    with pytest.raises(ServiceValidationError):
        await session_manager.cancel(uncertain["id"], uncertain["revision"])
    active = await session_manager.resolve(
        uncertain["id"], uncertain["revision"], "retry"
    )
    assert active["status"] == "active"
    assert active["end_time"] == uncertain["end_time"]
    session_manager.coordinator.client.create_workout.side_effect = None
    await session_manager.finish(active["id"], active["revision"])
    assert session_manager.coordinator.client.create_workout.await_count == 2


async def test_storage_failure_before_submit_never_calls_hevy(session_manager):
    draft = await completed(session_manager)
    session_manager.store.async_save = AsyncMock(side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        await session_manager.finish(draft["id"], draft["revision"])
    session_manager.coordinator.client.create_workout.assert_not_called()
    assert session_manager.snapshot() == draft


async def test_real_atomic_writer_failure_prevents_post(
    hass, session_manager, monkeypatch
):
    draft = await completed(session_manager)

    def fail_write(*args, **kwargs):
        raise WriteError("disk full")

    monkeypatch.setattr(
        "custom_components.hevy.session_store.write_utf8_file_atomic", fail_write
    )
    with pytest.raises(WriteError):
        await session_manager.finish(draft["id"], draft["revision"])
    session_manager.coordinator.client.create_workout.assert_not_called()
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    assert reopened.snapshot() == draft


async def test_stopping_home_assistant_still_persists_before_post(
    hass, session_manager
):
    draft = await completed(session_manager)

    async def inspect_marker(payload):
        reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
        saved = await reopened.store.async_load()
        assert saved["session"]["status"] == "submitting"
        return {"id": "during-shutdown"}

    session_manager.coordinator.client.create_workout.side_effect = inspect_marker
    original_state = hass.state
    hass.set_state(CoreState.stopping)
    try:
        result = await session_manager.finish(draft["id"], draft["revision"])
    finally:
        hass.set_state(original_state)
    assert result["workout_id"] == "during-shutdown"
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    assert reopened.snapshot()["status"] == "finished"


async def test_storage_failure_on_edit_preserves_saved_version(session_manager):
    draft = await completed(session_manager)
    updated = deepcopy(draft)
    updated["title"] = "Not saved"
    session_manager.store.async_save = AsyncMock(side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        await session_manager.update(draft["id"], draft["revision"], updated)
    assert session_manager.snapshot() == draft


async def test_refresh_failure_does_not_turn_success_into_retry(session_manager):
    draft = await completed(session_manager)
    session_manager.coordinator.async_request_refresh.side_effect = HomeAssistantError(
        "offline"
    )
    result = await session_manager.finish(draft["id"], draft["revision"])
    assert result["workout_id"] == "saved-1"
    assert result["status"] == "finished"


async def test_cancelled_submission_is_uncertain(session_manager):
    draft = await completed(session_manager)
    entered = asyncio.Event()

    async def slow_submit(payload):
        entered.set()
        await asyncio.Event().wait()

    session_manager.coordinator.client.create_workout.side_effect = slow_submit
    pending = asyncio.create_task(
        session_manager.finish(draft["id"], draft["revision"])
    )
    await entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert session_manager.snapshot()["status"] == "uncertain"


async def test_receipt_save_failure_does_not_allow_second_post(hass, session_manager):
    draft = await completed(session_manager)
    save = session_manager.store.async_save
    calls = 0

    async def fail_receipt(data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        await save(data)

    session_manager.store.async_save = fail_receipt
    with pytest.raises(OSError):
        await session_manager.finish(draft["id"], draft["revision"])
    assert session_manager.snapshot()["status"] == "finished"
    receipt = await session_manager.finish(draft["id"], draft["revision"])
    assert receipt["workout_id"] == "saved-1"
    session_manager.coordinator.client.create_workout.assert_awaited_once()
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    assert reopened.snapshot()["status"] == "uncertain"


async def test_accounts_are_isolated_and_cancel_survives_restart(hass, session_manager):
    draft = await completed(session_manager)
    other = WorkoutSession(hass, "entry-two", session_manager.coordinator)
    await other.load()
    assert other.snapshot() is None
    with pytest.raises(ServiceValidationError):
        await other.cancel(draft["id"], draft["revision"])
    await session_manager.cancel(draft["id"], draft["revision"])
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    await reopened.load()
    assert reopened.snapshot() is None


async def test_unloaded_manager_rejects_queued_edits(session_manager):
    draft = await completed(session_manager)
    await session_manager.close()
    with pytest.raises(ServiceValidationError, match="unloading"):
        await session_manager.update(draft["id"], draft["revision"], draft)


async def test_services_select_account_and_apply_revision(hass, session_manager):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_API_KEY: "fixture"}, title="Home gym"
    )
    entry.add_to_hass(hass)
    coordinator = session_manager.coordinator
    coordinator.workout_session = session_manager
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    register_session_services(hass)
    board = await hass.services.async_call(
        DOMAIN, "get_workout_board", {}, blocking=True, return_response=True
    )
    assert board["config_entry_id"] == entry.entry_id
    assert board["accounts"] == [
        {"config_entry_id": entry.entry_id, "title": "Home gym"}
    ]
    started = await hass.services.async_call(
        DOMAIN,
        "start_workout",
        {"config_entry_id": entry.entry_id, "routine_id": "r1"},
        blocking=True,
        return_response=True,
    )
    assert started["session"]["status"] == "active"
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "get_workout_board",
            {"config_entry_id": "missing"},
            blocking=True,
            return_response=True,
        )


async def test_routines_include_later_pages_and_notes(session_manager):
    coordinator = session_manager.coordinator
    coordinator.client.get_routines.side_effect = [
        {
            "routines": [{"id": "first", "title": "First", "exercises": []}],
            "page_count": 2,
        },
        {
            "routines": [
                {
                    "id": "second",
                    "title": "Second",
                    "exercises": [
                        {
                            "title": "Bench Press",
                            "exercise_template_id": "t1",
                            "notes": "Slow descent",
                            "sets": [{"reps": 8}],
                        }
                    ],
                }
            ],
            "page_count": 2,
        },
    ]
    await coordinator.fetch_routines()
    assert [routine["id"] for routine in coordinator.routines] == ["first", "second"]
    draft = await session_manager.start("second", None)
    assert draft["exercises"][0]["notes"] == "Slow descent"
    assert coordinator.client.get_routines.call_args.kwargs == {
        "page": 2,
        "page_size": 10,
    }


async def test_repeated_cancel_keeps_writer_locked_until_durable(
    hass, session_manager, tmp_path
):
    import threading

    session_manager.store.path = tmp_path / "session.json"
    draft = await completed(session_manager)
    entered = threading.Event()
    release = threading.Event()
    original_write = session_manager.store._write

    def delayed_write(data):
        if data["session"] and data["session"]["title"] == "Late edit":
            entered.set()
            if not release.wait(timeout=10):
                raise TimeoutError("Test did not release the writer")
        original_write(data)

    session_manager.store._write = delayed_write
    changed = deepcopy(draft)
    changed["title"] = "Late edit"
    pending = asyncio.create_task(
        session_manager.update(draft["id"], draft["revision"], changed)
    )
    await asyncio.to_thread(entered.wait, 5)
    queued_finish = asyncio.create_task(
        session_manager.finish(draft["id"], draft["revision"])
    )
    try:
        assert entered.is_set()
        pending.cancel()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        pending.cancel()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not pending.done()
        assert session_manager.lock.locked()
        assert not queued_finish.done()
        session_manager.coordinator.client.create_workout.assert_not_called()
    finally:
        release.set()
        outcomes = await asyncio.gather(pending, queued_finish, return_exceptions=True)

    assert isinstance(outcomes[0], asyncio.CancelledError)
    assert isinstance(outcomes[1], ServiceValidationError)
    current = session_manager.snapshot()
    assert current["title"] == "Late edit"
    assert current["revision"] == draft["revision"] + 1
    receipt = await session_manager.finish(current["id"], current["revision"])
    assert receipt["status"] == "finished"
    reopened = WorkoutSession(hass, "entry-one", session_manager.coordinator)
    reopened.store.path = session_manager.store.path
    await reopened.load()
    assert reopened.snapshot() == receipt
    assert await reopened.finish(current["id"], current["revision"]) == receipt
    session_manager.coordinator.client.create_workout.assert_awaited_once()
