# www.ahaolearn.com

视频配套的提示词和 Skill 的网页版，由这个仓库自动生成。

- 构建：`python3 site/build.py`，产物在 `dist/`。`--drafts` 会把 `episodes.json` 里标了 `"draft": true` 的期也构建出来，供本地预览。
- 本地预览：`python3 site/build.py --drafts && python3 -m http.server 4173 --directory dist`。
- 新增一期：在 `prompts/` 放提示词，在 `skills/` 放 Skill，在 `episodes.json` 加一条。视频发布后，把 `draft` 改成 `false`，再在 `videos` 里填上链接。

## 部署（两处都从这个仓库构建，测速后让域名指向更快的那个）

1. **GitHub Pages**：用 `.github/workflows/pages.yml`。Settings → Pages → Source 选 GitHub Actions；自定义域名填 `www.ahaolearn.com`。这个域名现在绑在 `ahaolearn.github.io` 仓库上，要先在那边移除。
2. **EdgeOne Pages**：腾讯云控制台 → EdgeOne Pages → 导入 Git 仓库，选这个仓库。
   - 加速区域选“全球可用区（不含中国大陆）”，这样不用备案。
   - 构建命令填 `python3 site/build.py`，输出目录填 `dist`。
   - 绑定自定义域名 `www.ahaolearn.com`，按提示在阿里云 DNS 加 CNAME。

不要把家里的 NAS 直接暴露到公网对外建站，原因见视频项目 `research/2026-10-09/分享机制调研.md` 第 4.5 节。
