"""
embed_figures_cvf_retry.py
重試 CVF PDF 圖片嵌入：針對上一輪下載失敗的論文，
加入重試機制（每篇最多 3 次）和更長的請求間隔（5 秒）。
跳過已有圖片的論文。
"""
import os, re, json, time, base64, hashlib, sys
import urllib.request, urllib.error
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print('錯誤：需要 PyMuPDF，請執行 pip install pymupdf')
    sys.exit(1)

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
TMPDIR = Path(os.environ.get('LOCALAPPDATA', '/tmp')) / 'Temp' / 'paper_figs_cvf'
TMPDIR.mkdir(parents=True, exist_ok=True)

MAX_FIGS = 4
MAX_RETRIES = 3
RETRY_DELAY = 8       # 重試間隔（秒）
REQUEST_DELAY = 5     # 每篇之間的間隔（秒）
DOWNLOAD_TIMEOUT = 120  # 下載超時（秒）

# 手動 PDF URL（與主腳本同步）
MANUAL_PDF_URLS = {
    'cvpr/2015/dynamicfusion.html':
        'https://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/'
        'Newcombe_DynamicFusion_Reconstruction_and_2015_CVPR_paper.pdf',
    'cvpr/2015/hrnn.html':
        'https://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/'
        'Du_Hierarchical_Recurrent_Neural_2015_CVPR_paper.pdf',
    'cvpr/2015/picture.html':
        'https://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/'
        'Kulkarni_Picture_A_Probabilistic_2015_CVPR_paper.pdf',
    'cvpr/2016/slidingshapes.html':
        'https://www.cv-foundation.org/openaccess/content_cvpr_2016/papers/'
        'Song_Deep_Sliding_Shapes_CVPR_2016_paper.pdf',
    'eccv/2014/edge-boxes.html':
        'https://www.microsoft.com/en-us/research/wp-content/uploads/2014/09/'
        'ZitnickDollarECCV14edgeBoxes.pdf',
    'eccv/2016/event-camera-3d.html':
        'https://www.doc.ic.ac.uk/~ajd/Publications/kim_etal_eccv2016.pdf',
    'iccv/2015/dndforest.html':
        'https://www.cv-foundation.org/openaccess/content_iccv_2015/papers/'
        'Kontschieder_Deep_Neural_Decision_ICCV_2015_paper.pdf',
    'iccv/2017/globalcomplete.html':
        'http://iizuka.cs.tsukuba.ac.jp/projects/completion/data/completion_sig2017.pdf',
    'iccv/2017/globalinlier.html':
        'https://arxiv.org/pdf/1709.09384',
    'iccv/2017/structuredvqa.html':
        'https://arxiv.org/pdf/1708.02071',
    'iccv/2017/opensetda.html':
        'https://openaccess.thecvf.com/content_ICCV_2017/papers/'
        'Busto_Open_Set_Domain_ICCV_2017_paper.pdf',
    'iccv/2025/autofocus.html':
        'https://openaccess.thecvf.com/content/ICCV2025/papers/'
        'Qin_Spatially-Varying_Autofocus_ICCV_2025_paper.pdf',
}


# ── 工具函式 ──────────────────────────────────────────────

