#!/usr/bin/env python3
"""Build the static site for www.ahaolearn.com from this repo.

Reads site/episodes.json, renders each episode page (with its prompt file and skills when it has them),
zips each skill folder for download, subsets the heading font to the characters actually used,
and writes everything to dist/. Standard library only; fontTools is optional (see subset_font).

    python3 site/build.py            # published episodes only
    python3 site/build.py --drafts   # also build episodes marked "draft" (local preview)
"""
import argparse
import html
import json
import os
import posixpath
import re
import shutil
import urllib.request
import zipfile

import pack_skill  # same folder; turns a skill into an install prompt for agents
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = ROOT / "dist"
GITHUB = "https://github.com/1095327780/ahao-learn-toolkit"
CNB = "https://cnb.cool/ahao-learn/ahao-learn-toolkit"
# 思源宋体 Heavy (SIL OFL). Used for headings only, subset per build so the page stays light.
SERIF_URL = "https://github.com/adobe-fonts/source-han-serif/raw/release/SubsetOTF/CN/SourceHanSerifCN-Heavy.otf"
SERIF_CACHE = ROOT / ".cache" / "SourceHanSerifCN-Heavy.otf"
LINKS = {}
ACCOUNTS = []  # platform accounts from episodes.json; the one with "primary": true goes in the nav and hero

esc = html.escape
serif_text = set()  # every character that may be set in the heading font


def serif(text):
    """Mark text as set in the heading font, so the subsetter keeps its glyphs."""
    serif_text.update(text)
    return esc(text)


# ---------- Markdown ----------

def inline(text):
    t = esc(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)

    def link(m):
        label, href = m.group(1), m.group(2)
        if not href.startswith(("http://", "https://", "#", "/")):
            href = f"{GITHUB}/blob/main/" + posixpath.normpath(posixpath.join("prompts", href))
        return f'<a href="{href}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)


def prompt_sections(md):
    """Split a prompt file into {heading: body_markdown}; the H1 becomes '_title'."""
    sections, current, buf = {}, None, []
    for line in md.splitlines():
        if m := re.match(r"^#\s+(.*)", line):
            sections["_title"] = m.group(1).strip()
        elif m := re.match(r"^##\s+(.*)", line):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = m.group(1).strip(), []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def markdown(md):
    out, para, items, list_tag = [], [], [], None

    def flush():
        nonlocal para, items, list_tag
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if items:
            out.append(f"<{list_tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{list_tag}>")
            items, list_tag = [], None

    lines, i = md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            out.append(code_block("\n".join(block)))
        elif m := re.match(r"^(#{3,4})\s+(.*)", line):
            flush()
            out.append(f"<h4>{inline(m.group(2))}</h4>")
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


def code_block(text, label="提示词"):
    return (
        '<figure class="doc"><figcaption><span class="dots"><i></i><i></i><i></i></span>'
        f'<span>{esc(label)}</span><button class="copy" type="button">复制全文</button></figcaption>'
        f"<pre><code>{esc(text)}</code></pre></figure>"
    )


# ---------- layout ----------

def page(title, body, description):
    nav = "".join(f'<a href="{href}">{label}</a>' for href, label in [("/#toc", "目录"), ("/#tools", "工具箱"), ("/#about", "关于")])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta name="theme-color" content="#0B1470">
