const CACHE_NAME = 'CACHE_VERSION_PLACEHOLDER';
const urlsToCache = URLS_TO_CACHE_PLACEHOLDER;

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                // 逐个缓存资源，避免单个失败导致全部失败
                return Promise.allSettled(
                    urlsToCache.map(url => {
                        return cache.add(url).catch(err => {
                            console.warn(`Failed to cache ${url}:`, err);
                            return null;
                        });
                    })
                );
            })
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('fetch', event => {
    // 不缓存API请求
    if (event.request.url.includes('/api/') || 
        event.request.url.includes('?token=') ||
        event.request.url.includes('/get_') ||
        event.request.url.includes('/send_') ||
        event.request.url.includes('/login') ||
        event.request.url.includes('/open_door')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
