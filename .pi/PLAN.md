# CRM Development Plan

> **This file**: Current and upcoming work only. No completed phases.  
> **Completed phases**: [ARCHIVE.md](./ARCHIVE.md)  
> **Stable API contracts**: [SPEC.md](./SPEC.md)

### AO — Life Case hub (shipped)

Person-first Cases on top of CRM Deal (`life_agency_mode`), Household contacts +
relationship, Quote/App/Policy journey, Deal assistant. See [AO_CHANGES.md](../AO_CHANGES.md)
and `crm/life/`. UI work: [`.cursor/skills/frappe-uiux/SKILL.md`](../.cursor/skills/frappe-uiux/SKILL.md).

---

## Insurance ops nav — Quoting / Policies / Documents

> **Product track (can ship in parallel with Phase 3B).** Sidebar divider + three
> list pages. Case remains system of record; these pages are cross-Case work queues.
> No company-branded product seed. AI quoting uses a generic indicative catalog →
> save as Insurance Quote on the Case (live carrier API = later / partner).

### Decisions (locked)

| Question | Recommendation |
|---|---|
| Applications | **Tab under Quoting** (not its own nav item) — quote→app is one sales motion |
| Divider position | **After Cases** (primary insurance ops), before Contacts — not buried in Tools |
| Documents scope (v1) | **CRM Deal attachments only**; Lead/Contact files later |
| Quoting nav label | **Quoting** (verb/work area; page title can say “Quotes”) |
| AI quoting | CTA on Quoting + existing AI chat; catalog → **Save to Case**; label rates indicative |
| Renewals / commissions / e-sign | **Out of v1** |

### Nav shape

```
Dashboard
Leads
Cases (Deals)
── divider ──
Quoting          ← Quotes list + Applications tab
Policies         ← Policy book list
Documents        ← Files linked to Cases
Contacts
Tasks
Notes
AI
── divider (tools) ──
…
```

### Page contents (v1)

**Quoting** (`/crm/quoting`)

- Tab **Quotes**: list `Insurance Quote` — filters status / carrier / date; row → Case `#quotes`
- Tab **Applications**: list `Insurance Application` — row → Case `#applications`
- Empty state: open a Case → Quotes tab; optional “Ask AI” → AI route
- No live multi-carrier engine in v1

**Policies** (`/crm/policies`)

- List `Insurance Policy` — filters In Force / Pending / Lapsed / Cancelled
- Summary chips (counts by status)
- Row → Case `#policies`
- Renewals 30/60/90 = phase 2 (needs anniversary/renewal fields)

**Documents** (`/crm/documents`)

- Index of File rows attached to CRM Deal
- Filters: Case, date, uploader; download / open Case
- Upload requires picking a Case (no orphans)
- Soft tags later: Illustration · App packet · ID · Policy delivery
- Keep **Forms** under Tools (intake builders ≠ file vault)

### Build order

1. Nav group + routes + empty shells (frappe-ui list density)
2. Policies list + Case deep-link
3. Quoting (Quotes + Applications tabs) + Case deep-link
4. Documents index (Deal files) + open Case
5. Wire AI “save quotes to Case” from Quoting CTA / chat (catalog, indicative)
6. Phase 2: renewals queue, richer doc tags, Lead files, partner quoter if needed

### Checklist

- [x] `navigation.js` — new `group: 'insurance'` divider after Cases
- [x] Routes: Quoting, Policies, Documents
- [x] `Policies.vue` list
- [x] `Quoting.vue` (Quotes + Applications tabs)
- [x] `Documents.vue` (Deal-linked files)
- [x] Deep-link to Deal hash tabs
- [x] Nav + unit tests
- [ ] AI “save quotes to Case” from Quoting CTA / chat (catalog, indicative)
- [ ] UI: [frappe-uiux skill](../.cursor/skills/frappe-uiux/SKILL.md)

### Non-goals (v1)

- Standalone Insurance tutorial hub
- Open/public carrier quote APIs
- Company-specific product catalogs in seed data
- Commission / certificate / ACORD modules

---

## Implementation Order

