const CACHE = 'r4b1t-v1';
const PRECACHE = ['/r4b1t/', '/r4b1t/index.html'];

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
  // Network first for urls.txt and Worker API calls, cache first for shell
  if (e.request.url.includes('urls.txt') || e.request.url.includes('workers.dev')) {
    return; // Let these go to network always
  }
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
