(function () {
  const root = document.createElement('div');
  root.id = 'site-version-footer';
  root.style.cssText = 'position:fixed;bottom:8px;right:8px;background:#111;color:#fff;font:12px/1.2 Arial,sans-serif;padding:6px 8px;border-radius:8px;opacity:.82;z-index:99999';

  fetch('/assets/site-version.json', { cache: 'no-store' })
    .then((r) => (r.ok ? r.json() : null))
    .then((v) => {
      if (!v) return;
      root.textContent = `v ${v.commit_short || 'unknown'} · ${v.updated_utc || ''}`;
      document.body.appendChild(root);
    })
    .catch(() => {});
})();