def fetch_url(url, timeout=DOWNLOAD_TIMEOUT):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,*/*',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f'    fetch 錯誤：{e}')
        return None


def b64uri_from_bytes(data, ext):
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


# ── 連結提取 ────────────────────────────────────────

def extract_pdf_url(html_text, rel_path):
    head = html_text[:5000]
    links = re.findall(r'href="(https?://[^"]+)"', head)

    for link in links:
        if any(x in link for x in ['index.html', 'favicon', 'paper.css',
                                    'github.com/Jung', 'font']):
            continue
        if link.endswith('.pdf'):
            return link
        if 'cv-foundation.org' in link and '/html/' in link:
            pdf = link.replace('www.cv-foundation.org/openaccess',
                               'openaccess.thecvf.com')
            pdf = pdf.replace('/html/', '/papers/')
            pdf = re.sub(r'\.html$', '.pdf', pdf)
            return pdf
        if 'openaccess.thecvf.com' in link and '/html/' in link:
            pdf = link.replace('/html/', '/papers/')
            pdf = re.sub(r'\.html$', '.pdf', pdf)
            return pdf
        if 'openaccess.thecvf.com' in link and link.endswith('.html'):
            pdf = re.sub(r'\.html$', '.pdf', link)
            return pdf

    if rel_path in MANUAL_PDF_URLS:
        return MANUAL_PDF_URLS[rel_path]

    return None


# ── PDF 下載（含重試） ──────────────────────────────────

def download_pdf_with_retry(url, dest_path, max_retries=MAX_RETRIES):
    """下載 PDF，失敗時自動重試"""
    for attempt in range(1, max_retries + 1):
        print(f'    下載嘗試 {attempt}/{max_retries}...')
        data = fetch_url(url, timeout=DOWNLOAD_TIMEOUT)

        if not data:
            if attempt < max_retries:
                print(f'    等待 {RETRY_DELAY} 秒後重試...')
                time.sleep(RETRY_DELAY)
            continue

        if len(data) < 30000:
            print(f'    檔案太小 ({len(data)} bytes)，可能不是 PDF')
            if attempt < max_retries:
                time.sleep(RETRY_DELAY)
            continue

        if not data[:4] == b'%PDF':
            print(f'    非 PDF 格式（magic bytes: {data[:4]}）')
            if attempt < max_retries:
                time.sleep(RETRY_DELAY)
            continue

        with open(dest_path, 'wb') as f:
            f.write(data)
        print(f'    下載完成 ({len(data) // 1024} KB)')
        return True

    return False


# ── PDF 圖片提取 ──────────────────────────────────────────

def extract_images_from_pdf(pdf_path, max_n=MAX_FIGS):
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

            if width < 100 or height < 70:
                continue
            if width > height * 10:
                continue
            if ext in ('jb2', 'ccitt'):
                continue

            area = width * height
            images.append({
                'bytes': img_bytes,
                'ext': 'png' if ext in ('png', 'jb2') else ext,
                'width': width,
                'height': height,
                'page': page_num + 1,
                'score': min(area, 1000000),
            })

    doc.close()
    if not images:
        return []

    images.sort(key=lambda x: (-x['score'], x['page']))
    unique = []
    seen_sizes = set()
    for img in images:
        size_key = (img['width'] // 40, img['height'] // 40)
        if size_key not in seen_sizes:
            seen_sizes.add(size_key)
            unique.append(img)

    selected = sorted(unique[:max_n * 2], key=lambda x: x['page'])[:max_n]
    return selected


# ── 主處理函式 ─────────────────────────────────────────────

def process_paper(rel_path):
    html_path = BASE / rel_path
    paper_key = rel_path.replace('/', '_').replace('.html', '')

    print(f'\n處理：{rel_path}')

    if not html_path.exists():
        print(f'  → 檔案不存在，跳過')
        return 'skip'

    html = html_path.read_text(encoding='utf-8')

    # 已有圖片則跳過
    if 'figure-container' in html:
        print(f'  → 已有圖片，跳過')
        return 'skip'

    # 找 PDF URL
    pdf_url = extract_pdf_url(html, rel_path)
    if not pdf_url:
        print(f'  → 找不到 PDF 連結，跳過')
        return 'no_url'

    print(f'  → PDF：{pdf_url}')

    # 下載 PDF（含重試）
    pdf_dest = TMPDIR / f'{paper_key}.pdf'
    if pdf_dest.exists() and pdf_dest.stat().st_size > 30000:
        print(f'  → 使用快取 ({pdf_dest.stat().st_size // 1024} KB)')
    else:
        ok = download_pdf_with_retry(pdf_url, pdf_dest)
        if not ok:
            print(f'  → PDF 下載失敗（已重試 {MAX_RETRIES} 次）')
            return 'download_fail'

    # 提取圖片
    images = extract_images_from_pdf(pdf_dest)
    if not images:
        print(f'  → PDF 中無可用圖片物件')
        return 'no_images'

    print(f'  → 提取 {len(images)} 張圖片')
    figures_html = []
    for i, img in enumerate(images, start=1):
        b64 = b64uri_from_bytes(img['bytes'], img['ext'])
        figures_html.append(make_figure_html(
            i, b64,
            caption_en=f'Figure {i} from original paper.',
            caption_zh=f'從原始論文 PDF 提取的圖 {i}'
        ))
        print(f'    圖 {i}：{img["width"]}x{img["height"]} px, '
              f'{len(img["bytes"])//1024} KB (第 {img["page"]} 頁)')

    # 插入 HTML
    new_html = insert_figures_into_html(html, figures_html)
    html_path.write_text(new_html, encoding='utf-8')

    # 驗證
    labels, dupes = verify_no_dup_figures(html_path)
    if dupes:
        print(f'  [警告] 重複編號：{dupes}')
    else:
        print(f'  [OK] Figure 編號：{labels}')

    return 'ok'


# ── 待重試清單 ──────────────────────────────────────────

RETRY_PAPERS = [
    'cvpr/2013/crowdlocalize.html',
    'cvpr/2013/detection100k.html',
    'cvpr/2013/facealign.html',
    'cvpr/2013/joint3d.html',
    'cvpr/2013/otb.html',
    'cvpr/2013/saliency.html',
    'cvpr/2013/slampp.html',
    'cvpr/2014/cascadehash.html',
    'cvpr/2014/deepface.html',
    'cvpr/2014/deepid.html',
    'cvpr/2014/liegroup.html',
    'cvpr/2014/seqlabel.html',
    'cvpr/2014/structuredlight.html',
    'cvpr/2016/sublabel.html',
    'cvpr/2017/compimaging.html',
    'cvpr/2018/graphmatch.html',
    'cvpr/2019/fermat.html',
    'cvpr/2022/dualshutter.html',
    'eccv/2014/edge-boxes.html',
    'iccv/2013/boolsaliency.html',
    'iccv/2013/datadescent.html',
    'iccv/2013/photoocr.html',
    'iccv/2013/rgbd3d.html',
    'iccv/2013/sceneflow.html',
    'iccv/2013/segfisher.html',
    'iccv/2015/dndforest.html',
    'iccv/2017/opensetda.html',
    'iccv/2021/viewgraph.html',
    'iccv/2023/uwbimaging.html',
    'iccv/2025/autofocus.html',
]


def main():
    print(f'重試 CVF 圖片嵌入：{len(RETRY_PAPERS)} 篇')
    print(f'每篇最多重試 {MAX_RETRIES} 次，間隔 {REQUEST_DELAY} 秒')

    results = {'ok': 0, 'skip': 0, 'no_url': 0, 'download_fail': 0, 'no_images': 0, 'error': 0}

    for i, rel in enumerate(RETRY_PAPERS):
        try:
            result = process_paper(rel)
            results[result] = results.get(result, 0) + 1
        except Exception as e:
            print(f'  [錯誤] {rel}: {e}')
            import traceback; traceback.print_exc()
            results['error'] += 1

        # 每篇之間間隔（最後一篇不用等）
        if i < len(RETRY_PAPERS) - 1:
            time.sleep(REQUEST_DELAY)

    print(f'\n===== 結果 =====')
    print(f'成功嵌入：{results["ok"]}')
    print(f'已有圖片（跳過）：{results["skip"]}')
    print(f'無 PDF 連結：{results["no_url"]}')
    print(f'下載失敗：{results["download_fail"]}')
    print(f'無可用圖片：{results["no_images"]}')
    print(f'執行錯誤：{results["error"]}')


if __name__ == '__main__':
    main()
