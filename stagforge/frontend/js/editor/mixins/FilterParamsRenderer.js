/**
 * FilterParamsRenderer - Reusable DOM-based filter parameter rendering.
 *
 * Used by the dynamic filters panel (FilterManager) to render filter
 * parameters inline without a Vue template. Generates the same visual
 * layout as the standalone filter dialog.
 *
 * Usage:
 *   const { html, bindEvents } = renderFilterParams(filterDef, params, { embedded: true });
 *   container.innerHTML = html;
 *   bindEvents(container, (paramId, value) => { ... });
 */

/**
 * Render filter parameter controls as HTML.
 *
 * @param {Object} filterDef - Filter definition with params array
 * @param {Object} params - Current parameter values
 * @param {Object} [options] - Rendering options
 * @param {boolean} [options.embedded=false] - If true, renders compact without title
 * @returns {{ html: string, bindEvents: (container: HTMLElement, onChange: Function) => void }}
 */
export function renderFilterParams(filterDef, params, options = {}) {
    const filterParams = filterDef?.params || [];

    if (filterParams.length === 0) {
        return {
            html: '<div class="filter-params-empty">No adjustable parameters.</div>',
            bindEvents: () => {},
        };
    }

    const fields = [];

    for (const param of filterParams) {
        // Handle visible_when conditional display
        const dataVisible = param.visible_when
            ? `data-visible-when='${JSON.stringify(param.visible_when)}'`
            : '';

        let input = '';

        if (param.type === 'range') {
            const value = params[param.id] ?? param.default ?? param.min ?? 0;
            input = `
                <div class="param-range-row">
                    <input type="range"
                        class="filter-param-input" data-param-id="${param.id}" data-param-type="range"
                        min="${param.min}" max="${param.max}" step="${param.step || 1}"
                        value="${value}">
                    <input type="number"
                        class="param-number-input filter-param-input" data-param-id="${param.id}" data-param-type="number"
                        min="${param.min}" max="${param.max}" step="${param.step || 1}"
                        value="${value}">
                    ${param.suffix ? `<span class="param-suffix">${param.suffix}</span>` : ''}
                </div>
            `;
        } else if (param.type === 'select') {
            const value = params[param.id] ?? param.default ?? param.options?.[0] ?? '';
            input = `
                <select class="filter-param-input" data-param-id="${param.id}" data-param-type="select">
                    ${(param.options || []).map(opt =>
                        `<option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>`
                    ).join('')}
                </select>
            `;
        } else if (param.type === 'checkbox') {
            const value = params[param.id] ?? param.default ?? false;
            input = `
                <input type="checkbox" class="filter-param-input" data-param-id="${param.id}" data-param-type="checkbox"
                    ${value ? 'checked' : ''}>
            `;
        } else if (param.type === 'color') {
            const value = params[param.id] ?? param.default ?? '#FFFFFF';
            input = `
                <div class="param-color-row">
                    <input type="color" class="filter-param-input" data-param-id="${param.id}" data-param-type="color"
                        value="${value}">
                    <input type="text" class="param-color-text filter-param-input" data-param-id="${param.id}" data-param-type="color-text"
                        value="${value}" maxlength="7">
                </div>
            `;
        }

        fields.push(`
            <div class="filter-param" ${dataVisible}>
                <label>${param.name}</label>
                ${input}
            </div>
        `);
    }

    const html = `<div class="filter-params-embedded">${fields.join('')}</div>`;

    const bindEvents = (container, onChange) => {
        // Update visible_when visibility
        const updateVisibility = () => {
            container.querySelectorAll('.filter-param[data-visible-when]').forEach(el => {
                const when = JSON.parse(el.dataset.visibleWhen);
                let visible = true;
                for (const [k, vals] of Object.entries(when)) {
                    if (!vals.includes(params[k])) {
                        visible = false;
                        break;
                    }
                }
                el.style.display = visible ? '' : 'none';
            });
        };

        container.querySelectorAll('.filter-param-input').forEach(input => {
            const paramId = input.dataset.paramId;
            const paramType = input.dataset.paramType;

            const handler = () => {
                let value;
                if (paramType === 'checkbox') {
                    value = input.checked;
                } else if (paramType === 'range' || paramType === 'number') {
                    value = parseFloat(input.value);
                    // Sync paired range/number inputs
                    const row = input.closest('.param-range-row');
                    if (row) {
                        row.querySelectorAll(`[data-param-id="${paramId}"]`).forEach(sibling => {
                            if (sibling !== input) sibling.value = value;
                        });
                    }
                } else if (paramType === 'color' || paramType === 'color-text') {
                    value = input.value;
                    // Sync paired color inputs
                    const row = input.closest('.param-color-row');
                    if (row) {
                        row.querySelectorAll(`[data-param-id="${paramId}"]`).forEach(sibling => {
                            if (sibling !== input) sibling.value = value;
                        });
                    }
                } else {
                    value = input.value;
                }

                params[paramId] = value;
                updateVisibility();
                if (onChange) onChange(paramId, value);
            };

            input.addEventListener('input', handler);
            if (paramType === 'select') {
                input.addEventListener('change', handler);
            }
        });

        updateVisibility();
    };

    return { html, bindEvents };
}

export default renderFilterParams;
