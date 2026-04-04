/**
 * GlobalModal - Modals, Confirm, Toast
 */
(function() {
    'use strict';

    // =========== TOAST ===========
    function showToast(msg, type) {
        type = type || 'info';
        // Auto-Typ-Erkennung
        const lower = (msg || '').toLowerCase();
        if (!type || type === 'info') {
            if (/erfolg|gespeichert|gelöscht|erstellt|erledigt|aktualisiert/.test(lower)) type = 'success';
            else if (/fehler|error|nicht|fehlgeschlagen/.test(lower)) type = 'error';
        }

        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const span = document.createElement('span');
        span.textContent = msg;
        toast.appendChild(span);
        container.appendChild(toast);

        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 350);
        }, 3500);
    }

    // =========== MODAL ===========
    function openModal(id) {
        const el = document.getElementById(id);
        if (el) { el.classList.add('active'); document.body.style.overflow = 'hidden'; }
    }

    function closeModal(id) {
        const el = typeof id === 'string' ? document.getElementById(id) : id;
        if (el) { el.classList.remove('active'); document.body.style.overflow = ''; }
    }

    // =========== CONFIRM ===========
    async function confirmDialog(message, opts) {
        opts = opts || {};
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay active';
            overlay.style.zIndex = '3000';
            const content = document.createElement('div');
            content.className = 'modal-content modal-sm';
            content.style.cssText = 'text-align:center; padding:2rem;';
            const p = document.createElement('p');
            p.style.cssText = 'font-size:1rem; margin-bottom:1.5rem;';
            p.textContent = message;
            const btnRow = document.createElement('div');
            btnRow.style.cssText = 'display:flex; gap:0.5rem; justify-content:center;';
            const btnNo = document.createElement('button');
            btnNo.className = 'btn btn-outline';
            btnNo.textContent = opts.nein || 'Nein';
            const btnYes = document.createElement('button');
            btnYes.className = 'btn ' + (opts.danger ? 'btn-danger' : 'btn-primary');
            btnYes.textContent = opts.ja || 'Ja';
            btnRow.appendChild(btnNo);
            btnRow.appendChild(btnYes);
            content.appendChild(p);
            content.appendChild(btnRow);
            overlay.appendChild(content);
            document.body.appendChild(overlay);
            btnYes.onclick = () => { overlay.remove(); resolve(true); };
            btnNo.onclick = () => { overlay.remove(); resolve(false); };
        });
    }

    // =========== PROMPT ===========
    async function promptDialog(message, opts) {
        opts = opts || {};
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay active';
            overlay.style.zIndex = '3000';
            const content = document.createElement('div');
            content.className = 'modal-content modal-sm';
            content.style.cssText = 'padding:2rem;';
            const p = document.createElement('p');
            p.style.cssText = 'font-size:1rem; margin-bottom:1rem;';
            p.textContent = message;
            const input = document.createElement('input');
            input.type = opts.type || 'text';
            input.className = 'form-control';
            input.value = opts.default || '';
            input.placeholder = opts.placeholder || '';
            const btnRow = document.createElement('div');
            btnRow.style.cssText = 'display:flex; gap:0.5rem; justify-content:flex-end; margin-top:1rem;';
            const btnCancel = document.createElement('button');
            btnCancel.className = 'btn btn-outline';
            btnCancel.textContent = 'Abbrechen';
            const btnOk = document.createElement('button');
            btnOk.className = 'btn btn-primary';
            btnOk.textContent = 'OK';
            btnRow.appendChild(btnCancel);
            btnRow.appendChild(btnOk);
            content.appendChild(p);
            content.appendChild(input);
            content.appendChild(btnRow);
            overlay.appendChild(content);
            document.body.appendChild(overlay);
            setTimeout(() => input.focus(), 50);
            input.onkeydown = e => { if (e.key === 'Enter') { overlay.remove(); resolve(input.value); } };
            btnOk.onclick = () => { overlay.remove(); resolve(input.value); };
            btnCancel.onclick = () => { overlay.remove(); resolve(null); };
        });
    }

    // Globale Exports
    window.showToast = showToast;
    window.openModal = openModal;
    window.closeModal = closeModal;
    window.confirm = confirmDialog;
    window.prompt = promptDialog;
    window.alert = function(msg) { showToast(msg); };

    // Close modal on overlay click
    document.addEventListener('click', e => {
        if (e.target.classList.contains('modal-overlay')) {
            closeModal(e.target);
        }
    });

    // Close modal on Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            const active = document.querySelector('.modal-overlay.active');
            if (active) closeModal(active);
        }
    });
})();
