/**
 * GlobalCamera -- Kamera-Integration für die BabyApp
 *
 * Strategie:
 *   1. HTTPS + getUserMedia verfügbar -> In-App Kamera (kein App-Wechsel)
 *   2. Sonst -> File-Input mit sofortigem Upload (kein State-Verlust)
 *
 * API:
 *   GlobalCamera.capture()           -> Promise<Blob|null>   (Einzelfoto)
 *   GlobalCamera.captureMultiple()   -> Promise<Blob[]>      (Mehrere Fotos)
 *   GlobalCamera.canUseNative()      -> boolean              (getUserMedia verfügbar?)
 */
(function() {
    'use strict';

    let stream = null;
    let overlay = null;
    let video = null;
    let canvas = null;
    let resolveCapture = null;
    let capturedBlobs = [];
    let multiMode = false;
    let facingMode = 'environment';

    // Prüfe ob native Kamera (getUserMedia) nutzbar ist
    // Nur über HTTPS oder localhost möglich
    function canUseNative() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
        const loc = window.location;
        if (loc.protocol === 'https:') return true;
        if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') return true;
        return false;
    }

    // =========================================================================
    // NATIVE KAMERA (getUserMedia)
    // =========================================================================

    function createOverlay() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.id = 'camera-overlay';
        overlay.innerHTML = `
            <style>
                #camera-overlay {
                    position: fixed; inset: 0; z-index: 5000;
                    background: #000; display: flex; flex-direction: column;
                    align-items: center; justify-content: center;
                }
                #camera-overlay video {
                    width: 100%; max-height: calc(100vh - 120px);
                    object-fit: cover; background: #111;
                }
                #camera-overlay canvas { display: none; }
                #camera-controls {
                    display: flex; align-items: center; justify-content: center;
                    gap: 20px; padding: 16px; background: rgba(0,0,0,0.8);
                    width: 100%;
                }
                #camera-controls button {
                    border: none; border-radius: 50%; cursor: pointer;
                    font-family: inherit; font-weight: 700; transition: all 0.15s;
                }
                .cam-btn-capture {
                    width: 64px; height: 64px; background: white;
                    box-shadow: 0 0 0 4px rgba(255,255,255,0.3);
                }
                .cam-btn-capture:active { transform: scale(0.9); }
                .cam-btn-close, .cam-btn-done, .cam-btn-flip {
                    width: 44px; height: 44px; background: rgba(255,255,255,0.2);
                    color: white; font-size: 1.1rem;
                }
                .cam-btn-close:hover, .cam-btn-done:hover, .cam-btn-flip:hover {
                    background: rgba(255,255,255,0.35);
                }
                #camera-preview-strip {
                    display: flex; gap: 6px; padding: 8px 12px;
                    overflow-x: auto; width: 100%; background: rgba(0,0,0,0.6);
                }
                #camera-preview-strip:empty { display: none; }
                #camera-preview-strip img {
                    width: 50px; height: 50px; object-fit: cover;
                    border-radius: 6px; border: 2px solid rgba(255,255,255,0.5);
                }
                #camera-count {
                    position: absolute; top: 12px; right: 12px;
                    background: rgba(93,122,84,0.9); color: white;
                    padding: 4px 12px; border-radius: 20px;
                    font-size: 0.85rem; font-weight: 700;
                }
                #camera-count:empty { display: none; }
            </style>
            <video id="cam-video" autoplay playsinline muted></video>
            <canvas id="cam-canvas"></canvas>
            <div id="camera-preview-strip"></div>
            <div id="camera-count"></div>
            <div id="camera-controls">
                <button class="cam-btn-close" onclick="GlobalCamera._close()" title="Abbrechen">&#10005;</button>
                <button class="cam-btn-flip" onclick="GlobalCamera._flip()" title="Kamera wechseln">&#8634;</button>
                <button class="cam-btn-capture" onclick="GlobalCamera._snap()" title="Foto"></button>
                <button class="cam-btn-done" onclick="GlobalCamera._done()" title="Fertig" style="display:none;">&#10003;</button>
            </div>
        `;
        document.body.appendChild(overlay);
        video = document.getElementById('cam-video');
        canvas = document.getElementById('cam-canvas');
    }

    async function startStream() {
        try {
            if (stream) stream.getTracks().forEach(t => t.stop());
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: facingMode, width: { ideal: 1280 }, height: { ideal: 960 } },
                audio: false
            });
            video.srcObject = stream;
            return true;
        } catch (err) {
            return false;
        }
    }

    function stopStream() {
        if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
        if (video) video.srcObject = null;
    }

    async function nativeCapture(multi) {
        multiMode = multi;
        capturedBlobs = [];
        return new Promise(async (resolve) => {
            resolveCapture = resolve;
            createOverlay();
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            overlay.querySelector('.cam-btn-done').style.display = multi ? '' : 'none';
            const strip = document.getElementById('camera-preview-strip');
            const count = document.getElementById('camera-count');
            if (strip) strip.innerHTML = '';
            if (count) count.textContent = '';
            const ok = await startStream();
            if (!ok) {
                // getUserMedia fehlgeschlagen -- Fallback auf File-Input
                overlay.style.display = 'none';
                document.body.style.overflow = '';
                resolve(await fileInputCapture(multi));
            }
        });
    }

    // =========================================================================
    // FILE-INPUT FALLBACK (für HTTP / kein Kamerazugriff)
    // =========================================================================

    function fileInputCapture(multi) {
        return new Promise(resolve => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            if (multi) input.multiple = true;
            // capture="environment" öffnet Kamera-App auf Handy
            // Das ist ok als Fallback -- der State ist hier minimal
            input.setAttribute('capture', 'environment');
            input.style.display = 'none';
            document.body.appendChild(input);

            input.onchange = () => {
                const files = Array.from(input.files);
                input.remove();
                if (multi) {
                    resolve(files.length ? files : []);
                } else {
                    resolve(files.length ? files[0] : null);
                }
            };

            // Wenn der User abbricht (kein change-Event), nach Timeout auflösen
            // Das passiert wenn der Browser-Tab entladen und wiederhergestellt wird
            let changed = false;
            input.addEventListener('change', () => { changed = true; });

            // Focus-back Detection: wenn Benutzer zur App zurückkehrt ohne Foto
            const onFocus = () => {
                setTimeout(() => {
                    if (!changed) {
                        input.remove();
                        resolve(multi ? [] : null);
                    }
                    window.removeEventListener('focus', onFocus);
                }, 500);
            };

            input.click();

            // Warte kurz bevor wir auf Focus hören (damit der click() durchgeht)
            setTimeout(() => {
                window.addEventListener('focus', onFocus);
            }, 1000);
        });
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    window.GlobalCamera = {
        canUseNative: canUseNative,

        /**
         * Einzelfoto aufnehmen.
         * @returns {Promise<Blob|File|null>}
         */
        async capture() {
            if (canUseNative()) {
                return await nativeCapture(false);
            }
            return await fileInputCapture(false);
        },

        /**
         * Mehrere Fotos aufnehmen.
         * @returns {Promise<(Blob|File)[]>}
         */
        async captureMultiple() {
            if (canUseNative()) {
                return await nativeCapture(true);
            }
            return await fileInputCapture(true);
        },

        _snap() {
            if (!video || !video.videoWidth) return;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            canvas.toBlob(blob => {
                if (!blob) return;
                if (multiMode) {
                    capturedBlobs.push(blob);
                    const strip = document.getElementById('camera-preview-strip');
                    const img = document.createElement('img');
                    img.src = URL.createObjectURL(blob);
                    strip.appendChild(img);
                    document.getElementById('camera-count').textContent =
                        capturedBlobs.length + ' Foto' + (capturedBlobs.length > 1 ? 's' : '');
                } else {
                    capturedBlobs = [blob];
                    GlobalCamera._done();
                }
            }, 'image/jpeg', 0.85);
        },

        _flip() {
            facingMode = facingMode === 'environment' ? 'user' : 'environment';
            startStream();
        },

        _close() {
            stopStream();
            if (overlay) overlay.style.display = 'none';
            document.body.style.overflow = '';
            if (resolveCapture) resolveCapture(multiMode ? [] : null);
            resolveCapture = null;
        },

        _done() {
            stopStream();
            if (overlay) overlay.style.display = 'none';
            document.body.style.overflow = '';
            if (resolveCapture) {
                resolveCapture(multiMode ? capturedBlobs : (capturedBlobs[0] || null));
            }
            resolveCapture = null;
        },
    };
})();
