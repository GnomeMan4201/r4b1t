const CACHE = 'r4b1t-v4-rabbit-hero';
const PRECACHE = [
  '/r4b1t/',
  '/r4b1t/index.html',
  '/r4b1t/anime.min.js',
  '/r4b1t/anime-core.min.js',
  '/r4b1t/dual-shell.js',
  '/r4b1t/dual-shell.css',
  '/r4b1t/rabbit-aperture.svg',
  '/r4b1t/banana-note.svg',
  '/r4b1t/favicon.ico',
  '/r4b1t/favicon.svg',
  '/r4b1t/manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Network first for the corpus and Worker API calls; cache first for shell assets.
  if (e.request.url.includes('urls.txt') || e.request.url.includes('workers.dev')) {
    return;
  }
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
