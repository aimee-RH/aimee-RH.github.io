import test from 'node:test';
import assert from 'node:assert/strict';
import {NoteStore, encodeNote, decodeNote} from '../assets/note-store.mjs';

const repo = 'aimee-RH/aimee-RH.github.io', owner = 182139164;
const token = 'github_pat_fixture_not_a_real_credential';
const sha = n => String(n).repeat(40);
const user = {id: owner, login: 'aimee-RH'};
const repository = {owner: {id: owner}, full_name: repo, permissions: {push: true}};
const file = (data, n = 1) => ({type: 'file', encoding: 'base64', content: encodeNote(data), sha: sha(n)});

function fixture(responses) {
  const calls = [];
  const store = new NoteStore(repo, owner, 'main', async (url, options) => {
    calls.push({url, options});
    const next = responses.shift();
    assert.ok(next, `Unexpected request to ${url}`);
    if (next instanceof Error) throw next;
    return {ok: !next.status || next.status < 400, status: next.status || 200, json: async () => next};
  });
  return {store, calls};
}

test('Unicode and blank-language notes round-trip without HTML interpretation', () => {
  const note = {zh: '第一段。🧠\n\n<script>alert(1)</script>', en: ''};
  assert.deepEqual(decodeNote(encodeNote(note)), note);
});

test('wrong GitHub identity cannot read or write author files', async () => {
  const {store, calls} = fixture([{id: 7, login: 'visitor'}]);
  await assert.rejects(store.connect(token), {code: 'not_owner'});
  assert.equal(store.connected, false);
  await assert.rejects(store.load('memonce'), {code: 'unauthorized'});
  assert.equal(calls.length, 1);
});

test('classic tokens are rejected before any network request', async () => {
  const {store, calls} = fixture([]);
  await assert.rejects(store.connect('ghp_fixture'), {code: 'fine_grained_required'});
  assert.equal(calls.length, 0);
});

test('repository owner and write authorization are checked', async () => {
  for (const changed of [{...repository, owner: {id: 7}}, {...repository, permissions: {push: false}}]) {
    const {store} = fixture([user, changed]);
    await assert.rejects(store.connect(token), {code: 'permission'});
    assert.equal(store.connected, false);
  }
});

test('note paths cannot escape the notes directory', async () => {
  const {store, calls} = fixture([user, repository]);
  await store.connect(token);
  for (const id of ['../site', 'x/y', 'x?ref=other', '%2e%2e', '']) {
    await assert.rejects(store.load(id), {code: 'invalid_article'});
  }
  assert.equal(calls.length, 2);
});

test('save merges untouched remote language and uses the latest file SHA', async () => {
  const base = {sha: sha(1), data: {zh: '旧中文', en: 'old English'}};
  const remote = {zh: '旧中文', en: 'new English', extra: 'preserve'};
  const {store, calls} = fixture([user, repository, file(remote, 2), {content: {sha: sha(3)}, commit: {sha: sha(4)}}]);
  await store.connect(token);
  const saved = await store.save('memonce', base, {zh: '新中文 🧠', en: 'old English'});
  assert.deepEqual(saved.data, {zh: '新中文 🧠', en: 'new English', extra: 'preserve'});
  const write = calls.at(-1);
  assert.equal(write.options.method, 'PUT');
  assert.equal(write.url, `https://api.github.com/repos/${repo}/contents/content/notes/memonce.json`);
  const body = JSON.parse(write.options.body);
  assert.equal(body.sha, sha(2));
  assert.equal(body.branch, 'main');
  assert.deepEqual(decodeNote(body.content), saved.data);
  assert.ok(!JSON.stringify(body).includes(token));
});

test('same-language conflict is detected before issuing a write', async () => {
  const {store, calls} = fixture([user, repository, file({zh: 'remote', en: ''}, 2)]);
  await store.connect(token);
  await assert.rejects(store.save('memonce', {data: {zh: 'base', en: ''}}, {zh: 'local', en: ''}), {code: 'conflict'});
  assert.ok(calls.every(call => call.options.method === 'GET'));
});

test('a lost acknowledgement can be retried without a duplicate commit', async () => {
  const desired = {zh: 'already saved', en: ''};
  const {store, calls} = fixture([user, repository, file(desired, 2)]);
  await store.connect(token);
  const result = await store.save('memonce', {data: {zh: '', en: ''}}, desired);
  assert.equal(result.commit, null);
  assert.ok(calls.every(call => call.options.method === 'GET'));
});

test('a race after the freshness check surfaces a conflict without retrying', async () => {
  const {store, calls} = fixture([user, repository, file({zh: '', en: ''}), {status: 409}]);
  await store.connect(token);
  await assert.rejects(store.save('memonce', {data: {zh: '', en: ''}}, {zh: 'my note', en: ''}), {code: 'conflict'});
  assert.equal(calls.filter(call => call.options.method === 'PUT').length, 1);
});

test('a revoked credential is forgotten and cannot make another request', async () => {
  const {store, calls} = fixture([user, repository, {status: 401}]);
  await store.connect(token);
  await assert.rejects(store.load('memonce'), {code: 'unauthorized'});
  await assert.rejects(store.load('memonce'), {code: 'unauthorized'});
  assert.equal(calls.length, 3);
  assert.equal(store.connected, false);
});

test('network error details cannot leak credentials into user messages', async () => {
  const {store} = fixture([new Error(`Request failed with ${token}`)]);
  await assert.rejects(store.connect(token), error => error.code === 'network' && !String(error).includes(token));
  assert.equal(store.connected, false);
});

test('credentials are sent only in an API header, never URL or request body', async () => {
  const {store, calls} = fixture([user, repository]);
  await store.connect(token);
  for (const {url, options} of calls) {
    assert.equal(new URL(url).origin, 'https://api.github.com');
    assert.ok(!url.includes(token));
    assert.ok(!options.body?.includes(token));
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.equal(options.redirect, 'error');
  }
  store.disconnect();
  assert.equal(store.connected, false);
});

test('malformed or oversized notes cannot be published', async () => {
  assert.throws(() => decodeNote('not base64'), {code: 'invalid_note'});
  const {store, calls} = fixture([user, repository]);
  await store.connect(token);
  for (const bad of [{zh: 3, en: ''}, {zh: 'x'.repeat(20001), en: ''}, null]) {
    await assert.rejects(store.save('memonce', {data: {zh: '', en: ''}}, bad), {code: 'invalid_note'});
  }
  assert.equal(calls.length, 2);
});
