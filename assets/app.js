(() => {
  'use strict';
  // Load giscus comments only on article pages where they are configured.
  const comments = document.getElementById('giscus');
  if (!comments) return;
  const script = document.createElement('script');
  script.src = 'https://giscus.app/client.js';
  const attributes = {
    repo: comments.dataset.repo, 'repo-id': comments.dataset.repoId,
    category: comments.dataset.category, 'category-id': comments.dataset.categoryId,
    mapping: 'specific', term: `fieldnotes/${comments.dataset.article}`,
    strict: '1', 'reactions-enabled': '1', 'emit-metadata': '0',
    'input-position': 'top', theme: 'preferred_color_scheme',
    lang: document.body.dataset.lang === 'en' ? 'en' : 'zh-CN', loading: 'lazy'
  };
  for (const [key, value] of Object.entries(attributes)) script.setAttribute(`data-${key}`, value);
  script.crossOrigin = 'anonymous';
  script.async = true;
  comments.appendChild(script);
})();
