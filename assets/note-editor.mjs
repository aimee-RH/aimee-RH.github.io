import {NoteStore, validateNote} from './note-store.mjs';

const root = document.querySelector('.author-editor');
const en = document.body.dataset.lang === 'en';
const say = (zh, english) => en ? english : zh;
const $ = id => document.getElementById(id);
const picker = $('article-picker');
const fields = $('note-fields');
const status = $('editor-status');
const tokenInput = $('github-token');
const store = new NoteStore(root.dataset.repository, Number(root.dataset.ownerId));
let article = '', base = null, busy = false, dirty = false, ready = false;
const value = () => ({zh: $('note-zh').value, en: $('note-en').value});
const draftKey = id => `fieldnotes:author-draft:v1:${id}`;

const errors = {
  not_owner: ['这个账号不是博客作者，请使用 aimee-RH 的通行证。', 'This account is not the author. Use a token from aimee-RH.'],
  fine_grained_required: ['请填写以 github_pat_ 开头的 fine-grained token。', 'Use a fine-grained token starting with github_pat_.'],
  unauthorized: ['连接已失效，请重新连接；文字草稿仍保留。', 'The connection expired. Reconnect; your draft is retained.'],
  permission: ['GitHub 拒绝了请求：请检查仓库选择、Contents 读写权限及请求配额。草稿仍保留。', 'GitHub rejected the request. Check repository selection, Contents write access, and rate limits. Your draft is retained.'],
  conflict: ['GitHub 上的同一段旁注已有更新，尚未覆盖。请先下载草稿，再载入最新版本并合并。', 'The same note changed on GitHub. Nothing was overwritten. Download your draft, load the latest version, and merge.'],
  not_found: ['没有读到这篇旁注，请检查通行证是否选中了博客仓库。', 'The note could not be read. Check that the token includes the blog repository.'],
  invalid_note: ['旁注格式有误，或超过每种语言两万字的限制。草稿仍保留。', 'Invalid note format or the 20,000-character language limit was exceeded. Your draft is retained.'],
  network: ['网络请求未能确认完成。草稿仍保留；再次保存前会核对 GitHub 最新内容，避免重复提交。', 'The request could not be confirmed. Your draft is retained; another save will first check GitHub for an existing update.'],
  github_error: ['GitHub 暂未确认保存结果。请查看发布进度，或稍后重试；草稿仍保留。', 'GitHub did not confirm the save. Check publication progress or retry later; your draft is retained.']
};

function controls() {
  picker.disabled = busy || !ready;
  fields.disabled = busy || !store.connected || !base;
  $('connect-form').querySelector('button').disabled = busy || !ready;
  tokenInput.disabled = busy;
  $('disconnect').disabled = busy;
  $('disconnect').hidden = !store.connected;
  $('identity').hidden = !store.connected;
  $('export-draft').disabled = busy || !base;
  if (!store.connected) $('connection').open = true;
}

async function run(action) {
  if (busy) return;
  busy = true; controls();
  try { await action(); }
  catch (error) {
    const message = errors[error.code];
    status.textContent = message ? say(...message) : say('暂时无法完成，请保留草稿后重试。', 'Unable to complete this step. Keep your draft and try again.');
  } finally { busy = false; controls(); }
}

function render() {
  const text = value()[en ? 'en' : 'zh'];
  $('note-preview').textContent = text || say('这篇还没有写旁注。', 'No note in this language yet.');
}

function fill(note) {
  $('note-zh').value = note.zh;
  $('note-en').value = note.en;
  render();
}

function stash() {
  if (!base) return;
  dirty = ['zh', 'en'].some(lang => value()[lang] !== base.data[lang]);
  try {
    if (dirty) localStorage.setItem(draftKey(article), JSON.stringify({base, data: value()}));
    else localStorage.removeItem(draftKey(article));
    $('draft-status').textContent = dirty ? say('文字草稿已备份到当前浏览器，尚未公开。', 'Text draft backed up in this browser; not yet public.') : '';
  } catch {
    $('draft-status').textContent = say('浏览器无法备份草稿，请使用「下载文字草稿」留存。', 'Browser draft backup is unavailable. Download a text draft to keep a copy.');
  }
  render();
}

