"""
將所有會議論文 HTML 的論證結構總覽 CSS 更新為亮色系設計
排除 classics/ 資料夾（已在上一輪更新）
"""

import os
import re
import glob

# 新版論證結構 CSS（亮色系）
NEW_ARG_CSS = '''        @keyframes bar-flow {
            0%   { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }

        .argument-overview {
            margin-top: 80px;
            padding: 52px 36px 56px;
            background: linear-gradient(180deg, #f5f2ec 0%, #ece8e0 100%);
            color: #2c2c2c;
            border-radius: 14px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 2px 24px rgba(26,35,50,0.07);
        }

        .argument-overview::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ffc107, #dc3545, #007bff, #28a745, #7b61c4, #ffc107);
            background-size: 200% 100%;
            animation: bar-flow 6s linear infinite;
            border-radius: 14px 14px 0 0;
        }

        .argument-overview > * { position: relative; z-index: 1; }

        .argument-overview h2 {
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 5px;
            text-transform: uppercase;
            margin-bottom: 42px;
            text-align: center;
            color: #1a2332;
        }

        .arg-skeleton {
            display: flex;
            flex-wrap: nowrap;
            justify-content: center;
            align-items: stretch;
            gap: 0;
            margin: 0 auto 48px;
            max-width: 920px;
        }

        .arg-step {
            background: #fff;
            padding: 20px 12px 16px;
            border-radius: 10px;
            font-size: 0.82rem;
            text-align: center;
            flex: 1;
            min-width: 0;
            border: 1px solid #e8e4dc;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
        }
        .arg-step:hover { transform: translateY(-4px); }
        .arg-step:nth-child(1):hover { box-shadow: 0 8px 24px rgba(255,193,7,0.18); }
        .arg-step:nth-child(3):hover { box-shadow: 0 8px 24px rgba(220,53,69,0.15); }
        .arg-step:nth-child(5):hover { box-shadow: 0 8px 24px rgba(0,123,255,0.16); }
        .arg-step:nth-child(7):hover { box-shadow: 0 8px 24px rgba(40,167,69,0.15); }
        .arg-step:nth-child(9):hover { box-shadow: 0 8px 24px rgba(123,97,196,0.18); }

        .arg-step:nth-child(1) { border-top: 4px solid #ffc107; }
        .arg-step:nth-child(3) { border-top: 4px solid #dc3545; }
        .arg-step:nth-child(5) { border-top: 4px solid #007bff; }
        .arg-step:nth-child(7) { border-top: 4px solid #28a745; }
        .arg-step:nth-child(9) { border-top: 4px solid #7b61c4; }

        .arg-step strong {
            display: inline-block;
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
            padding: 3px 12px;
            border-radius: 10px;
        }
        .arg-step:nth-child(1) strong { background: #ffc107; color: #1a2332; }
        .arg-step:nth-child(3) strong { background: #dc3545; color: #fff; }
        .arg-step:nth-child(5) strong { background: #007bff; color: #fff; }
        .arg-step:nth-child(7) strong { background: #28a745; color: #fff; }
        .arg-step:nth-child(9) strong { background: #7b61c4; color: #fff; }

        .arg-arrow {
            display: flex;
            align-items: center;
            padding: 0 5px;
            font-size: 1.1rem;
            color: #b8b0a4;
            flex-shrink: 0;
        }

        .arg-detail-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            max-width: 920px;
            margin: 0 auto;
        }

        .arg-detail-card:first-child {
            grid-column: 1 / -1;
            background: #fff;
            border: 1px solid rgba(255,193,7,0.35);
            border-radius: 12px;
            padding: 32px 40px;
            text-align: center;
            position: relative;
            box-shadow: 0 1px 8px rgba(255,193,7,0.08);
        }
        .arg-detail-card:first-child::before {
            content: '\\201C';
            position: absolute;
            top: 6px; left: 22px;
            font-size: 4rem;
            color: rgba(255,193,7,0.25);
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1;
        }
        .arg-detail-card:first-child h3 {
            font-size: 0.7rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #b8960a;
            margin-bottom: 14px;
        }
        .arg-detail-card:first-child p {
            font-size: 1.02rem;
            line-height: 1.95;
            color: #3a3a3a;
            max-width: 700px;
            margin: 0 auto;
            font-style: italic;
        }

        .arg-detail-card {
            background: #fff;
            border: 1px solid #e8e4dc;
            border-radius: 10px;
            padding: 22px 20px;
            transition: transform 0.2s ease;
        }
        .arg-detail-card:hover { transform: translateY(-2px); }

        .arg-detail-card:nth-child(2) { border-left: 4px solid #4caf50; }
        .arg-detail-card:nth-child(2) h3 { color: #2e7d32; }

        .arg-detail-card:nth-child(3) { border-left: 4px solid #ff7043; }
        .arg-detail-card:nth-child(3) h3 { color: #d84315; }

        .arg-detail-card h3 { font-size: 0.82rem; font-weight: 600; margin-bottom: 10px; color: #1a2332; }
        .arg-detail-card p { font-size: 0.86rem; line-height: 1.7; color: #555; }
        .arg-detail-card p strong { color: #2c2c2c; }'''

