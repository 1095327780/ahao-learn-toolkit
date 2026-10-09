#!/usr/bin/env python3
"""Build the static site for www.ahaolearn.com from this repo.

Reads site/episodes.json, renders each episode's prompt file (Markdown) into a page,
zips each skill folder for download, and writes everything to dist/.
No third-party packages, so GitHub Actions / EdgeOne Pages can run it as is:

    python3 site/build.py            # published episodes only
    python3 site/build.py --drafts   # also build episodes marked "draft" (local preview)
"""
import argparse
import html
import posixpath
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
GITHUB = "https://github.com/1095327780/ahao-learn-toolkit"
CNB = "https://cnb.cool/ahao-learn/ahao-learn-toolkit"


def inline(text):
    """Escape, then apply the few inline Markdown forms our files use."""
    t = html.escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)

    def link(m):
        label, href = m.group(1), m.group(2)
        # links into the repo point at GitHub; the site only hosts the rendered pages
        if not href.startswith(("http://", "https://", "#", "/")):
            href = f"{GITHUB}/blob/main/" + posixpath.normpath(posixpath.join("prompts", href))
        return f'<a href="{href}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)


def markdown(md, skip_title=True):
    """Tiny Markdown renderer: headings, paragraphs, lists, fenced code (with copy button)."""
    out, para, items, list_tag = [], [], [], None
    lines = md.splitlines()
    i = 0

    def flush():
        nonlocal para, items, list_tag
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if items:
            out.append(f"<{list_tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{list_tag}>")
            items, list_tag = [], None

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            code = html.escape("\n".join(block))
            out.append(
                '<div class="code"><button class="copy" type="button">复制全文</button>'
                f"<pre><code>{code}</code></pre></div>"
            )
        elif m := re.match(r"^(#{1,3})\s+(.*)", line):
            flush()
            level = len(m.group(1))
            if not (skip_title and level == 1):
                out.append(f"<h{level + 1}>{inline(m.group(2))}</h{level + 1}>")
        elif m := re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", line):
            tag = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            if para or (list_tag and list_tag != tag):
                flush()
            list_tag = tag
            items.append(m.group(1))
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def page(title, body, description, depth):
    up = "/"  # the site lives at the domain root
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="{up}static/favicon.jpg">
<link rel="stylesheet" href="{up}static/style.css">
</head>
<body>
<header class="top"><a class="brand" href="{up}"><img src="{up}static/logo.jpg" alt="" width="36" height="36"><span>阿浩_Learn</span></a><span class="slogan">AI 时代的成长说明书</span></header>
<main>
{body}
</main>
<footer>
<p>视频里用到的提示词和 Skill 都放在这里，免费拿去用，不用关注、不用留言。</p>
<p>源文件：<a href="{GITHUB}">GitHub</a> · <a href="{CNB}">CNB 国内镜像</a></p>
</footer>
<script src="{up}static/copy.js"></script>
</body>
</html>
"""


def zip_skill(name, dist):
    src = ROOT / "skills" / name
    target = dist / "downloads" / f"{name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            if f.is_file() and f.name != ".DS_Store":
                z.write(f, Path(name) / f.relative_to(src))
    return target


def skill_title(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else name


def build(drafts):
    dist = ROOT / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    shutil.copytree(SITE / "static", dist / "static")
    episodes = json.loads((SITE / "episodes.json").read_text(encoding="utf-8"))
    episodes = [e for e in episodes if drafts or not e.get("draft")]

    cards = []
    for ep in episodes:
        md = (ROOT / ep["prompt"]).read_text(encoding="utf-8")
        md = re.sub(r"^对应视频：.*\n", "", md, flags=re.M)  # the page header already says which video
        heading = re.search(r"^#\s+(.+)$", md, re.M).group(1)
        videos = "".join(
            f'<a class="pill" href="{html.escape(url)}">在{html.escape(name)}看视频</a>' for name, url in ep["videos"].items()
        )
        skills = ""
        for name in ep["skills"]:
            zip_skill(name, dist)
            install = (
                f"帮我安装这个 Skill：{GITHUB}/tree/main/skills/{name}\n"
                f"（国内打不开 GitHub 就用 {CNB}）\n"
                "装到你的 Skill 目录（Claude Code 是 ~/.claude/skills/），装好后告诉我怎么用。"
            )
            skills += f"""
<section class="skill">
<h2>Skill 版：{html.escape(skill_title(name))}</h2>
<p>给 Claude Code、Codex、Cursor 这类 AI agent 用。可以直接下载压缩包，解压到 Skill 目录；也可以把下面这段发给你的 agent，让它帮你装。</p>
<p><a class="button" href="/downloads/{name}.zip" download>下载 {name}.zip</a></p>
<div class="code"><button class="copy" type="button">复制全文</button><pre><code>{html.escape(install)}</code></pre></div>
</section>"""
        body = f"""
<article class="episode" style="--accent:{ep['color']}">
<p class="tag"><span>成长说明书 No.{ep['no']}</span><b>{html.escape(ep['volume'])}</b></p>
<h1>{html.escape(heading)}</h1>
<p class="video-title">对应视频：{html.escape(ep['title'])}</p>
<p>{videos}</p>
{markdown(md)}
{skills}
<p class="back"><a href="/">← 所有期</a></p>
</article>"""
        out = dist / ep["no"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{heading}｜阿浩_Learn", body, ep["summary"], 1), encoding="utf-8")
        cards.append(
            f'<a class="card" href="/{ep["no"]}/" style="--accent:{ep["color"]}">'
            f'<span class="tag"><span>No.{ep["no"]}</span><b>{html.escape(ep["volume"])}</b></span>'
            f"<strong>{html.escape(ep['title'])}</strong><span>{html.escape(ep['summary'])}</span></a>"
        )

    home = f"""
<section class="hero">
<h1>AI 时代的成长说明书</h1>
<p>我是阿浩。每期视频讲清一个关于大脑、注意力、情绪、判断力的问题，能做成工具的，就做成提示词或 Skill 放在这里。</p>
</section>
<section class="cards">
{''.join(cards)}
</section>"""
    (dist / "index.html").write_text(page("阿浩_Learn｜AI 时代的成长说明书", home, "阿浩_Learn 视频配套的提示词和 Skill，免费拿去用。", 0), encoding="utf-8")
    (dist / "404.html").write_text(
        page("没找到这一页｜阿浩_Learn", '<section class="hero"><h1>没找到这一页</h1><p><a href="/">回到首页</a></p></section>', "", 0),
        encoding="utf-8",
    )
    (dist / "CNAME").write_text("www.ahaolearn.com\n", encoding="utf-8")
    print(f"built {len(episodes)} episode(s) into {dist}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true", help="include episodes marked draft")
    build(ap.parse_args().drafts)