| Order | Phase | Scope | Status |
|---|---|---|---|
| ~~1~~ | ~~Phase 3A — FieldLayout standalone mode~~ | ~~Small~~ | ✅ Done — [see ARCHIVE](./ARCHIVE.md#phase-3a--fieldlayout-standalone-mode) |
| ~~2~~ | ~~Phase 2 — formDialog()~~ | ~~Medium~~ | ✅ Done — [see ARCHIVE](./ARCHIVE.md#phase-2--formdialog) |
| **—** | [Insurance ops nav](#insurance-ops-nav--quoting--policies--documents) | Product (lists + divider) | 📋 Planned — parallel OK |
| **3** | [Phase 3B — Full decouple (Grid independent)](#phase-3b--full-decouple-grid-independent) | Structural refactor | 🔜 Next (scripting track) |
| **4** | [Phase 4 — getMeta single source of truth](#phase-4--getmeta-single-source-of-truth) | Architectural cleanup | After 3B |
| **5** | [Phase 6 — More Capabilities (selected)](#phase-6--more-capabilities-selected) | Feature expansion | After 4 |
| **6** | [Phase 5 — Scripting DX Rethink](#phase-5--scripting-dx-rethink) | Syntax/API redesign | Last |

---

## Phase 3B — Full Decouple (Grid Independent)

> **Do after Phase 2 is stable. Structural refactor.**

### Goal

Make `Grid` work as a standalone component that does not depend on inject/provide chains from `FieldLayout → Field.vue`. Make `FieldLayout` and `Field` use a single unified context instead of 6+ separate inject keys.

### Why after Phase 2

Phase 3B touches `Field.vue` and `Grid.vue` — the riskiest components in the codebase (every form surface uses them). Phase 2 is now merged and stable.

### Current inject/provide chain (to eliminate)

```
FieldLayout provides:     data, hasTabs, doctype, preview, isGridRow
Field.vue provides:       triggerOnChange, triggerButton, triggerOnRowAdd,
                          triggerOnRowRemove, fieldPropertyOverrides
Field.vue provides:       (also) parentFieldname — for Grid
Grid.vue provides:        parentDoc, fieldPropertyOverrides, parentFieldname
GridRowModal provides:    parentFieldname
```

If Grid is used outside this chain, all injects fall back to defaults (empty functions/objects) and scripting silently doesn't work.

### Proposed approach

**`useFieldLayout(doctype, options)` composable** — encapsulates all wiring. One provide/inject key replaces all 6+.

```js
// src/composables/useFieldLayout.js
export function useFieldLayout(doctype, options = {}) {
  // options.docname         — for existing doc (triggers script loading via useDocument)
  // options.doc             — for standalone mode (local reactive data, no useDocument)
  // options.readonly        — all fields read-only
  // options.onFieldChange   — callback instead of script hooks

  const fieldPropertyOverrides = reactive({})

  return {
    context: {
      doc,
      doctype,
      fieldPropertyOverrides,
      triggerOnChange,
      triggerButton,
      triggerOnRowAdd,
      triggerOnRowRemove,
      setFieldProperty: (target, property, value, rowName) => { ... },
      removeFieldProperty: (target, property, rowName) => { ... },
    }
  }
}
```

`FieldLayout`, `Field.vue`, `Grid.vue` all inject `'fieldLayoutContext'` instead of 6 separate keys. External consumers that don't use `useFieldLayout` get safe no-op defaults automatically.

### Decisions needed before starting

1. **Should Grid work completely without any FieldLayout context?**
   - If yes: Grid needs its own script-loading path for child doctype scripts.
   - If no: Grid without FieldLayout context = display only, no scripting.
   - Recommendation: "no" for now.

2. **Should FieldLayout continue to accept `tabs` as a prop, or should it fetch its own layout?**
   - Currently all callers fetch tabs via `createResource` and pass them in.
   - Moving fetch inside FieldLayout would make it self-contained but less flexible.
   - Ask before deciding.

### Files

| File | Change |
|---|---|
| `frontend/src/composables/useFieldLayout.js` | **New** — unified composable |
| `frontend/src/components/FieldLayout/FieldLayout.vue` | Use `useFieldLayout`; provide single context key |
| `frontend/src/components/FieldLayout/Field.vue` | Inject `'fieldLayoutContext'`; remove 6 separate injects |
| `frontend/src/components/Controls/Grid.vue` | Inject `'fieldLayoutContext'` with safe fallback |
| `frontend/src/components/Controls/GridRowModal.vue` | Simplify — propagate context, remove `parentFieldname` prop |

### Checklist

- [ ] Decide Grid standalone behaviour (display only vs full scripting)
- [ ] Decide whether FieldLayout fetches its own layout
- [ ] `useFieldLayout.js` composable
- [ ] `FieldLayout.vue` — provide `fieldLayoutContext`; keep Phase 3A `context` prop working
- [ ] `Field.vue` — inject `fieldLayoutContext`; remove `isGridRow` branch
- [ ] `Grid.vue` — inject `fieldLayoutContext`; fallback to props-only mode
- [ ] `GridRowModal.vue` — simplify
- [ ] Regression test: all existing forms (Lead, Deal, Contact, Organization pages, all modals)

---

## Phase 4 — getMeta Single Source of Truth

> **After Phase 3B. Completes the architectural cleanup.**

### Goal

1. `getMeta.getField(fieldname)` is the single place that clones, applies overrides, and transforms (Select→array, Link→User).
2. Layout APIs (`get_fields_layout`, `get_sidepanel_sections`) return fieldname strings only + a perm overrides map — no embedded `field.as_dict()`.
3. Rendering components call `getMeta.getField()` instead of doing their own transforms.
4. `getFields()` no longer filters `hidden` fields — callers decide.

### Why after Phase 3B

Phase 3B gives a single context object (`useFieldLayout`) as the wiring point. Routing all field resolution through `getMeta.getField()` can happen there in one place.

### What remains (not done in Phase 1)

- `getFields()` in `meta.js` still mutates `doctypesMeta` field objects
- Layout APIs still return full `field.as_dict()` per field (redundant)
- `getFields()` still has `!f.hidden` filter
- `processField()` is tested but not wired into rendering

### Checklist

- [ ] Phase 3B must be merged first
- [ ] `meta.js` — `getField(fieldname, options)` method: clones + applies perm overrides + script overrides + transforms
- [ ] `meta.js` — `getFields()` uses `getField()` internally; removes `!f.hidden` filter
- [ ] `useFieldLayout.js` — routes field resolution through `getMeta.getField()`
- [ ] `crm_fields_layout.py` — `get_fields_layout` returns `{ tabs: [...fieldname strings...], perm_overrides: {...} }`
- [ ] Update all callers of layout APIs to handle new format
- [ ] `ColumnSettings`, `ViewControls`, `KanbanSettings` — add explicit `hidden` filter
- [ ] Remove redundant Select/Link transforms from `SidePanelLayout.vue`

---

## Phase 6 — More Capabilities (selected)

> **After Phase 4. Feature expansion on clean foundation.**

### 6A — Programmatic layout manipulation

Inject virtual fields and sections that exist only at runtime — not in the DocType:

```js
class CRMLead {
  onLoad() {
    this.addField('basic_section', {
      fieldname: '_score_display',
      fieldtype: 'HTML',
      label: 'Lead Score',
      after: 'status',
    })

    this.addSection({
      name: '_ext_section',
      label: 'Extension Data',
      after: 'contact_section',
      fields: [
        { fieldname: '_ext_field1', fieldtype: 'Data', label: 'Custom Field' },
      ],
    })
  }
}
```

Virtual fields are managed in a separate `virtualFields` map on the document context.

### 6B — `usePermLevel` composable

Move perm level restriction logic client-side. Currently `handle_perm_level_restrictions` in `crm_fields_layout.py` modifies `read_only`/`hidden` on the server. This means the client must re-fetch the layout to reflect permission changes.

A `usePermLevel(doctype)` composable would:
- Fetch the user's permitted perm levels per doctype (once, cached)
- Expose `getPermOverrides(fields)` computing restrictions client-side
- Pass result as `permOverrides` into `getMeta.getField()`

**Depends on Phase 4.**

### Checklist

- [ ] Phase 4 must be merged first
- [ ] 6A: `addField(sectionName, fieldDef)` prototype method in `script.js`
- [ ] 6A: `addSection(sectionDef)` prototype method
- [ ] 6A: `virtualFields` map on document context
- [ ] 6A: Layout resolution merges virtual fields
- [ ] 6B: `usePermLevel(doctype)` composable
- [ ] 6B: `crm_fields_layout.py` — return raw perm data instead of modifying fields
- [ ] 6B: Wire into `getMeta.getField()` via Phase 4

---

## Phase 5 — Scripting DX Rethink

> **Last. Do once the full capability set (Phases 3B–6) is known and stable.**

### Why last

- The syntax should reflect all capabilities — not a subset.
- A syntax change is a breaking change for script authors — do it once.
- `setFieldProperty` works well enough in the meantime.

### Ideas (not decided — decide with maintainer)

#### Builder / chainable API

```js
this.field('annual_revenue').hide()
this.field('status').setOptions('New\nOpen\nClosed')
this.field('email').makeRequired().setLabel('Work Email')
this.section('financial_section').collapse()
this.fields(['email', 'phone']).makeRequired()
```

#### Declarative rules

```js
class CRMLead {
  rules = {
    lost_reason: {
      hidden: (doc) => doc.status !== 'Lost',
      reqd:   (doc) => doc.status === 'Lost',
    },
  }
}
```

#### Reactive shortcuts

```js
this.field('lost_reason')
  .showWhen(() => this.doc.status === 'Lost')
  .requireWhen(() => this.doc.status === 'Lost')
```

### Backwards compatibility

`setFieldProperty`, `setFieldProperties`, `removeFieldProperty`, `getField`, `formDialog` continue to work. New syntax is additive.

---

## Deferred / Backlog

| Feature | Notes |
|---|---|
| List view scripting | Column visibility, custom cell renderers, bulk action hooks |
| Inter-script communication | `this.emit('event', data)` / `this.on('event', handler)` across scripts |
| Conditional field injection | Variant of 6A — scripts inject fields only when a condition is true |

---

## Design Principles

1. **Generic-first** — No CRM-specific assumptions in FieldLayout, Grid, Field, or the scripting engine. CRM-specific behaviour lives in Form Script records.

2. **Ask before deciding** — Document the options, pick the right one with the maintainer. Especially for: prop names, composable APIs, breaking changes.

3. **Props > inject for public API** — Components accept props for their core inputs. inject/provide is for internal wiring only.

4. **Test pure logic first** — Extract functions to utility files, write unit tests, then wire into components. Vitest is already set up (118 tests, ~250ms).

5. **Incremental, independently shippable** — Each phase merges and is usable on its own.

6. **Extensibility via records** — Third-party apps extend via `CRM Form Script` records. No source code modification. Multiple scripts per doctype run sequentially; last-write-wins for overrides.