# 新版 media query 中的 arg 相關規則
NEW_MEDIA_ARG = '''            .argument-overview { padding: 40px 20px 44px; }
            .arg-skeleton {
                flex-direction: column;
                align-items: center;
                max-width: 280px;
                margin-left: auto;
                margin-right: auto;
            }
            .arg-step { width: 100%; }
            .arg-arrow {
                transform: rotate(90deg);
                padding: 3px 0;
                font-size: 0.9rem;
            }
            .arg-detail-grid { grid-template-columns: 1fr; }
            .arg-detail-card:first-child { padding: 24px 20px; }
            .arg-detail-card:first-child::before { font-size: 2.5rem; top: 4px; left: 12px; }'''

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 找出所有非 classics 的 HTML 檔案
html_files = []
for conf in ['cvpr', 'iccv', 'eccv']:
    html_files.extend(glob.glob(os.path.join(BASE, conf, '*', '*.html')))

print(f'找到 {len(html_files)} 個會議論文 HTML 檔案')

# --- 主 CSS 區塊的舊模式（single-line 版）---
OLD_SINGLE_PATTERN = re.compile(
    r'\.argument-overview \{ margin-top: 60px; padding: 30px; background: #1a2332; color: #eee; border-radius: 6px; \}\s*'
    r'\.argument-overview h2 \{ font-size: 1\.3rem; font-weight: 700; margin-bottom: 22px; text-align: center; color: #fff; \}\s*'
    r'\.arg-skeleton \{ display: flex; flex-wrap: wrap; justify-content: center; gap: 0; margin-bottom: 28px; \}\s*'
    r'\.arg-step \{ background: rgba\(255,255,255,0\.08\); padding: 12px 20px; border-radius: 4px; font-size: 0\.9rem; text-align: center; min-width: 130px; \}\s*'
    r'\.arg-arrow \{ display: flex; align-items: center; padding: 0 6px; font-size: 1\.4rem; color: #5b9bd5; \}\s*'
    r'\.arg-detail-grid \{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; \}\s*'
    r'\.arg-detail-card \{ background: rgba\(255,255,255,0\.06\); border-radius: 4px; padding: 16px; \}\s*'
    r'\.arg-detail-card h3 \{ font-size: 0\.9rem; font-weight: 600; margin-bottom: 8px; color: #5b9bd5; \}\s*'
    r'\.arg-detail-card p \{ font-size: 0\.88rem; line-height: 1\.65; color: #ccc; \}',
    re.DOTALL
)

# --- 主 CSS 區塊的舊模式（multi-line 版）---
OLD_MULTI_PATTERN = re.compile(
    r'\.argument-overview \{\s*margin-top: 60px;\s*padding: 30px;\s*background: #1a2332;\s*color: #eee;\s*border-radius: 6px;\s*\}\s*'
    r'\.argument-overview h2 \{[^}]+\}\s*'
    r'\.arg-skeleton \{[^}]+\}\s*'
    r'\.arg-step \{[^}]+\}\s*'
    r'\.arg-arrow \{[^}]+\}\s*'
    r'\.arg-detail-grid \{[^}]+\}\s*'
    r'\.arg-detail-card \{[^}]+\}\s*'
    r'\.arg-detail-card h3 \{[^}]+\}\s*'
    r'\.arg-detail-card p \{[^}]+\}',
    re.DOTALL
)

# --- media query 中舊的 arg 規則（single-line 版）---
OLD_MEDIA_SINGLE = re.compile(
    r'\.arg-detail-grid \{ grid-template-columns: 1fr; \}\s*'
    r'\.arg-skeleton \{ flex-direction: column; align-items: center; \}\s*'
    r'\.arg-arrow \{ transform: rotate\(90deg\); \}'
)

# --- media query 中舊的 arg 規則（multi-line 版）---
OLD_MEDIA_MULTI = re.compile(
    r'\.arg-detail-grid \{\s*grid-template-columns: 1fr;\s*\}\s*'
    r'\.arg-skeleton \{\s*flex-direction: column;\s*align-items: center;\s*\}\s*'
    r'\.arg-arrow \{\s*transform: rotate\(90deg\);\s*\}',
    re.DOTALL
)

updated = 0
skipped = 0
errors = []

for path in sorted(html_files):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 跳過已更新的（不含舊的深色背景）
        if 'background: #1a2332; color: #eee; border-radius: 6px;' not in content and \
           'background: #1a2332;\n            color: #eee;' not in content:
            skipped += 1
            continue

        original = content

        # 1. 替換主 CSS 區塊
        new_content, n = OLD_SINGLE_PATTERN.subn(NEW_ARG_CSS, content)
        if n == 0:
            new_content, n = OLD_MULTI_PATTERN.subn(NEW_ARG_CSS, content)
        if n == 0:
            errors.append(f'[主CSS未匹配] {os.path.relpath(path, BASE)}')
            continue

        # 2. 替換 media query 中的舊 arg 規則
        new_content, m = OLD_MEDIA_SINGLE.subn(NEW_MEDIA_ARG, new_content)
        if m == 0:
            new_content, m = OLD_MEDIA_MULTI.subn(NEW_MEDIA_ARG, new_content)
        if m == 0:
            errors.append(f'[MediaQuery未匹配] {os.path.relpath(path, BASE)}')
            # 仍然寫入主 CSS 的更新

        if new_content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1

    except Exception as e:
        errors.append(f'[錯誤] {os.path.relpath(path, BASE)}: {e}')

print(f'\n完成：更新 {updated} 個，跳過 {skipped} 個（已是新版）')
if errors:
    print(f'\n以下 {len(errors)} 個檔案有問題：')
    for e in errors:
        print(' ', e)
else:
    print('無錯誤。')
