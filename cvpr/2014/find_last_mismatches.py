"""
找出最後剩餘的缺失高亮。
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

def count_highlights(text):
    return len(re.findall(r'<span class="hl-\w+">', text))

def extract_highlights(text):
    pattern = re.compile(r'<span class="(hl-\w+)">(.*?)</span>', re.DOTALL)
    return [(m.group(1), m.group(2).strip()) for m in pattern.finditer(text)]

def strip_html(text):
    return re.sub(r'<[^>]+>', '', text)

base_dir = os.path.dirname(os.path.abspath(__file__))

# 有問題的檔案和段落
problems = {
    'camerashape.html': [3],
    'deepface.html': [0],
    'deepid.html': [3],
    'liegroup.html': [2, 3, 4],
    'mcg.html': [5],
    'rcnn.html': [5],
    'transfercnn.html': [1],
}

for fname, para_idxs in problems.items():
    filepath = os.path.join(base_dir, fname)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = find_para_rows(content)

    for row in rows:
        if row['row_idx'] not in para_idxs:
            continue

        en_hl = extract_highlights(row['en_inner'])
        zh_hl = extract_highlights(row['zh_inner'])

        # 找出 en 中有但 zh 中沒有的 class
        en_classes = {}
        for cls, txt in en_hl:
            en_classes[cls] = en_classes.get(cls, 0) + 1

        zh_classes = {}
        for cls, txt in zh_hl:
            zh_classes[cls] = zh_classes.get(cls, 0) + 1

        print(f"\n--- {fname} 段落{row['row_idx']} ---")
        zh_plain = strip_html(row['zh_inner'])
        print(f"中文: {zh_plain[:200]}...")
        print(f"英文高亮 by class: {en_classes}")
        print(f"中文高亮 by class: {zh_classes}")

        # 找出缺少的
        for cls in en_classes:
            diff = en_classes[cls] - zh_classes.get(cls, 0)
            if diff > 0:
                print(f"  缺少 {diff} 個 [{cls}]")
                # 列出所有該 class 的英文高亮
                for c, t in en_hl:
                    if c == cls:
                        print(f"    EN: {t}")
                # 列出已有的中文高亮
                for c, t in zh_hl:
                    if c == cls:
                        print(f"    ZH (已有): {t}")