<link rel="icon" href="/static/favicon.jpg">
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="nav"><div class="wrap nav-inner">
<a class="brand" href="/"><img src="/static/logo.jpg" alt="" width="34" height="34"><span>阿浩_Learn</span></a>
<nav class="nav-links">{nav}</nav>
<a class="nav-cta" href="{primary_account()['url']}">{esc(primary_account()['platform'])}主页</a>
</div></header>
{body}
<footer class="footer"><div class="wrap">
<div class="footer-top">
<div class="footer-brand"><img src="/static/logo.jpg" alt="" width="44" height="44"><div><strong class="serif">{serif('AI 时代的成长说明书')}</strong><span>收录视频配套的提示词与 Skill。</span></div></div>
<div class="footer-right"><div class="footer-social">{social_icons("social social-sm")}</div>
<div class="footer-links">{''.join(f'<a href="{url}">{esc(name)}</a>' for name, url in LINKS.items())}</div></div>
</div>
<p class="fine">© 2026 阿浩_Learn · 提示词和 Skill 以 MIT 许可开源</p>
</div></footer>
{qr_dialogs()}
<script src="/static/site.js"></script>
</body>
</html>
"""


def primary_account():
    return next((a for a in ACCOUNTS if a.get("primary") and a.get("url")), ACCOUNTS[0])


# platform -> (icon file in site/icons, brand colour)
PLATFORMS = {
    "B站": ("bilibili", "#00A1D6"),
    "抖音": ("tiktok", "#111111"),
    "YouTube": ("youtube", "#FF0000"),
    "小红书": ("xiaohongshu", "#FF2442"),
    "视频号": ("channels", "#FA9D3B"),
    "公众号": ("wechat", "#07C160"),
    "X": ("x", "#111111"),
}


def icon(name):
    svg = (SITE / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<title>.*?</title>", "", svg)
    return svg.replace("<svg ", '<svg aria-hidden="true" focusable="false" ', 1).replace(' role="img"', "")


def social_icons(cls="social"):
    """Round platform icons, the usual way sites link their accounts; WeChat ones open a QR dialog."""
    out = ""
    for i, a in enumerate(ACCOUNTS):
        slug, colour = PLATFORMS.get(a["platform"], ("github", "#333333"))
        attrs = f'class="{cls}" style="--brand:{colour}" aria-label="{esc(a["platform"])}" data-label="{esc(a["platform"])}"'
        if a.get("url"):
            out += f'<a {attrs} href="{esc(a["url"])}">{icon(slug)}</a>'
        elif a.get("qr"):
            out += f'<button {attrs} type="button" data-qr="qr-{i}">{icon(slug)}</button>'
    return out


def qr_dialogs():
    """One <dialog> per account that has a QR code; opened by any [data-qr] button on the page."""
    out = ""
    for i, a in enumerate(ACCOUNTS):
        if a.get("qr"):
            out += (
                f'<dialog class="qr" id="qr-{i}" aria-label="{esc(a["platform"])}二维码">'
                '<button class="qr-close" type="button" aria-label="关闭">×</button>'
                f'<p class="qr-title"><b>{esc(a["platform"])}</b>{esc(a["name"])}</p>'
                f'<img src="/static/{a["qr"]}" alt="{esc(a["platform"])}「{esc(a["name"])}」二维码">'
                f'<p class="qr-tip">{esc(a.get("search", "微信扫一扫"))}<br><small>在手机微信里打开本页时，长按二维码识别</small></p>'
                "</dialog>"
            )
    return out

def badge(ep, vol):
    return (
        f'<span class="badge" style="--c:{vol["color"]}"><span>成长说明书<b>No.{ep["no"]}</b></span>'
        f'<em>{esc(vol["name"])}</em></span>'
    )


def tool_chips(ep):
    chips = []
    if ep.get("prompt"):
        chips.append('<span class="chip">提示词</span>')
    if ep.get("skills"):
        chips.append('<span class="chip">Skill</span>')
    return "".join(chips)


# ---------- pages ----------

def zip_skill(name):
    src = ROOT / "skills" / name
    target = DIST / "downloads" / f"{name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            if f.is_file() and f.name != ".DS_Store":
                z.write(f, Path(name) / f.relative_to(src))
    return target.stat().st_size


def skill_meta(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    title = re.search(r"^#\s+(.+)$", text, re.M)
    goal = re.search(r"^目标：(.+)$", text, re.M)
    return (title.group(1).strip() if title else name), (goal.group(1).strip() if goal else "")


def collapsible(text, label, copy_label="复制全文"):
    """A document panel that shows the first lines and expands on demand; copy always copies everything."""
    return (
        f'<figure class="doc is-collapsed"><figcaption><span class="dots"><i></i><i></i><i></i></span><span>{esc(label)}</span>'
        f'<button class="copy" type="button">{esc(copy_label)}</button></figcaption>'
        f'<pre><code>{esc(text)}</code></pre>'
        '<button class="expand" type="button" data-more="展开全文" data-less="收起">展开全文</button></figure>'
    )


def episode_page(ep, vol, older, newer):
    has_tools = bool(ep.get("prompt") or ep.get("skills"))
    sec = prompt_sections((ROOT / ep["prompt"]).read_text(encoding="utf-8")) if ep.get("prompt") else {}
    heading = sec.get("_title", ep["title"])
    video_url = next(iter(ep["videos"].values()), None)
    video_links = "".join(f'<a class="btn btn-ghost" href="{esc(u)}">在{esc(k)}观看</a>' for k, u in ep["videos"].items())
    if ep.get("cover"):
        cover = (f'<a class="ep-cover" href="{esc(video_url or "#")}"><img src="/static/{ep["cover"]}" alt="{esc(ep["title"])} 封面">'
                 '<span class="play" aria-hidden="true"></span></a>')
    else:
        cover = (f'<div class="ep-cover"><div class="ep-cover-soon"><span class="serif">{serif("No." + ep["no"])}</span>'
                 f'<small>{esc(vol["name"])} · 视频即将发布</small></div></div>')

    blocks = []
    if has_tools:
        tabs, panels = [], []
        if ep.get("prompt"):
            prompt_key = next((k for k in sec if k.startswith("提示词")), "")
            note = prompt_key[len("提示词"):].strip("（）() ")
            code = re.search(r"```(?:text)?\n(.*?)```", sec.get(prompt_key, ""), re.S)
            tabs.append(("prompt", "提示词版"))
            panels.append(
                f'<div class="tab-panel" id="tab-prompt"><p class="panel-note">{esc(note) if note else "复制全文，发送给常用的 AI。"}</p>'
                f'{collapsible(code.group(1).rstrip() if code else sec.get(prompt_key, ""), "提示词", "复制提示词")}</div>'
            )
        for name in ep.get("skills", []):
            size = zip_skill(name)
            title, _ = skill_meta(name)
            files, _ = pack_skill.collect(ROOT / "skills" / name)
            n_files = len(files)
            prompt_text = pack_skill.install_prompt(name, pack_skill.skill_title(dict(files).get("SKILL.md", ""), name), files)
            install = (
                f"帮我安装这个 Skill：{GITHUB}/tree/main/skills/{name}\n"
                f"（国内打不开 GitHub 的话，用这个地址：{CNB}）\n"
                "装到你的 Skill 目录（Claude Code 是 ~/.claude/skills/），装好后告诉我怎么用。"
            )
            tabs.append((f"skill-{name}", "Skill 版"))
            panels.append(f"""<div class="tab-panel" id="tab-skill-{name}" hidden>
