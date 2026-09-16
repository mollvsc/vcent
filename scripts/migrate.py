#!/usr/bin/env python3
"""One-time migration: Squarespace/WordPress WXR export -> Jekyll site.

Run once from the project root: python3 scripts/migrate.py
Safe to re-run (overwrites generated content + downloaded images).
"""
import re
import os
import sys
import hashlib
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XML_PATH = os.path.join(ROOT, "Squarespace-Wordpress-Export-09-06-2026 (2).xml")
IMAGES_DIR = os.path.join(ROOT, "assets", "images")

NS = {"wp": "http://wordpress.org/export/1.2/", "content": "http://purl.org/rss/1.0/modules/content/"}
CONTENT_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"

OLD_DOMAINS = ["https://www.vcent.in", "http://www.vcent.in", "https://vcent.in", "http://vcent.in"]

CAPTION_RE = re.compile(
    r'\[caption[^\]]*\]\s*(<img[^>]*/?>)\s*(.*?)\s*\[/caption\]',
    re.DOTALL,
)
IMG_SRC_RE = re.compile(r'(<img[^>]+src=")([^"]+)(")')
MULTI_BLANK_RE = re.compile(r'\n{3,}')

_downloaded = {}  # remote url -> local web path


def yaml_str(value):
    """Minimal safe double-quoted YAML scalar."""
    s = str(value)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", " ").replace("\r", " ")
    return f'"{s}"'


def yaml_list(items):
    if not items:
        return "[]"
    return "[" + ", ".join(yaml_str(i) for i in items) + "]"


def download_image(url):
    if url in _downloaded:
        return _downloaded[url]

    fetch_url = url
    if fetch_url.startswith("http://"):
        fetch_url = "https://" + fetch_url[len("http://"):]

    parsed_name = fetch_url.split("?")[0].rstrip("/").split("/")[-1]
    parsed_name = parsed_name.replace(" ", "-")
    if not parsed_name:
        parsed_name = "image"

    # disambiguate by short hash of the full url in case of duplicate filenames
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    base, ext = os.path.splitext(parsed_name)
    if not ext:
        ext = ".jpg"
    local_name = f"{base}-{h}{ext}"
    local_path = os.path.join(IMAGES_DIR, local_name)
    web_path = f"/assets/images/{local_name}"

    if not os.path.exists(local_path):
        try:
            req = urllib.request.Request(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(local_path, "wb") as f:
                f.write(resp.read())
            print(f"  downloaded {fetch_url} -> {local_name}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"  WARNING: failed to download {fetch_url}: {e}", file=sys.stderr)
            _downloaded[url] = url  # leave original url in place
            return url

    _downloaded[url] = web_path
    return web_path


def convert_captions(html):
    def repl(m):
        img_tag, caption_text = m.group(1), m.group(2)
        caption_text = caption_text.strip()
        if caption_text:
            return f'<figure>{img_tag}<figcaption>{caption_text}</figcaption></figure>'
        return f'<figure>{img_tag}</figure>'
    return CAPTION_RE.sub(repl, html)


def rewrite_images(html):
    def repl(m):
        pre, src, post = m.groups()
        if "squarespace-cdn.com" in src:
            src = download_image(src)
        return pre + src + post
    return IMG_SRC_RE.sub(repl, html)


def clean_html(html):
    if html is None:
        return ""
    for domain in OLD_DOMAINS:
        html = html.replace(domain, "")
    html = convert_captions(html)
    html = rewrite_images(html)
    html = MULTI_BLANK_RE.sub("\n\n", html)
    return html.strip()


def write_file(path, front_matter_lines, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for line in front_matter_lines:
            f.write(line + "\n")
        f.write("---\n\n")
        f.write(body)
        f.write("\n")


def main():
    tree = ET.parse(XML_PATH)
    channel = tree.getroot().find("channel")
    items = channel.findall("item")

    os.makedirs(IMAGES_DIR, exist_ok=True)

    pages_written = 0
    posts_written = 0

    for item in items:
        ptype = item.findtext("wp:post_type", default="", namespaces=NS)
        status = item.findtext("wp:status", default="", namespaces=NS)
        if ptype not in ("page", "post") or status != "publish":
            continue

        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        pub_date_raw = item.findtext("pubDate", default="")
        # wp:post_name is the full date-path for posts (e.g. "2019/10/21/some-slug"),
        # not a bare slug -- always derive the slug from the last link segment instead.
        slug = link.rstrip("/").split("/")[-1]
        content_el = item.find(CONTENT_TAG)
        raw_html = content_el.text if content_el is not None else ""

        try:
            dt = parsedate_to_datetime(pub_date_raw)
        except (TypeError, ValueError):
            dt = None

        tags = [c.text for c in item.findall("category") if c.attrib.get("domain") == "post_tag" and c.text]

        body = clean_html(raw_html)

        if ptype == "page":
            if slug == "about":
                # This page's content ("Welcome to my tiny real estate...", "Latest
                # posts", "Also.") reads as homepage copy, not a bio page -- Squarespace
                # exported it as "About" but it was serving as the site's index/home.
                front = [
                    "layout: home",
                    f"title: {yaml_str(title)}",
                    "permalink: \"/\"",
                ]
                out_path = os.path.join(ROOT, "index.html")
                write_file(out_path, front, body)
                pages_written += 1
                print("page  -> index.html (from 'about' export, used as homepage)")
                continue
            front = [
                "layout: page",
                f"title: {yaml_str(title)}",
                f"permalink: \"/{slug}/\"",
            ]
            out_path = os.path.join(ROOT, f"{slug}.html")
            write_file(out_path, front, body)
            pages_written += 1
            print(f"page  -> {slug}.html")
            continue

        # posts: bucket by URL prefix
        if link.startswith("/writing/"):
            collection = "_writing"
            layout = "writing-post"
        elif link.startswith("/music-reviews/"):
            collection = "_music-reviews"
            layout = "music-review"
        else:
            # one-minute-vlogs (and anything else unrecognized) intentionally
            # dropped -- the vlogs section was removed from the site.
            print(f"  SKIP unrecognized/excluded post link: {link}", file=sys.stderr)
            continue

        date_prefix = dt.strftime("%Y-%m-%d") if dt else "1970-01-01"
        date_full = dt.strftime("%Y-%m-%d %H:%M:%S %z") if dt else "1970-01-01 00:00:00 +0000"
        filename = f"{date_prefix}-{slug}.html"
        out_path = os.path.join(ROOT, collection, filename)

        front = [
            f"layout: {layout}",
            f"title: {yaml_str(title)}",
            f"date: {date_full}",
            f"tags: {yaml_list(tags)}",
            f"permalink: \"{link}/\"",
        ]
        write_file(out_path, front, body)
        posts_written += 1

    print(f"\nDone. {pages_written} pages, {posts_written} posts written. "
          f"{len(_downloaded)} unique images processed.")


if __name__ == "__main__":
    main()
