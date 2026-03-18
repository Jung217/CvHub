"""
逐段提取每個 para-row 中的英文高亮和中文全文 - 後半部分檔案。
"""

import re
import os
import glob

def find_para_rows(content):
    rows = []
    pos = 0
    row_idx = 0
    while True:
        pr_idx = content.find('<div class="para-row">', pos)
        if pr_idx == -1:
            break
        en_start = content.find('<div class="en-text">', pr_idx)
        if en_start == -1:
            pos = pr_idx + 1
            continue
        en_inner_start = en_start + len('<div class="en-text">')
        en_end = content.find('</div>', en_inner_start)

        zh_start = content.find('<div class="zh-text">', en_end)
        if zh_start == -1:
            pos = en_end + 1
            continue
        zh_inner_start = zh_start + len('<div class="zh-text">')
        zh_end = content.find('</div>', zh_inner_start)

        en_inner = content[en_inner_start:en_end].strip()
        zh_inner = content[zh_inner_start:zh_end].strip()

        rows.append({
            'row_idx': row_idx,
            'en_inner': en_inner,
            'zh_inner': zh_inner,
        })
        row_idx += 1
        pos = zh_end + 1
    return rows

def extract_highlights(text):
    pattern = re.compile(r'<span class="(hl-\w+)">(.*?)</span>', re.DOTALL)
    return [(m.group(1), m.group(2).strip()) for m in pattern.finditer(text)]

def strip_html(text):
    return re.sub(r'<[^>]+>', '', text)

base_dir = os.path.dirname(os.path.abspath(__file__))
# 只處理後半部分的檔案
target_files = ['liegroup.html', 'mcg.html', 'partialopt.html', 'rcnn.html', 'seqlabel.html', 'structuredlight.html', 'transfercnn.html']

for fname in target_files:
    filepath = os.path.join(base_dir, fname)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = find_para_rows(content)
    print(f"\n{'='*80}")
    print(f"FILE: {fname}")
    print(f"{'='*80}")

    for row in rows:
        en_hl = extract_highlights(row['en_inner'])
        zh_hl = extract_highlights(row['zh_inner'])

        if not en_hl:
            continue
        if zh_hl:
            continue

        print(f"\n--- 段落 {row['row_idx']} ---")
        print(f"中文全文: {strip_html(row['zh_inner'])}")
        print(f"英文高亮 ({len(en_hl)} 個):")
        for cls, txt in en_hl:
            print(f"  [{cls}] {txt}")
