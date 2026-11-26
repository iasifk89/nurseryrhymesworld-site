"""Build the /videos pages from the YouTube channel uploads.

Needs env YT_API_KEY (YouTube Data API v3 key). Writes:
  videos.json, videos/index.html, videos/<id>.html, sitemap.xml
"""
import html
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

CHANNEL_ID = "UCHuJk_CXAflfAHFsubz87yA"
SITE = "https://nurseryrhymesworldz.com"
API = "https://www.googleapis.com/youtube/v3"
KEY = os.environ["YT_API_KEY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLE = """
body{margin:0;font-family:"Atkinson Hyperlegible",system-ui,sans-serif;background:#f2f9ff;color:#22306b}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
a{color:#22306b}
h1{font-family:Fredoka,system-ui,sans-serif;margin:8px 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:18px}
.card{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 5px 0 #9fd8f7;text-decoration:none}
.card img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover}
.card span{display:block;padding:10px 12px 14px;font-weight:700}
.player{position:relative;aspect-ratio:16/9;width:100%;border-radius:20px;overflow:hidden;background:#000}
.player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.desc{white-space:pre-wrap;margin-top:16px;line-height:1.5}
"""


def get(path, **params):
    params["key"] = KEY
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def fetch_videos():
    ch = get("channels", part="contentDetails", id=CHANNEL_ID)
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos, token = [], None
    while True:
        page = get("playlistItems", part="snippet", playlistId=uploads,
                   maxResults=50, pageToken=token) if token else \
               get("playlistItems", part="snippet", playlistId=uploads, maxResults=50)
        for it in page["items"]:
            sn = it["snippet"]
            vid = sn["resourceId"]["videoId"]
            thumbs = sn.get("thumbnails", {})
            thumb = (thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium")
                     or thumbs.get("default") or {}).get("url", f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg")
            videos.append({"id": vid, "title": sn["title"], "description": sn.get("description", ""),
                           "published": sn["publishedAt"][:10], "thumb": thumb})
        token = page.get("nextPageToken")
        if not token:
            break
    return videos


def page_head(title, desc, canonical):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc[:155])}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:type" content="video.other">
<style>{STYLE}</style>
</head>
<body>
<main>
<p><a href="{SITE}/">&larr; Nursery Rhymes World Z</a></p>
"""


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def build(videos):
    write("videos.json", json.dumps(videos, ensure_ascii=False, indent=1))

    cards = []
    for v in videos:
        t = html.escape(v["title"])
        cards.append(f'<a class="card" href="videos/{v["id"]}.html"><img src="{html.escape(v["thumb"])}" '
                     f'alt="{t}" loading="lazy" width="480" height="270"><span>{t}</span></a>')
        body = (page_head(f'{v["title"]} | Nursery Rhymes World Z', v["description"] or v["title"],
                          f"{SITE}/videos/{v['id']}.html")
                + f'<h1>{t}</h1>\n<div class="player"><iframe src="https://www.youtube-nocookie.com/embed/{v["id"]}" '
                  f'title="{t}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                  f'gyroscope; picture-in-picture" allowfullscreen></iframe></div>\n'
                + f'<p class="desc">{html.escape(v["description"])}</p>\n'
                + f'<p><a href="https://www.youtube.com/watch?v={v["id"]}">Watch on YouTube</a></p>\n'
                + '</main>\n</body>\n</html>\n')
        write(f"videos/{v['id']}.html", body)

    index = (page_head("All Videos | Nursery Rhymes World Z",
                       "Watch all Nursery Rhymes World Z sing-along videos for kids ages 2-6.",
                       f"{SITE}/videos/")
             + '<h1>All videos</h1>\n<div class="grid">\n' + "\n".join(cards)
             + '\n</div>\n</main>\n</body>\n</html>\n')
    write("videos/index.html", index)

    urls = ["/", "/privacy.html", "/terms.html", "/videos/"] + [f"/videos/{v['id']}.html" for v in videos]
    entries = "\n".join(
        f"  <url>\n    <loc>{SITE}{u}</loc>\n    <changefreq>weekly</changefreq>\n    "
        f"<priority>{'1.0' if u == '/' else '0.6'}</priority>\n  </url>" for u in urls)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n')


if __name__ == "__main__":
    vids = fetch_videos()
    build(vids)
    print(f"built {len(vids)} videos at {datetime.utcnow().isoformat()}Z")
