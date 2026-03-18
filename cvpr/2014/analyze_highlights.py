"""
分析 CVPR 2014 所有 HTML 檔案中的高亮情況。
提取每個 para-row 中 en-text 的高亮片段，以及 zh-text 中是否已有高亮。
"""

import re
import os
import glob

def find_para_rows(content):
    """找到所有 para-row 中的 en-text 和 zh-text 配對"""
    rows = []
    pos = 0
    row_idx = 0
    while True:
        # 找 para-row
        pr_idx = content.find('<div class="para-row">', pos)
        if pr_idx == -1:
            break

        # 找 en-text
        en_start = content.find('<div class="en-text">', pr_idx)
        if en_start == -1:
            pos = pr_idx + 1
            continue
        # 找 en-text 結束的 </div>  - 需要注意內部可能有 span 但不應有 div
        en_inner_start = en_start + len('<div class="en-text">')
        # 找到下一個 </div>
        en_end = content.find('</div>', en_inner_start)

        # 找 zh-text
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
            'zh_start_pos': zh_inner_start,  # 在原始檔案中的位置
            'zh_end_pos': zh_end,
        })
        row_idx += 1
        pos = zh_end + 1

    return rows

def extract_highlights(text):
    """提取 <span class="hl-xxx">...</span> 片段"""
    pattern = re.compile(r'<span class="(hl-\w+)">(.*?)</span>', re.DOTALL)
    return [(m.group(1), m.group(2).strip()) for m in pattern.finditer(text)]

base_dir = os.path.dirname(os.path.abspath(__file__))
html_files = sorted(glob.glob(os.path.join(base_dir, '*.html')))

print(f"共找到 {len(html_files)} 個 HTML 檔案\n")

total_missing = 0
for filepath in html_files:
    fname = os.path.basename(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = find_para_rows(content)

    file_missing = 0
    for row in rows:
        en_hl = extract_highlights(row['en_inner'])
        zh_hl = extract_highlights(row['zh_inner'])

        if en_hl and not zh_hl:
            file_missing += 1

    if file_missing > 0:
        print(f"[!] {fname}: {len(rows)} 段落, {file_missing} 段缺少中文高亮")
        total_missing += file_missing
    else:
        print(f"[OK] {fname}: {len(rows)} 段落, 中文高亮完整")

print(f"\n總計 {total_missing} 個段落需要補充中文高亮")
