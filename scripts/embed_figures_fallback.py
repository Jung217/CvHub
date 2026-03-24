"""
embed_figures_fallback.py
針對 ar5iv 無法轉換的論文，使用兩階段策略嵌入圖片：
  1. 先試 ar5iv 直接資產 URL（x1.png ~ x20.png）
  2. 失敗則從 arXiv PDF 提取嵌入圖片物件
用法：python embed_figures_fallback.py
"""
import os, re, sys, json, time, base64, hashlib
import urllib.request, urllib.error
from pathlib import Path
import fitz  # PyMuPDF

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
TMPDIR = Path(os.environ.get('LOCALAPPDATA', '/tmp')) / 'Temp' / 'paper_figs'
TMPDIR.mkdir(parents=True, exist_ok=True)
ARXIV_JSON = BASE / 'scripts' / 'paper_arxiv_ids.json'

MAX_FIGS = 4

# ar5iv 「轉換失敗」佔位圖的 MD5（325×400 LA PNG）
AR5IV_PLACEHOLDER_MD5 = 'ded85833'


def is_placeholder(data):
    """偵測 ar5iv 佔位圖（hash 固定為 ded85833）"""
    return hashlib.md5(data).hexdigest()[:8] == AR5IV_PLACEHOLDER_MD5

# ── 工具函式 ──────────────────────────────────────────────

