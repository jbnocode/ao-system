import CalendarIcon from '@/components/Icons/CalendarIcon.vue'
import ContactsIcon from '@/components/Icons/ContactsIcon.vue'
import DealsIcon from '@/components/Icons/DealsIcon.vue'
import LeadsIcon from '@/components/Icons/LeadsIcon.vue'
import NoteIcon from '@/components/Icons/NoteIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import TaskIcon from '@/components/Icons/TaskIcon.vue'
import LucideLayoutDashboard from '~icons/lucide/layout-dashboard'
import LucideCalendarCheck from '~icons/lucide/calendar-check'
import LucideFileText from '~icons/lucide/file-text'
import LucideFolderOpen from '~icons/lucide/folder-open'
import LucidePhoneCall from '~icons/lucide/phone-call'
import LucideTextCursorInput from '~icons/lucide/text-cursor-input'
import LucideMessageSquare from '~icons/lucide/message-square'
import LucideWorkflow from '~icons/lucide/workflow'
import LucideMegaphone from '~icons/lucide/megaphone'
import LucideShield from '~icons/lucide/shield'
import LucideSparkles from '~icons/lucide/sparkles'
import router from '@/router'
import { getSettings } from '@/stores/settings'
import { usersStore } from '@/stores/users'

export const navigationItems = [
  {
    label: 'Dashboard',
    icon: LucideLayoutDashboard,
    route: 'Dashboard',
    desktopOnly: true,
  },
  { label: 'Leads', icon: LeadsIcon, route: 'Leads' },
  { label: 'Deals', icon: DealsIcon, route: 'Deals', lifeLabel: 'Cases' },
  {
    label: 'Quoting',
    icon: LucideFileText,
    route: 'Quoting',
    group: 'insurance',
  },
  {
    label: 'Policies',
    icon: LucideShield,
    route: 'Policies',
    group: 'insurance',
  },
  {
    label: 'Documents',
    icon: LucideFolderOpen,
    route: 'Documents',
    group: 'insurance',
  },
  { label: 'Contacts', icon: ContactsIcon, route: 'Contacts' },
  { label: 'Tasks', icon: TaskIcon, route: 'Tasks' },
  { label: 'Notes', icon: NoteIcon, route: 'Notes' },
  {
    label: 'AI',
    icon: LucideSparkles,
    route: 'AI',
  },
  {
    label: 'AI Call',
    icon: LucidePhoneCall,
    route: 'Dialer',
    group: 'tools',
  },
  {
    label: 'Phone',
    icon: PhoneIcon,
    route: 'Human Dialer',
    group: 'tools',
  },
  {
    label: 'Text',
    icon: LucideMessageSquare,
    route: 'Text Inbox',
    group: 'tools',
  },
  {
    label: 'Automations',
    icon: LucideWorkflow,
    route: 'Automations',
    desktopOnly: true,
    group: 'tools',
  },
  {
    label: 'Campaigns',
    icon: LucideMegaphone,
    route: 'Campaigns',
    desktopOnly: true,
    group: 'tools',
  },
  {
    label: 'Forms',
    icon: LucideTextCursorInput,
    route: 'Forms',
    desktopOnly: true,
    group: 'tools',
  },
  {
    label: 'Calendar',
    icon: CalendarIcon,
    route: 'Calendar',
    desktopOnly: true,
    group: 'tools',
  },
  {
    label: 'Booking',
    icon: LucideCalendarCheck,
    route: 'Booking',
    desktopOnly: true,
    group: 'tools',
  },
]

export function getNavigationItems({ mobile = false } = {}) {
  const lifeMode = !!getSettings().settings.value?.life_agency_mode
  const { isManager } = usersStore()
  let insuranceDividerPlaced = false
  let toolsDividerPlaced = false
  return navigationItems
    .filter(
      (item) =>
        router.hasRoute(item.route) &&
        (!mobile || !item.desktopOnly) &&
        (!item.managerOnly || isManager()),
    )
    .map((item) => {
      let dividerBefore = false
      if (item.group === 'insurance' && !insuranceDividerPlaced) {
        insuranceDividerPlaced = true
        dividerBefore = true
      }
      if (item.group === 'tools' && !toolsDividerPlaced) {
        toolsDividerPlaced = true
        dividerBefore = true
      }
      return {
        ...item,
        label: lifeMode && item.lifeLabel ? item.lifeLabel : item.label,
        dividerBefore,
      }
    })
}
