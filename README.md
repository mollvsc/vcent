# vcent.in

Personal site, migrated from Squarespace to Jekyll for GitHub Pages.

## Structure

- `index.html` — homepage (migrated from the Squarespace export's "About"
  page, which was actually serving as the homepage/intro content)
- `photography.html`, `newsletter.html` — standalone pages
- `_writing/`, `_music-reviews/` — Jekyll collections for the two post
  sections, each rendered by its own layout in `_layouts/`
- `writing/index.html`, `music-reviews/index.html` — section listing pages
- `assets/images/` — all images self-hosted (downloaded from Squarespace's
  CDN during migration, since the CDN may stop working after the
  Squarespace subscription ends)
- `scripts/migrate.py` — the one-time WXR-export-to-Jekyll conversion
  script (kept for reference; safe to re-run, will overwrite generated
  content)
- `scripts/set_baseurl.py` — utility to switch hardcoded root-absolute
  paths baked into post/page bodies between a GitHub Pages project
  subpath (`/vcent`) and domain-root (`""`) — see **Custom domain** below
- `Squarespace-Wordpress-Export-09-06-2026 (2).xml` — the original export,
  kept for reference

9 unpublished Squarespace drafts were intentionally left out of this
migration (not in git history at all). If you want them, they're still in
the original XML export.

## Local preview

Requires Ruby >= 3.0 (macOS system Ruby is 2.6, too old for the
`github-pages` gem). Easiest path: `brew install ruby`, then:

```
bundle install
bundle exec jekyll serve
```

## Deploying

Push to GitHub, then in the repo's Settings → Pages, set the source to
the `main` branch (GitHub Pages builds Jekyll sites automatically, no
Actions workflow needed).

## Custom domain (www.vcent.in)

DNS is hosted at Bigrock, pointed at GitHub Pages:

- Apex domain (`vcent.in`): 4 `A` records to GitHub's IPs —
  `185.199.108.153`, `185.199.109.153`, `185.199.110.153`,
  `185.199.111.153`
- `www.vcent.in`: a `CNAME` record to `mollvsc.github.io`

`www.vcent.in` is canonical (matches the original Squarespace site's
links); the bare `vcent.in` apex redirects to it. This is declared via
the `CNAME` file in this repo and the custom domain setting in the
repo's GitHub Pages settings.

If the site is ever temporarily served from a GitHub Pages project
subpath again (e.g. `https://mollvsc.github.io/vcent/`, before DNS is
ready), hardcoded root-absolute paths baked into migrated post/page
bodies (image `src`, internal `href` — these bypass Jekyll's
`relative_url` filter) need the subpath prefixed onto them, and
`_config.yml`'s `baseurl` needs to match:

```
python3 scripts/set_baseurl.py /vcent   # prefix for project-subpath hosting
python3 scripts/set_baseurl.py ""       # strip prefix back out for domain-root hosting
```
