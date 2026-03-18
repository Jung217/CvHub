import re, os, glob
base_dir = os.path.dirname(os.path.abspath(__file__))
html_files = sorted(glob.glob(os.path.join(base_dir, '*.html')))
total_ok = total_partial = total_missing = 0
for filepath in html_files:
    fname = os.path.basename(filepath)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    pos = 0; row_idx = 0; file_ok = file_partial = file_missing = 0; details = []
    while True:
        pr = content.find('<div class="para-row">', pos)
        if pr == -1: break
        es = content.find('<div class="en-text">', pr)
        if es == -1: pos = pr+1; continue
        ei = es + len('<div class="en-text">')
        ee = content.find('</div>', ei)
        zs = content.find('<div class="zh-text">', ee)
        if zs == -1: pos = ee+1; continue
        zi = zs + len('<div class="zh-text">')
        ze = content.find('</div>', zi)
        en = content[ei:ee]; zh = content[zi:ze]
        ec = len(re.findall(r'<span class="hl-\w+">', en))
        zc = len(re.findall(r'<span class="hl-\w+">', zh))
        if ec > 0:
            if zc == 0: file_missing += 1; details.append(f"  P{row_idx}: en={ec} zh=0")
            elif zc < ec: file_partial += 1; details.append(f"  P{row_idx}: en={ec} zh={zc} (-{ec-zc})")
            else: file_ok += 1
        row_idx += 1; pos = ze+1
    s = "OK" if file_missing == 0 and file_partial == 0 else "!!"
    print(f"[{s}] {fname}: ok={file_ok} partial={file_partial} miss={file_missing}")
    for d in details: print(d)
    total_ok += file_ok; total_partial += file_partial; total_missing += file_missing
print(f"\nTotal: ok={total_ok} partial={total_partial} miss={total_missing} => {total_ok*100//(total_ok+total_partial+total_missing)}%")
