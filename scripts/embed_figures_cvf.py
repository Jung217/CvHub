"""
embed_figures_cvf.py
針對無 arXiv ID 的論文，從 CVF Open Access PDF 提取圖片並嵌入。
策略：
  1. 從 HTML navbar 提取 CVF/其他 PDF 連結
  2. 轉換 HTML 頁面連結 → PDF 下載連結
  3. 用 PyMuPDF 提取嵌入圖片物件
  4. Base64 嵌入至 HTML
用法：python embed_figures_cvf.py [--dry-run]
"""
import os, re, json, time, base64, hashlib
import urllib.request, urllib.error
from pathlib import Path
import fitz  # PyMuPDF

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
TMPDIR = Path(os.environ.get('LOCALAPPDATA', '/tmp')) / 'Temp' / 'paper_figs_cvf'
TMPDIR.mkdir(parents=True, exist_ok=True)

MAX_FIGS = 4

# 無連結論文的 CVF PDF（人工確認可下載）
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

def fetch_url(url, timeout=60):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
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


# ── 連結提取與轉換 ────────────────────────────────────────

def extract_pdf_url(html_text, rel_path):
    """
    從 HTML 提取 CVF 連結並轉為 PDF URL。
    回傳 PDF URL 字串，或 None。
    """
    # 先找 navbar 區塊（前 5000 字元）
    head = html_text[:5000]
    links = re.findall(r'href="(https?://[^"]+)"', head)

    for link in links:
        # 跳過非論文連結
        if any(x in link for x in ['index.html', 'favicon', 'paper.css',
                                    'github.com/Jung', 'font']):
            continue

        # 直接 PDF 連結
        if link.endswith('.pdf'):
            return link

        # cv-foundation.org HTML → thecvf.com PDF
        if 'cv-foundation.org' in link and '/html/' in link:
            pdf = link.replace('www.cv-foundation.org/openaccess',
                               'openaccess.thecvf.com')
            pdf = pdf.replace('/html/', '/papers/')
            pdf = re.sub(r'\.html$', '.pdf', pdf)
            return pdf

        # openaccess.thecvf.com HTML → PDF
        if 'openaccess.thecvf.com' in link and '/html/' in link:
            pdf = link.replace('/html/', '/papers/')
            pdf = re.sub(r'\.html$', '.pdf', pdf)
            return pdf

        # openaccess.thecvf.com 頁面連結（可能需要找 PDF）
        if 'openaccess.thecvf.com' in link and link.endswith('.html'):
            pdf = re.sub(r'\.html$', '.pdf', link)
            return pdf

    # 手動覆蓋
    if rel_path in MANUAL_PDF_URLS:
        return MANUAL_PDF_URLS[rel_path]

    return None


# ── PDF 圖片提取 ──────────────────────────────────────────

def download_pdf(url, dest_path):
    data = fetch_url(url, timeout=90)
    if not data or len(data) < 30000:
        return False
    # 確認是 PDF（magic bytes）
    if not data[:4] == b'%PDF':
        return False
    with open(dest_path, 'wb') as f:
        f.write(data)
    return True


