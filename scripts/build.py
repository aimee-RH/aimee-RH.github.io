"""Build a bilingual, dependency-free GitHub Pages publication."""
from __future__ import annotations
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_site'
TOPICS = {'Training': '训练与数据', 'Memory': '记忆', 'Science': '科学探索', 'Infrastructure': '基础设施', 'Architecture': '模型架构', 'Safety': '对齐与安全', 'Multimodal': '多模态', 'Generation': '生成模型', 'Robotics': '机器人', 'Evaluation': '评估', 'Retrieval': '检索'}

def esc(value):
    return html.escape(str(value), quote=True)

def load_articles(path=ROOT / 'content/articles.json'):
    items = json.loads(path.read_text())
    seen = set()
    required = {'id', 'issue', 'published', 'source', 'topic', 'minutes', 'original', 'url', 'title', 'intro', 'body', 'limits', 'path'}
    for a in items:
        if not required <= a.keys() or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', a['id']) or a['id'] in seen:
            raise ValueError('Invalid or duplicate article')
        seen.add(a['id'])
        if urlparse(a['url']).scheme != 'https' or not urlparse(a['url']).netloc:
            raise ValueError('Article sources must be absolute HTTPS URLs')
        if a['topic'] not in TOPICS or not isinstance(a['minutes'], int) or not 1 <= a['minutes'] <= 60:
            raise ValueError('Invalid topic or reading time')
        if date.fromisoformat(a['published']) > date.fromisoformat(a['issue']):
            raise ValueError('Original publication date must not follow the issue date')
        for key in ('title', 'intro', 'body', 'limits', 'path'):
            for lang in ('zh', 'en'):
                val = a[key].get(lang)
                if not val or (key == 'body' and (not isinstance(val, list) or not all(isinstance(p, str) and p for p in val))):
                    raise ValueError('Both languages must contain complete content')
    return sorted(items, key=lambda a: a['issue'], reverse=True)

def route(lang, article=None):
    return ('/en' if lang == 'en' else '') + (f'/read/{article}/' if article else '/')

def label(lang, zh, en):
    return zh if lang == 'zh' else en

def icon(name):
    shapes = {
        'book': '<path d="M3 4.5c3-1 6-.5 9 1.5 3-2 6-2.5 9-1.5v15c-3-1-6-.5-9 1.5-3-2-6-2.5-9-1.5z"/><path d="M12 6v15"/>',
        'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
        'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 1v2m0 18v2M1 12h2m18 0h2M4 4l1.5 1.5m13 13L20 20M4 20l1.5-1.5m13-13L20 4"/>',
        'chat': '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z"/><path d="M7 10h9M7 14h6"/>',
        'pen': '<path d="m15 4 5 5M4 20l4-1 12-12a3 3 0 0 0-4-4L4 15z"/>',
        'copy': '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
        'rss': '<circle cx="5" cy="19" r="1"/><path d="M4 4a16 16 0 0 1 16 16M4 10a10 10 0 0 1 10 10"/>',
        'menu': '<path d="M4 6h16M4 12h16M4 18h16"/>',
        'close': '<path d="m6 6 12 12M6 18 18 6"/>'}
    return '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + shapes[name] + '</svg>'

def date_text(value, lang):
    d = date.fromisoformat(value)
    return f'{d.month} 月 {d.day} 日' if lang == 'zh' else d.strftime('%b %d').replace(' 0', ' ')

def note_for(article):
    file = ROOT / 'content/notes' / (article['id'] + '.json')
    return json.loads(file.read_text()) if file.exists() else {'zh': '', 'en': ''}

