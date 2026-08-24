# Production-safe crawler load mitigation research

**Scope:** Research and rollout guidance only. No application or production configuration was changed.

## Executive recommendation

Treat crawler load as both a URL-inventory problem and a capacity-control problem, not primarily as a user-agent blocking problem.

1. **Measure first:** Use Traefik access logs and the already preloaded `pg_stat_statements` module to identify load by hostname, normalized path family, query string, status, latency, and verified crawler.
2. **Stop avoidable work:** Canonicalize host, path, and query variants before Django; move canonical redirects before expensive GIS queries; narrow crawler discovery to valuable URLs; and serve static files, media, and `robots.txt` outside Gunicorn.
3. **Cache anonymous public representations:** After separating or correctly varying the personalized navbar, cache canonical page responses by object, language, and content version. Until then, cache low-level computed data and safe fragments instead of naïvely sharing entire responses.
4. **Protect capacity at the edge:** Use a global in-flight ceiling plus a generous per-client token bucket for all traffic, and a lower bucket only for *verified* crawler classes. Return `429` on overload. Do not rely on a spoofable `User-Agent` or use `403` as a crawl-rate signal.
5. **Reduce multiplicative concurrency:** Tune Gunicorn threads and PostgreSQL connections and memory together. The current theoretical concurrency—`10` workers × `100` threads—and PostgreSQL settings—`max_connections=7000`, `work_mem=128MB`—can amplify a crawl spike into connection and memory pressure.

A safe order is:

1. observability;
2. URL and robots cleanup;
3. cache canary;
4. edge admission control;
5. query and index work;
6. concurrency and database right-sizing.

Each stage should have latency, error-rate, cache-hit, PostgreSQL-active-session, and normal-user conversion rollback thresholds.

## Repository and stack findings

There was no existing `docs/` or research convention; the only repository Markdown file was `README.md`, so `docs/research/` is a sensible destination for this report.

### Runtime topology visible in the repository

