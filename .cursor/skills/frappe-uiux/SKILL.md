---
name: frappe-uiux
description: >-
  MANDATORY for every Vue UI build or edit in this CRM (pages, dialogs, forms,
  settings, Deal/Case, new features). Prefer frappe-ui and @framework/ui; match
  existing CRM density and patterns. Do not ship custom card/marketing layouts.
---

# Frappe UI/UX (this CRM) — required for every build

**Read and follow this skill before any UI add/edit in `frontend/`.**  
Applies to new pages, settings tabs, dialogs, lists, and refactors — not only when the user mentions design.

## Stack

| Layer | Package | Use for |
|---|---|---|
| Components + resources | `frappe-ui` | `Button`, `Dialog`, `FormControl`, `Combobox`, `Badge`, `Avatar`, `Tabs`, `Dropdown`, `Switch`, `Tooltip`, `call`, `createResource`, `createListResource`, `createDocumentResource`, `toast` |
| Framework extras | `@framework/ui` | Telemetry, onboarding, and other framework UI already used in-app |

Dependencies: [`frontend/package.json`](../../../frontend/package.json) (`frappe-ui`, `@framework/ui`).

## Rules (non-negotiable)

1. **Prefer library components** — do not invent parallel buttons, inputs, modals, selects, or toasts.
2. **Match density** — follow Deal, Settings, and list pages: compact rows, `text-p-sm` / `text-ink-gray-*`, `border-outline-gray-modals`, `surface-*` tokens.
3. **Forms** — `FormControl` for fields; `Combobox` / `FormControl type="select"` for known option lists (never free-text for enums like timezone); `ErrorMessage` for errors; Dialog `#actions` for primary/cancel.
4. **Settings vs page** — account / OAuth / provider integrations belong in **Settings** (`SettingsLayoutBase` + tab in `Settings.vue`). Operational surfaces (lists, builders, booking page content) are full pages with `LayoutHeader`.
5. **Data** — `call` / `createResource` / `createListResource` for server I/O; no ad-hoc `fetch` for Frappe APIs.
6. **Feedback** — `toast.success` / `toast.error` / `toast.info` from `frappe-ui`.
7. **Icons** — existing `~icons/lucide/*` or app icons under `frontend/src/components/Icons/`.
8. **Do not** add card-heavy marketing layouts, custom “picker tiles” when `FormControl`/`Combobox` fits, new CSS frameworks, or raw `<input>`/`<select>` where library controls fit.
9. **Settings shell** — use `SettingsLayoutBase` for settings tabs (title, description, `header-actions`, `content`). Prefer stacked `FormControl` + `Switch` rows like `AiSettings` / `PreferencesSettings`.
10. **No settings “cards”** — do **not** wrap settings groups in `rounded-lg border border-outline-gray-modals … p-4` containers. Use section titles (`text-base-semibold text-ink-gray-9`), helper text (`text-p-sm text-ink-gray-6`), and `space-y-4` / `justify-between` rows only (see Preferences + Calendar settings).

## Checklist before shipping UI

- [ ] Used `frappe-ui` primitives for controls and feedback
- [ ] Integrations / connect-account flows live under Settings (agents + managers when personal)
- [ ] Enums (timezone, provider, status) use select/Combobox with real options
- [ ] Density and tokens match an existing Settings or list page
- [ ] No bordered card wrappers around settings field groups
- [ ] No one-off marketing cards or custom form chrome

## Reference pages

- Deal / Case: `frontend/src/pages/Deal.vue`
- Settings: `frontend/src/components/Settings/` + `SettingsLayoutBase.vue`
- Timezone Combobox: `frontend/src/components/Settings/PreferencesSettings.vue` (`frappe.core.doctype.user.user.get_timezones`)
- Calendar connect: `frontend/src/components/Settings/GoogleCalendarSettings.vue`
- Booking page: `frontend/src/pages/Booking.vue`
- Booking integrations: `frontend/src/components/Settings/BookingSettings.vue`
- Insurance lists: `frontend/src/components/Activities/InsuranceRecords.vue`
- Life pack settings: `frontend/src/components/Settings/LifeInsuranceSettings.vue`

See [reference.md](./reference.md) for common imports.