def sidebar(lang, articles, current, cfg):
    home = route(lang)
    topics = ''.join(f'<a class="topic-link" href="{home}?topic={quote(t)}"><span>{esc(TOPICS[t] if lang == "zh" else t)}</span><span class="count">{sum(a["topic"] == t for a in articles)}</span></a>' for t in TOPICS if any(a['topic'] == t for a in articles))
    issues = sorted({a['issue'] for a in articles}, reverse=True)
    archives = ''.join(f'<a class="archive-link" href="{home}?date={d}"><span class="small-square"></span>{date_text(d, lang)}<span class="count">{sum(a["issue"] == d for a in articles)}</span></a>' for d in issues)
    return f'''<aside class="sidebar" id="sidebar" aria-label="{label(lang, '站点导航', 'Site navigation')}">
      <a class="wordmark" href="{home}"><span class="monogram">a<span>.</span></span><span>AI Fieldnotes<small>BY AIMEE GAO</small></span></a>
      <div class="sidebar-intro">{label(lang, '一间开放的 AI 阅读室。', 'An open notebook on AI.')}</div>
      <nav><a class="main-nav {'active' if not current else ''}" href="{home}">{icon('book')}{label(lang,'阅读笔记','Reading notes')}<span class="count">{len(articles)}</span></a>
      <a class="main-nav" href="{home}about/">{icon('sun')}{label(lang,'关于我','About Aimee')}</a>
      <p class="nav-caption">{label(lang,'按主题探索','EXPLORE TOPICS')}</p>{topics}
      <p class="nav-caption">{label(lang,'每日归档','DAILY ARCHIVE')}</p>{archives}</nav>
      <div class="sidebar-bottom"><span class="leaf-mark">✳</span><p>{label(lang,'保持好奇，把思考写下来。','Stay curious. Leave a margin.')}</p><a href="{esc(cfg['github'])}" target="_blank" rel="noopener">GitHub</a><span>·</span><a href="{esc(cfg['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a></div>
    </aside>'''

def shell(lang, articles, cfg, body, title, description, path, current=None):
    alternate = route('en' if lang == 'zh' else 'zh', current) if path != 'about/' else ('/en/about/' if lang == 'zh' else '/about/')
    actual = route(lang, current) if path != 'about/' else ('/en/about/' if lang == 'en' else '/about/')
    canonical = cfg['url'] + actual
    nav = sidebar(lang, articles, current, cfg)
    return f'''<!doctype html><html lang="{'zh-CN' if lang == 'zh' else 'en'}"><head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{esc(title)} · AI Fieldnotes</title><meta name="description" content="{esc(description)}">
      <meta name="theme-color" content="#176b58"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
      <link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="{'en' if lang == 'zh' else 'zh-CN'}" href="{cfg['url']}{alternate}">
      <meta property="og:type" content="{'article' if current else 'website'}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:site_name" content="AI Fieldnotes">
      <link rel="alternate" type="application/rss+xml" title="AI Fieldnotes" href="/feed.xml">
      <link rel="stylesheet" href="/assets/style.css"><script src="/assets/app.js" defer></script>
      </head><body data-lang="{lang}" data-article="{esc(current or '')}">
      <a class="skip-link" href="#main">{label(lang,'跳到正文','Skip to content')}</a>{nav}<button class="scrim" aria-label="{label(lang,'关闭目录','Close navigation')}" hidden></button>
      <div class="workspace"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" aria-label="{label(lang,'打开目录','Open navigation')}" aria-expanded="false">{icon('menu')}</button><span>FIELDNOTES</span><span class="crumb-divider">/</span><span>{label(lang,'阅读、提问、连接','Read. Question. Connect.')}</span></div>
      <div class="top-actions"><a class="language" href="{alternate}" lang="{'en' if lang == 'zh' else 'zh'}">{label(lang,'EN','中文')}</a><a class="icon-button" href="/feed.xml" aria-label="RSS">{icon('rss')}</a><a class="profile-dot" href="{route(lang)}about/" aria-label="About Aimee">A</a></div></header>
      <main id="main">{body}</main><footer class="footer"><span>© {date.today().year} Aimee Gao</span><span>{label(lang,'AI 辅助整理 · 原文归原作者所有','AI-assisted summaries · Original work belongs to its authors')}</span><a href="https://github.com/{cfg['repository']}">{label(lang,'本站源码','Source')}</a></footer></div>
      <div class="toast" role="status" aria-live="polite"></div></body></html>'''