- Django `5.1`, psycopg `3.2.1`, and Django REST Framework `3.15.2` are pinned in `requirements/base.txt:4-14`.
- Production is WSGI under Gunicorn `23.0.0` (`requirements/production.txt:5`) with `--workers=10 --threads=100` (`docker/production/gunicorn.sh:8-10`).
- PostgreSQL 16 plus PostGIS 3 is built in `docker/postgres/Dockerfile:1-11`; Django uses the PostGIS backend, `CONN_MAX_AGE=60`, and `ATOMIC_REQUESTS=True` (`config/settings/base.py:47-60`).
- Production PostgreSQL starts with:
  - `shared_buffers=2GB`
  - `work_mem=128MB`
  - `statement_timeout=300000`
  - `max_parallel_workers_per_gather=16`
  - `max_worker_processes=32`
  - `max_connections=7000`
  - `shared_preload_libraries=pg_stat_statements`

  These are set in `docker-compose.yml:18-29`.

  The repository does not create the `pg_stat_statements` extension, so preloading alone may not expose its view. The extension must be checked in the live database. PostgreSQL requires both preload and `CREATE EXTENSION` for use. [PostgreSQL: `pg_stat_statements`](https://www.postgresql.org/docs/16/pgstatstatements.html)

- Compose defines a `memcached:alpine` service (`docker-compose.yml:31-32`), and `python-memcached` is installed, but the production `CACHES` block is commented out (`config/settings/production.py:27-35`). Therefore this service currently provides no demonstrated Django page or data caching.
- The commented `MemcachedCache` backend should not simply be uncommented without checking Django 5.1’s supported Memcached backends and client packages. [Django cache framework](https://docs.djangoproject.com/en/5.1/topics/cache/)
- No Redis dependency, Redis service, page or fragment caching, conditional GET middleware, DRF throttles, Compose health checks, restart policies, or resource limits were found.
- No Traefik configuration, labels, version, provider, or network is present. The production `web` service also has no published port or Traefik label (`docker-compose.yml:3-16`). Traefik is therefore external to this repository, or the checked-in Compose file is incomplete. Any Traefik syntax must be matched to the deployed version and provider rather than copied blindly.
- `SECURE_PROXY_SSL_HEADER` confirms that an upstream proxy is expected (`config/settings/production.py:37-42`).

### Crawler-visible work

- The repository has fallback routes for `/static/`, `/media/`, `robots.txt`, and `ads.txt` through `django.views.static.serve` (`config/urls.py:23-25,44-45`). Django explicitly says this view is not hardened or suitable for production. Live Coolify inspection found a separate `web-static` service with Nginx containers for `/static` and `/media`, mounting the same host directories as Django. The live Traefik labels currently route `cualbondi.org` and `cualbondi.com.ar` to those containers, but omit `cualbondi.com` even though Coolify’s stored FQDN list includes it. Consequently, `cualbondi.com/static/*` and `/media/*` still reach Gunicorn; `cualbondi.org/static/*` reaches Nginx. Completing the existing offload is preferable to adding another static sidecar. [Django static deployment](https://docs.djangoproject.com/en/5.1/howto/static-files/deployment/) [Django built-in file-serving view](https://docs.djangoproject.com/en/5.1/ref/views/#serving-files-in-development)
- Public indexable detail pages include administrative areas, lines, routes, stops, and POIs, with both country-prefixed and fallback URL patterns (`config/urls.py:58-64`, `apps/core/urls.py:8-24`, `apps/catastro/urls.py:4-10`).
- APIs are exposed under both `/api/v3/` and `/v3/` (`config/urls.py:40-42`).
- The sitemap advertises lines, routes, stops, POIs, and administrative areas in pages of 10,000 (`config/sitemaps.py:43-47,88-104`).
- For every sitemap object, alternate URLs are built from all 14 active languages (`config/sitemaps.py:10-28`; `config/settings/base.py:384-483`). Alternate URLs also consume crawl budget. [Google: crawling myths](https://developers.google.com/crawling/docs/myths-about-crawling)
- Sitemap objects have no configured `lastmod`, so the code’s `latest_lastmod` path never becomes useful (`config/sitemaps.py:58-85,88-104`). Django can emit a sitemap `Last-Modified` header and answer conditionally when all items provide `lastmod` and `ConditionalGetMiddleware` is active. [Django sitemap framework](https://docs.djangoproject.com/en/5.1/ref/contrib/sitemaps/)
- `robots.txt` only disallows `/editor/` (`apps/core/static/robots.txt:1-2`) and does not advertise a fully qualified sitemap.
- Several canonical redirects happen **after** expensive work:
  - `ver_linea` runs geometry simplification and intersection queries before checking the requested URL (`apps/core/views.py:88-136`).
  - `ver_recorrido` similarly performs GIS work before checking the canonical URL (`apps/core/views.py:164-204`).

  These requests should cheaply resolve the object and canonical target, redirect if needed, and only then run page queries.

- The route page is especially costly. It performs:
  - GIS intersection and area calculations;
  - `ST_DumpPoints` joined with `ST_DWithin`;
  - random POI selection;
  - random schedule selection;
  - a Hausdorff-similarity query.

  See `apps/core/views.py:179-305` and `apps/core/managers.py:495-520`.

- Administrative-area pages run multiple spatial intersections, two random samples, and a correlated route-count subquery (`apps/catastro/views.py:168-229`).
- Stop and POI pages also execute multiple proximity queries (`apps/core/views.py:342-379`; `apps/catastro/views.py:75-161`).
- Public pages contain a user-specific navbar (`templates/navbar.html:27-36`). This is the current obstacle to naïve shared full-page caching: an authenticated response must not be served to another user or to an anonymous crawler.
- Route and POI pages currently render a review aggregate, which adds database work during template rendering:
  - `templates/core/ver_recorrido.html:68-70`
  - `templates/catastro/ver_poi.html:58-60`
  - aggregate implementation: `apps/reviews/templatetags/reviews.py:33-49`
- Review form and review list blocks are currently inside Django template comments and therefore are not rendered:
  - `templates/core/ver_recorrido.html:172-176`
  - `templates/catastro/ver_poi.html:148-152`

  If those blocks are re-enabled later, the review form contains CSRF-bearing markup at `apps/reviews/templates/reviews/form.html:1-13`, which would add another full-page cache-safety concern.

- Language is selected from a valid `?lang=` value, otherwise from the country prefix (`apps/core/middlewares/locale.py:17-31`; `apps/utils/get_lang.py:3-9`).
- Other query parameters are ignored by the HTML views but still create distinct URLs and distinct URL-based per-view cache entries. Unbounded query strings are therefore both a crawl-space and cache-cardinality risk.
- Current canonical markup combines `rel="canonical"` with `hreflang` on the default-language link while treating other languages as alternates—for example, `templates/core/ver_recorrido.html:14-19`. Localized variants should list themselves and all alternates with fully qualified URLs, while canonical and alternate relations should be separate and internally consistent. [Google: localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions) [Google: canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- `LoggingMiddleware` trusts raw `X-Forwarded-For`, blocks a UA substring inside Django, prints every request, and raises `PermissionDenied` (`apps/core/middlewares/log.py:5-29`).
  - It consumes a Gunicorn slot before rejecting the request.
  - User-Agent strings are spoofable.
  - `ua=None` can cause a type error in `if blockua in ua`.
  - `403` is not a Google crawl-rate signal.

  Google treats `429` as overload but says other `4xx`, including `403`, do not reduce crawl rate. [Google: HTTP status effects](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes)

### Live production evidence collected during this investigation

A one-hour application-log sample contained 92,737 successful requests:

- 68,559 distinct full URLs, giving a 26.1% exact-repeat rate within the hour;
- 55,257 distinct paths after removing query strings, giving a 40.4% repeated-object rate;
- 80,401 requests with a `lang` parameter;
- repeated requests to sitemap pages, static assets, and the same objects in different languages.

This indicates that a canonical full-response cache could avoid at least about one quarter of the sampled view executions within one hour. A longer TTL should capture more recrawls, while an object-data cache shared by language variants has a higher theoretical reuse rate where the underlying computation is language-independent.

Anonymous detail responses currently include `Vary: Cookie` and no `Cache-Control`, `ETag`, or `Last-Modified` validator. A sampled sitemap response was approximately 15.6 MB and also lacked cache validators. These observations reinforce that naïve URL caching is not active and that sitemap caching is independently valuable.

The live `web-static` Coolify service (`mksccws`) has separate `nginx` containers and correct bind mounts for the shared static and media directories. The running containers are stable and small. Routing is incomplete, however: `cualbondi.com` resolves to this server but is absent from the running Nginx containers’ Traefik labels, so sampled `.com` static requests report `server: gunicorn`. `cualbondi.org` static requests report `server: nginx`; `cualbondi.com.ar` currently resolves to a different public IP. In one application-log hour, Gunicorn still accepted about 255 `/static/` and 2,348 `/media/` requests. This is worth correcting, but it is only a few percent of request volume and does not explain the PostgreSQL overload.

`pg_stat_statements`, whose statistics were last reset on 2025-09-19, identifies the same public-view queries as dominant cumulative database work:

- route proximity `ST_DWithin`: about 546 million calls at 187 ms mean execution time;
- route lookup by `osm_id` plus slug similarity: about 33 million calls at 2.76 seconds mean execution time;
- administrative-area intersection: about 555 million calls at 31.8 ms mean execution time;
- stop schedule lookup: about 305 million calls at 48.5 ms mean execution time;
- random nearby POI selection: about 29 million calls at 160 ms mean execution time.

At the start of this investigation, the live database had no B-tree index on `core_recorrido.osm_id`, and PostgreSQL planned the route lookup as a five-worker parallel sequential scan over a table occupying about 2.8 GB. On 2026-08-24, `core_recorrido_osm_id_idx` was created concurrently in production and validated as ready and valid; the same query now uses an index scan. The repository still needs a state-only/concurrent Django migration so schema history represents that production index without trying to create it again. `core_linea.osm_id` remains unindexed, although that table is much smaller. The production database already has the expected GiST indexes for route and point geometry and a composite `(osm_type, osm_id)` POI index.

## Option comparison

| Option | Expected origin/DB relief | Main safety condition | Fit here |
|---|---:|---|---|
| Canonical host/path/query redirects at Traefik | High for duplicate requests; immediate | Preserve only supported parameters and test every hostname | **First choice.** Multiple allowed hosts, optional country prefixes, legacy routes, and ignored query parameters expand crawl inventory. |
| Early application canonical redirect | High on malformed or old detail URLs | Fetch only fields needed to identify the target | **First choice.** Existing line and route redirects occur after GIS work. |
| Full-page Django cache | Very high on repeated GET/HEAD | Anonymous/public-only representation or correctly varied user state; bounded canonical keys; deterministic output; explicit invalidation/TTL | **High value after addressing the navbar.** The current personalized navbar makes naïve shared response caching unsafe. |
| Low-level data/computation cache | High for repeated GIS/object work | Versioned keys, serializable values, dependency-aware invalidation, stampede control | **Best initial cache.** It preserves dynamic user chrome while avoiding repeated route/admin-area work. |
| Template fragment cache | Low to medium | Include object ID, active language, and content version in the key | Useful for review aggregates and large rendered lists, but it does **not** stop view queries that run before rendering. |
| Redis cache | Enables shared cache and counters | Memory limit and eviction, private network/auth, outage behavior, key isolation | Good if one shared platform is wanted for Django and throttling. Existing inert Memcached is a lower-change alternative for cache-only use. |
| Conditional GET and cache headers | Medium bandwidth relief; high compute relief only with a cheap validator | Validator must cover every visible dependency | Add after version semantics exist. Middleware-generated ETags after rendering do not avoid the expensive query/render path. |
| Query and index optimization | High on cache misses | Profile first; production-safe migrations; verify plans and result semantics | Required for tail safety; does not bound aggregate request concurrency by itself. |
| Robots, sitemap, and crawl policy | High for compliant crawlers over time | Do not hide valuable pages or confuse `robots` with `noindex` | **First choice.** Current policy is nearly open and the sitemap multiplies each object across languages. |
| Traefik rate and in-flight limiting | High and immediate under spikes | Correct client-IP trust, headroom for normal users, path classes, `429`, canary rollout | **Primary overload guard.** It rejects before Gunicorn and PostgreSQL. |
| DRF/application throttle | Medium for APIs | Shared cache; not treated as DoS security; race tolerance | Defense in depth for `/api/v3/` and `/v3/`, not the only protection. DRF documents non-atomic/racy counters. [DRF throttling](https://www.django-rest-framework.org/api-guide/throttling/) |
| Gunicorn recycling | Little steady-state relief | Jittered recycling and readiness | Reliability aid only; it does not make expensive requests cheaper or establish a sustainable crawl rate. |
| Lower Gunicorn concurrency | High protection for PostgreSQL and RAM | Load-test throughput; retain enough slots for normal users | Likely necessary. The current 1,000-thread ceiling is disproportionate to DB-heavy synchronous work. |
| PostgreSQL timeouts, memory, and connection bounds | High blast-radius reduction | Separate web and batch needs; tune from measured plans | Necessary guardrails, not a substitute for caching and admission control. |
| Compose health, resource, and network changes | Indirect but important | Match the deployed Compose and Traefik topology | Add as part of implementation after capacities and the Traefik version are known. |

## Detailed production-safe approach

### 1. Establish a baseline and a reversible emergency control

1. Enable structured Traefik access logs at the actual deployment layer. Keep:
   - request host and path;
   - status;
   - total and origin duration;
   - router and service;
   - client address;
   - User-Agent.

   Redact authorization and cookies, and decide whether query values may contain sensitive data. Traefik supports JSON access logs, status and duration filters, and field/header controls. [Traefik access logs](https://doc.traefik.io/traefik/reference/install-configuration/observability/logs-and-accesslogs/)

2. Report request rates and p50/p95/p99 latency by:
   - normalized route family;
   - canonical versus noncanonical host;
   - query-parameter names;
   - status;
   - verified crawler.

   Distinguish cacheable HTML, sitemap, static/media, APIs, auth/editor, and unknown 404 space.

3. In PostgreSQL:
   - verify `CREATE EXTENSION pg_stat_statements` in the live database;
   - rank normalized queries by total execution time, calls, mean/max time, rows, and temporary I/O;
   - use `QuerySet.explain()` and `EXPLAIN (ANALYZE, BUFFERS)` on a staging copy or carefully selected read queries.

   `EXPLAIN ANALYZE` executes the statement. [Django database optimization](https://docs.djangoproject.com/en/5.1/topics/db/optimization/) [PostgreSQL `EXPLAIN`](https://www.postgresql.org/docs/16/sql-explain.html)

4. Set an initial global Traefik `inFlightReq` ceiling just below the concurrency at which DB latency rises sharply. Reserve capacity through separate route classes for cheap/static/health traffic. `inFlightReq` returns `429` when full. [Traefik InFlightReq](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/inflightreq/)

5. Add token-bucket `RateLimit` with a normal-user-friendly burst:
   - use a generous general limit to avoid punishing shared NAT users;
   - apply lower rates to expensive route families;
   - apply crawler-specific rates only where crawler identity is verified by source IP or confirmed reverse DNS.

   A User-Agent-only branch is advisory and spoofable. Traefik defines rate as `average / period` and `burst` as bucket size. [Traefik RateLimit](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ratelimit/)

6. Do not add automatic retries around an overloaded Django service. Traefik retries can multiply backend attempts when a server does not reply. [Traefik Retry](https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/retry/)

For a short Googlebot emergency, Google explicitly recommends temporary `429`, `500`, or `503`; `429` is the least ambiguous overload response. Persistent server errors can eventually affect indexing, so this is a guardrail while permanent fixes roll out, not a standing blanket policy. [Google: reduce crawl rate](https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate)

### 2. Collapse URL inventory before caching it

- Pick one production host for each intended country or domain representation.
- Redirect `www`, `.org`, and other aliases at Traefik before Django unless a hostname intentionally serves unique content.
- Robots rules are scoped by scheme, host, and port, so every still-live host needs a valid policy. [Google robots specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)
- Preserve the current Argentine/non-Argentine product intent in `apps/utils/reverse.py:5-24`, but make path redirects cheap.
- Resolve only `(osm_type, osm_id)` plus the fields required for slug, country, and canonical URL; issue one permanent redirect; then run GIS queries only on canonical requests.
- On public HTML routes, allow only one validated `lang` parameter.
- Strip known tracking parameters with a permanent redirect and define a deliberate response for unknown parameters.
- Apply query normalization path by path so API parameters such as `q`, `l`, and `t` remain intact.
- This bounds cache keys and prevents infinite URL spaces. Google identifies parameter combinations as a common overcrawling cause. [Google: faceted URL crawling](https://developers.google.com/crawling/docs/faceted-navigation)
- Emit one standalone, fully qualified, self-referential `rel="canonical"` for each language representation.
- Emit separate `rel="alternate" hreflang="…"` links in which every variant includes itself and all other variants.
- Make HTML and sitemap alternates identical.
- Confirm whether all 14 configured languages have useful translated content; advertise only deliberate variants.
- Keep only canonical URLs in internal links and sitemaps.
- Redirect old city, line, and route URLs once, avoiding redirect chains.

### 3. Deliberate robots and sitemap policy

`robots.txt` is a cooperative crawl policy, not access control.

`noindex` generally requires a fetch before it can be seen, so it does not immediately save crawl work. A URL blocked by robots cannot expose its page-level `noindex` to that crawler. [Google: crawling myths](https://developers.google.com/crawling/docs/myths-about-crawling)

After confirming product and SEO requirements, a future policy should:

- keep valuable canonical administrative-area, line, route, stop, and POI pages crawlable;
- disallow crawler access to non-search surfaces such as:
  - `/editor/`;
  - authentication endpoints;
  - comments submission endpoints;
  - user/account pages;
  - API route families, if those APIs are not intended as search documents;
- advertise the canonical, fully qualified sitemap URL;
- remove low-value or duplicate URL classes from the sitemap;
- consider `noindex` or robots restrictions only after examining Search Console traffic and index value;
- add accurate per-object `lastmod` values based on import and update timestamps;
- cache or conditionally serve sitemap pages;
- avoid advertising every language for every object unless the representation is intentional and materially localized.

#### Crawler-specific policy

**Google**

- `crawl-delay` is unsupported.
- Use inventory cleanup, Search Console diagnostics, fast/cacheable responses, and temporary `429` overload signaling. [Google robots specification](https://developers.google.com/crawling/docs/robots-txt/robots-txt-spec)
- Verify claimed Google crawlers with Google’s published IP lists or forward-confirmed reverse DNS, not User-Agent alone. [Google crawler verification](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests)

**Bing**

- Bing documents that `Crawl-delay` is a 1–30 second window with at most one fetch in the window.
- Bing Webmaster Tools can also schedule crawl intensity.
- A Bing-specific delay can provide an explicit sustainable pace without slowing humans or Google. [Bing: crawl-delay](https://blogs.bing.com/webmaster/May-2012/To-crawl-or-not-to-crawl,-that-is-BingBot-s-questi) [Bing Crawl Control](https://blogs.bing.com/webmaster/december-2018/bingbot-Series-Getting-most-of-Bingbot-via-Bing-Webmaster-Tools)

**Applebot**

- Applebot respects standard robots rules.
- It does not follow `crawl-delay`.
- It adjusts when a site slows down or returns errors.
- Use explicit allow/disallow scope and edge admission control. [Apple: About Applebot](https://support.apple.com/en-us/119829)

**Meta**

- Decide separately whether AI and indexing crawl has product value.
- Meta documents `meta-externalagent` robots controls.
- User-triggered fetchers may bypass robots, so preserve sharing-preview functionality if it is needed. [Meta web crawlers](https://developers.facebook.com/docs/sharing/webmasters/web-crawlers)

**Amazonbot**

- The application currently rejects Amazonbot by User-Agent.
- If the product decision is to opt out, express that policy in `robots.txt`.
- Enforce abusive or noncompliant traffic at the edge instead of spending Django capacity returning `403`.
- Amazon documents Amazonbot’s robots behavior and crawler identity. [Amazonbot documentation](https://developer.amazon.com/support/amazonbot)

### 4. Cache design: page, data, and fragments

Django supports per-site, per-view, fragment, and low-level caching.

Per-view cache keys are URL-based. With `USE_I18N=True`, generated cache keys include the active language. `cache_page` also sets downstream `Cache-Control` and `Expires` headers. [Django cache framework](https://docs.djangoproject.com/en/5.1/topics/cache/)

#### Stage A: safe initial caching

- Cache serializable, deterministic results for costly route and administrative-area computations under versioned keys such as:

  `route-page-data:vN:<id>:<content-version>:<lang>`

- Do not cache a lazy QuerySet or open DB/GEOS object graph without testing serialization behavior.
- Include all visible dependencies in the version:
  - route/import timestamp;
  - related stops;
  - schedules;
  - POIs;
  - administrative areas;
  - review aggregate where shown.
- If a complete dependency version is unavailable, use a conservative TTL and explicit invalidation after import or moderation.
- Use different TTLs for stable imported topology and frequently changing review data.
- Add randomized TTL jitter or single-flight locking/prewarming for popular keys to avoid a simultaneous cache miss, or “stampede,” after expiry or deployment.
- Fragment-cache the review aggregate and large rendered lists with object ID, language, and content version.
- Remember that fragment caching only saves the fragment’s queries and rendering. It does not avoid the main view’s GIS queries that already ran.
- Cache sitemap sections separately.
- Add accurate `lastmod` values so conditional sitemap requests can cheaply return `304`.

#### Stage B: anonymous full-page caching

The personalized navbar is the present full-page cache obstacle.

Possible safe designs include:

- move user-specific navbar state to a separate client-side/user endpoint;
- render a cacheable anonymous page shell and hydrate authenticated state separately;
- maintain explicitly separate authenticated and anonymous variants with correct cache keys and `Vary` semantics;
- bypass shared page caching for authenticated requests.

Then:

- per-view cache anonymous canonical GET/HEAD `200` responses;
- never shared-cache auth, editor, account, or comments POST surfaces;
- verify cookies, `Vary`, content language, host, scheme, and query normalization before enabling `public` caching;
- canary one route family;
- expose cache hit, miss, and age metrics;
- compare anonymous and authenticated bodies across every supported language before expanding.

Review forms and lists are currently commented out, so CSRF markup is not part of today’s public response. If those forms are re-enabled, they must remain outside any shared public response cache or be handled as a separate user-specific fragment.

#### Redis versus the checked-in Memcached service

- The least architectural change for cache-only use is to repair and enable the existing Memcached path using a Django-5.1-supported backend and client.
- Redis is more useful if the same platform also needs:
  - shared application-throttle counters;
  - atomic coordination;
  - richer invalidation;
  - single-flight or lock primitives.
- Django 5.1 has a built-in `django.core.cache.backends.redis.RedisCache`, but a compatible Redis Python client must be added. [Django cache framework: Redis](https://docs.djangoproject.com/en/5.1/topics/cache/#redis)
- For cache use, configure Redis `maxmemory` and an eviction policy such as `allkeys-lru` or `allkeys-lfu`.
- Redis documents that cache copies can normally be evicted and that `maxmemory` triggers policy-driven eviction. [Redis key eviction](https://redis.io/docs/latest/develop/reference/eviction/)
- Cache-only Redis can disable AOF and RDB persistence, avoiding unnecessary disk work. Redis explicitly lists no persistence as a caching option. [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- Do not publish Redis to the host or internet.
- Use an internal network and authentication or ACLs as appropriate. Redis warns against externally reachable, unhardened instances. [Redis security](https://redis.io/docs/latest/operate/oss_and_stack/management/security/)
- Do not let page-cache eviction silently remove overload-protection counters.
- Prefer separate Redis instances or services when page-cache and rate-limit state have different eviction and failure requirements.
- Numbered Redis databases do not provide memory isolation.
- Define cache-outage behavior and keep the proxy in-flight ceiling independent of Redis.

### 5. Conditional HTTP and downstream cache headers

- `ConditionalGetMiddleware` can turn a response with `ETag` or `Last-Modified` into `304`.
- An ETag calculated from the completed response still pays the DB, GIS, and rendering cost.
- Django’s `condition()`, `etag()`, and `last_modified()` decorators can bail out **before** the view only when their validator function is cheap. [Django conditional processing](https://docs.djangoproject.com/en/5.1/topics/conditional-view-processing/)
- A route’s `ruta_last_updated` or `import_timestamp` is a starting point, but it is not sufficient if visible stops, schedules, POIs, administrative areas, or reviews changed.
- Create one trustworthy page-version value, or rely on bounded cache TTL until that exists.
- Once public responses are truly anonymous, add conservative `Cache-Control` and `Vary` semantics.
- Do not use `Vary: Cookie` casually on public pages:
  - it can protect personalization;
  - it also fragments cache cardinality;
  - it reduces sharing between crawler and user responses.
- Django provides `cache_control`, `vary_on_headers`, and `vary_on_cookie` helpers. [Django HTTP decorators](https://docs.djangoproject.com/en/5.1/topics/http/decorators/)
- Googlebot supports caching on recrawls, and `304` saves transfer. It does not replace server-side caching or admission control. [Google crawler overview](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers)

### 6. Query and schema work for cache misses

Profile before changing queries or adding indexes.

Candidate work, in likely payoff order:

1. **Move canonical redirects ahead of GIS work.**
2. **Avoid evaluating an entire QuerySet when only one row is needed.** Replace truth-testing followed by `[0]` with a single limited query where appropriate (`apps/core/views.py:126-131,194-199`).
3. **Remove `order_by('?')` from hot request paths** (`apps/core/views.py:296-305`; `apps/catastro/views.py:187-194`) in favor of a stable or precomputed rotation if randomness is not essential. A stable bounded result also makes caching effective.
4. **Audit `.only()` and `.defer()` against every accessed field.** For example, line URL generation accesses fields omitted from `linea_q` (`apps/core/views.py:88-97`; `apps/core/models.py:49-63`), potentially creating deferred-field queries.
5. **Use `select_related` and `prefetch_related` only where evaluation proves N+1 work.** Django recommends profiling and `QuerySet.explain()` rather than assuming. [Django database optimization](https://docs.djangoproject.com/en/5.1/topics/db/optimization/)
6. **Confirm GiST indexes are used by every hot `ST_Intersects` and `ST_DWithin` plan.** PostGIS documents that `ST_DWithin` includes an index-usable bounding-box comparison, but casts, functions, or poor selectivity can still prevent the desired plan. [PostGIS `ST_DWithin`](https://postgis.net/docs/en/ST_DWithin.html)
7. **Evaluate B-tree and composite indexes for actual lookup predicates**, especially:
   - line `osm_id`;
   - route `osm_id`;
   - POI `(osm_type, osm_id)`;
   - trigram indexes for similarity lookup.
8. **Check uniqueness assumptions before adding constraints.** Route code explicitly allows duplicate OSM IDs (`apps/core/views.py:170-176`).
9. **Bound API parameter radius and result count.** Cache only safe, deterministic searches; do not cache arbitrary high-cardinality geospatial requests.
10. **Add API throttles as defense in depth.** DRF currently has no configured throttles (`config/settings/base.py:307-314`).
11. **Add indexes in a production-aware migration.** PostgreSQL notes that ordinary index creation blocks writes; `CREATE INDEX CONCURRENTLY` permits writes but costs extra work and has caveats. [PostgreSQL index introduction](https://www.postgresql.org/docs/16/indexes-intro.html)

### 7. Gunicorn and PostgreSQL safeguards

Django says each thread maintains its own database connection and the database must support at least as many simultaneous connections as worker threads. [Django persistent connections](https://docs.djangoproject.com/en/5.1/ref/databases/#persistent-connections)

Here, `10 × 100` means up to roughly 1,000 Django thread-local connections before other jobs or replicas. The commented psycopg pool—`min_size=10`, `max_size=100`—would also multiply per process and must not be enabled unchanged.

#### Gunicorn

- Benchmark a much smaller worker/thread matrix based on:
  - CPU;
  - memory;
  - PostgreSQL capacity;
  - the blocking fraction of requests.
- Gunicorn’s worker guidance is a starting heuristic, not permission to maximize threads. [Gunicorn design](https://docs.gunicorn.org/en/stable/design.html#how-many-workers)
- Set `max_requests` plus `max_requests_jitter` only to contain memory growth and stagger worker restarts.
- Gunicorn documents these as restart controls; they do not throttle requests. [Gunicorn settings: max requests](https://docs.gunicorn.org/en/stable/settings.html#max-requests) [Gunicorn settings: jitter](https://docs.gunicorn.org/en/stable/settings.html#max-requests-jitter)
- Keep Gunicorn `timeout` aligned with proxy and DB timeouts, but understand that it kills silent workers rather than safely cancelling every PostgreSQL statement. [Gunicorn settings: timeout](https://docs.gunicorn.org/en/stable/settings.html#timeout)
- Roll changes one variable at a time.
- Use graceful shutdown and readiness checks.
- Retain enough spare capacity for worker recycling.

#### PostgreSQL

- `work_mem=128MB` is per sort or hash operation.
- One query can use it multiple times, while many sessions do so concurrently.
- PostgreSQL explicitly warns that total use can be many times `work_mem`. [PostgreSQL resource consumption](https://www.postgresql.org/docs/16/runtime-config-resource.html)
- Lower the web default after measuring.
- Grant higher values locally to controlled batch or import jobs if required.
- Replace `max_connections=7000` with a capacity derived from:
  - measured active web threads or pool size;
  - maintenance and batch needs;
  - available RAM;
  - emergency reserved slots.
- PostgreSQL uses a backend process per connection and provides reserved and superuser connection slots for emergency access. [PostgreSQL connection settings](https://www.postgresql.org/docs/16/runtime-config-connection.html)
- Reducing Gunicorn concurrency or connection pooling must happen before, or in the same rollout as, reducing `max_connections`.
- A 300-second global `statement_timeout` is too permissive as the only web guardrail.
- Use:
  - a measured web-role or database `statement_timeout`;
  - a shorter `lock_timeout`;
  - `idle_in_transaction_session_timeout`.
- PostgreSQL documents their distinct behavior and cautions against indiscriminate global settings. [PostgreSQL client defaults](https://www.postgresql.org/docs/16/runtime-config-client.html)
- `ATOMIC_REQUESTS=True` wraps even read pages in transactions. Django documents per-request transaction overhead as traffic increases.
- After profiling, consider exempting safe read-only public views rather than removing transaction guarantees globally. [Django transactions](https://docs.djangoproject.com/en/5.1/topics/db/transactions/#tying-transactions-to-http-requests)
- `SET STATEMENT_TIMEOUT=30000` in `apps/core/managers.py:35` is session-scoped, not transaction-local.
- With persistent connections, that setting can affect later work on the same thread.
- Prefer explicit role-level or transaction-local policy in a future implementation.

### 8. Future Docker Compose changes

These changes were not applied.

After the chosen cache and live proxy topology are confirmed, a production change should consider:

- pinning the cache image to an intended major or minor line rather than an unbounded tag;
- replacing the inert cache service with:
  - a configured modern Memcached service; or
  - Redis with `maxmemory`, eviction, cache-appropriate persistence, health checking, and no host-published port;
- separating page-cache state from rate-limit state when their eviction and failure requirements differ;
- adding PostgreSQL and cache health checks;
- using long-form `depends_on: condition: service_healthy`.

Short `depends_on` starts dependencies but does not wait for readiness. [Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)

Also consider:

- restart policies;
- graceful stop periods;
- tested web readiness and liveness checks;
- an internal back-tier network for DB and cache;
- attaching web to both the back-tier and the actual external Traefik network.

Docker documents that service-to-service traffic uses container ports and that `internal: true` isolates a network from external connectivity. [Docker Compose networking](https://docs.docker.com/compose/how-tos/networking/)

Set measured CPU and memory limits and reservations with enough headroom for PostgreSQL shared memory and Redis overhead. Compose supports `cpus` and `mem_limit`; limits chosen without measurement can create a new outage mode. [Docker Compose services](https://docs.docker.com/reference/compose-file/services/)

Finally:

- serve static files, media, and robots through a dedicated static service or CDN rather than Django;
- remember that Traefik routes to services but is not itself a general file server;
- add Traefik routers and middlewares only in the repository or infrastructure configuration that actually owns Traefik;
- confirm the deployed Traefik version before relying on Redis-backed or distributed rate-limit options.

## Rollout and acceptance checklist

1. Capture at least one normal period and one crawler spike.
2. Record:
   - request rate;
   - canonical-redirect ratio;
   - top query-parameter sets;
   - Gunicorn busy workers and threads;
   - DB active and waiting sessions;
   - query totals;
   - CPU and RAM;
   - normal-user p95 latency, error rate, and conversion.
3. Verify crawler identity. Do not infer “Googlebot” or another privileged class from User-Agent alone.
4. Deploy canonical host, query, and path redirects plus static and robots offload.
5. Confirm:
   - no redirect loops;
   - no redirect chains;
   - no API parameter loss;
   - no language loss.
6. Update robots and sitemap using Search Console and Bing testing.
7. Watch indexed canonical and crawl statistics.
8. Do not remove valuable page classes solely because they are expensive.
9. Introduce low-level caching for one expensive route family.
10. Require:
    - correct anonymous and authenticated output;
    - correct language output;
    - bounded key count;
    - high hit ratio;
    - clean invalidation;
    - acceptable cold-miss latency.
11. Add proxy in-flight and token-bucket controls in report-only or very-high-threshold mode if supported, then lower them toward measured capacity.
12. Verify that:
    - shared-IP or NAT users can burst normally;
    - overload receives `429` before Django;
    - cheap health and static traffic remains available.
13. Reduce Gunicorn threads and PostgreSQL connection and memory ceilings together in small steps.
14. Exercise:
    - cache-down behavior;
    - DB-slow behavior;
    - rolling restart;
    - worker recycling;
    - expired-cache stampede;
    - crawler spike.
15. Optimize the top remaining `pg_stat_statements` entries and inspect plans after each schema or query change.
16. Roll back any stage if:
    - normal-user p95, error rate, or conversion regresses;
    - cache correctness fails;
    - PostgreSQL waits increase;
    - index or crawler coverage changes outside the agreed policy.

## Bottom line

The largest safe wins are to:

1. stop duplicate and noncanonical work;
2. reduce advertised crawl inventory;
3. cache deterministic anonymous page data;
4. reject excess concurrency before Gunicorn.

Redis is an enabler, not the fix by itself. Gunicorn recycling is reliability hygiene, not load control. PostgreSQL’s current connection and `work_mem` ceilings make excessive application concurrency more dangerous; right-size them only after edge admission control and caching reveal the true steady-state demand.