def fetch_url(url, timeout=30):
    """抓取 URL，回傳 bytes，失敗回傳 None"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def b64uri_from_bytes(data, ext):
    """bytes → data URI"""
    mime = 'image/jpeg' if ext in ('jpeg', 'jpg') else \
           'image/gif' if ext == 'gif' else \
           'image/webp' if ext == 'webp' else 'image/png'
    return f'data:{mime};base64,{base64.b64encode(data).decode()}'


def make_figure_html(num, b64, caption_en='', caption_zh=''):
    cap_en = caption_en or f'Figure {num} from original paper.'
    cap_zh = caption_zh or f'原論文圖 {num}'
    return (
        f'\n<div class="figure-container">\n'
        f'    <img src="{b64}" alt="Figure {num}">\n'
        f'    <div class="figure-caption">\n'
        f'        <span class="fig-label">Figure {num}.</span> {cap_en}<br>\n'
        f'        圖 {num}. {cap_zh}\n'
        f'    </div>\n'
        f'</div>\n'
    )


def insert_figures_into_html(html, figures_html_list):
    """插入圖片 HTML 至 .argument-overview 前"""
    ao_match = re.search(r'\n\s*<div class="argument-overview"', html)
    if ao_match:
        insert_pos = ao_match.start()
    else:
        insert_pos = html.rfind('</div>')
        if insert_pos == -1:
            insert_pos = html.rfind('</body>')
    figs_block = '\n'.join(figures_html_list)
    return html[:insert_pos] + '\n' + figs_block + '\n' + html[insert_pos:]


def verify_no_dup_figures(html_path):
    txt = Path(html_path).read_text(encoding='utf-8')
    labels = re.findall(r'fig-label\">Figure ([^<]+)', txt)
    dupes = [x for x in set(labels) if labels.count(x) > 1]
    return labels, dupes


# ── 策略 1：ar5iv 直接資產 URL ────────────────────────────

def try_ar5iv_direct(arxiv_id, paper_key, max_n=MAX_FIGS):
    """
    嘗試直接存取 ar5iv 的資產 URL：
    https://ar5iv.labs.arxiv.org/html/{arxiv_id}/assets/x{N}.png
    回傳 list of (fig_num, bytes, ext)，最多 max_n 張
    """
    base_url = f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}/assets'
    found = []

    # 先用 x1.png 探針：若第一張就是佔位圖，代表 ar5iv 整批無效
    probe = fetch_url(f'{base_url}/x1.png', timeout=15)
    if not probe or is_placeholder(probe):
        print(f'    ar5iv x1.png 為佔位圖，跳過直接資產策略')
        return []

    # 第一張有效，繼續抓後續圖片
    found.append(('1', probe, 'png'))
    dest = TMPDIR / f'{paper_key}_ar5iv_x1.png'
    dest.write_bytes(probe)
    print(f'    ar5iv x1.png OK ({len(probe)//1024} KB)')

    consecutive_miss = 0
    for n in range(2, 25):
        url = f'{base_url}/x{n}.png'
        data = fetch_url(url, timeout=15)
        if data and len(data) > 2000 and not is_placeholder(data):
            dest = TMPDIR / f'{paper_key}_ar5iv_x{n}.png'
            dest.write_bytes(data)
            found.append((str(n), data, 'png'))
            print(f'    ar5iv x{n}.png OK ({len(data)//1024} KB)')
            consecutive_miss = 0
            if len(found) >= max_n:
                break
        else:
            # 遇到缺失或佔位圖，連續兩次就停止
            consecutive_miss += 1
            if consecutive_miss >= 2:
                break

    return found


# ── 策略 2：arXiv PDF 提取 ──────────────────────────────

def download_pdf(arxiv_id, dest_path):
    """下載 arXiv PDF"""
    url = f'https://arxiv.org/pdf/{arxiv_id}'
    data = fetch_url(url, timeout=90)
    if not data or len(data) < 50000:
        return False
    with open(dest_path, 'wb') as f:
        f.write(data)
    return True


def extract_images_from_pdf(pdf_path, max_n=MAX_FIGS):
    """
    用 PyMuPDF 從 PDF 提取嵌入圖片物件。
    回傳 list of dict: {num, bytes, ext, width, height, page}
    """
    doc = fitz.open(str(pdf_path))
    images = []
    seen_xrefs = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_img = doc.extract_image(xref)
            except Exception:
                continue

            img_bytes = base_img['image']
            ext = base_img['ext']
            width = base_img['width']
            height = base_img['height']

            # 過濾：太小（圖示、分隔線）
            if width < 120 or height < 80:
                continue
            # 過濾：極寬扁（頁首頁尾）
            if width > height * 8:
                continue
            # 過濾：不支援格式（jb2 = JBIG2 二值，多為掃描文字）
            if ext in ('jb2', 'ccitt'):
                continue
            # 過濾：SMASK（遮罩）通常不是圖片內容
            if img_info[1] != 0:  # smask xref
                pass  # 允許有 smask 的圖

            area = width * height
            score = min(area, 800000)

            images.append({
                'bytes': img_bytes,
                'ext': 'png' if ext in ('png', 'jb2') else ext,
                'width': width,
                'height': height,
                'page': page_num + 1,
                'score': score,
            })

    doc.close()

    if not images:
        return []

    # 按分數排序（面積大的優先），去重相似尺寸
    images.sort(key=lambda x: (-x['score'], x['page']))
    unique = []
    seen_sizes = set()
    for img in images:
        size_key = (img['width'] // 40, img['height'] // 40)
        if size_key not in seen_sizes:
            seen_sizes.add(size_key)
            unique.append(img)

    # 重新按頁面順序排序
    selected = sorted(unique[:max_n * 2], key=lambda x: x['page'])[:max_n]
    return selected


# ── 主處理函式 ─────────────────────────────────────────────

def process_paper(rel_path, arxiv_id):
    html_path = BASE / rel_path
    paper_key = rel_path.replace('/', '_').replace('.html', '')

    print(f'\n處理：{rel_path}  (arXiv: {arxiv_id})')

    figures_html = []

    # ── 策略 1：ar5iv 直接資產 URL ──
    print(f'  → 嘗試 ar5iv 直接資產 URL...')
    ar5iv_figs = try_ar5iv_direct(arxiv_id, paper_key)

    if ar5iv_figs:
        print(f'  → ar5iv 直接資產：找到 {len(ar5iv_figs)} 張')
        for num, data, ext in ar5iv_figs:
            b64 = b64uri_from_bytes(data, ext)
            figures_html.append(make_figure_html(num, b64))
    else:
        # ── 策略 2：arXiv PDF 提取 ──
        print(f'  → ar5iv 無資產，改用 PDF 提取...')
        pdf_dest = TMPDIR / f'{paper_key}.pdf'

        if not pdf_dest.exists():
            ok = download_pdf(arxiv_id, pdf_dest)
            if not ok:
                print(f'  → PDF 下載失敗，跳過')
                return False
            print(f'  → PDF 下載完成 ({pdf_dest.stat().st_size // 1024} KB)')
        else:
            print(f'  → 使用快取 PDF ({pdf_dest.stat().st_size // 1024} KB)')

        images = extract_images_from_pdf(pdf_dest)
        if not images:
            print(f'  → PDF 中無可用圖片物件，跳過')
            return False

        print(f'  → 從 PDF 提取 {len(images)} 張圖片')
        for i, img in enumerate(images, start=1):
            b64 = b64uri_from_bytes(img['bytes'], img['ext'])
            figures_html.append(make_figure_html(
                i, b64,
                caption_en=f'Figure {i} extracted from original paper.',
                caption_zh=f'從原始論文 PDF 提取的圖 {i}'
            ))
            print(f'    圖 {i}：{img["width"]}×{img["height"]} px, '
                  f'{len(img["bytes"])//1024} KB (第 {img["page"]} 頁)')

    if not figures_html:
        print(f'  → 無圖片可嵌入')
        return False

    # ── 插入 HTML ──
    html = html_path.read_text(encoding='utf-8')
    new_html = insert_figures_into_html(html, figures_html)
    html_path.write_text(new_html, encoding='utf-8')

    # ── 驗證 ──
    labels, dupes = verify_no_dup_figures(html_path)
    if dupes:
        print(f'  [警告] 重複 Figure 編號：{dupes}')
    else:
        print(f'  [OK] Figure 編號：{labels}')

    return True


# ── 主程式 ──────────────────────────────────────────────

def main():
    data = json.loads(ARXIV_JSON.read_text(encoding='utf-8'))
    targets = [
        (path, info['arxiv_id'])
        for path, info in data.items()
        if not info['has_figs']
    ]

    print(f'待處理：{len(targets)} 篇（使用備援策略）')

    ok = fail = 0
    for path, arxiv_id in targets:
        try:
            success = process_paper(path, arxiv_id)
            if success:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f'  [錯誤] {path}: {e}')
            import traceback; traceback.print_exc()
            fail += 1
        time.sleep(1)  # 避免 arXiv rate limit

    print(f'\n完成：成功 {ok} / 失敗 {fail}')


if __name__ == '__main__':
    main()
