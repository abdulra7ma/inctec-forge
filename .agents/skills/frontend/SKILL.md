---
name: frontend
description: House patterns for TypeScript/React frontends — structure, data fetching with TanStack Query, generated API types, forms, state, design-system usage, accessibility and performance. Use for any UI code.
---
# Frontend patterns

## Structure (feature-first)
```
src/
  app/            # routing, providers, layout shell
  features/<x>/   # components, hooks, api.ts, types — everything for one feature
  components/ui/  # design-system primitives (no business logic)
  lib/            # api client, utils, formatting
  api/generated/  # OpenAPI-generated types/client — never edit by hand
```

## Data
- Generate types from backend OpenAPI (`openapi-typescript` / `orval`). Regenerating with no contract change is T0.
- All server state through TanStack Query: query keys from a factory (`deviceKeys.detail(id)`), sensible `staleTime`, invalidate on mutation success, optimistic updates only with rollback.
- No `useEffect` for fetching. No duplicating server state into global stores.

## Components
- Small, typed props, no `any`. Composition over configuration flags.
- Every data view handles: loading (skeleton), empty (helpful message + action), error (message + retry), success.
- Forms: `react-hook-form` + `zod` schema mirroring backend constraints; disable submit while pending; show server errors inline.

## Design system
- Only tokens (colours, spacing, radius, type scale) from the theme; no magic numbers or hex values in components.
- Reuse `components/ui` primitives; new primitive → discuss with UX/UI first.

## Accessibility (non-negotiable)
Semantic HTML, every input labelled, keyboard reachable, visible focus, `aria-live` for async status, contrast AA.

## Performance
Route-level code splitting, virtualise lists > 100 rows, memoise only after profiling, images sized and lazy.

## Checks before done
`pnpm lint && pnpm typecheck && pnpm test` · manual pass in browser at mobile and desktop widths · no console errors.
