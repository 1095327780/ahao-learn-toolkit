# www.ahaolearn.com

视频配套的提示词和 Skill 的网页版，由这个仓库自动生成。

- 构建：`python3 site/build.py`，产物在 `dist/`。`--drafts` 会把 `episodes.json` 里标了 `"draft": true` 的期也构建出来，供本地预览。
- 标题字体：思源宋体 Heavy，构建时只截取页面上用到的字（约 30 KB）。需要 `fonttools` 和 `brotli`；本机有字体文件可以用 `SERIF_FONT=路径` 指定，否则自动下载到 `.cache/`。缺了就退回系统宋体，不影响构建。
- 本地预览：`python3 site/build.py --drafts && python3 -m http.server 4173 --directory dist`。
- 新增一期：在 `prompts/` 放提示词，在 `skills/` 放 Skill，在 `episodes.json` 加一条。视频发布后，把 `draft` 改成 `false`，再在 `videos` 里填上链接。

## 部署（当前：域名指向 EdgeOne Pages，GitHub Pages 作备用；2026-10-09）

部署工作流所在仓库：<https://github.com/ahao-learn/ahao-learn-toolkit>。

1. **GitHub Pages**：使用该仓库的 `.github/workflows/pages.yml`。当前 Source 为 GitHub Actions，自定义域名为 `www.ahaolearn.com`；保留这些设置作为备用部署。线上 DNS 指向 EdgeOne，不需要为组织迁移改回 GitHub Pages。
2. **EdgeOne Pages**：腾讯云控制台 → EdgeOne Pages → 导入 Git 仓库，选择 `ahao-learn/ahao-learn-toolkit`。
   - 加速区域选“全球可用区（不含中国大陆）”，这样不用备案。
   - 分支选 `site-dist`（GitHub Actions 每次构建完会把成品推到这个分支）；框架选“无/静态”，构建命令留空，输出目录填 `/`。
   - 绑定自定义域名 `www.ahaolearn.com`，按提示在阿里云 DNS 加 CNAME。

不要把家里的 NAS 直接暴露到公网对外建站，原因见视频项目 `research/2026-10-09/分享机制调研.md` 第 4.5 节。

## 验证中国大陆能打开

```
python3 site/check_cn.py /NN/ "页面上一定有的一句话"
```

用 Globalping 的公开接口，从 10 个中国大陆节点取页面，并核对拿到的是不是本站内容。8 个及以上成功算通过。10-09 两次实测都是 9/10：解析到 EdgeOne 的 43.174.246.64 和 43.174.247.64；宁波移动那个节点两次都在建立 HTTPS 连接时超时。完整维护流程见视频项目 `.agents/skills/ahao-site/SKILL.md`。
