# AI Fieldnotes · Aimee Gao

A bilingual AI research notebook with a knowledge-base sidebar, author’s margin notes, and GitHub Discussions comments.

Live site: https://aimee-rh.github.io/

## Local preview

Python 3.9+ is the only build dependency. No API key or package installation is required.

```sh
python3 -m unittest discover -s tests -v
python3 -m http.server 8765 --directory _site --bind 127.0.0.1
```

Open http://127.0.0.1:8765/ or `/en/`.

## Add a daily reading note

Add an object to `content/articles.json`, following the existing schema. Each note needs a stable unique `id`, an edition date (`issue`), the original publication date (`published`), a direct HTTPS source link, and complete Chinese/English text. Do not change existing IDs: links, comments, and scratchpads use them.

Run the tests and commit to `main`. GitHub Actions builds and deploys automatically. `_site/` is generated and is not committed.

### Editorial rules

- Read original sources, distinguish author claims from evidence and interpretation, and retain limitations.
- Summaries are AI-assisted and explicitly labeled. Never fabricate personal opinions, reading progress, experiments, or results for Aimee.
- Curated dates and original publication dates are separate.
- Link to original articles; do not republish copyrighted full text.
- Preserve any author-written text in `content/notes/` when adding daily content.
- Avoid duplicate original-source URLs within the same week.

## Add your own margin notes

Click “Edit author’s note” on a reading page, or edit `content/notes/<article-id>.json`:

```json
{"zh": "你的中文观点。\n\n另一个段落。", "en": "Your English reflection.\n\nAnother paragraph."}
```

Commit to publish. Empty fields deliberately show that no personal note has been written. They are never filled with AI-generated opinions presented as yours.

The optional reading scratchpad uses localStorage only. It is not public and is not synced across devices. Use “Export draft” for a text backup. Never put private material in this public repository, even outside the generated site.

## Comments with giscus

1. Enable Discussions in the repository (Settings → General).
2. Install https://github.com/apps/giscus for this repository only.
3. Configure https://giscus.app/ with `aimee-RH/aimee-RH.github.io` and a public Discussion category.
4. The repository ID and category ID are already in `site.json`. After installing the app, set `giscus.enabled` to `true`.

Use `mapping: specific` and the stable term `fieldnotes/<article-id>` (already implemented) so Chinese and English versions share one discussion. Until the IDs are configured, pages show an honest link to Discussions rather than a broken embed.

Visitors sign in to GitHub to comment. Comments, replies, reactions, and moderation live in GitHub Discussions. No personal access token belongs in browser code.

## Deployment

In repository Settings → Pages, select **GitHub Actions**. The workflow validates content, checks internal links, builds both languages, uploads `_site/`, and deploys to GitHub Pages. An action failure leaves the previously deployed version intact.

## Daily automation handoff

The existing AI digest automation can append bilingual summaries to `content/articles.json`, create empty per-article margin-note files, run tests, and push a commit. It must never overwrite Aimee’s notes or publish local scratchpads. Publication is complete only after the GitHub Actions deployment succeeds.

RSS: `/feed.xml` · Sitemap: `/sitemap.xml`
