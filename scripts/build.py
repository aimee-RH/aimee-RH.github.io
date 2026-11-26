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

def date_text(value, lang):
    d = date.fromisoformat(value)
    return f'{d.year}/{d.month:02d}/{d.day:02d}' if lang == 'zh' else d.strftime('%b %d, %Y').replace(' 0', ' ')

def topic_name(topic, lang):
    return TOPICS[topic] if lang == 'zh' else topic

def note_for(article):
    file = ROOT / 'content/notes' / (article['id'] + '.json')
    return json.loads(file.read_text()) if file.exists() else {'zh': '', 'en': ''}

def about_url(lang):
    return route(lang) + 'about/'

def shell(lang, cfg, body, title, description, actual, alternate, is_article=False):
    canonical = cfg['url'] + actual
    other = 'en' if lang == 'zh' else 'zh'
    return f'''<!doctype html><html lang="{'zh-CN' if lang == 'zh' else 'en'}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · AI Fieldnotes</title><meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#4870ac"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="{'en' if lang == 'zh' else 'zh-CN'}" href="{cfg['url']}{alternate}">
<meta property="og:type" content="{'article' if is_article else 'website'}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:site_name" content="AI Fieldnotes">
<link rel="alternate" type="application/rss+xml" title="AI Fieldnotes" href="/feed.xml">
<link rel="stylesheet" href="/assets/style.css"><script src="/assets/app.js" defer></script>
</head><body data-lang="{lang}">
<a class="skip-link" href="#main">{label(lang,'跳到正文','Skip to content')}</a>
<header class="site-header"><a class="site-name" href="{route(lang)}">AI Fieldnotes</a>
<nav aria-label="{label(lang,'站点导航','Site')}"><a href="{route(lang)}">{label(lang,'笔记','Notes')}</a><a href="{about_url(lang)}">{label(lang,'关于','About')}</a><a href="/feed.xml">RSS</a><a href="{alternate}" lang="{other if other == 'en' else 'zh-CN'}">{label(lang,'EN','中文')}</a></nav></header>
<main id="main">{body}</main>
<footer class="site-footer">© {date.today().year} Aimee Gao · {label(lang,'摘要由 AI 辅助整理，原文归原作者所有','AI-assisted summaries; original work belongs to its authors')} · <a href="https://github.com/{cfg['repository']}">{label(lang,'源码','Source')}</a></footer>
</body></html>'''

def home_page(lang, articles, cfg):
    topics_in_use = [t for t in TOPICS if any(a['topic'] == t for a in articles)]
    rows = []
    for t in topics_in_use:
        group = [a for a in articles if a['topic'] == t]
        for i, a in enumerate(group):
            rows.append(f'''<tr><td class="topic">{esc(topic_name(t, lang)) if i == 0 else ''}</td><td><a href="{route(lang,a['id'])}">{esc(a['title'][lang])}</a></td><td class="muted"><a href="{esc(a['url'])}" target="_blank" rel="noopener">{esc(a['source'])}</a></td><td class="date">{a['issue']}</td></tr>''')
    updates = ''.join(f'''<li><strong>{date_text(a['issue'], lang)}</strong>: {esc(topic_name(a['topic'], lang))} → <a href="{route(lang,a['id'])}">{esc(a['title'][lang])}</a></li>''' for a in articles[:8])
    body = f'''<article class="prose">
<h1>AI Fieldnotes</h1>
<p class="lead">{label(lang,
  '我是 Aimee，Georgia Tech 在读（M.S. 2027）。这里是我的 AI 阅读笔记：每篇挑一项值得读的研究，讲清楚它在解决什么、证据是什么、边界在哪里，再留一段我自己的判断。',
  'I’m Aimee, an M.S. student at Georgia Tech (2027). These are my AI reading notes: one piece of research at a time, what it solves, what the evidence shows, where it stops, and what I think about it.')}</p>
<p class="links"><a href="{esc(cfg['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a> · <a href="{esc(cfg['github'])}" target="_blank" rel="noopener">GitHub</a> · <a href="/feed.xml">{label(lang,'RSS 订阅','Subscribe via RSS')}</a></p>

<h2>{label(lang,'每篇笔记包含','In every note')}</h2>
<ul>
<li>{label(lang,'<strong>原文</strong>：直达论文或文章，保留原始发布日期','<strong>Source</strong>: a direct link to the paper or post, with its original date')}</li>
<li>{label(lang,'<strong>方法与发现</strong>：用两三段话说清楚做了什么、结果如何','<strong>Idea &amp; evidence</strong>: what was done and what came out, in a few paragraphs')}</li>
<li>{label(lang,'<strong>局限</strong>：证据在哪里停止，哪些结论还不能下','<strong>Limits</strong>: where the evidence stops and what it can’t yet claim')}</li>
<li>{label(lang,'<strong>我的旁注</strong>：我自己的看法，与 AI 辅助整理的摘要分开','<strong>My take</strong>: my own view, kept separate from the AI-assisted summary')}</li>
</ul>

<h2>{label(lang,'笔记列表','Notes')}</h2>
<div class="table-wrap"><table><thead><tr><th>{label(lang,'主题','Topic')}</th><th>{label(lang,'笔记','Note')}</th><th>{label(lang,'来源','Source')}</th><th>{label(lang,'日期','Date')}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>

<h2>{label(lang,'为什么写','Why I write this')}</h2>
<p>{label(lang,
  'AI 研究更新太快，只读标题很容易被结论带着走。把一篇研究写成几段话，逼自己分清作者的主张、实验的证据和我自己的解读；公开写下来，也方便和做研究、做工程、做产品的朋友交流。',
  'AI research moves fast, and headlines make it easy to adopt conclusions secondhand. Writing a few paragraphs per paper forces me to separate the authors’ claims, the evidence, and my own reading. Doing it in public makes it easier to compare notes with people building research, engineering, and products.')}</p>

<h2>{label(lang,'更新历史','Recent updates')}</h2>
<ul class="updates">{updates}</ul>
</article>'''
    return shell(lang, cfg, body, label(lang,'Aimee 的 AI 阅读笔记','AI reading notes by Aimee'),
                 label(lang,'AI 研究精选、中英双语阅读笔记与个人观点。','Bilingual AI research notes with a personal point of view.'),
                 route(lang), route('en' if lang == 'zh' else 'zh'))

