#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
為 cvpr/2025 下的 HTML 檔案中 zh-text 區塊補上缺失的 hl- 高亮。
逐個 para-row 分析 en-text 的高亮，在 zh-text 中找到對應文字並加上相同 class。
"""

import re
import os
import glob


def extract_hl_spans(html_text):
    """從 HTML 中提取所有 hl- span 的 (class, 純文字內容)"""
    pattern = r'<span class="(hl-[a-z]+)">(.*?)</span>'
    matches = re.findall(pattern, html_text, re.DOTALL)
    result = []
    for cls, raw in matches:
        clean = re.sub(r'<[^>]+>', '', raw).strip()
        result.append((cls, clean))
    return result


def has_hl_wrap(html, text):
    """檢查文字是否已在某個 hl- span 內"""
    esc = re.escape(text)
    return bool(re.search(r'<span class="hl-[a-z]+">[^<]*?' + esc + r'[^<]*?</span>', html))


def safe_add_highlight(zh_html, hl_class, target_text):
    """
    在 zh_html 中為 target_text 的第一次出現添加 hl-class span。
    確保不在已有的 span 標籤內部操作。
    """
    if has_hl_wrap(zh_html, target_text):
        return zh_html, False

    esc = re.escape(target_text)

    # 將 HTML 分割成：已有 span 部分 和 普通文字部分
    parts = re.split(r'(<span class="hl-[a-z]+">[^<]*?</span>)', zh_html)
    new_parts = []
    done = False
    for part in parts:
        if done or re.match(r'<span class="hl-', part):
            new_parts.append(part)
        else:
            if re.search(esc, part):
                part = re.sub(esc, f'<span class="{hl_class}">{target_text}</span>', part, count=1)
                done = True
            new_parts.append(part)

    if done:
        return ''.join(new_parts), True
    return zh_html, False


def process_file(filepath):
    """處理單一 HTML 檔案，回傳新增的高亮數量"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 提取所有 en-text 和 zh-text 的配對
    en_pat = re.compile(r'<div class="en-text">(.*?)</div>\s*<div class="lang-divider">', re.DOTALL)
    zh_pat = re.compile(r'(<div class="zh-text">)(.*?)(</div>\s*</div>\s*<div class="right-col">)', re.DOTALL)

    en_blocks = list(en_pat.finditer(content))
    zh_blocks = list(zh_pat.finditer(content))

    # 配對
    pairs = []
    for en_m in en_blocks:
        en_end = en_m.end()
        for zh_m in zh_blocks:
            if zh_m.start() > en_end - 50:
                pairs.append((en_m, zh_m))
                break

    # 從後往前替換
    total_added = 0
    for en_m, zh_m in reversed(pairs):
        en_html = en_m.group(1)
        zh_html = zh_m.group(2)
        zh_clean = re.sub(r'<[^>]+>', '', zh_html)

        en_spans = extract_hl_spans(en_html)

        new_zh = zh_html
        para_added = 0

        for hl_class, en_text in en_spans:
            # --- 策略 1：英文縮寫/專有名詞直接出現在中文中 ---
            if en_text in zh_clean and len(en_text) <= 80:
                new_zh, ok = safe_add_highlight(new_zh, hl_class, en_text)
                if ok:
                    para_added += 1
                    continue

            # 針對帶括號的專有名詞，如 "Multimodal Large Language Models (MLLMs)"
            # 提取括號內的縮寫
            abbr_match = re.search(r'\(([A-Z][A-Za-z0-9]+(?:s)?)\)\s*$', en_text)
            if abbr_match:
                abbr = abbr_match.group(1)
                if abbr in zh_clean:
                    new_zh, ok = safe_add_highlight(new_zh, hl_class, abbr)
                    if ok:
                        para_added += 1
                        continue

            # --- 策略 2：提取英文中的專有名詞/縮寫 ---
            # 找到所有大寫開頭的連續詞組（可能是專有名詞）
            proper_nouns = re.findall(r'\b([A-Z][A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\b', en_text)
            for noun in proper_nouns:
                if len(noun) >= 2 and noun in zh_clean and not has_hl_wrap(new_zh, noun):
                    new_zh, ok = safe_add_highlight(new_zh, hl_class, noun)
                    if ok:
                        para_added += 1
                        break

        if para_added > 0 and new_zh != zh_html:
            start = zh_m.start(2)
            end = zh_m.end(2)
            content = content[:start] + new_zh + content[end:]
            total_added += para_added

    fname = os.path.basename(filepath)
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        old_n = len(re.findall(r'<span class="hl-[a-z]+">', original))
        new_n = len(re.findall(r'<span class="hl-[a-z]+">', content))
        print(f'{fname}: +{new_n - old_n} highlights (was {old_n}, now {new_n})')
    else:
        n = len(re.findall(r'<span class="hl-[a-z]+">', content))
        print(f'{fname}: no changes ({n} highlights)')

    return total_added


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    html_dir = os.path.join(base, 'cvpr', '2025')
    files = sorted(glob.glob(os.path.join(html_dir, '*.html')))
    total = 0
    for f in files:
        total += process_file(f)
    print(f'\nTotal added: {total}')


if __name__ == '__main__':
    main()
