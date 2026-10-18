<template>
  <div
    class="relative h-full overflow-hidden"
    :class="[
      side == 'right' ? 'border-l' : 'border-r',
      !sidebarResizing && 'transition-[width] duration-300 ease-in-out',
    ]"
    :style="{ width: `${displayedWidth}px` }"
  >
    <div
      class="h-full min-w-0 transition-opacity duration-300 ease-in-out"
      :class="[
        attrs.class,
        collapsed ? 'pointer-events-none opacity-0' : 'opacity-100',
        // Right panels grow/shrink from the viewport edge, not the content seam.
        side == 'right' ? 'absolute inset-y-0 right-0' : '',
      ]"
      :style="{ width: `${sidebarWidth}px` }"
    >
      <slot
        v-bind="{
          sidebarResizing,
          sidebarWidth,
          collapsed,
          collapse,
          expand,
          toggle,
        }"
      />
    </div>

    <div
      v-if="collapsible"
      class="absolute inset-y-0 flex w-12 flex-col items-center pt-2 transition-opacity duration-300 ease-in-out"
      :class="[
        // Collapsed rail hugs the outer edge (right for right sidebars).
        side == 'right' ? 'right-0' : 'left-0',
        collapsed ? 'opacity-100' : 'pointer-events-none opacity-0',
      ]"
    >
      <Button
        :tooltip="__('Expand')"
        variant="ghost"
        :icon="expandIcon"
        @click="expand"
      />
    </div>

    <div
      v-show="!collapsed"
      class="absolute z-10 h-full w-1 cursor-col-resize bg-surface-gray-4 opacity-0 transition-opacity hover:opacity-100"
      :class="{
        'opacity-100': sidebarResizing,
        'left-0': side == 'right',
        'right-0': side == 'left',
      }"
      @mousedown="startResize"
    />
  </div>
</template>
<script setup>
import { Button } from 'frappe-ui'
import { computed, ref, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })

const DEFAULT_COLLAPSED_KEY = 'detailSidePanelCollapsed'
const DEFAULT_WIDTH_KEY = 'sidebarWidth'
const COLLAPSED_WIDTH = 48

const props = defineProps({
  defaultWidth: { type: Number, default: 352 },
  minWidth: { type: Number, default: 16 * 16 },
  maxWidth: { type: Number, default: 30 * 16 },
  side: { type: String, default: 'left' },
  parent: { type: Object, default: null },
  collapsible: { type: Boolean, default: false },
  /** localStorage key for collapsed state (isolate panels that share Resizer). */
  collapsedStorageKey: { type: String, default: DEFAULT_COLLAPSED_KEY },
  /** localStorage key for width. */
  widthStorageKey: { type: String, default: DEFAULT_WIDTH_KEY },
})

const attrs = useAttrs()
const sidebarResizing = ref(false)
const sidebarWidth = ref(getInitialWidth())
const collapsed = ref(props.collapsible && getInitialCollapsed())

const displayedWidth = computed(() =>
  collapsed.value ? COLLAPSED_WIDTH : sidebarWidth.value,
)

const expandIcon = computed(() =>
  props.side === 'right'
    ? 'lucide-panel-right-open'
    : 'lucide-panel-left-open',
)

function getInitialWidth() {
  let storedWidth = Number(localStorage.getItem(props.widthStorageKey))
  if (
    storedWidth &&
    storedWidth >= props.minWidth &&
    storedWidth <= props.maxWidth
  ) {
    return storedWidth
  }
  return props.defaultWidth
}

function getInitialCollapsed() {
  return localStorage.getItem(props.collapsedStorageKey) === '1'
}

function persistCollapsed(value) {
  localStorage.setItem(props.collapsedStorageKey, value ? '1' : '0')
}

function collapse() {
  if (!props.collapsible) return
  collapsed.value = true
  persistCollapsed(true)
}

function expand() {
  if (!props.collapsible) return
  collapsed.value = false
  persistCollapsed(false)
}

function toggle() {
  if (collapsed.value) expand()
  else collapse()
}

function startResize() {
  document.addEventListener('mousemove', resize)
  document.addEventListener('mouseup', () => {
    document.body.classList.remove('select-none')
    document.body.classList.remove('cursor-col-resize')
    document.querySelectorAll('.select-text1').forEach((el) => {
      el.classList.remove('select-text1')
      el.classList.add('select-text')
    })
    localStorage.setItem(props.widthStorageKey, sidebarWidth.value)
    sidebarResizing.value = false
    document.removeEventListener('mousemove', resize)
  })
}
function resize(e) {
  sidebarResizing.value = true
  document.body.classList.add('select-none')
  document.body.classList.add('cursor-col-resize')
  document.querySelectorAll('.select-text').forEach((el) => {
    el.classList.remove('select-text')
    el.classList.add('select-text1')
  })
  sidebarWidth.value =
    props.side == 'left' ? e.clientX : window.innerWidth - e.clientX

  let gap = props.parent ? distance() : 0
  sidebarWidth.value = sidebarWidth.value - gap

  // snap to props.defaultWidth
  let range = [props.defaultWidth - 10, props.defaultWidth + 10]
  if (sidebarWidth.value > range[0] && sidebarWidth.value < range[1]) {
    sidebarWidth.value = props.defaultWidth
  }

  if (sidebarWidth.value < props.minWidth) {
    sidebarWidth.value = props.minWidth
  }
  if (sidebarWidth.value > props.maxWidth) {
    sidebarWidth.value = props.maxWidth
  }
}
function distance() {
  if (!props.parent) return 0
  const rect = props.parent.getBoundingClientRect()
  return rect[props.side]
}

defineExpose({ collapse, expand, toggle, collapsed })
</script>