def art_svg():
    return '''<svg class="book-art" viewBox="0 0 280 220" fill="none" aria-hidden="true"><circle cx="147" cy="109" r="85" fill="#e1f2e9"/><circle cx="212" cy="46" r="19" fill="#d6ed9e"/><path d="M58 69q44-13 85 12 35-24 78-11l-9 107q-35-9-69 12-44-21-89-12z" fill="white" stroke="#176b58" stroke-width="2"/><path d="M143 81v108M74 95l48 10M73 111l49 10M72 127l35 8M162 104l40-8M161 120l39-7M162 136l25-4" stroke="#83ad9b" stroke-width="2" stroke-linecap="round"/><path d="m196 146 26-70 9-8 3 12-27 70-12 12z" fill="#176b58"/><path d="m222 76 11 4" stroke="#d6ed9e" stroke-width="3"/><path d="M39 49q21 0 22-22-23 1-22 22zM49 51l8-14" fill="#d5e99b" stroke="#176b58"/><path d="m250 143-9 4m9-15-8 3M104 30v13m-6-6h13" stroke="#176b58" stroke-width="1.5" stroke-linecap="round"/><path d="M59 197q87 9 161-1" stroke="#c9ddd2" stroke-width="2" stroke-linecap="round"/></svg>'''

def home_page(lang, articles, cfg):
    latest = max(a['issue'] for a in articles)
    featured = articles[0]
    chips = ''.join(f'<button class="filter" data-topic="{t}">{esc(TOPICS[t] if lang == "zh" else t)}</button>' for t in ('Training','Memory','Science','Architecture','Safety'))
    rows = []
    for a in articles:
        search = esc(' '.join([a['title'][lang], a['original'], a['source'], a['intro'][lang], a['topic'], TOPICS[a['topic']]]).lower())
        rows.append(f'''<article class="entry" data-topic="{a['topic']}" data-date="{a['issue']}" data-search="{search}"><div class="entry-date"><span>{date_text(a['issue'],lang)}</span><small>{a['issue'][:4]}</small></div><div class="entry-content"><div class="entry-meta"><span class="tag">{TOPICS[a['topic']] if lang == 'zh' else a['topic']}</span><span>{esc(a['source'])}</span><span>{a['minutes']} {label(lang,'分钟','min')}</span></div><h3><a href="{route(lang,a['id'])}">{esc(a['title'][lang])}</a></h3><p>{esc(a['intro'][lang])}</p><div class="entry-bottom"><span class="original-title">{esc(a['original'])}</span><span class="note-indicator">{icon('pen')}{label(lang,'旁注与讨论','Notes & discussion')}</span></div></div></article>''')
    body = f'''<div class="home-grid"><section class="home-content"><div class="hero"><div class="hero-text"><p class="eyebrow">A PERSONAL LEARNING JOURNAL</p><h1>{label(lang,'读得更广，<br>想得更深。','Stay curious.<br>Think in public.')}</h1><p class="hero-subtitle">{label(lang,'我是 Aimee。这里收集值得读的 AI 研究，<br>也给疑问、连接和自己的判断留一点空白。','I’m Aimee. A collection of AI research worth reading,<br>with room for questions, connections, and a point of view.')}</p><a class="text-link" href="{route(lang)}about/">{label(lang,'关于这个笔记本','About this notebook')}</a></div>{art_svg()}</div>
      <a class="featured" href="{route(lang,featured['id'])}"><div><span class="eyebrow">{label(lang,'本期推荐','FROM THE LATEST EDITION')}</span><h2>{esc(featured['title'][lang])}</h2><p>{esc(featured['intro'][lang])}</p></div><span class="featured-mark">✳</span></a>
      <div class="section-top"><h2>{label(lang,'最近阅读','The reading desk')}</h2><span id="result-count">{len(articles)} {label(lang,'篇笔记','reading notes')}</span></div>
      <div class="filter-toolbar"><div class="filters" role="group" aria-label="{label(lang,'主题筛选','Filter by topic')}"><button class="filter selected" data-topic="all">{label(lang,'全部','All notes')}</button>{chips}</div><label class="search">{icon('search')}<input type="search" id="search" aria-label="{label(lang,'搜索文章','Search notes')}" placeholder="{label(lang,'搜索研究、主题…','Search research…')}"></label></div>
      <div class="active-filter" hidden></div><div class="entries">{''.join(rows)}</div><div class="empty-search" hidden><h3>{label(lang,'还没有找到对应笔记','No matching notes yet')}</h3><p>{label(lang,'试试其他关键词，或清除主题和日期筛选。','Try another keyword, or clear the topic and date filters.')}</p><button class="button" id="clear-filters">{label(lang,'清除筛选','Clear filters')}</button></div></section>
      <aside class="home-rail"><div class="about-card"><span class="mini-avatar">A<span>✳</span></span><p class="eyebrow">THE PERSON IN THE MARGINS</p><h2>Aimee Gao</h2><p>Georgia Tech · M.S. 2027</p><p class="about-description">{label(lang,'从 AI 研究出发，探索工程、产品与人与技术之间的连接。','Exploring the connections between AI research, engineering, products, and people.')}</p><a class="text-link" href="{route(lang)}about/">{label(lang,'认识 Aimee','Meet Aimee')}</a></div>
      <div class="margin-card"><span class="eyebrow">IN THE MARGINS</span><h3>{label(lang,'不急着得出结论。','Leave room for a question.')}</h3><p>{label(lang,'每篇文章旁边，都留有作者笔记的位置。阅读之后，让问题继续生长。','Every article has room for author’s notes. A question is a useful place to begin.')}</p><div class="paper-lines"><span></span><span></span><span></span></div></div>
      <div class="reading-guide"><p class="eyebrow">{label(lang,'如何阅读','HOW TO READ')}</p><p>{label(lang,'先看研究在解决什么，再看证据和边界。原文发布日期与精选日期分别保留。','Start with the problem, then examine the evidence and limitations. Original publication dates remain separate from edition dates.')}</p><p class="latest">{label(lang,'最近一期','Latest edition')} · {latest}</p></div></aside></div>'''
    return shell(lang, articles, cfg, body, label(lang,'Aimee 的 AI 阅读笔记','AI reading notes by Aimee'), label(lang,'AI 研究精选、中英双语阅读笔记、个人旁注与公开讨论。','Bilingual AI research notes, personal reflections, and open discussion.'), '')

