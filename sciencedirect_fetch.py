#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScienceDirect 组合结构论文检索（驱动已登录的 Edge，经 CDP）
- 8 大主题关键词检索，限近 5 年
- 仅保留 Q1 顶刊（config.json 白名单）
- 进文章页提取 DOI、摘要、引言（引言在摘要下方，直接读取）
- 输出 sciencedirect_results.json
"""
import json
import re
import os
import sys
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
CDP_URL = "http://127.0.0.1:9223"
OUT = os.path.join(HERE, "sciencedirect_results.json")

YEARS = "2021-2026"  # 近 5 年
MAX_RESULTS_PER_QUERY = 25
MAX_ARTICLES = 20

QUERIES = [
    # 类别一：材料革新
    "concrete-filled steel tube",
    "stainless steel concrete-filled",
    "aluminum alloy concrete-filled",
    "UHPC filled steel",
    "recycled aggregate concrete-filled",
    # 类别二：界面粘结
    "bond-slip concrete-filled",
    "FRP bar bond",
    "interface bond steel concrete",
    # 类别三：约束混凝土
    "confined concrete",
    "FRP-confined concrete",
    # 类别四：机器学习/深度学习
    "machine learning concrete-filled",
    "deep learning concrete",
    # 类别五：海上风电
    "offshore wind concrete-filled",
    "grouted connection offshore",
    # 类别六/七/八：多灾害/LCA/新型体系
    "post-fire concrete-filled",
    "digital twin concrete structure",
    "self-centering concrete column",
]


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(s):
    return re.sub(r"[\s\-]+", "", (s or "").lower())


def extract_results(page):
    items = page.locator("li.ResultItem")
    n = items.count()
    out = []
    for i in range(n):
        try:
            it = items.nth(i)
            a = it.locator("a.result-list-title-link")
            title = a.inner_text().strip() if a.count() else ""
            href = a.get_attribute("href") if a.count() else ""
            m = re.search(r"/pii/([A-Za-z0-9]+)", href or "")
            pii = m.group(1) if m else ""
            jtxt = ""
            j = it.locator("a.subtype-srctitle-link")
            if j.count():
                jtxt = j.inner_text().strip()
            dtext = ""
            d = it.locator(".srctitle-date-fields")
            if d.count():
                dtext = d.inner_text().strip()
            atype = ""
            at = it.locator("span.article-type")
            if at.count():
                atype = at.inner_text().strip()
            authors = []
            for au in it.locator("ol.Authors span.author").all():
                try:
                    authors.append(au.inner_text().strip())
                except Exception:
                    pass
            if pii and title:
                out.append({
                    "title": title, "pii": pii, "href": href,
                    "journal": jtxt, "date": dtext, "type": atype,
                    "authors": authors,
                })
        except Exception:
            pass
    return out


def _extract_introduction(page):
    """从文章页正文提取引言（摘要下方，无需 View full text）。"""
    try:
        body = page.inner_text("body")
        out = ""
        for m in re.finditer(r"\bIntroduction\b", body):
            tail = body[m.end():]
            # 跳过左侧目录里的 "Introduction"（其后紧跟 Section snippets）
            if tail.lstrip().startswith("Section snippets"):
                continue
            for stop in ["\nSection snippets", "\n2.", "\nConclusion", "\nReferences",
                         "\nHighlights", "\nGraphical abstract", "\nKeywords", "\n1."]:
                j = tail.find(stop)
                if j > 0:
                    tail = tail[:j]
                    break
            tail = tail.strip()
            if len(tail) > 120:
                out = tail
                break
        return out[:3000]
    except Exception:
        return ""


def fetch_article(page, pii):
    """进文章页取 DOI + 摘要 + 引言。"""
    url = f"https://www.sciencedirect.com/science/article/pii/{pii}"
    result = {"doi": "", "abstract": "", "introduction": ""}
    for attempt in range(2):
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            d = page.locator("meta[name='citation_doi']")
            if d.count():
                result["doi"] = (d.get_attribute("content") or "").strip()
            a = page.locator("div.abstract.author")
            if a.count():
                result["abstract"] = a.inner_text().strip()
            result["introduction"] = _extract_introduction(page)
            if result["doi"] or result["abstract"]:
                return result
            time.sleep(8)
        except Exception as e:
            if attempt == 1:
                result["error"] = str(e)[:120]
            time.sleep(8)
    return result


def main():
    cfg = load_config()
    journal_whitelist = {norm(j["name"]): j for j in cfg["journals"]}
    batch_size = int(cfg.get("batch_size", 12))

    # 增量模式：读取已有结果，跳过已抓取的
    existing = []
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
    fetched_piis = {p.get("pii") for p in existing if p.get("pii")}

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()

        seen = {}
        for q in QUERIES:
            url = f"https://www.sciencedirect.com/search?qs={quote(q)}&date={quote(YEARS)}&show={MAX_RESULTS_PER_QUERY}"
            print(f"[检索] {q}")
            try:
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
            except Exception as e:
                print("  检索失败:", e)
                continue
            res = extract_results(page)
            kept = 0
            for r in res:
                if norm(r["journal"]) not in journal_whitelist:
                    continue
                if r["pii"] not in seen:
                    seen[r["pii"]] = r
                    kept += 1
            print(f"  命中 {len(res)} 条，其中 Q1 顶刊 {kept} 条")
            time.sleep(6)

        # 待抓取 = 候选 - 已抓取
        candidates = [r for r in seen.values() if r["pii"] not in fetched_piis]
        print(f"\n候选 {len(seen)} 篇，已抓 {len(fetched_piis)} 篇，本次抓 {min(batch_size, len(candidates))} 篇")

        batch = candidates[:batch_size]
        for i, paper in enumerate(batch, 1):
            info = fetch_article(page, paper["pii"])
            paper["doi"] = info.get("doi", "")
            paper["abstract"] = info.get("abstract", "")
            paper["introduction"] = info.get("introduction", "")
            print(f"  [{i}/{len(batch)}] {paper['title'][:46]} | DOI={bool(paper['doi'])} | 摘要{len(paper['abstract'])}字 | 引言{len(paper['introduction'])}字")
            time.sleep(15)

        merged = existing + batch
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\n已保存 {OUT}（累计 {len(merged)} 篇）")
        return 0


if __name__ == "__main__":
    sys.exit(main())
