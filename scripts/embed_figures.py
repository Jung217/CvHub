"""
embed_figures.py
從 ar5iv 抓取原始論文圖片，base64 嵌入至所有論文 HTML。
用法：python embed_figures.py [--conf cvpr/2023] [--dry-run]
"""
import os, re, sys, json, time, base64, argparse
import urllib.request, urllib.error
from pathlib import Path
from html.parser import HTMLParser

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
TMPDIR = Path(os.environ.get('LOCALAPPDATA', '/tmp')) / 'Temp' / 'paper_figs'
TMPDIR.mkdir(parents=True, exist_ok=True)

ARXIV_JSON = BASE / 'scripts' / 'paper_arxiv_ids.json'

# ── 圖片選取：優先選這些關鍵字（出現在 caption 中優先） ──
PRIORITY_KEYWORDS = [
    'architecture', 'framework', 'pipeline', 'overview', 'network',
    'model', 'method', 'structure', 'comparison', 'result', 'performance'
]

MAX_FIGS = 4  # 每篇最多嵌入圖片數

# ── 驗證工具 ──
def verify_no_dup_figures(html_path):
    """回傳 (labels_list, dup_list)"""
    txt = Path(html_path).read_text(encoding='utf-8')
    labels = re.findall(r'fig-label">\s*Figure\s+([^<]+?)\s*\.?\s*<', txt)
    dupes = [x for x in set(labels) if labels.count(x) > 1]
    return labels, dupes

# ── ar5iv 頁面解析 ──
def fetch_ar5iv_figures(arxiv_id):
    """
    回傳 list of dict: {num, img_url, caption_en}
    num 為字串，如 '1', '2', '2a'
    """
    url = f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f'    [ar5iv 失敗] {e}')
        return []

    figures = []

    # 方法 1：找 <figure> 區塊
    fig_blocks = re.findall(
        r'<figure[^>]*>(.*?)</figure>',
        html, re.DOTALL | re.IGNORECASE
    )
    for block in fig_blocks:
        # 找 Figure 編號
        num_m = re.search(
            r'Figure\s+(\d+[a-z]?)\b|fig(?:ure)?[:\s]+(\d+[a-z]?)\b',
            block, re.IGNORECASE
        )
        if not num_m:
            continue
        num = (num_m.group(1) or num_m.group(2)).strip()

        # 找 img src
        img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block)
        if not img_m:
            continue
        src = img_m.group(1)
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = f'https://ar5iv.labs.arxiv.org{src}'
        elif not src.startswith('http'):
            src = f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}/{src}'

        # 只要 png/jpg/jpeg/gif/webp（排除 svg 和 ico）
        if re.search(r'\.(svg|ico)(\?|$)', src, re.IGNORECASE):
            continue

        # 找 caption
        cap_m = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', block, re.DOTALL | re.IGNORECASE)
        caption = ''
        if cap_m:
            caption = re.sub(r'<[^>]+>', '', cap_m.group(1)).strip()
            caption = re.sub(r'\s+', ' ', caption)[:300]

        figures.append({'num': num, 'img_url': src, 'caption': caption})

    # 去重（同一 num 只保留第一個）
    seen = set()
    unique = []
    for fig in figures:
        if fig['num'] not in seen:
            seen.add(fig['num'])
            unique.append(fig)

    return unique

# ── 選取最重要的圖 ──
def select_figures(figures, max_n=MAX_FIGS):
    if not figures:
        return []
    # 先依編號排序
    def sort_key(f):
        m = re.match(r'(\d+)', f['num'])
        return int(m.group(1)) if m else 999
    figures = sorted(figures, key=sort_key)

    if len(figures) <= max_n:
        return figures

    # 計算優先分
    def priority(f):
        cap_lower = f['caption'].lower()
        score = 0
        for kw in PRIORITY_KEYWORDS:
            if kw in cap_lower:
                score += 1
        # 前 3 張圖加分
        n = sort_key(f)
        if n <= 3:
            score += 2
        return score

    scored = sorted(figures, key=lambda f: (-priority(f), sort_key(f)))
    selected = scored[:max_n]
    # 重新按編號排序後回傳
    return sorted(selected, key=sort_key)