def extract_images_from_pdf(pdf_path, max_n=MAX_FIGS):
    """用 PyMuPDF 從 PDF 提取嵌入圖片物件"""
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

            # 過濾太小（圖示、分隔線）
            if width < 100 or height < 70:
                continue
            # 過濾極寬扁（頁首頁尾橫條）
            if width > height * 10:
                continue
            # 過濾 JBIG2（掃描文字）
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

    # 按品質分數排序，去除重複尺寸
    images.sort(key=lambda x: (-x['score'], x['page']))
    unique = []
    seen_sizes = set()
    for img in images:
        size_key = (img['width'] // 40, img['height'] // 40)
        if size_key not in seen_sizes:
            seen_sizes.add(size_key)
            unique.append(img)

    # 重新按頁面順序排列
    selected = sorted(unique[:max_n * 2], key=lambda x: x['page'])[:max_n]
    return selected


# ── 主處理函式 ─────────────────────────────────────────────

def process_paper(rel_path, dry_run=False):
    html_path = BASE / rel_path
    paper_key = rel_path.replace('/', '_').replace('.html', '')

    print(f'\n處理：{rel_path}')

    html = html_path.read_text(encoding='utf-8')

    # 已有圖片則跳過
    if 'figure-container' in html:
        print(f'  → 已有圖片，跳過')
        return True

    # 找 PDF URL
    pdf_url = extract_pdf_url(html, rel_path)
    if not pdf_url:
        print(f'  → 找不到 PDF 連結，跳過')
        return False

    print(f'  → PDF：{pdf_url}')

    if dry_run:
        return True

    # 下載 PDF
    pdf_dest = TMPDIR / f'{paper_key}.pdf'
    if not pdf_dest.exists():
        ok = download_pdf(pdf_url, pdf_dest)
        if not ok:
            print(f'  → PDF 下載失敗')
            return False
        print(f'  → 下載完成 ({pdf_dest.stat().st_size // 1024} KB)')
    else:
        print(f'  → 使用快取 ({pdf_dest.stat().st_size // 1024} KB)')

    # 提取圖片
    images = extract_images_from_pdf(pdf_dest)
    if not images:
        print(f'  → PDF 中無可用圖片物件')
        return False

    print(f'  → 提取 {len(images)} 張圖片')
    figures_html = []
    for i, img in enumerate(images, start=1):
        b64 = b64uri_from_bytes(img['bytes'], img['ext'])
        figures_html.append(make_figure_html(
            i, b64,
            caption_en=f'Figure {i} from original paper.',
            caption_zh=f'從原始論文 PDF 提取的圖 {i}'
        ))
        print(f'    圖 {i}：{img["width"]}×{img["height"]} px, '
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

    return True


# ── 主程式 ──────────────────────────────────────────────

NO_ARXIV_PAPERS = [
    'cvpr/2013/crowdlocalize.html', 'cvpr/2013/detection100k.html',
    'cvpr/2013/facealign.html', 'cvpr/2013/hon4d.html',
    'cvpr/2013/joint3d.html', 'cvpr/2013/multitarget.html',
    'cvpr/2013/nonblinddeblur.html', 'cvpr/2013/otb.html',
    'cvpr/2013/rgbdscene.html', 'cvpr/2013/saliency.html',
    'cvpr/2013/slampp.html', 'cvpr/2014/camerashape.html',
    'cvpr/2014/cascadehash.html', 'cvpr/2014/deepface.html',
    'cvpr/2014/deepid.html', 'cvpr/2014/liegroup.html',
    'cvpr/2014/partialopt.html', 'cvpr/2014/seqlabel.html',
    'cvpr/2014/structuredlight.html', 'cvpr/2014/transfercnn.html',
    'cvpr/2015/dynamicfusion.html', 'cvpr/2015/hrnn.html',
    'cvpr/2015/picture.html', 'cvpr/2016/slidingshapes.html',
    'cvpr/2016/sublabel.html', 'cvpr/2017/compimaging.html',
    'cvpr/2018/graphmatch.html', 'cvpr/2019/fermat.html',
    'cvpr/2022/dualshutter.html', 'eccv/2014/edge-boxes.html',
    'eccv/2014/scene-chronology.html', 'eccv/2016/event-camera-3d.html',
    'iccv/2013/absorbing.html', 'iccv/2013/boolsaliency.html',
    'iccv/2013/datadescent.html', 'iccv/2013/entrylevel.html',
    'iccv/2013/improvedtraj.html', 'iccv/2013/multilife.html',
    'iccv/2013/photoocr.html', 'iccv/2013/rgbd3d.html',
    'iccv/2013/sceneflow.html', 'iccv/2013/segfisher.html',
    'iccv/2015/dndforest.html', 'iccv/2017/globalcomplete.html',
    'iccv/2017/globalinlier.html', 'iccv/2017/opensetda.html',
    'iccv/2017/structuredvqa.html', 'iccv/2021/viewgraph.html',
    'iccv/2023/uwbimaging.html', 'iccv/2025/autofocus.html',
]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f'待處理：{len(NO_ARXIV_PAPERS)} 篇（CVF PDF 來源）')

    ok = fail = skip = 0
    for rel in NO_ARXIV_PAPERS:
        try:
            result = process_paper(rel, dry_run=args.dry_run)
            if result:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f'  [錯誤] {rel}: {e}')
            import traceback; traceback.print_exc()
            fail += 1
        time.sleep(0.5)

    print(f'\n完成：成功 {ok} / 失敗或跳過 {fail}')


if __name__ == '__main__':
    main()
