/**
 * Globale Icon-Hilfsfunktion
 * icon('name') -> SVG aus dem Sprite-Sheet
 */
function icon(name, classes, attrs) {
    const cls = 'icon' + (classes ? ' ' + classes : '');
    let extra = '';
    if (attrs) {
        for (const [k, v] of Object.entries(attrs)) {
            extra += ` ${k}="${v}"`;
        }
    }
    return `<svg class="${cls}"${extra}><use href="#icon-${name}"/></svg>`;
}