<p class="panel-note">适用于 Claude Code、Codex、Cursor 等 AI Agent。下载后解压至 Skill 目录，或将下方指令发送给 Agent 自动安装。</p>
<div class="skill-row"><a class="btn" href="/downloads/{name}.zip" download>下载 {name}.zip</a><span class="muted small">{size / 1024:.1f} KB · 源文件在 <a href="{GITHUB}/tree/main/skills/{name}">GitHub</a> / <a href="{CNB}">CNB</a></span></div>
<figure class="doc"><figcaption><span class="dots"><i></i><i></i><i></i></span><span>安装说明</span><button class="copy" type="button">复制全文</button></figcaption><pre><code>{esc(install)}</code></pre></figure>
<p class="panel-note">下载不了、也打不开 GitHub 时，把下面这段整段发给 agent，它会把全部 {n_files} 个文件逐字建好。</p>
{collapsible(prompt_text, "安装提示词（含全部文件）", "复制安装提示词")}
</div>""")
        tab_buttons = "".join(
            f'<button class="tab" type="button" role="tab" data-tab="tab-{i}" aria-selected="{str(n == 0).lower()}">{esc(t)}</button>'
            for n, (i, t) in enumerate(tabs)
        )
        blocks.append(f'<section class="tool-panel" id="tool"><div class="tabs" role="tablist">{tab_buttons}</div>{"".join(panels)}</section>')

        cards = ""
        if sec.get("什么时候用"):
            cards += f'<div class="info-card"><h2 class="serif">{serif("适用场景")}</h2>{markdown(sec["什么时候用"])}</div>'
        if sec.get("用法"):
            cards += f'<div class="info-card steps"><h2 class="serif">{serif("使用方法")}</h2>{markdown(sec["用法"])}</div>'
        if cards:
            blocks.append(f'<section class="info-grid">{cards}</section>')
        if sec.get("背后的依据"):
            refs = "\n".join(l for l in sec["背后的依据"].splitlines() if "skills/" not in l)  # the Skill tab already covers this
            blocks.append(f'<details class="refs"><summary class="serif">{serif("参考依据")}</summary>{markdown(refs)}</details>')
    else:
        points = "".join(f"<li>{esc(x)}</li>" for x in ep.get("points", []))
        blocks.append(f'<section class="info-card steps wide"><h2 class="serif">{serif("观看要点")}</h2>'
                      + (f"<ol>{points}</ol>" if points else "")
                      + '<p class="muted note">本期无配套提示词与 Skill，相关方法已在视频中完整讲解。</p></section>')

    pager = '<nav class="pager">' + (
        f'<a href="/{older["no"]}/"><small>← 上一期 · No.{older["no"]}</small><span>{esc(older["title"])}</span></a>' if older else "<span></span>"
    ) + (
        f'<a class="next" href="/{newer["no"]}/"><small>下一期 · No.{newer["no"]} →</small><span>{esc(newer["title"])}</span></a>' if newer else "<span></span>"
    ) + "</nav>"
    primary = '<a class="btn" href="#tool">查看提示词</a>' if ep.get("prompt") else ""

    body = f"""
