# Testing Hevy 1.4

Use this checklist to verify the workout card on your Home Assistant installation. Back up the integration before updating so you can roll back if needed.

## Install

1. Back up the existing `config/custom_components/hevy` folder in your Home Assistant installation.
2. Update to 1.4.0 through HACS, or extract the release source ZIP and replace that folder with its `custom_components/hevy` folder. Keep your existing Home Assistant configuration.
3. Restart Home Assistant.
4. In your profile, enable Advanced mode. Open **Settings → Dashboards → Resources** and add `/hevy/hevy-workout-card.js?version=1.4.0` as a **JavaScript Module**. If this resource already exists, update its URL and reload the browser.
5. Add a manual dashboard card with:

```yaml
type: custom:hevy-workout-card
```

Home Assistant 2024.7 or later is required. With more than one Hevy account configured, select the account on the card. The visual card editor lets you pick favorite routines and exercises.

## Try the workout flow

1. Start one of your routines. Confirm the exercises, weights, reps, and units match what you expect.
2. Change a weight and rep count, add or remove a set, and check off a set. Wait for **Saved in Home Assistant**.
3. Refresh the tablet. Open the card on another device, then restart Home Assistant. Confirm the same draft and checked sets return.
4. Try an exercise from the catalog. For a timed or distance exercise, confirm the relevant fields and units appear.
5. When you're ready to log a workout, check the sets you actually completed. Choose **Finish** and review the confirmation. This sends a real workout to your Hevy account. Confirm it appears once with only the checked sets and correct measurements.
6. Check the native Hevy calendar in Home Assistant. The saved workout should appear after the integration refreshes.

You can test everything before step 5 without creating a workout in Hevy. Clear the draft to discard it. A mistaken submitted workout must be deleted in Hevy.

If submission is uncertain, check Hevy before using recovery controls. Choose retry only when the workout is absent. No automatic retry is made. Workout drafts are shared by cards using the same Hevy integration entry. The second device reloads a newer saved revision before it can overwrite another device's edits.

The routine suggestion uses existing rotation data. Hevy's public create-workout API does not attach logs to routines, so a card-created workout does not automatically advance that rotation.

## Roll back

Restore your backed-up `custom_components/hevy` folder and restart Home Assistant. Remove the workout card or its resource while using 1.3. Saved draft files under `.storage/hevy.workout.*` can remain for a later test build. Rolling back does not remove workouts already sent to Hevy.
