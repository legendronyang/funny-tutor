# 高考生物考纲网站抓取说明

目标站点：https://nuxaap6e7b46i.ok.kimi.link/

## 当前归档状态

- docs/gaokao-biology-kimi-site-capture.md 是目前可确认目录内容的**部分捕获记录**，不是完整站点镜像。
- docs/gaokao-biology-current-standard-audit-2026-10-20.md 是与现行课程标准的结构性对照审查，明确标注了不能逐字核验的范围。
- scripts/scrape_kimi_biology_outline.py 是 Playwright 浏览器抓取脚本。本次执行环境无法稳定访问目标域名，因此没有用猜测内容冒充完整抓取结果。

## 在能够访问该网站的本地 WSL/Ubuntu 环境运行

在 Funny Tutor 仓库根目录运行：

~~~bash
python -m pip install playwright
python -m playwright install chromium
python scripts/scrape_kimi_biology_outline.py
~~~

脚本默认把浏览器渲染文本写入 docs/gaokao-biology-kimi-site-capture.md。如果访问失败或展开不工作，改用可视化浏览器诊断：

~~~bash
python scripts/scrape_kimi_biology_outline.py --headed
~~~

生成后先检查是否覆盖网站最后一个模块，是否缺少展开节点、分页内容或图片旁的说明，再保存输出：

~~~bash
git diff -- docs/gaokao-biology-kimi-site-capture.md
git add docs/gaokao-biology-kimi-site-capture.md
git commit -m 'docs: refresh Kimi biology outline capture'
git push
~~~

## 爬取完整性注意事项

1. 浏览器渲染文本可捕获页面当前已显示的正文，但不能保证包括未加载的分页、虚拟列表、登录后数据或接口失败时的内容。
2. 如果页面只有目录导航、正文通过点击节点加载，请在抓取脚本中定位真正的“全部展开”控件，并在输出中检查末尾模块。
3. 对于图片形式的知识点、表格、流程图，应另行保存并在 Markdown 中加入本地相对路径；仅抓取 body.inner_text() 无法保存这些非文本资源。
4. 不要将旧式“考纲”目录自动认定为当年度官方考查范围。按省份和年度核对教育考试院文件，并将课程标准、教材依据与真题统计分开保存。
