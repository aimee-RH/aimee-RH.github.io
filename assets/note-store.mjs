export class NoteError extends Error {
  constructor(code) { super(code); this.code = code; }
}

export function validateNote(note) {
  if (!note || Array.isArray(note) || ['zh', 'en'].some(lang =>
    typeof note[lang] !== 'string' || note[lang].length > 20000)) throw new NoteError('invalid_note');
  return note;
}

export function encodeNote(note) {
  const bytes = new TextEncoder().encode(JSON.stringify(validateNote(note), null, 2) + '\n');
  return btoa(Array.from(bytes, byte => String.fromCharCode(byte)).join(''));
}

export function decodeNote(content) {
  try {
    const bytes = Uint8Array.from(atob(content.replace(/\s/g, '')), c => c.charCodeAt(0));
    return validateNote(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)));
  } catch { throw new NoteError('invalid_note'); }
}

export class NoteStore {
  #token = '';
  #authorized = false;
  #session = 0;
  constructor(repository, ownerId, branch = 'main', request = globalThis.fetch) {
    if (!/^[\w.-]+\/[\w.-]+$/.test(repository) || !Number.isSafeInteger(ownerId) || ownerId < 1 ||
        !/^[\w./-]+$/.test(branch)) throw new NoteError('invalid_config');
    this.repository = repository;
    this.ownerId = ownerId;
    this.branch = branch;
    this.request = request;
  }

  get connected() { return this.#authorized; }
  disconnect() { this.#token = ''; this.#authorized = false; this.#session++; }

  async #api(path, method = 'GET', body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await this.request('https://api.github.com' + path, {
        method, signal: controller.signal, credentials: 'omit', cache: 'no-store',
        referrerPolicy: 'no-referrer', redirect: 'error',
        headers: {Accept: 'application/vnd.github+json', Authorization: `Bearer ${this.#token}`,
          'X-GitHub-Api-Version': '2026-03-10', ...(body ? {'Content-Type': 'application/json'} : {})},
        ...(body ? {body: JSON.stringify(body)} : {})
      });
      if (!response.ok) {
        if (response.status === 401) { this.disconnect(); throw new NoteError('unauthorized'); }
        if (response.status === 403 || response.status === 429) throw new NoteError('permission');
        if (response.status === 409 || response.status === 422) throw new NoteError('conflict');
        if (response.status === 404) throw new NoteError('not_found');
        throw new NoteError('github_error');
      }
      return await response.json();
    } catch (error) {
      // Do not expose response bodies or request errors that might contain credentials.
      if (error instanceof NoteError) throw error;
      throw new NoteError('network');
    } finally { clearTimeout(timeout); }
  }

  async connect(token) {
    this.disconnect();
    if (typeof token !== 'string' || !/^github_pat_[A-Za-z0-9_]+$/.test(token.trim())) {
      throw new NoteError('fine_grained_required');
    }
    this.#token = token.trim();
    const session = this.#session;
    try {
      const user = await this.#api('/user');
      if (user.id !== this.ownerId) throw new NoteError('not_owner');
      const repo = await this.#api(`/repos/${this.repository}`);
      if (repo.owner?.id !== this.ownerId ||
          repo.full_name?.toLowerCase() !== this.repository.toLowerCase() || !repo.permissions?.push) {
        throw new NoteError('permission');
      }
      if (session !== this.#session) throw new NoteError('unauthorized');
      this.#authorized = true;
      return user.login;
    } catch (error) { this.disconnect(); throw error; }
  }

  #path(id) {
    if (!this.connected) throw new NoteError('unauthorized');
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) throw new NoteError('invalid_article');
    return `/repos/${this.repository}/contents/content/notes/${id}.json`;
  }

  async load(id) {
    const file = await this.#api(`${this.#path(id)}?ref=${encodeURIComponent(this.branch)}`);
    if (file.type !== 'file' || file.encoding !== 'base64' || !/^[a-f0-9]{40}$/.test(file.sha)) {
      throw new NoteError('invalid_note');
    }
    return {sha: file.sha, data: decodeNote(file.content)};
  }

  async save(id, base, desired) {
    validateNote(base?.data); validateNote(desired);
    const latest = await this.load(id);
    const merged = {...latest.data};
    for (const lang of ['zh', 'en']) {
      if (desired[lang] === base.data[lang]) continue;
      if (latest.data[lang] !== base.data[lang] && latest.data[lang] !== desired[lang]) {
        throw new NoteError('conflict');
      }
      merged[lang] = desired[lang];
    }
    if (['zh', 'en'].every(lang => merged[lang] === latest.data[lang])) {
      return {...latest, commit: null};
    }
    const result = await this.#api(this.#path(id), 'PUT', {
      message: `Update author note: ${id}`, branch: this.branch,
      sha: latest.sha, content: encodeNote(merged)
    });
    if (!/^[a-f0-9]{40}$/.test(result.content?.sha) || !/^[a-f0-9]{40}$/.test(result.commit?.sha)) {
      throw new NoteError('github_error');
    }
    return {sha: result.content.sha, data: merged, commit: result.commit.sha};
  }
}