def article_page(lang, a, articles, cfg):
    note = note_for(a).get(lang, '').strip()
    note_html = ''.join(f'<p>{esc(p)}</p>' for p in note.split('\n\n') if p.strip()) if note else f'''<p class="unwritten">{label(lang,'Aimee 还没有发布这篇的个人旁注。','Aimee hasn’t published a personal note on this piece yet.')}</p><ul class="note-prompts"><li>{label(lang,'哪里让我改变了看法？','What changed my mind?')}</li><li>{label(lang,'哪些证据还不充分？','Where is the evidence incomplete?')}</li><li>{label(lang,'接下来想验证什么？','What would I test next?')}</li></ul>'''
    edit = f'https://github.com/{cfg["repository"]}/edit/main/content/notes/{a["id"]}.json'
    g = cfg.get('giscus', {})
    ready = bool(g.get('enabled') and g.get('repoId') and g.get('categoryId'))
    discussion_link = f'https://github.com/{cfg["repository"]}/discussions?discussions_q={quote(a["id"])}'
    discussion = f'<div class="giscus" id="giscus" data-repo="{esc(cfg["repository"])}" data-repo-id="{esc(g.get("repoId", ""))}" data-category="{esc(g.get("category", "General"))}" data-category-id="{esc(g.get("categoryId", ""))}"></div>' if ready else f'<div class="discussion-fallback"><p>{label(lang,"站内评论正在配置中。现在也可以在 GitHub Discussions 交流。","Embedded comments are being connected. You can already start a conversation in GitHub Discussions.")}</p><a class="button" target="_blank" rel="noopener" href="{discussion_link}">{label(lang,"打开 GitHub 讨论区","Open GitHub Discussions")}</a></div>'
    more = [x for x in articles if x['id'] != a['id']][:2]
    related = ''.join(f'<a href="{route(lang,x["id"])}"><span>{esc(TOPICS[x["topic"]] if lang == "zh" else x["topic"])}</span>{esc(x["title"][lang])}</a>' for x in more)
    body = f'''<div class="reader-layout"><article class="reader"><a class="back-link" href="{route(lang)}">{label(lang,'返回阅读笔记','Back to reading notes')}</a><div class="article-category">{esc(TOPICS[a['topic']] if lang == 'zh' else a['topic'])}<span>·</span>{a['minutes']} {label(lang,'分钟重点阅读','min focused reading')}</div><h1>{esc(a['title'][lang])}</h1><p class="article-deck">{esc(a['intro'][lang])}</p>
      <div class="article-byline"><span class="byline-avatar">A</span><div><strong>AI Fieldnotes</strong><span>{label(lang,'精选于','Curated')} {a['issue']} · {label(lang,'AI 辅助整理','AI-assisted summary')}</span></div><button class="icon-button share-button" aria-label="{label(lang,'复制文章链接','Copy article link')}">{icon('copy')}</button></div>
      <div class="source-card"><p class="eyebrow">{label(lang,'原始研究 / 文章','ORIGINAL SOURCE')}</p><a href="{esc(a['url'])}" target="_blank" rel="noopener">{esc(a['original'])}</a><p>{esc(a['source'])}<span>·</span>{label(lang,'原始发布','Published')} {a['published']}</p><a class="source-button" href="{esc(a['url'])}" target="_blank" rel="noopener">{label(lang,'阅读原文','Read original')}</a></div>
      <section class="article-prose" id="findings"><h2>{label(lang,'方法与发现','The idea & the evidence')}</h2>{''.join('<p>'+esc(p)+'</p>' for p in a['body'][lang])}</section>
      <section class="limitations" id="limits"><span class="eyebrow">{label(lang,'保留一点谨慎','WHERE THE EVIDENCE ENDS')}</span><h2>{label(lang,'局限与待验证','Limits & open questions')}</h2><p>{esc(a['limits'][lang])}</p></section>
      <section class="reading-path"><span>{icon('book')}</span><div><strong>{label(lang,'建议阅读路径','Suggested reading path')}</strong><p>{esc(a['path'][lang])}</p></div></section>
      <section class="discussion" id="discussion"><div class="section-top"><h2>{label(lang,'一起讨论','Keep the conversation going')}</h2>{icon('chat')}</div><p class="discussion-intro">{label(lang,'补充证据、提出不同看法，或分享你想到的连接。使用 GitHub 账号参与。','Add evidence, challenge an interpretation, or share a connection. Join with your GitHub account.')}</p>{discussion}</section>
      <section class="related"><p class="eyebrow">{label(lang,'接着读','CONTINUE READING')}</p>{related}</section></article>
      <aside class="notes-rail"><div class="on-this-page"><p class="eyebrow">{label(lang,'本文目录','ON THIS PAGE')}</p><a href="#findings">{label(lang,'方法与发现','The idea & the evidence')}</a><a href="#limits">{label(lang,'局限与待验证','Limits & open questions')}</a><a href="#discussion">{label(lang,'读者讨论','Discussion')}</a></div>
      <section class="author-note"><div class="note-heading">{icon('pen')}<span>{label(lang,'Aimee 的旁注','Aimee’s margin notes')}</span></div><span class="note-label">{label(lang,'作者的观点 · 与 AI 整理分开','AUTHOR’S VIEW · SEPARATE FROM THE SUMMARY')}</span><div class="note-body">{note_html}</div><a class="edit-note" href="{edit}" target="_blank" rel="noopener">{label(lang,'作者编辑旁注','Edit author’s note')}</a></section>
      <section class="scratch"><details><summary>{label(lang,'我的阅读草稿','My reading scratchpad')}</summary><label for="scratchpad">{label(lang,'只保存在当前浏览器，不会公开或跨设备同步。','Saved only in this browser. Not public or synced across devices.')}</label><textarea id="scratchpad" rows="6" placeholder="{label(lang,'记下一个问题，或一个还没成形的想法…','A question, a connection, an unfinished thought…')}"></textarea><div class="scratch-actions"><span id="scratch-status" role="status"></span><button class="text-button" id="export-draft">{label(lang,'下载草稿','Export draft')}</button></div></details></section>
      </aside></div>'''
    return shell(lang, articles, cfg, body, a['title'][lang], a['intro'][lang], '', a['id'])