# ── 下載圖片 ──
def download_img(url, dest_path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        if len(data) < 1000:  # 檔案過小，可能是錯誤頁
            return False
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        print(f'    [下載失敗] {url}: {e}')
        return False

# ── base64 編碼 ──
def b64uri(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    ext = str(filepath).rsplit('.', 1)[-1].lower()
    mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else \
           'image/gif' if ext == 'gif' else \
           'image/webp' if ext == 'webp' else 'image/png'
    return f'data:{mime};base64,{base64.b64encode(data).decode()}'

# ── 產生 figure-container HTML ──
def make_figure_html(fig, b64):
    num = fig['num']
    cap = fig['caption']
    # 從 caption 中移除 "Figure N." 前綴
    cap_clean = re.sub(r'^Figure\s+\d+[a-z]?\.\s*', '', cap).strip()
    # 簡短中文說明（取前 100 字）
    zh_cap = cap_clean[:100] + ('…' if len(cap_clean) > 100 else '')
    return (
        f'\n<div class="figure-container">\n'
        f'    <img src="{b64}" alt="Figure {num}">\n'
        f'    <div class="figure-caption">\n'
        f'        <span class="fig-label">Figure {num}.</span> {cap_clean}<br>\n'
        f'        圖 {num}. {zh_cap}\n'
        f'    </div>\n'
        f'</div>\n'
    )

# ── 找插入點：在對應段落後插入 ──
def insert_figures_into_html(html, figures_html_list):
    """
    將所有圖片集中插入在 </div><!-- main-container --> 的前面
    更精確：插入在最後一個 .para-row 之後、.argument-overview 之前
    """
    # 找 argument-overview 的起點
    ao_match = re.search(r'\n\s*<div class="argument-overview"', html)
    if ao_match:
        insert_pos = ao_match.start()
    else:
        # fallback：在 </div>\n</body> 前
        insert_pos = html.rfind('</div>')
        if insert_pos == -1:
            insert_pos = html.rfind('</body>')

    figs_block = '\n'.join(figures_html_list)
    return html[:insert_pos] + '\n' + figs_block + '\n' + html[insert_pos:]

# ── 處理單篇論文 ──
def process_paper(rel_path, arxiv_id, dry_run=False):
    html_path = BASE / rel_path
    paper_key = rel_path.replace('/', '_').replace('.html', '')

    print(f'\n處理：{rel_path}  (arXiv: {arxiv_id})')

    # 1. 抓 ar5iv 圖片列表
    figures = fetch_ar5iv_figures(arxiv_id)
    if not figures:
        print(f'  → 無可用圖片，跳過')
        return False

    # 2. 選圖
    selected = select_figures(figures)
    print(f'  → 找到 {len(figures)} 張圖，選取 {len(selected)} 張：{[f["num"] for f in selected]}')

    if dry_run:
        return True

    # 3. 下載、編碼
    figures_html = []
    for fig in selected:
        ext = re.search(r'\.(png|jpg|jpeg|gif|webp)', fig['img_url'], re.IGNORECASE)
        suffix = ext.group(0).lower() if ext else '.png'
        dest = TMPDIR / f'{paper_key}_fig{fig["num"]}{suffix}'
        ok = download_img(fig['img_url'], dest)
        if not ok:
            print(f'    Figure {fig["num"]} 下載失敗，跳過')
            continue
        b64 = b64uri(dest)
        figures_html.append(make_figure_html(fig, b64))
        print(f'    Figure {fig["num"]}：{dest.stat().st_size // 1024} KB')

    if not figures_html:
        print(f'  → 所有圖片下載失敗')
        return False

    # 4. 插入 HTML
    html = html_path.read_text(encoding='utf-8')
    new_html = insert_figures_into_html(html, figures_html)
    html_path.write_text(new_html, encoding='utf-8')

    # 5. 驗證編號
    labels, dupes = verify_no_dup_figures(html_path)
    if dupes:
        print(f'  [警告] 重複 Figure 編號：{dupes}')
    else:
        print(f'  [OK] Figure 編號：{labels}')

    return True


# ── 主程式 ──
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', help='只處理此路徑前綴，如 cvpr/2023')
    parser.add_argument('--dry-run', action='store_true', help='只列出圖片不實際嵌入')
    parser.add_argument('--limit', type=int, default=0, help='最多處理 N 篇（測試用）')
    args = parser.parse_args()

    data = json.loads(ARXIV_JSON.read_text(encoding='utf-8'))

    papers = [
        (path, info['arxiv_id'])
        for path, info in data.items()
        if not info['has_figs']  # 跳過已有圖片的
    ]

    if args.conf:
        papers = [(p, a) for p, a in papers if p.startswith(args.conf)]

    if args.limit:
        papers = papers[:args.limit]

    print(f'待處理：{len(papers)} 篇')

    ok = fail = 0
    for path, arxiv_id in papers:
        try:
            success = process_paper(path, arxiv_id, dry_run=args.dry_run)
            if success:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f'  [錯誤] {path}: {e}')
            fail += 1
        time.sleep(0.3)  # 避免過快請求

    print(f'\n完成：成功 {ok} / 失敗 {fail}')


if __name__ == '__main__':
    main()
