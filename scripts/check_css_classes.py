"""
掃描所有論文 HTML，找出有非標準 CSS 類別的檔案
"""
import glob, re, os

base = r'C:\Users\alex2\Desktop\vsCode\CvHub'

STANDARD = {
    'top-navbar','navbar-inner','navbar-top-row','navbar-title','course-tag',
    'best-paper-badge','honorable-badge','honorable-mention-badge',
    'navbar-links','navbar-home-link','section-nav','section-nav-inner',
    'main-container','section-heading','subsection-heading',
    'para-row','left-col','en-text','lang-divider','zh-text','right-col',
    'annotation-card','ann-label','ann-section',
    'ann-intro','ann-concept','ann-evidence','ann-rebuttal','ann-method',
    'hl-thesis','hl-concept','hl-evidence','hl-rebuttal','hl-method',
    'argument-overview','arg-skeleton','arg-step','arg-arrow',
    'arg-detail-grid','arg-detail-card',
    'floating-legend','legend-panel','legend-toggle','fl-item','fl-swatch',
    'hl-icon','figure-container','figure-caption','fig-label',
}

files = (
    glob.glob(os.path.join(base, 'cvpr', '*', '*.html')) +
    glob.glob(os.path.join(base, 'iccv', '*', '*.html')) +
    glob.glob(os.path.join(base, 'eccv', '*', '*.html')) +
    glob.glob(os.path.join(base, 'classics', '*.html'))
)

non_standard = []
for f in files:
    txt = open(f, encoding='utf-8').read()
    m = re.search(r'<style>(.*?)</style>', txt, re.DOTALL)
    if not m:
        continue
    css = m.group(1)
    classes = set(re.findall(r'\.([\w-]+)\s*[\{,:\[]', css))
    # 排除偽類與數字
    extra = {c for c in classes if c not in STANDARD and not c[0].isdigit()}
    if extra:
        rel = os.path.relpath(f, base)
        non_standard.append((rel, extra))

print(f'有非標準 CSS 的論文：{len(non_standard)} 個')
for rel, extra in sorted(non_standard):
    print(f'  {rel}: {sorted(extra)}')
