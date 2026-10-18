<template>
  <div class="flex h-full flex-col gap-6 py-8 px-6 text-ink-gray-8">
    <div class="flex flex-col gap-1 px-2">
      <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
        {{ __('Life Insurance') }}
      </h2>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Apply the life underwriting pipeline, Case (person-first) mode, and stage-tied automation recipes. You can still rename or reorder stages anytime.',
          )
        }}
      </p>
    </div>

    <div class="flex-1 flex flex-col gap-6 overflow-y-auto px-2">
      <div
        class="flex items-center justify-between gap-3 rounded-lg border border-outline-gray-modals bg-surface-white p-4"
      >
        <div>
          <div class="text-p-base-medium text-ink-gray-8">
            {{ __('Life agency mode') }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{
              __(
                'Deals become Cases, Household contacts, person-first titles, hide B2B organization chrome.',
              )
            }}
          </div>
        </div>
        <Switch
          :modelValue="!!status.life_agency_mode"
          size="sm"
          @update:modelValue="toggleLifeMode"
        />
      </div>

      <div class="rounded-lg border border-outline-gray-modals bg-surface-white p-4">
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('Pipeline stages') }}
        </div>
        <div class="mt-1 text-p-sm text-ink-gray-5">
          {{
            status.pipeline_applied
              ? __('Life stages are installed.')
              : __('Some life stages are missing.')
          }}
        </div>
        <ol class="mt-3 grid gap-1 text-p-sm text-ink-gray-7 sm:grid-cols-2">
          <li v-for="(s, i) in status.statuses || []" :key="s.deal_status">
            {{ i + 1 }}. {{ s.deal_status }}
            <span class="text-ink-gray-4">({{ s.type }})</span>
          </li>
        </ol>
      </div>

      <div class="rounded-lg border border-outline-gray-modals bg-surface-white p-4">
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('Automation recipes') }}
        </div>
        <ul class="mt-3 space-y-2 text-p-sm text-ink-gray-7">
          <li
            v-for="f in status.flows || []"
            :key="f.title"
            class="flex items-center justify-between gap-2"
          >
            <span>{{ f.title }}</span>
            <Badge
              :label="
                f.installed
                  ? f.enabled
                    ? __('Enabled')
                    : __('Installed')
                  : __('Missing')
              "
              :theme="f.enabled ? 'green' : f.installed ? 'blue' : 'gray'"
            />
          </li>
        </ul>
      </div>

      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-p-base-medium text-ink-gray-7">
              {{ __('Replace existing deal stages') }}
            </div>
            <div class="text-p-sm text-ink-gray-5">
              {{
                __(
                  'Remaps deals on non-life stages to Contacted, then removes those stages.',
                )
              }}
            </div>
          </div>
          <Switch v-model="replacePipeline" size="sm" />
        </div>
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-p-base-medium text-ink-gray-7">
              {{ __('Enable automation flows') }}
            </div>
            <div class="text-p-sm text-ink-gray-5">
              {{ __('Turn the five life recipes on immediately after install.') }}
            </div>
          </div>
          <Switch v-model="enableFlows" size="sm" />
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <Button
          variant="solid"
          :loading="applying"
          :label="__('Apply life pack')"
          @click="apply"
        />
        <Button
          :label="__('Refresh')"
          :loading="pack.loading"
          @click="pack.reload()"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Badge, Button, Switch, call, createResource, toast } from 'frappe-ui'
import { getSettings } from '@/stores/settings'

const replacePipeline = ref(true)
const enableFlows = ref(false)
const applying = ref(false)
const toggling = ref(false)

const { _settings } = getSettings()

const pack = createResource({
  url: 'crm.life.api.get_life_pack_status',
  auto: true,
  initialData: {
    statuses: [],
    flows: [],
    pipeline_applied: false,
    missing_statuses: [],
    life_agency_mode: false,
  },
})

const status = computed(() => pack.data || {})

async function toggleLifeMode(enabled) {
  if (toggling.value) return
  toggling.value = true
  try {
    await call('crm.life.api.set_life_agency_mode', {
      enabled: enabled ? 1 : 0,
    })
    toast.success(
      enabled ? __('Life agency mode on') : __('Life agency mode off'),
    )
    pack.reload()
    _settings.reload?.() || _settings.fetch?.()
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Could not update'))
  } finally {
    toggling.value = false
  }
}

async function apply() {
  applying.value = true
  try {
    const result = await call('crm.life.api.apply_life_pack', {
      replace_pipeline: replacePipeline.value ? 1 : 0,
      enable_flows: enableFlows.value ? 1 : 0,
      enable_life_mode: 1,
    })
    const remapped = result?.pipeline?.remapped_deals || 0
    toast.success(
      remapped
        ? __('Life pack applied ({0} deals remapped)', [remapped])
        : __('Life pack applied'),
    )
    pack.reload()
    _settings.reload?.() || _settings.fetch?.()
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Could not apply'))
  } finally {
    applying.value = false
  }
}
</script>
