#!/usr/bin/env python3
"""
修復 zh-text 中嵌套的 <span class="hl-..."> 標籤。
策略：在每個 zh-text 區塊中，反覆移除嵌套的 span，只保留最外層的。
"""
import re
import os


def fix_nested_spans_in_block(block_html):
    """修復單個 zh-text 區塊中的嵌套 span"""
    # 反覆處理直到沒有嵌套
    max_iter = 20
    for _ in range(max_iter):
        # 找到嵌套的 span: <span class="hl-X">...<span class="hl-Y">...</span>...</span>
        # 移除內層 span 的標籤（保留文字）
        pattern = r'(<span class="hl-[a-z]+">[^<]*)<span class="hl-[a-z]+">(.*?)</span>'
        new_block = re.sub(pattern, r'\1\2', block_html)
        if new_block == block_html:
            break
        block_html = new_block
    return block_html


def process_file(filepath):
    """處理單個檔案"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    def fix_zh_block(match):
        inner = match.group(1)
        fixed = fix_nested_spans_in_block(inner)
        return f'<div class="zh-text">{fixed}</div>'

    new_content = re.sub(
        r'<div class="zh-text">(.*?)</div>',
        fix_zh_block,
        content,
        flags=re.DOTALL
    )
    return new_content


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = [f for f in os.listdir(base_dir) if f.endswith('.html')]
    files.sort()

    for filename in files:
        filepath = os.path.join(base_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()

        modified = process_file(filepath)

        if modified != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"[FIXED] {filename}")
        else:
            print(f"[OK] {filename}: no nesting issues")


if __name__ == '__main__':
    main()
