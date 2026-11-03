#!/usr/bin/env python3
"""Generate self-hosted GitHub stats SVGs (no third-party services).

Writes assets/github-stats.svg and assets/top-languages.svg.
Uses only the Python standard library. Set GITHUB_TOKEN to raise API limits.
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Yazechi")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = os.environ.get("OUT_DIR", "assets")

LANG_COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "PHP": "#4f5d95",
    "HTML": "#e34c26", "CSS": "#563d7c", "C#": "#178600", "Python": "#3572a5",
    "SCSS": "#c6538c", "Vue": "#41b883", "Shell": "#89e051", "Java": "#b07219",
}


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"User-Agent": "profile-stats", "Accept": "application/vnd.github+json"},
    )
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[lang] = langs.get(lang, 0) + n
    try:
        commits = api(f"/search/commits?q=author:{USER}&per_page=1")["total_count"]
    except Exception:
        commits = None
    return {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in own),
        "forks": sum(r["forks_count"] for r in own),
        "commits": commits,
        "langs": langs,
    }


STYLE = """<style>
  .bg{fill:#ffffff;stroke:#d0d7de}
  .title{font:600 18px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#0969da}
  .label{font:400 14px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#57606a}
  .value{font:600 14px 'Segoe UI',Ubuntu,Arial,sans-serif;fill:#1f2328}
  .track{fill:#eaeef2}
  @media (prefers-color-scheme: dark){
    .bg{fill:#0d1117;stroke:#30363d}
    .title{fill:#58a6ff}
    .label{fill:#8b949e}
    .value{fill:#e6edf3}
    .track{fill:#21262d}
  }
</style>"""


def stats_svg(d):
    rows = [
        ("Total stars earned", d["stars"]),
        ("Total commits (public)", d["commits"] if d["commits"] is not None else "n/a"),
        ("Public repositories", d["repos"]),
        ("Followers", d["followers"]),
        ("Total forks", d["forks"]),
    ]
    h = 70 + 28 * len(rows)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}" role="img" aria-label="GitHub statistics for {escape(USER)}">',
        STYLE,
        f'<rect class="bg" x="0.5" y="0.5" width="419" height="{h-1}" rx="6"/>',
        f'<text class="title" x="24" y="36">{escape(USER)} - GitHub Statistics</text>',
    ]
    y = 70
    for label, value in rows:
        out.append(f'<text class="label" x="24" y="{y}">{escape(label)}</text>')
        out.append(f'<text class="value" x="396" y="{y}" text-anchor="end">{escape(str(value))}</text>')
        y += 28
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(d, top=6):
    total = sum(d["langs"].values()) or 1
    items = sorted(d["langs"].items(), key=lambda kv: kv[1], reverse=True)[:top]
    shown = sum(n for _, n in items) or 1
    h = 70 + 28 * len(items) + 10
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}" role="img" aria-label="Most used languages for {escape(USER)}">',
        STYLE,
        f'<rect class="bg" x="0.5" y="0.5" width="419" height="{h-1}" rx="6"/>',
        '<text class="title" x="24" y="36">Most Used Languages</text>',
        '<rect class="track" x="24" y="50" width="372" height="8" rx="4"/>',
    ]
    x = 24.0
    for lang, n in items:
        w = 372 * n / shown
        color = LANG_COLORS.get(lang, "#8b949e")
        out.append(f'<rect x="{x:.1f}" y="50" width="{max(w,1):.1f}" height="8" fill="{color}"/>')
        x += w
    y = 90
    for lang, n in items:
        color = LANG_COLORS.get(lang, "#8b949e")
        pct = 100 * n / total
        out.append(f'<circle cx="30" cy="{y-5}" r="5" fill="{color}"/>')
        out.append(f'<text class="label" x="44" y="{y}">{escape(lang)}</text>')
        out.append(f'<text class="value" x="396" y="{y}" text-anchor="end">{pct:.1f}%</text>')
        y += 28
    out.append("</svg>")
    return "\n".join(out)


def seed_svg(title, note):
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="130" viewBox="0 0 420 130" role="img" aria-label="' + escape(title) + '">',
        STYLE,
        '<rect class="bg" x="0.5" y="0.5" width="419" height="129" rx="6"/>',
        '<text class="title" x="24" y="36">' + escape(title) + '</text>',
        '<text class="label" x="24" y="70">' + escape(note) + '</text>',
        '<text class="label" x="24" y="94">Run the "Update GitHub stats" workflow to fill this in.</text>',
        "</svg>",
    ])


def main():
    if "--seed" in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "github-stats.svg"), "w", encoding="utf-8") as f:
            f.write(seed_svg(USER + " - GitHub Statistics", "Statistics are generated automatically."))
        with open(os.path.join(OUT, "top-languages.svg"), "w", encoding="utf-8") as f:
            f.write(seed_svg("Most Used Languages", "Statistics are generated automatically."))
        return 0
    if "--demo" in sys.argv:
        demo = {"repos": 8, "followers": 4, "stars": 3, "forks": 3, "commits": 120,
                "langs": {"JavaScript": 520000, "PHP": 210000, "HTML": 90000, "CSS": 70000, "TypeScript": 30000}}
        os.makedirs(OUT, exist_ok=True)
        open(os.path.join(OUT, "github-stats.svg"), "w").write(stats_svg(demo))
        open(os.path.join(OUT, "top-languages.svg"), "w").write(langs_svg(demo))
        return 0
    try:
        data = collect()
    except Exception as exc:  # keep existing images if the API is unreachable
        print("Could not fetch stats, leaving existing files untouched:", exc, file=sys.stderr)
        return 0
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "github-stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open(os.path.join(OUT, "top-languages.svg"), "w", encoding="utf-8") as f:
        f.write(langs_svg(data))
    print("Updated:", {k: v for k, v in data.items() if k != "langs"}, list(data["langs"])[:6])
    return 0


if __name__ == "__main__":
    sys.exit(main())
