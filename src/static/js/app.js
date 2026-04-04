/**
 * BabyApp - Globale Hilfsfunktionen
 */
(function() {
    'use strict';

    // =========== HTML-Escape ===========
    window.esc = function(s) {
        if (s == null) return '';
        const d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    };

    // =========== API Helper ===========
    window.api = async function(url, opts) {
        opts = opts || {};
        const config = {
            method: opts.method || 'GET',
            headers: { 'Content-Type': 'application/json' },
        };
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
        if (csrf) config.headers['X-CSRFToken'] = csrf;
        if (opts.body) config.body = JSON.stringify(opts.body);
        const resp = await fetch(url, config);
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.error || 'Fehler');
        }
        return data;
    };

    // =========== Timer ===========
    window.BabyTimer = {
        _intervals: {},

        start(id, startTime, displayEl) {
            if (this._intervals[id]) clearInterval(this._intervals[id]);
            const startMs = new Date(startTime).getTime();
            const update = () => {
                const diff = Date.now() - startMs;
                const h = Math.floor(diff / 3600000);
                const m = Math.floor((diff % 3600000) / 60000);
                const s = Math.floor((diff % 60000) / 1000);
                displayEl.textContent =
                    (h > 0 ? h + ':' : '') +
                    String(m).padStart(2, '0') + ':' +
                    String(s).padStart(2, '0');
            };
            update();
            this._intervals[id] = setInterval(update, 1000);
        },

        stop(id) {
            if (this._intervals[id]) {
                clearInterval(this._intervals[id]);
                delete this._intervals[id];
            }
        },
    };

    // =========== Datum-Formatierung ===========
    window.formatDate = function(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        return d.toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: '2-digit' });
    };

    window.formatTime = function(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        return d.toLocaleTimeString('de-AT', { hour: '2-digit', minute: '2-digit' });
    };

    window.formatDateTime = function(iso) {
        if (!iso) return '-';
        return formatDate(iso) + ' ' + formatTime(iso);
    };

    window.formatDauer = function(minuten) {
        if (!minuten && minuten !== 0) return '-';
        const h = Math.floor(minuten / 60);
        const m = minuten % 60;
        if (h > 0) return `${h}h ${m}min`;
        return `${m}min`;
    };

    window.zeitSeit = function(minuten) {
        if (!minuten && minuten !== 0) return '-';
        if (minuten < 60) return `vor ${minuten} Min.`;
        const h = Math.floor(minuten / 60);
        const m = minuten % 60;
        return `vor ${h}h ${m}min`;
    };

    // =========== Navigation + Kind-Dropdown ===========
    document.addEventListener('click', e => {
        const dd = document.getElementById('kind-dropdown');
        if (dd && !dd.contains(e.target)) dd.classList.remove('open');
    });

    document.addEventListener('DOMContentLoaded', () => {
        const menuIcon = document.getElementById('menu-icon');
        const sideNav = document.getElementById('side-nav');
        const overlay = document.getElementById('nav-overlay');

        if (menuIcon && sideNav) {
            menuIcon.addEventListener('click', () => {
                sideNav.classList.toggle('open');
                if (overlay) overlay.classList.toggle('show');
            });
        }
        if (overlay) {
            overlay.addEventListener('click', () => {
                sideNav.classList.remove('open');
                overlay.classList.remove('show');
            });
        }

        // Aktiven Nav-Link markieren
        const path = window.location.pathname;
        document.querySelectorAll('.nav-button').forEach(btn => {
            if (btn.getAttribute('href') && path.startsWith(btn.getAttribute('href')) && btn.getAttribute('href') !== '/') {
                btn.classList.add('active');
            }
        });
    });

    // =========== Kind-Wechsel ===========
    window.setActiveKind = async function(kindId) {
        await api(`/api/set-kind/${kindId}`, { method: 'POST' });
        location.reload();
    };

    // =========== Aktives Kind ===========
    window.getActiveKindId = function() {
        // KIND_ID wird serverseitig im Template gesetzt (httponly Cookie)
        return window.KIND_ID || null;
    };

    // =========== Dark Mode ===========
    window.toggleDarkMode = function() {
        const html = document.documentElement;
        const isDark = html.classList.toggle('dark-mode');
        localStorage.setItem('babyapp-darkmode', isDark ? '1' : '0');
    };

    // Dark Mode beim Laden wiederherstellen
    if (localStorage.getItem('babyapp-darkmode') === '1') {
        document.documentElement.classList.add('dark-mode');
    }

    // =========== Service Worker (PWA) ===========
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then(reg => {
                    // Auto-Update prüfen
                    reg.addEventListener('updatefound', () => {
                        const newSW = reg.installing;
                        newSW.addEventListener('statechange', () => {
                            if (newSW.state === 'activated' && navigator.serviceWorker.controller) {
                                showToast('App aktualisiert -- bitte Seite neu laden', 'info');
                            }
                        });
                    });
                })
                .catch(() => { /* SW nicht verfügbar (HTTP) */ });
        });
    }
})();