<main class="episode" style="--c:{vol['color']}">
<section class="ep-hero"><div class="wrap ep-hero-grid">
<div class="ep-hero-copy">
<p class="crumbs"><a href="/#toc">目录</a><span>/</span><a href="/#vol-{vol['short']}">{esc(vol['name'])}</a><span>/</span><span>No.{ep['no']}</span></p>
{badge(ep, vol)}
<h1 class="serif">{serif(heading)}</h1>
<p class="ep-video">对应视频：{esc(ep['title'])}{('　' + ep['date']) if ep.get('date') else ''}</p>
<p class="ep-summary">{esc(ep['summary'])}</p>
<div class="actions">{primary}{video_links}</div>
</div>
{cover}
</div></section>
<div class="wrap ep-body">{''.join(blocks)}{pager}</div>
</main>"""
    return page(f"{heading}｜阿浩_Learn", body, ep["summary"])


def home_page(episodes, volumes):
    vols = {v["name"]: v for v in volumes}
    published = [e for e in episodes if e.get("cover")]
    latest = episodes[0]
    lv = vols[latest["volume"]]
    stack = "".join(f'<img src="/static/{e["cover"]}" alt="" style="--i:{i}">' for i, e in enumerate(published[:3]))

    def row(e):
        v = vols[e["volume"]]
        return (
            f'<a class="toc-row" href="/{e["no"]}/" style="--c:{v["color"]}"><span class="toc-no">No.{e["no"]}</span>'
            f'<span class="toc-title">{esc(e["title"])}</span><span class="toc-leader"></span>'
            f'<span class="toc-vol"><i></i>{esc(v["short"])}</span><span class="toc-tools">{tool_chips(e)}</span>'
            f'<span class="toc-date">{e.get("date", "即将发布")}</span></a>'
        )

    vol_cards = ""
    for v in volumes:
        count = sum(1 for e in episodes if e["volume"] == v["name"])
        status = "即将开放" if v.get("upcoming") else f"{count} 期"
        vol_cards += (
            f'<div class="vol{" vol-soon" if v.get("upcoming") else ""}" id="vol-{v["short"]}" style="--c:{v["color"]}">'
            f'<span class="vol-bar"></span><h3 class="serif">{serif(v["name"])}</h3><p>{esc(v["about"])}</p><small>{status}</small></div>'
        )

    tools = ""
    for e in episodes:
        if not (e.get("prompt") or e.get("skills")):
            continue
        v = vols[e["volume"]]
        name = prompt_sections((ROOT / e["prompt"]).read_text(encoding="utf-8")).get("_title", e["title"]) if e.get("prompt") else e["title"]
        tools += (
            f'<a class="tool" href="/{e["no"]}/" style="--c:{v["color"]}"><div class="tool-top">{badge(e, v)}<span class="tool-chips">{tool_chips(e)}</span></div>'
            f'<h3 class="serif">{serif(name)}</h3><p>{esc(e["summary"])}</p><span class="tool-go">查看 →</span></a>'
        )

    latest_art = (f'<img src="/static/{latest["cover"]}" alt="">' if latest.get("cover")
                  else f'<div class="feature-soon"><span class="serif">{serif("No." + latest["no"])}</span><small>视频即将发布</small></div>')
    body = f"""
<main>
<section class="hero"><div class="wrap hero-grid">
<div class="hero-copy">
<p class="eyebrow">阿浩_Learn · 视频配套工具箱</p>
<h1 class="serif">{serif('AI 时代的')}<br><mark>{serif('成长说明书')}</mark></h1>
<p class="lead">围绕大脑、注意力、情绪与判断力，每期讲清一个日常卡点，并提供配套的提示词与 Skill。</p>
<div class="actions"><a class="btn btn-light" href="#tools">查看工具</a><a class="btn btn-outline" href="{primary_account()['url']}">观看视频</a></div>
<dl class="stats"><div><dt>{len(published)}</dt><dd>期已发布</dd></div><div><dt>5</dt><dd>本分册</dd></div></dl>
</div>
<div class="hero-art" aria-hidden="true">{stack}</div>
</div></section>