def article_page(lang, a, articles, cfg):
    note = note_for(a).get(lang, '').strip()
    if note:
        note_html = ''.join(f'<p>{esc(p)}</p>' for p in note.split('\n\n') if p.strip())
    else:
        note_html = f'<p class="muted">{label(lang,"这篇还没有写旁注。","No personal note on this one yet.")}</p>'
    g = cfg.get('giscus', {})
    ready = bool(g.get('enabled') and g.get('repoId') and g.get('categoryId'))
    discussion_link = f'https://github.com/{cfg["repository"]}/discussions?discussions_q={quote(a["id"])}'
    discussion = (f'<div class="giscus" id="giscus" data-article="{esc(a["id"])}" data-repo="{esc(cfg["repository"])}" data-repo-id="{esc(g.get("repoId", ""))}" data-category="{esc(g.get("category", "General"))}" data-category-id="{esc(g.get("categoryId", ""))}"></div>'
                  if ready else
                  f'<p>{label(lang,"有不同看法或补充证据？欢迎在","Have a different read or more evidence? Join the conversation on")} <a href="{discussion_link}" target="_blank" rel="noopener">GitHub Discussions</a>{label(lang," 留言。",".")}</p>')
    idx = articles.index(a)
    newer = articles[idx - 1] if idx > 0 else None
    older = articles[idx + 1] if idx + 1 < len(articles) else None
    pager = ''.join([
        f'<a class="prev" href="{route(lang,older["id"])}"><span>{label(lang,"上一篇","Previous")}</span>{esc(older["title"][lang])}</a>' if older else '<span></span>',
        f'<a class="next" href="{route(lang,newer["id"])}"><span>{label(lang,"下一篇","Next")}</span>{esc(newer["title"][lang])}</a>' if newer else '<span></span>'])
    body = f'''<article class="prose">
<p class="meta"><a href="{route(lang)}">{label(lang,'← 全部笔记','← All notes')}</a></p>
<h1>{esc(a['title'][lang])}</h1>
<p class="meta">{esc(topic_name(a['topic'], lang))} · {a['minutes']} {label(lang,'分钟','min read')} · {label(lang,'整理于','Noted')} {a['issue']}</p>
<p class="lead">{esc(a['intro'][lang])}</p>
<blockquote class="source">{label(lang,'原文','Source')}：<a href="{esc(a['url'])}" target="_blank" rel="noopener">{esc(a['original'])}</a><br><span class="muted">{esc(a['source'])} · {label(lang,'发布于','published')} {a['published']} · {label(lang,'建议先读','Start with')} {esc(a['path'][lang])}</span></blockquote>
<h2>{label(lang,'方法与发现','Idea & evidence')}</h2>
{''.join('<p>'+esc(p)+'</p>' for p in a['body'][lang])}
<h2>{label(lang,'局限','Limits')}</h2>
<p>{esc(a['limits'][lang])}</p>
<h2>{label(lang,'我的旁注','My take')}</h2>
{note_html}
<p class="small"><a href="{'/en' if lang == 'en' else ''}/editor/?article={a['id']}" target="_blank" rel="noopener noreferrer">{label(lang,'编辑旁注（作者）','Edit note (author)')}</a></p>
<p class="muted small">{label(lang,'以上「方法与发现」「局限」由 AI 辅助整理；「我的旁注」只包含我本人写下的内容。','The idea and limits sections are AI-assisted; “My take” contains only what I’ve written myself.')}</p>
<h2>{label(lang,'讨论','Discussion')}</h2>
{discussion}
<nav class="pager" aria-label="{label(lang,'更多笔记','More notes')}">{pager}</nav>
</article>'''
    return shell(lang, cfg, body, a['title'][lang], a['intro'][lang], route(lang, a['id']), route('en' if lang == 'zh' else 'zh', a['id']), True)

