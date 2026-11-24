(() => {
  'use strict';
  const en = document.body.dataset.lang === 'en';
  const say = (zh, english) => en ? english : zh;
  const toast = message => {
    const el = document.querySelector('.toast');
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(window.fieldnotesToast);
    window.fieldnotesToast = setTimeout(() => el.classList.remove('show'), 2600);
  };
  const menu = document.querySelector('.mobile-menu');
  const sidebar = document.querySelector('.sidebar');
  const scrim = document.querySelector('.scrim');
  const closeMenu = () => {
    sidebar.classList.remove('is-open');
    menu.setAttribute('aria-expanded', 'false');
    scrim.hidden = true;
  };
  menu?.addEventListener('click', () => {
    const open = !sidebar.classList.contains('is-open');
    sidebar.classList.toggle('is-open', open);
    menu.setAttribute('aria-expanded', String(open));
    scrim.hidden = !open;
  });
  scrim?.addEventListener('click', closeMenu);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
  matchMedia('(min-width: 731px)').addEventListener('change', e => { if (e.matches) closeMenu(); });

  const entries = [...document.querySelectorAll('.entry')];
  const search = document.getElementById('search');
  if (search) {
    const params = new URLSearchParams(location.search);
    let topic = params.get('topic') || 'all';
    let issue = params.get('date') || '';
    search.value = params.get('q') || '';
    const allTopics = new Set(entries.map(el => el.dataset.topic));
    if (topic !== 'all' && !allTopics.has(topic)) topic = 'all';
    if (issue && !entries.some(el => el.dataset.date === issue)) issue = '';
    const filter = () => {
      const q = search.value.trim().toLowerCase();
      let count = 0;
      for (const entry of entries) {
        const visible = (topic === 'all' || entry.dataset.topic === topic)
          && (!issue || entry.dataset.date === issue)
          && (!q || entry.dataset.search.includes(q));
        entry.hidden = !visible;
        count += Number(visible);
      }
      document.getElementById('result-count').textContent = `${count} ${say('篇笔记', 'reading notes')}`;
      document.querySelector('.empty-search').hidden = count !== 0;
      document.querySelectorAll('.filter').forEach(el => {
        el.classList.toggle('selected', el.dataset.topic === topic);
        el.setAttribute('aria-pressed', String(el.dataset.topic === topic));
      });
      const active = document.querySelector('.active-filter');
      active.replaceChildren();
      active.hidden = !issue && topic === 'all';
      if (!active.hidden) {
        const text = document.createElement('span');
        text.textContent = `${issue || ''}${issue && topic !== 'all' ? ' · ' : ''}${topic === 'all' ? '' : topic}`;
        const reset = document.createElement('button');
        reset.textContent = say('清除筛选', 'Clear filters');
        reset.addEventListener('click', clearFilters);
        active.append(text, reset);
      }
      const next = new URL(location.href);
      for (const [key, value] of [['q', q], ['topic', topic === 'all' ? '' : topic], ['date', issue]]) {
        if (value) next.searchParams.set(key, value); else next.searchParams.delete(key);
      }
      history.replaceState({}, '', next);
    };
    const clearFilters = () => { topic = 'all'; issue = ''; search.value = ''; filter(); };
    document.querySelectorAll('.filter').forEach(el => el.addEventListener('click', () => { topic = el.dataset.topic; filter(); }));
    document.getElementById('clear-filters').addEventListener('click', clearFilters);
    search.addEventListener('input', filter);
    filter();
  }

  document.querySelector('.share-button')?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(location.origin + location.pathname);
      toast(say('文章链接已复制', 'Article link copied'));
    } catch {
      window.prompt(say('复制文章链接', 'Copy article link'), location.origin + location.pathname);
    }
  });

  const scratch = document.getElementById('scratchpad');
  if (scratch) {
    const key = `aimee-fieldnotes:${document.body.dataset.article}:${document.body.dataset.lang}`;
    const status = document.getElementById('scratch-status');
    const download = document.getElementById('export-draft');
    try { scratch.value = localStorage.getItem(key) || ''; } catch { status.textContent = say('本地存储不可用', 'Local storage unavailable'); }
    download.disabled = !scratch.value;
    scratch.addEventListener('input', () => {
      download.disabled = !scratch.value;
      try {
        localStorage.setItem(key, scratch.value);
        status.textContent = say('已保存至本浏览器', 'Saved in this browser');
      } catch {
        status.textContent = say('未保存，请下载草稿', 'Not saved. Export your draft.');
      }
    });
    download.addEventListener('click', () => {
      if (!scratch.value) return;
      const blob = new Blob([scratch.value], {type: 'text/plain;charset=utf-8'});
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `${document.body.dataset.article}-${document.body.dataset.lang}-draft.txt`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(href), 1000);
    });
  }

  const comments = document.getElementById('giscus');
  if (comments) {
    const script = document.createElement('script');
    script.src = 'https://giscus.app/client.js';
    const attributes = {
      repo: comments.dataset.repo, 'repo-id': comments.dataset.repoId,
      category: comments.dataset.category, 'category-id': comments.dataset.categoryId,
      mapping: 'specific', term: `fieldnotes/${document.body.dataset.article}`,
      strict: '1', 'reactions-enabled': '1', 'emit-metadata': '0',
      'input-position': 'top', theme: 'light', lang: en ? 'en' : 'zh-CN', loading: 'lazy'
    };
    for (const [key, value] of Object.entries(attributes)) script.setAttribute(`data-${key}`, value);
    script.crossOrigin = 'anonymous';
    script.async = true;
    comments.appendChild(script);
  }
})();