<section class="section" id="latest"><div class="wrap">
<a class="feature" href="/{latest['no']}/" style="--c:{lv['color']}">
<div class="feature-copy"><p class="kicker">最新一期</p>{badge(latest, lv)}<h2 class="serif">{serif(latest['title'])}</h2><p>{esc(latest['summary'])}</p>
<span class="btn">{'查看配套工具' if latest.get('prompt') else '查看本期'}</span></div>
<div class="feature-art">{latest_art}</div>
</a>
</div></section>

<section class="section" id="toc"><div class="wrap">
<div class="section-head"><p class="kicker">目录</p><h2 class="serif">{serif('往期内容')}</h2><p>每一期均可在 B 站观看完整视频。</p></div>
<div class="toc">{''.join(row(e) for e in episodes)}</div>
</div></section>

<section class="section section-alt"><div class="wrap">
<div class="section-head"><p class="kicker">分册</p><h2 class="serif">{serif('五本使用说明')}</h2></div>
<div class="vols">{vol_cards}</div>
</div></section>

<section class="section" id="tools"><div class="wrap">
<div class="section-head"><p class="kicker">工具箱</p><h2 class="serif">{serif('配套工具')}</h2><p>提供每期配套的提示词与 Skill，支持主流 AI 工具与 Agent。</p></div>
<div class="tools">{tools}</div>
</div></section>

<section class="section section-alt" id="about"><div class="wrap about">
<img src="/static/logo.jpg" alt="阿浩_Learn" width="112" height="112">
<div><p class="kicker">关于</p><h2 class="serif">{serif('阿浩_Learn')}</h2>
<p class="about-line">AI 时代的成长说明书</p>
<div class="socials">{social_icons()}</div></div>
</div></section>
</main>"""
    return page("阿浩_Learn｜AI 时代的成长说明书", body, "阿浩_Learn：AI 时代的成长说明书。收录每期视频配套的提示词与 Skill。")


# ---------- font ----------

def subset_font():
    """Subset 思源宋体 Heavy to the characters used in headings. Skips quietly if fontTools or the font
    is unavailable; the CSS then falls back to the system serif."""
    try:
        from fontTools import subset
    except ImportError:
        print("fontTools not installed; headings use the system serif")
        return
    src = Path(os.environ.get("SERIF_FONT", SERIF_CACHE))
    if not src.exists():
        try:
            src.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(SERIF_URL, src)
        except Exception as e:  # offline build: keep going without the web font
            print(f"could not fetch heading font ({e}); headings use the system serif")
            return
    text = "".join(sorted(serif_text | set("0123456789No.·、，。？！：（）“”")))
    out = DIST / "static" / "serif.woff2"
    opts = subset.Options()
    opts.flavor = "woff2"
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    subset.save_font(font, str(out), opts)
    print(f"heading font: {len(text)} glyphs, {out.stat().st_size / 1024:.0f} KB")


# ---------- main ----------

def build(drafts):
    data = json.loads((SITE / "episodes.json").read_text(encoding="utf-8"))
    LINKS.update(data["links"])
    ACCOUNTS[:] = data["accounts"]
    volumes = data["volumes"]
    vols = {v["name"]: v for v in volumes}
    episodes = [e for e in data["episodes"] if drafts or not e.get("draft")]

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(SITE / "static", DIST / "static")
    for i, ep in enumerate(episodes):  # episodes are listed newest first
        newer = episodes[i - 1] if i > 0 else None
        older = episodes[i + 1] if i + 1 < len(episodes) else None
        out = DIST / ep["no"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(episode_page(ep, vols[ep["volume"]], older, newer), encoding="utf-8")
    (DIST / "index.html").write_text(home_page(episodes, volumes), encoding="utf-8")
    (DIST / "404.html").write_text(
        page("页面未找到｜阿浩_Learn",
             f'<main class="section"><div class="wrap narrow"><h1 class="serif">{serif("页面未找到")}</h1><p><a class="btn" href="/">返回首页</a></p></div></main>', ""),
        encoding="utf-8",
    )
    (DIST / "CNAME").write_text("www.ahaolearn.com\n", encoding="utf-8")
    subset_font()
    print(f"built {len(episodes)} episode(s) into {DIST}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", action="store_true", help="include episodes marked draft")
    build(ap.parse_args().drafts)
