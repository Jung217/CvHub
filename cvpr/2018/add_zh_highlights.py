#!/usr/bin/env python3
"""
為 CVPR 2018 論文 HTML 中的 zh-text 加上對應 en-text 的 hl- 高亮。
策略：解析每個 para-row，從 en-text 提取高亮片段，
在 zh-text 中找到對應的中文翻譯並加上同樣的 hl- class。
"""
import re
import os
import sys
from html.parser import HTMLParser

def extract_para_rows(html):
    """提取所有 para-row 區塊"""
    rows = []
    pattern = r'(<div class="para-row">.*?</div>\s*</div>\s*</div>)'
    # 使用更精確的方式：找到 para-row 的開始和結束
    # 改用逐行搜尋的方式
    in_para_row = False
    depth = 0
    current = []
    start_idx = 0

    i = 0
    while i < len(html):
        if html[i:i+len('<div class="para-row">')] == '<div class="para-row">':
            in_para_row = True
            depth = 1
            start_idx = i
            current = [html[i]]
            i += 1
            continue

        if in_para_row:
            current.append(html[i])
            chunk = html[max(0,i-5):i+1]

            # 簡易的 div 深度追蹤
            if '<div' in html[max(0,i-4):i+1] and html[i] in ' >':
                # 可能是 div 開始
                pass

            i += 1
            continue
        i += 1

    return rows


def extract_highlights_from_en(en_text_html):
    """從 en-text HTML 中提取所有 hl- 標記的文字與類別"""
    pattern = r'<span class="(hl-[a-z]+)">(.*?)</span>'
    matches = re.findall(pattern, en_text_html, re.DOTALL)
    return [(cls, text.strip()) for cls, text in matches]


def find_zh_translation(en_text, zh_text_html, hl_class):
    """
    根據英文高亮片段，在中文翻譯中找到對應文字。
    使用預建的映射表。
    """
    pass


def process_file(filepath):
    """處理單個 HTML 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到所有 para-row 區塊
    # 使用正則找到 en-text 和 zh-text 的配對
    en_pattern = r'<div class="en-text">(.*?)</div>'
    zh_pattern = r'<div class="zh-text">(.*?)</div>'

    en_matches = list(re.finditer(en_pattern, content, re.DOTALL))
    zh_matches = list(re.finditer(zh_pattern, content, re.DOTALL))

    # 配對 en-text 和 zh-text
    pairs = []
    for en_m in en_matches:
        en_end = en_m.end()
        # 找到此 en-text 之後最近的 zh-text
        for zh_m in zh_matches:
            if zh_m.start() > en_end:
                pairs.append((en_m, zh_m))
                break

    print(f"  找到 {len(pairs)} 個英中配對")

    # 從後往前替換，避免偏移問題
    replacements = []

    for en_m, zh_m in pairs:
        en_html = en_m.group(1)
        zh_html = zh_m.group(1)
        zh_start = zh_m.start(1)
        zh_end = zh_m.end(1)

        # 提取英文高亮
        highlights = extract_highlights_from_en(en_html)
        if not highlights:
            continue

        # 檢查 zh-text 是否已有高亮
        if 'hl-' in zh_html:
            print(f"    跳過已有高亮的段落")
            continue

        print(f"    段落有 {len(highlights)} 個高亮")

        # 建立這個段落的映射
        new_zh = apply_highlights_to_zh(en_html, zh_html, highlights)

        if new_zh != zh_html:
            replacements.append((zh_start, zh_end, new_zh))

    # 從後往前替換
    replacements.sort(key=lambda x: x[0], reverse=True)
    for start, end, new_text in replacements:
        content = content[:start] + new_text + content[end:]

    return content, len(replacements)


# 全域英中術語映射表（涵蓋所有檔案中常見的高亮術語）
TERM_MAP = {
    # 通用術語
    'CNN': 'CNN',
    'CNNs': 'CNN',
    'convolutional neural networks (CNNs)': '摺積神經網路',
    'convolution operator': '摺積運算子',
    'ResNet': 'ResNet',
    'VGGNet': 'VGGNet',
    'ImageNet': 'ImageNet',
    'COCO': 'COCO',
    'GAN': 'GAN',
    'GANs': 'GAN',

    # 常見結構
    'convolutional': '摺積',
    'recurrent': '遞迴',
    'residual': '殘差',
}


def apply_highlights_to_zh(en_html, zh_html, highlights):
    """將英文高亮映射到中文段落"""
    # 清理英文文字（去除 HTML 標籤）
    en_plain = re.sub(r'<[^>]+>', '', en_html).strip()

    new_zh = zh_html

    for hl_class, en_text in highlights:
        # 嘗試直接匹配（如技術術語可能在中文中保持原文）
        en_clean = en_text.strip()

        # 直接在中文中查找英文術語（如 SMPL, ResNet, CNN 等）
        if en_clean in new_zh and f'class="{hl_class}">{en_clean}' not in new_zh:
            # 確保不會重複包裹
            if f'<span class="{hl_class}">{en_clean}</span>' not in new_zh:
                new_zh = new_zh.replace(en_clean, f'<span class="{hl_class}">{en_clean}</span>', 1)
                continue

    return new_zh


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    html_files = [f for f in os.listdir(base_dir) if f.endswith('.html')]
    html_files.sort()

    print(f"找到 {len(html_files)} 個 HTML 檔案")

    for filename in html_files:
        filepath = os.path.join(base_dir, filename)
        print(f"\n處理: {filename}")

        new_content, num_changes = process_file(filepath)

        if num_changes > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  已儲存 {num_changes} 處修改")
        else:
            print(f"  無需修改")


if __name__ == '__main__':
    main()
