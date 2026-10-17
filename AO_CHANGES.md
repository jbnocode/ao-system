# AO CRM changes on top of frappe/crm 1.88.0

Frontend only. Base: frappe/crm `main` at 0baa1e8 (v1.88.0), running on Frappe 16.

- Deal page: new tabs Quotes, Applications, Policies (`pages/Deal.vue`, `pages/MobileDeal.vue`, `components/Activities/Activities.vue`, `components/Activities/ActivityHeader.vue`, new `components/Activities/InsuranceRecords.vue`).
- New page Automations at `/crm/automations` that reuses the Settings Workflow Automations component (`pages/Automations.vue`, `router.js`, `utils/navigation.js`).

Not in this repo (stored in the site database, back up the site to keep them): the Insurance Quote / Application / Policy doctypes, custom lead and deal fields, field layouts, lead and deal stages, and the three Automation Flows.
