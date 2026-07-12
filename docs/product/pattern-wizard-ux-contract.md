# Pattern Wizard UX Contract

A pattern wizard must hide implementation internals from Simple Mode and make the happy path obvious.

## Required structure

1. Intro panel: user-facing scenario, not technical objects.
2. Stepper: stable steps for request, lookup, payload/response, preview and save.
3. Preview: no database writes and clear errors.
4. Save: creates a disabled integration or requires an explicit operator action.
5. Success: links to created integration, saved test and Timeline/run history.
6. Advanced details: low-level artifacts are collapsed and marked as advanced.
7. Run test panel: dry-run or manual test before production enable.

## Shared components

The common layer lives in `frontend/src/features/pattern-wizards/shared/`:

- `PatternWizardShell.tsx`
- `PatternIntroPanel.tsx`
- `PatternStepper.tsx`
- `PatternPreviewPanel.tsx`
- `PatternSaveSuccess.tsx`
- `PatternErrorSummary.tsx`
- `PatternAdvancedDetails.tsx`
- `PatternRunTestPanel.tsx`

Do not refactor all wizards at once. Migrate one or two patterns per task and preserve their existing API behavior.
