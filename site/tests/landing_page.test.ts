import { tick } from 'svelte'
import { beforeEach, describe, expect, it } from 'vitest'
import Page from '../src/routes/+page.svelte'

describe(`Landing Page`, () => {
  beforeEach(() => {
    document.body.innerHTML = ``
    new Page({ target: document.body })
  })

  it(`renders discovery set toggle buttons`, () => {
    const buttons = document.body.querySelectorAll(`.discovery-set-toggle button`)
    expect(buttons).toHaveLength(3)

    const button_texts = Array.from(buttons).map((btn) => btn.textContent?.trim())
    expect(button_texts).toContain(`Full Test Set`)
    expect(button_texts).toContain(`Unique Prototypes`)
    expect(button_texts).toContain(`10k Most Stable`)
  })

  it(`toggles discovery set when clicking buttons`, async () => {
    const buttons = document.body.querySelectorAll(`.discovery-set-toggle button`)
    const [full_test_btn, unique_protos_btn] = buttons

    // Initially Unique Prototypes should be active
    expect(unique_protos_btn.classList.contains(`active`)).toBe(true)
    expect(full_test_btn.classList.contains(`active`)).toBe(false)

    // Click Full Test Set button
    full_test_btn.click()
    await tick()

    expect(unique_protos_btn.classList.contains(`active`)).toBe(false)
    expect(full_test_btn.classList.contains(`active`)).toBe(true)
  })

  it(`toggles column visibility panel`, async () => {
    const columns_btn = document.body.querySelector(`details.column-toggles summary`)
    const column_menu = document.body.querySelector(`.column-menu`)

    // Column menu should be hidden initially
    expect(column_menu?.closest(`details`)?.open).toBe(false)

    // Click columns button to open menu
    columns_btn?.click()
    expect(column_menu?.closest(`details`)?.open).toBeTruthy()

    // Click outside to close menu
    columns_btn?.click()
    expect(column_menu?.closest(`details`)?.open).toBe(false)
  })

  it(`toggles non-compliant models`, async () => {
    const toggle = document.body.querySelector(`input[type="checkbox"]`)
    expect(toggle).toBeDefined()

    // Should be unchecked by default
    expect(toggle?.checked).toBe(false)
    // get number of table rows
    const n_compliant_models = document.body.querySelectorAll(`tbody tr`).length

    // Click to show non-compliant models
    toggle?.click()
    expect(toggle?.checked).toBe(true)
    await tick()
    const n_all_models = document.body.querySelectorAll(`tbody tr`).length
    expect(n_all_models).toBeGreaterThan(n_compliant_models)
  })

  it(`updates column visibility when toggling checkboxes`, async () => {
    const columns_btn = document.body.querySelector(`details.column-toggles summary`)
    columns_btn?.click()
    await tick()
    // Table should reflect column visibility changes
    let f1_cells = document.body.querySelectorAll(`th, td`)
    let has_f1_column = Array.from(f1_cells).some((cell) =>
      cell.textContent?.includes(`F1`),
    )
    expect(has_f1_column).toBe(true)

    const checkboxes = document.body.querySelectorAll(
      `.column-menu input[type="checkbox"]`,
    )
    const f1_checkbox = Array.from(checkboxes).find((cb) =>
      cb.parentElement?.textContent?.includes(`F1`),
    )
    expect(f1_checkbox?.checked).toBe(true)

    // Uncheck F1
    f1_checkbox?.click()
    await tick()
    expect(f1_checkbox?.checked).toBe(false)

    // Table should reflect column visibility changes
    f1_cells = document.body.querySelectorAll(`th, td`)
    has_f1_column = Array.from(f1_cells).some((cell) => cell.textContent?.includes(`F1`))
    expect(has_f1_column).toBe(false)
  })

  it(`displays best model information`, () => {
    const best_model_info = document.body.querySelector(`[slot="best-report"]`)
    expect(best_model_info?.textContent).toMatch(/highest F1 score/)
    expect(best_model_info?.textContent).toMatch(/discovery acceleration factor/)
  })

  it(`renders table downloads section`, () => {
    const download_links = document.body.querySelectorAll(`.downloads a`)
    expect(download_links).toHaveLength(2)

    const [pdf_link, svg_link] = download_links
    expect(pdf_link.getAttribute(`href`)).toMatch(/\.pdf$/)
    expect(svg_link.getAttribute(`href`)).toMatch(/\.svg$/)
  })

  it(`displays valid metric values`, () => {
    const best_model_info = document.body.querySelector(`[slot="best-report"]`)
    const text = best_model_info?.textContent || ``

    // Extract F1 and DAF values using regex
    const f1_match = text.match(/F1 score of ([\d.]+)/)
    const daf_match = text.match(/DAF\) of ([\d.]+)/)

    if (f1_match && daf_match) {
      const f1_value = parseFloat(f1_match[1])
      const daf_value = parseFloat(daf_match[1])

      expect(0 < f1_value && f1_value < 1, `F1=${f1_value} is out of range`).toBe(true)
      expect(0 < daf_value && daf_value < 10, `DAF=${daf_value} is out of range`).toBe(
        true,
      )
    } else {
      throw new Error(`Could not find F1 or DAF values in text: ${text}`)
    }
  })
})
