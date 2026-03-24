"""
從所有論文 HTML 提取 arXiv ID，輸出 JSON 供後續圖片嵌入使用
"""
import glob, re, json, os

BASE = r'C:\Users\alex2\Desktop\vsCode\CvHub'

files = (
    glob.glob(os.path.join(BASE, 'cvpr', '*', '*.html')) +
    glob.glob(os.path.join(BASE, 'iccv', '*', '*.html')) +
    glob.glob(os.path.join(BASE, 'eccv', '*', '*.html'))
)

# 排除已有圖片的 classics（單獨處理）
result = {}
no_arxiv = []

for f in sorted(files):
    txt = open(f, encoding='utf-8').read()
    m = re.search(r'arxiv\.org/abs/([\d.v]+)', txt)
    rel = os.path.relpath(f, BASE).replace('\\', '/')
    if m:
        arxiv_id = m.group(1).split('v')[0]  # 去掉版本號
        # 檢查是否已有圖片
        has_figs = 'figure-container' in txt
        result[rel] = {'arxiv_id': arxiv_id, 'has_figs': has_figs}
    else:
        no_arxiv.append(rel)

# 輸出 JSON
out = os.path.join(BASE, 'scripts', 'paper_arxiv_ids.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 統計
with_figs = sum(1 for v in result.values() if v['has_figs'])
without_figs = sum(1 for v in result.values() if not v['has_figs'])

print(f'有 arXiv ID：{len(result)} 篇')
print(f'  已有圖片：{with_figs} 篇')
print(f'  待新增圖片：{without_figs} 篇')
print(f'無 arXiv ID（跳過）：{len(no_arxiv)} 篇')
print(f'\n輸出至：{out}')
