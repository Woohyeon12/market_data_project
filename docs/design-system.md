# Design System

## Purpose

This file is the durable design baseline for the BTC research dashboard. Each automated design pass should read this file first, then record a concrete change in `docs/ui-iteration-log.md`.

## Source Of Truth

- Main UI component: `frontend/components/ResearchDashboard.tsx`
- Shared styling: `frontend/app/globals.css`
- Model experiment results: `docs/model-experiment-log.md`
- UI iteration history: `docs/ui-iteration-log.md`

Note: the current project uses `frontend/components/`, not `src/components/`.

## Product Character

- Institution-grade, calm, and information-dense
- Data-first before decoration
- Clean spacing and clear grouping over visual novelty
- One primary accent family with restrained positive/negative color use

## Visual Tokens

- Radius: 8px maximum for cards, buttons, and pills
- Base surfaces: white panels on a muted light background
- Accent: green for positive or active emphasis
- Warning: red for drawdown, negative return, and risk states
- Supporting neutral: muted gray copy for metadata and helper text

## Layout Rules

- The first screen should surface usable research immediately.
- Repeated metrics belong in flat grids with stable heights.
- Long model metadata should be grouped by meaning, not poured into one undifferentiated stat wall.
- Mobile layout must collapse to one column without text clipping or badge overflow.
- Primary charts should remain readable without depending on hover.

## Model Page Rules

- Primary performance belongs in the hero region: Sharpe, return, drawdown, win rate, split stability.
- Validation, regime, turnover, and feature-selection metadata are secondary layers and should be visually grouped.
- Execution controls that can cap downside, such as minimum hold, cooldown, and stop-loss floors, must stay visible without forcing the user into a tooltip hunt.
- If the latest completed experiment is not yet reflected in the imported run summaries, data synchronization takes priority over visual polish.
- Unknown values should render as `n/a` or `off`, never stale historical numbers.

## Current Visual Debt

- The model showcase detail area is too dense because execution, validation, and regime metadata are mixed into one large stat grid.
- Experiment freshness is easy to miss because imported run timing is buried inside secondary details.
- The dashboard depends on successful Kaggle output import; when download paths nest unexpectedly, freshness silently degrades.
- Risk controls are easy to miss when they are buried inside long technical metadata instead of surfaced as first-class decision context.

## Iteration Priorities

1. Data synchronization from completed experiments into the dashboard
2. Model page information hierarchy and readability
3. Dark/light contrast polish and spacing refinement
4. Interaction clarity such as tooltips, labels, and hover affordances
