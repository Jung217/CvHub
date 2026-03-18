"""
掃描 CVPR 2014 所有 HTML 檔案，
對每個 para-row 中 en-text 有 hl- 高亮但 zh-text 缺少對應高亮的地方，
在 zh-text 中找到中文翻譯並加上相同 hl- class。
"""

import re
import os
import glob
from html.parser import HTMLParser

# 定義英文高亮片段到中文翻譯的對應
# 這個腳本會逐檔案、逐 para-row 處理

def extract_para_rows(html_content):
    """提取所有 para-row 區塊的位置"""
    rows = []
    pattern = re.compile(r'<div class="para-row">(.*?)</div>\s*</div>\s*</div>', re.DOTALL)
    # 更精確的方式：找到每個 para-row 的開始和結束
    start = 0
    while True:
        idx = html_content.find('<div class="para-row">', start)
        if idx == -1:
            break
        # 找到這個 para-row 中的 en-text 和 zh-text
        en_start = html_content.find('<div class="en-text">', idx)
        if en_start == -1:
            start = idx + 1
            continue
        en_end = html_content.find('</div>', en_start)
        if en_end == -1:
            start = idx + 1
            continue

        zh_start = html_content.find('<div class="zh-text">', en_end)
        if zh_start == -1:
            start = idx + 1
            continue
        zh_end = html_content.find('</div>', zh_start)
        if zh_end == -1:
            start = idx + 1
            continue

        en_content = html_content[en_start:en_end + len('</div>')]
        zh_content = html_content[zh_start:zh_end + len('</div>')]

        rows.append({
            'en_start': en_start,
            'en_end': en_end + len('</div>'),
            'zh_start': zh_start,
            'zh_end': zh_end + len('</div>'),
            'en_content': en_content,
            'zh_content': zh_content,
        })
        start = zh_end + 1
    return rows

def extract_highlights(en_text):
    """從 en-text 中提取所有高亮片段及其 class"""
    pattern = re.compile(r'<span class="(hl-\w+)">(.*?)</span>', re.DOTALL)
    highlights = []
    for m in pattern.finditer(en_text):
        hl_class = m.group(1)
        hl_text = m.group(2).strip()
        highlights.append((hl_class, hl_text))
    return highlights

def zh_text_has_highlights(zh_text):
    """檢查 zh-text 中是否已有高亮"""
    return 'hl-' in zh_text

def build_en_to_zh_mapping(en_highlights):
    """
    為每個英文高亮片段建立對應的中文翻譯關鍵字。
    這是一個大型對照表，根據實際內容建立。
    """
    # 這個函數不夠通用，改用另一種策略
    pass

def process_file(filepath):
    """處理單個 HTML 檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = extract_para_rows(content)
    if not rows:
        print(f"  [跳過] 未找到 para-row: {filepath}")
        return False

    modified = False
    # 從後往前處理，這樣修改位置不會影響前面的索引
    for row in reversed(rows):
        en_content = row['en_content']
        zh_content = row['zh_content']

        highlights = extract_highlights(en_content)
        if not highlights:
            continue

        # 檢查 zh-text 中已有的高亮數量
        existing_zh_hl = len(re.findall(r'<span class="hl-\w+">', zh_content))
        en_hl_count = len(highlights)

        if existing_zh_hl >= en_hl_count:
            # 已經有足夠的高亮了
            continue

        # 需要新增的高亮
        # 提取 zh-text 的純文字內容
        zh_inner_start = zh_content.find('>') + 1
        zh_inner_end = zh_content.rfind('</div>')
        zh_inner = zh_content[zh_inner_start:zh_inner_end]

        print(f"  段落有 {en_hl_count} 個英文高亮，{existing_zh_hl} 個中文高亮")

    return False  # 暫時不做修改，先分析

# 先分析所有檔案的情況
base_dir = os.path.dirname(os.path.abspath(__file__))
html_files = sorted(glob.glob(os.path.join(base_dir, '*.html')))

print(f"找到 {len(html_files)} 個 HTML 檔案")
for f in html_files:
    fname = os.path.basename(f)
    print(f"\n=== 分析 {fname} ===")
    process_file(f)
