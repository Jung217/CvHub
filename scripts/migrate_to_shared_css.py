"""
將所有論文 HTML 從 inline CSS 遷移到引用 public/paper.css
- 移除 <style>...</style> 區塊
- 插入 <link rel="stylesheet"> 標籤
- 跳過有完全不同 HTML 結構的舊版論文
"""

import os
import re
import glob

BASE = r'C:\Users\alex2\Desktop\vsCode\CvHub'

# 跳過這些有完全不同 HTML 結構的舊版論文（保持原樣）
SKIP_FILES = {
    os.path.normpath(os.path.join(BASE, 'cvpr', '2019', 'bagoftricks.html')),
    os.path.normpath(os.path.join(BASE, 'cvpr', '2019', 'stylegan.html')),
    os.path.normpath(os.path.join(BASE, 'cvpr', '2019', 'giou.html')),
    os.path.normpath(os.path.join(BASE, 'cvpr', '2019', 'spade.html')),
}

# 收集所有論文 HTML
all_files = (
    glob.glob(os.path.join(BASE, 'classics', '*.html')) +
    glob.glob(os.path.join(BASE, 'cvpr', '*', '*.html')) +
    glob.glob(os.path.join(BASE, 'iccv', '*', '*.html')) +
    glob.glob(os.path.join(BASE, 'eccv', '*', '*.html'))
)

# 計算每個檔案的相對深度（classics 是 1 層，會議論文是 2 層）
def get_css_href(filepath):
    rel = os.path.relpath(filepath, BASE)
    parts = rel.split(os.sep)
    if parts[0] == 'classics':
        return '../public/paper.css'
    else:
        return '../../public/paper.css'

# 正規表達式：匹配整個 <style>...</style> 區塊
STYLE_BLOCK_RE = re.compile(r'\s*<style>.*?</style>', re.DOTALL)

updated = 0
skipped_structure = 0
already_done = 0
errors = []

for filepath in sorted(all_files):
    norm_path = os.path.normpath(filepath)

    # 跳過結構不同的舊版論文
    if norm_path in SKIP_FILES:
        skipped_structure += 1
        continue

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 已經遷移過的（沒有 <style> 區塊）
        if '<style>' not in content:
            already_done += 1
            continue

        css_href = get_css_href(filepath)
        link_tag = f'    <link rel="stylesheet" href="{css_href}">'

        # 移除 <style>...</style> 區塊
        new_content = STYLE_BLOCK_RE.sub('', content, count=1)

        # 在 </head> 前插入 <link> 標籤
        if '</head>' in new_content:
            new_content = new_content.replace('</head>', f'{link_tag}\n</head>', 1)
        else:
            errors.append(f'[無 </head>] {os.path.relpath(filepath, BASE)}')
            continue

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1

    except Exception as e:
        errors.append(f'[錯誤] {os.path.relpath(filepath, BASE)}: {e}')

print(f'完成：')
print(f'  已更新：{updated} 個')
print(f'  已跳過（結構不同）：{skipped_structure} 個')
print(f'  已是最新：{already_done} 個')
if errors:
    print(f'\n問題檔案（{len(errors)} 個）：')
    for e in errors:
        print(f'  {e}')
else:
    print('  無錯誤')