def about_page(lang, articles, cfg):
    body = f'''<div class="about-page"><p class="eyebrow">ABOUT THE NOTEBOOK</p><h1>{label(lang,'你好，我是 Aimee。','Hi, I’m Aimee.')}</h1><p class="about-lead">{label(lang,'把持续阅读，变成可以分享和讨论的思考。','Turning a reading habit into ideas we can share and discuss.')}</p><div class="about-bio"><span class="mini-avatar">A<span>✳</span></span><div><h2>Aimee Gao</h2><p>Georgia Tech · M.S. 2027</p><p>AI · Engineering · Product</p></div></div>
      <h2>{label(lang,'这里会记录什么','What lives here')}</h2><p>{label(lang,'这个笔记本关注 AI 研究与应用：从训练、推理和记忆，到多模态、安全与科学探索。每期精选保留原文链接、发布日期、主要方法、证据与局限，方便继续读下去。','This notebook follows AI research and applications: training, inference, memory, multimodal systems, safety, and science. Each reading note keeps the original source, publication date, methods, evidence, and limitations close at hand.')}</p>
      <h2>{label(lang,'怎样区分整理与观点','Summaries and perspectives')}</h2><p>{label(lang,'正文是 AI 辅助整理的阅读摘要，不代表我已独立复现实验。右侧「Aimee 的旁注」专门留给我自己的判断、问题与连接；没有写过的地方会保持空白。欢迎在文章下方补充证据或提出不同看法。','The main text contains AI-assisted reading summaries and does not imply independent reproduction. The margin is reserved for my own judgments, questions, and connections; unwritten notes stay unwritten. Evidence and different perspectives are welcome in the discussion.')}</p>
      <h2>{label(lang,'一起交流','Let’s connect')}</h2><div class="connect-links"><a class="button" href="{esc(cfg['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a><a class="button secondary" href="{esc(cfg['github'])}" target="_blank" rel="noopener">GitHub</a><a class="text-link" href="/feed.xml">RSS</a></div><p class="about-credit">{label(lang,'原始研究与文章归各自作者所有。本站提供简短摘要与原文入口，不转载全文。','Original work belongs to its authors. This site offers short summaries and links, not full-text republication.')}</p></div>'''
    return shell(lang, articles, cfg, body, label(lang,'关于 Aimee','About Aimee'), label(lang,'Aimee Gao 的 AI 阅读笔记与公开学习。','Aimee Gao’s AI reading notebook.'), 'about/')