def about_page(lang, articles, cfg):
    topics = '、'.join(topic_name(t, 'zh') for t in TOPICS if any(a['topic'] == t for a in articles)) if lang == 'zh' else ', '.join(t.lower() for t in TOPICS if any(a['topic'] == t for a in articles))
    body = f'''<article class="prose">
<h1>{label(lang,'关于','About')}</h1>
<p class="lead">{label(lang,'你好，我是 Aimee Gao。','Hi, I’m Aimee Gao.')}</p>
<ul>
<li>Georgia Tech · M.S. 2027</li>
<li>{label(lang,'关注 AI 研究、工程与产品之间的连接','Interested in where AI research, engineering, and product meet')}</li>
</ul>
<h2>{label(lang,'这里写什么','What I write about')}</h2>
<p>{label(lang,'目前覆盖：','So far: ')}{esc(topics)}{label(lang,'。','.')}</p>
<p>{label(lang,'正文是 AI 辅助整理的阅读摘要，不代表我已独立复现实验。每篇末尾的「我的旁注」只放我自己写下的判断和问题；没写的地方就留空。','Summaries are AI-assisted and don’t imply I’ve reproduced the experiments. “My take” at the end of each note holds only my own judgments and questions; if I haven’t written one, it stays empty.')}</p>
<h2>{label(lang,'联系','Get in touch')}</h2>
<p><a href="{esc(cfg['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a> · <a href="{esc(cfg['github'])}" target="_blank" rel="noopener">GitHub</a> · <a href="/feed.xml">RSS</a></p>
<p class="muted small">{label(lang,'原始研究与文章归各自作者所有。本站只提供简短摘要与原文链接，不转载全文。','Original work belongs to its authors. This site offers short summaries and links, never full text.')}</p>
</article>'''
    return shell(lang, cfg, body, label(lang,'关于 Aimee','About Aimee'), label(lang,'Aimee Gao 的 AI 阅读笔记。','Aimee Gao’s AI reading notes.'),
                 about_url(lang), about_url('en' if lang == 'zh' else 'zh'))

def write_page(path, text):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