async function load(restore = true) {
  status.textContent = say('正在载入 GitHub 上的旁注…', 'Loading the note from GitHub…');
  const latest = await store.load(article);
  base = latest;
  fill(latest.data);
  dirty = false;
  if (restore) {
    try {
      const saved = JSON.parse(localStorage.getItem(draftKey(article)) || 'null');
      if (saved) {
        validateNote(saved.base?.data); validateNote(saved.data);
        base = saved.base;
        fill(saved.data);
        dirty = true;
      }
    } catch {
      $('draft-status').textContent = say('本地草稿无法恢复，已保留原备份。', 'The local draft could not be restored; its stored backup was retained.');
    }
  }
  status.textContent = dirty ? say('已恢复本地草稿。保存时会核对 GitHub 上的最新版本。', 'Local draft restored. Saving will check the latest GitHub version.') : say('已载入。保存后会公开发布两种语言的旁注。', 'Loaded. Saving publishes the notes in both languages.');
  $('publish-status').hidden = true;
}

function selectArticle(id) {
  article = id;
  picker.value = id;
  const prefix = en ? '/en' : '';
  $('read-article').href = `${prefix}/read/${id}/`;
  history.replaceState(null, '', `${prefix}/editor/?article=${encodeURIComponent(id)}`);
  base = null; dirty = false; fill({zh: '', en: ''});
  $('draft-status').textContent = '';
  $('publish-status').hidden = true;
}

picker.addEventListener('change', () => {
  stash();
  selectArticle(picker.value);
  if (store.connected) run(() => load());
  else { status.textContent = say('连接 GitHub 后即可开始编辑。', 'Connect GitHub to start editing.'); controls(); }
});

$('connect-form').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    const token = tokenInput.value;
    tokenInput.value = '';
    status.textContent = say('正在验证 GitHub 身份…', 'Verifying GitHub identity…');
    const login = await store.connect(token);
    $('identity').textContent = say(`已连接：${login}（仅当前标签页）`, `Connected: ${login} (this tab only)`);
    $('connection').open = false;
    await load();
  });
});

$('note-form').addEventListener('input', stash);
$('note-form').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    stash();
    status.textContent = say('正在核对版本并保存…', 'Checking versions and saving…');
    const result = await store.save(article, base, value());
    base = {sha: result.sha, data: result.data};
    fill(result.data); stash();
    const progress = $('publish-status');
    progress.href = result.commit ? `https://github.com/${store.repository}/commit/${result.commit}/checks` : `https://github.com/${store.repository}/actions/workflows/pages.yml`;
    progress.hidden = false;
    status.textContent = result.commit ? say('已保存到 GitHub，网站正在更新。通常约一分钟后可在阅读页看到；可通过下方链接确认发布结果。', 'Saved to GitHub. Publication is pending, usually about a minute. Check the link below before refreshing the reading page.') : say('GitHub 已是这些内容，无需重复提交。', 'GitHub already has this content; no duplicate commit was created.');
  });
});

$('reload-note').addEventListener('click', () => {
  if (dirty && !confirm(say('重新载入会替换当前编辑框的文字。本地草稿会继续保留；建议先下载备份。继续吗？', 'Reloading replaces the text in the editor. The local draft will remain; download a backup first if needed. Continue?'))) return;
  run(() => load(false));
});

$('disconnect').addEventListener('click', () => {
  stash(); store.disconnect(); tokenInput.value = '';
  status.textContent = say('已断开连接。未发布的文字草稿仍在当前浏览器中。', 'Disconnected. Unpublished text drafts remain in this browser.');
  controls();
});

$('export-draft').addEventListener('click', () => {
  const blob = new Blob([`Article: ${article}\n\n中文\n${value().zh}\n\nEnglish\n${value().en}\n`], {type: 'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = `${article}-draft.txt`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

window.addEventListener('beforeunload', event => {
  if (dirty) { event.preventDefault(); event.returnValue = ''; }
});
window.addEventListener('pagehide', () => { store.disconnect(); tokenInput.value = ''; });
window.addEventListener('pageshow', controls);

try {
  const response = await fetch('/editor/articles.json', {credentials: 'omit'});
  if (!response.ok) throw new Error();
  const articles = await response.json();
  if (!Array.isArray(articles) || !articles.length || articles.some(a =>
    !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(a.id) || typeof a.title?.zh !== 'string' || typeof a.title?.en !== 'string')) throw new Error();
  picker.replaceChildren(...articles.map(a => {
    const option = document.createElement('option');
    option.value = a.id; option.textContent = a.title[en ? 'en' : 'zh']; return option;
  }));
  const requested = new URL(location.href).searchParams.get('article');
  selectArticle(articles.some(a => a.id === requested) ? requested : articles[0].id);
  ready = true;
  controls();
} catch {
  status.textContent = say('文章列表暂时无法加载，请刷新页面。', 'The article list could not be loaded. Refresh to retry.');
  $('connect-form').querySelector('button').disabled = true;
}
