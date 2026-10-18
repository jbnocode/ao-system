/**
 * Apply structured AI ops to an automation builder document tree.
 * Mutates `doc` in place. Returns ids of created/patched steps.
 */

import { insertAfter, newStep, removeStep } from '@/components/Settings/WorkflowAutomations/workflowSteps'

export function applyAiOps(doc, ops = []) {
  const touched = []
  if (!doc || !Array.isArray(ops)) return touched

  for (const raw of ops) {
    if (!raw || typeof raw !== 'object') continue
    const op = raw.op
    if (op === 'set_meta') {
      if (raw.title != null) doc.title = raw.title
      if (raw.document_type != null) doc.document_type = raw.document_type
      if (raw.enabled != null) doc.enabled = raw.enabled ? 1 : 0
      continue
    }
    if (op === 'set_trigger') {
      if (raw.document_type) doc.document_type = raw.document_type
      doc.trigger_type = raw.trigger_type || doc.trigger_type
      if (raw.trigger_field != null) doc.trigger_field = raw.trigger_field
      if (raw.from_value != null) doc.from_value = raw.from_value
      if (raw.to_value != null) doc.to_value = raw.to_value
      if (raw.custom_event != null) doc.custom_event = raw.custom_event
      if (raw.cron_expression != null) doc.cron_expression = raw.cron_expression
      if (raw.date_field != null) doc.date_field = raw.date_field
      continue
    }
    if (op === 'add_step') {
      const created = newStep(raw.values || {})
      const afterId = raw.after_id
      const branch = raw.branch
      if (!afterId) {
        doc.actions.push(created)
      } else {
        const after = findById(doc.actions, afterId)
        if (!after) doc.actions.push(created)
        else if (branch && after.children?.[branch]) after.children[branch].push(created)
        else insertAfter(doc.actions, after, created)
      }
      touched.push(created._id)
      continue
    }
    if (op === 'patch_step') {
      const node = findById(doc.actions, raw.id)
      if (!node) continue
      Object.assign(node, raw.values || {})
      touched.push(node._id)
      continue
    }
    if (op === 'remove_step') {
      removeStep(doc.actions, raw.id)
    }
  }
  return touched
}

function findById(nodes, id) {
  if (!id || !Array.isArray(nodes)) return null
  for (const node of nodes) {
    if (node._id === id) return node
    if (node.children?.If) {
      const found =
        findById(node.children.If, id) || findById(node.children.Else, id)
      if (found) return found
    }
  }
  return null
}
