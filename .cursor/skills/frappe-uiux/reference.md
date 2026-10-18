# frappe-ui common imports

```js
import {
  Avatar,
  Badge,
  Button,
  Combobox,
  Dialog,
  Dropdown,
  ErrorMessage,
  FormControl,
  Switch,
  Tabs,
  Tooltip,
  call,
  createResource,
  createListResource,
  createDocumentResource,
  toast,
} from 'frappe-ui'
```

## Dialog vs page vs settings

| Use | When |
|---|---|
| `Dialog` | Short task, confirm, create-one-record, assistant, settings subsections |
| Full page + `LayoutHeader` | Ongoing work (timeline, lists, kanban, Case workspace, Booking page) |
| Settings tab + `SettingsLayoutBase` | Configuration and account connections (Calendar, Booking integrations, AI, Telephony) |

## Timezones

Use Frappe’s list, not a free-text field:

```js
const timeZones = createResource({
  url: 'frappe.core.doctype.user.user.get_timezones',
  cache: 'TimeZones',
  auto: true,
})

function getTimezoneOptions() {
  return timeZones.data?.timezones.map((tz) => ({ label: tz, value: tz })) || []
}
```

```vue
<Combobox v-model="form.timezone" :options="getTimezoneOptions()" />
```

## Integrations (agents + managers)

Personal account connections (Google Calendar / Meet, Zoom) must be available to Sales User and managers in Settings — not buried only on an operational page. System-wide OAuth client credentials stay System Manager–only when applicable.

## Life / Case UI

When `life_agency_mode` is on, prefer person/household language (Cases, Household) and hide B2B org chrome. Still use the same frappe-ui primitives.
