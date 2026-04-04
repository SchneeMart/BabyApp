/**
 * BabyApp Service Worker
 * - Cacht UI-Dateien für Offline-Zugriff
 * - Network-first für API-Aufrufe
 * - Cache-first für statische Dateien
 */
const CACHE_NAME = 'babyapp-v1';

const PRECACHE = [
    '/static/css/base.css',
    '/static/css/layout.css',
    '/static/css/buttons.css',
    '/static/css/forms.css',
    '/static/css/cards.css',
    '/static/css/tables.css',
    '/static/css/modals.css',
    '/static/css/utilities.css',
    '/static/js/app.js',
    '/static/js/global-modals.js',
    '/static/js/global-icons.js',
    '/static/js/global-camera.js',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
];

// Install: Precache
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(PRECACHE).catch(() => {
                // Einzeln versuchen falls etwas fehlschlägt
                return Promise.allSettled(PRECACHE.map(url => cache.add(url)));
            });
        })
    );
    self.skipWaiting();
});

// Activate: Alte Caches löschen
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            );
        })
    );
    self.clients.claim();
});

// Fetch: Strategie je nach Request-Typ
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // API-Aufrufe: immer Netzwerk, kein Cache
    if (url.pathname.startsWith('/api/') || url.pathname.includes('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // POST-Requests: immer Netzwerk
    if (event.request.method !== 'GET') {
        event.respondWith(fetch(event.request));
        return;
    }

    // Statische Dateien: Cache-first, dann Netzwerk
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(cached => {
                return cached || fetch(event.request).then(response => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // HTML-Seiten: Network-first, Cache als Fallback
    event.respondWith(
        fetch(event.request).then(response => {
            if (response.ok) {
                const clone = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
            }
            return response;
        }).catch(() => {
            return caches.match(event.request).then(cached => {
                return cached || caches.match('/');
            });
        })
    );
});
