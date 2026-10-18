import { describe, expect, it } from 'vitest'
import { applyAiOps } from '../../src/utils/applyAiOps'
import { newStep } from '../../src/components/Settings/WorkflowAutomations/workflowSteps'

function blankDoc() {
  return {
    title: '',
    document_type: 'CRM Lead',
    trigger_type: '',
    actions: [],
  }
}

describe('applyAiOps', () => {
  it('sets meta and trigger', () => {
    const doc = blankDoc()
    applyAiOps(doc, [
      { op: 'set_meta', title: 'Demo', document_type: 'CRM Deal' },
      {
        op: 'set_trigger',
        trigger_type: 'Field Value Changed',
        trigger_field: 'status',
        to_value: 'Qualified',
      },
    ])
    expect(doc.title).toBe('Demo')
    expect(doc.document_type).toBe('CRM Deal')
    expect(doc.trigger_type).toBe('Field Value Changed')
    expect(doc.trigger_field).toBe('status')
    expect(doc.to_value).toBe('Qualified')
  })

  it('adds sequential steps', () => {
    const doc = blankDoc()
    const ids = applyAiOps(doc, [
      { op: 'add_step', values: { step_type: 'Wait' } },
      { op: 'add_step', values: { step_type: 'Action', action_type: 'CreateDocument' } },
    ])
    expect(doc.actions).toHaveLength(2)
    expect(ids).toHaveLength(2)
    expect(doc.actions[0].step_type).toBe('Wait')
    expect(doc.actions[1].action_type).toBe('CreateDocument')
  })

  it('patches and removes by id', () => {
    const doc = blankDoc()
    const step = newStep({ step_type: 'If', step_condition: '' })
    doc.actions.push(step)
    applyAiOps(doc, [
      {
        op: 'patch_step',
        id: step._id,
        values: { step_condition: 'doc.status == "New"' },
      },
    ])
    expect(doc.actions[0].step_condition).toBe('doc.status == "New"')
    applyAiOps(doc, [{ op: 'remove_step', id: step._id }])
    expect(doc.actions).toHaveLength(0)
  })
})