def write_page(path, text):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

def build():
    cfg = json.loads((ROOT / 'site.json').read_text())
    articles = load_articles()
    OUT.mkdir(exist_ok=True)
    # Remove only generated output inside this checkout; never source or drafts.
    for p in OUT.iterdir():
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(ROOT / 'assets', OUT / 'assets')
    paths = []
    for lang in ('zh', 'en'):
        base = 'en/' if lang == 'en' else ''
        write_page(base + 'index.html', home_page(lang, articles, cfg)); paths.append('/' + base)
        write_page(base + 'about/index.html', about_page(lang, articles, cfg)); paths.append('/' + base + 'about/')
        for a in articles:
            dest = base + 'read/' + a['id'] + '/index.html'
            write_page(dest, article_page(lang, a, articles, cfg)); paths.append('/' + base + 'read/' + a['id'] + '/')
    write_page('404.html', '<!doctype html><html lang="en"><meta charset="utf-8"><title>Page not found</title><body><h1>This page hasn’t been written yet.</h1><a href="/">Back to AI Fieldnotes</a></body></html>')
    write_page('.nojekyll', '')
    write_page('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {cfg["url"]}/sitemap.xml\n')
    write_page('sitemap.xml', '<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{xml_escape(cfg["url"] + p)}</loc></url>' for p in paths) + '</urlset>')
    rss = ''.join(f'<item><title>{xml_escape(a["title"]["zh"])}</title><link>{cfg["url"]}{route("zh",a["id"])}</link><guid isPermaLink="true">{cfg["url"]}{route("zh",a["id"])}</guid><description>{xml_escape(a["intro"]["zh"] + " / " + a["intro"]["en"])}</description></item>' for a in articles)
    write_page('feed.xml', f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>AI Fieldnotes · Aimee Gao</title><link>{cfg["url"]}</link><description>Bilingual AI reading notes and personal perspectives.</description>{rss}</channel></rss>')
    print(f'Built {len(paths)} pages, {len(articles)} bilingual notes, RSS and sitemap into {OUT}')

if __name__ == '__main__':
    build()