def editor_page(lang, cfg):
    token_url = ('https://github.com/settings/personal-access-tokens/new?name=AI%20Fieldnotes'
                 '&description=Edit%20author%20notes&target_name=' + quote(cfg['repository'].split('/')[0]) +
                 '&expires_in=30&contents=write')
    body = f'''<article class="prose author-editor" data-repository="{esc(cfg['repository'])}" data-owner-id="{cfg['editor']['ownerId']}">
<h1>{label(lang,'写下我的旁注','Write my take')}</h1>
<p>{label(lang,'在这里编辑中文和英文旁注。点击保存后会公开发布；阅读摘要不受影响。','Edit Chinese and English notes here. Saving publishes them publicly; the reading summary is kept separately.')}</p>
<noscript>{label(lang,'请启用 JavaScript 使用在线编辑器。','Enable JavaScript to use this editor.')}</noscript>
<label for="article-picker">{label(lang,'文章','Article')}</label>
<select id="article-picker" disabled><option>{label(lang,'正在加载文章…','Loading articles…')}</option></select>
<p><a id="read-article" href="{route(lang)}" target="_blank" rel="noopener noreferrer">{label(lang,'打开阅读页','Open reading page')}</a></p>
<details id="connection" open>
<summary>{label(lang,'连接我的 GitHub','Connect my GitHub')}</summary>
<p>{label(lang,'只允许 Aimee 的账号保存。首次使用，按下面三步生成一张博客通行证（GitHub fine-grained token）。','Only Aimee’s account can save. On first use, create a fine-grained GitHub token in three steps.')}</p>
<ol>
<li><a href="{esc(token_url)}" target="_blank" rel="noopener noreferrer">{label(lang,'在 GitHub 生成通行证','Create a token on GitHub')}</a>{label(lang,'，账号选择 aimee-RH。',' with the aimee-RH account.')}</li>
<li>{label(lang,'Repository access 选择 Only select repositories，仅勾选 aimee-RH.github.io。','Under Repository access, choose Only select repositories and select aimee-RH.github.io only.')}</li>
<li>{label(lang,'确认 Contents 为 Read and write，生成后复制到下方。','Confirm Contents is Read and write, generate the token, and paste it below.')}</li>
</ol>
<p class="muted small">{label(lang,'它授权读写所选仓库；此编辑器只写旁注文件。通行证仅发给 GitHub，保留在当前标签页内存中。文字草稿另存于本浏览器，不会自动公开。','The token grants read/write access to the selected repository; this editor writes only note files. It is sent only to GitHub and kept in this tab’s memory. Text drafts are stored separately in this browser and are not published automatically.')}</p>
<form id="connect-form">
<label for="github-token">{label(lang,'GitHub 通行证','GitHub token')}</label>
<input id="github-token" type="password" autocomplete="off" spellcheck="false" maxlength="300" placeholder="github_pat_…" required>
<button type="submit">{label(lang,'连接并开始编辑','Connect and edit')}</button>
</form></details>
<p id="identity" class="muted" hidden></p>
<button id="disconnect" type="button" hidden>{label(lang,'断开连接','Disconnect')}</button>
<p id="editor-status" role="status" aria-live="polite"></p>
<form id="note-form">
<fieldset id="note-fields" disabled>
<legend>{label(lang,'我的旁注','My take')}</legend>
<label for="note-zh">中文</label><textarea id="note-zh" lang="zh-CN" maxlength="20000" rows="9"></textarea>
<label for="note-en">English</label><textarea id="note-en" lang="en" maxlength="20000" rows="9"></textarea>
<div class="editor-actions">
<button type="submit">{label(lang,'保存并公开发布','Save and publish')}</button>
<button id="reload-note" type="button">{label(lang,'载入 GitHub 最新版本','Load latest from GitHub')}</button>
</div></fieldset></form>
<button id="export-draft" type="button" disabled>{label(lang,'下载文字草稿','Download text draft')}</button>
<p id="draft-status" class="muted small" role="status"></p>
<p><a id="publish-status" href="https://github.com/{esc(cfg['repository'])}/actions/workflows/pages.yml" target="_blank" rel="noopener noreferrer" hidden>{label(lang,'查看网站发布进度','Check publication progress')}</a></p>
<h2>{label(lang,'旁注预览','Note preview')}</h2><div id="note-preview" class="note-preview"></div>
</article>'''
    base = '/en/' if lang == 'en' else '/'
    page = shell(lang, cfg, body, label(lang,'编辑旁注','Edit author note'),
                 label(lang,'作者专用的在线旁注编辑器。','Online author-note editor.'),
                 base + 'editor/', ('/' if lang == 'en' else '/en/') + 'editor/')
    # Keep credentials away from third-party scripts and prevent form navigation.
    policy = "default-src 'self'; script-src 'self'; connect-src 'self' https://api.github.com; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'"
    return page.replace('<head>', '<head>\n<meta name="robots" content="noindex,nofollow">\n<meta name="referrer" content="no-referrer">\n<meta http-equiv="Content-Security-Policy" content="' + policy + '">', 1).replace(
        '<script src="/assets/app.js" defer></script>', '<script type="module" src="/assets/note-editor.mjs"></script>')

def build():
    cfg = json.loads((ROOT / 'site.json').read_text())
    articles = load_articles()
    OUT.mkdir(exist_ok=True)
    # Remove only generated output inside this checkout; never source or drafts.
    for p in OUT.iterdir():
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(ROOT / 'assets', OUT / 'assets')
    write_page('editor/articles.json', json.dumps([{'id': a['id'], 'title': a['title']} for a in articles], ensure_ascii=False))
    paths = []
    for lang in ('zh', 'en'):
        base = 'en/' if lang == 'en' else ''
        write_page(base + 'index.html', home_page(lang, articles, cfg)); paths.append('/' + base)
        write_page(base + 'about/index.html', about_page(lang, articles, cfg)); paths.append('/' + base + 'about/')
        write_page(base + 'editor/index.html', editor_page(lang, cfg))
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
