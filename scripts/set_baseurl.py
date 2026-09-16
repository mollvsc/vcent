#!/usr/bin/env python3
"""Prefix (or un-prefix) hardcoded root-absolute paths baked into migrated
content bodies with a base path, for when the site is temporarily served
from a GitHub Pages project subpath (https://user.github.io/repo/) instead
of its own domain root.

This does NOT touch _config.yml's `baseurl` (set that yourself to match) or
front-matter `permalink:` values (those are already subpath-agnostic --
Jekyll/GitHub Pages serve the whole tree under the subpath transparently).
It only rewrites literal src="/assets/images/..." and internal
href="/writing|music-reviews|photography|newsletter..." strings baked into
post/page bodies, which bypass Jekyll's `relative_url` Liquid filter and
so need the prefix baked in by hand.

Usage:
  python3 scripts/set_baseurl.py /vcent   # prefix for project-page hosting
  python3 scripts/set_baseurl.py ""       # strip prefix for custom-domain root hosting
"""
import glob
import re
import sys

TARGET_GLOBS = [
    "_writing/*.html",
    "_music-reviews/*.html",
    "index.html",
    "photography.html",
    "newsletter.html",
]

SECTIONS = "writing|music-reviews|photography|newsletter"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    base = sys.argv[1].rstrip("/")  # "" or "/vcent"

    files = []
    for pattern in TARGET_GLOBS:
        files.extend(glob.glob(pattern))

    # Normalize first: strip any existing single-segment base prefix (idempotent),
    # by collapsing any current prefix before /assets/images or before a known
    # section path back to the bare root form, then re-apply the requested one.
    strip_re = re.compile(
        r'((?:src|href)=")(?:/[A-Za-z0-9_-]+)?(/assets/images/|/(?:' + SECTIONS + r')\b)'
    )

    changed = 0
    for f in files:
        text = open(f, encoding="utf-8").read()
        new_text = strip_re.sub(lambda m: m.group(1) + base + m.group(2), text)
        if new_text != text:
            open(f, "w", encoding="utf-8").write(new_text)
            changed += 1

    print(f"Updated {changed}/{len(files)} files with base path {base!r}")


if __name__ == "__main__":
    main()
