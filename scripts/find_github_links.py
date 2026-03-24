"""
find_github_links.py
批量查詢所有論文對應的 GitHub 程式碼庫連結。
策略：
  1. 從 HTML 檔名提取論文短名（如 cyclegan, detr, resnet）
  2. 用短名搜尋 GitHub（排除 awesome-list/paper-list 等）
  3. 用全名搜尋補充（短名沒結果時）
  4. 按星星數 + 相關性挑選最佳 repo
  5. 結果儲存至 scripts/paper_github_links.json
用法：python scripts/find_github_links.py [--resume]
"""
import os, re, json, time, sys
import urllib.request, urllib.error, urllib.parse
from pathlib import Path
from glob import glob

BASE = Path(r'C:\Users\alex2\Desktop\vsCode\CvHub')
ARXIV_JSON = BASE / 'scripts' / 'paper_arxiv_ids.json'
OUTPUT_JSON = BASE / 'scripts' / 'paper_github_links.json'

GITHUB_API = 'https://api.github.com/search/repositories'
REQUEST_DELAY = 6.5  # GitHub 未驗證 10 req/min


def fetch_json(url, timeout=30):
    """抓取 JSON API，遇 rate limit 自動等待"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'CvHub-Research-Tool',
            'Accept': 'application/vnd.github+json',
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            reset = e.headers.get('X-RateLimit-Reset')
            if reset:
                wait = max(int(reset) - int(time.time()), 10)
                print(f'    Rate limit，等待 {wait} 秒...')
                time.sleep(wait + 1)
                return fetch_json(url, timeout)
            print(f'    HTTP 403 rate limit')
            return None
        if e.code == 422:
            return None
        print(f'    HTTP 錯誤 {e.code}')
        return None
    except Exception as e:
        print(f'    請求錯誤：{e}')
        return None


def extract_info_from_html(html_path):
    """從 HTML 提取論文標題與第一作者"""
    try:
        text = Path(html_path).read_text(encoding='utf-8')
        title = None
        m = re.search(r'<title>([^<]+)</title>', text)
        if m:
            title = m.group(1).strip()
            for suffix in [' — CvHub', ' - CvHub', '| CvHub']:
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()

        # 提取第一作者（通常在 meta 或 paper-authors 區塊）
        first_author = None
        # 嘗試 meta author
        am = re.search(r'<meta[^>]+name="author"[^>]+content="([^"]+)"', text)
        if am:
            first_author = am.group(1).split(',')[0].strip()
        # 嘗試 paper-authors 區塊
        if not first_author:
            am = re.search(r'class="author-name"[^>]*>([^<]+)', text)
            if am:
                first_author = am.group(1).strip()

        return title, first_author
    except Exception:
        return None, None


def short_name_from_path(rel_path):
    """從檔案路徑提取論文短名"""
    fname = os.path.basename(rel_path).replace('.html', '')
    return fname


# 排除的 repo 模式（論文列表、教學、框架）
EXCLUDE_PATTERNS = [
    'awesome-', 'paper-reading', 'papers-', 'reading-roadmap',
    'paper-list', 'deep-learning-papers', 'survey-', 'curriculum',
    'interview', 'cheatsheet', '-tutorial', 'tutorial-',
    'learning-notes', 'paper-note', 'study-', 'review-of-',
    'literature-', '-digest', 'collection-', 'reproduction',
]

EXCLUDE_ORGS = [
    'huggingface/transformers', 'pytorch/pytorch', 'tensorflow/tensorflow',
    'keras-team/keras', 'PaddlePaddle/Paddle',
]


def is_valid_repo(repo, short_name):
    """判斷 repo 是否可能是論文實作（非論文列表等）"""
    name_lower = repo['full_name'].lower()
    desc_lower = (repo.get('description') or '').lower()

    # 排除論文列表等
    for pat in EXCLUDE_PATTERNS:
        if pat in name_lower:
            return False

    # 排除超大型框架
    for org in EXCLUDE_ORGS:
        if name_lower == org:
            return False

    # 排除 fork 數遠大於 stars 的（通常是課程 template）
    if repo.get('forks_count', 0) > repo.get('stargazers_count', 0) * 3 + 10:
        if repo.get('stargazers_count', 0) < 50:
            return False

    return True


def search_github_repos(query, per_page=10):
    """GitHub Search API 搜尋 repo"""
    encoded = urllib.parse.quote(query)
    url = f'{GITHUB_API}?q={encoded}&sort=stars&order=desc&per_page={per_page}'
    data = fetch_json(url)
    if not data:
        return []
    return data.get('items', [])


def find_best_repo(short_name, title, first_author):
    """
    多策略搜尋論文的 GitHub repo：
    1. 短名精確搜尋
    2. 短名 + 作者
    3. 全名搜尋
    選出最佳候選。
    """
    all_candidates = []

    # 策略 1：用短名搜尋（最有效）
    print(f'  搜尋 1："{short_name}"')
    items = search_github_repos(f'{short_name} in:name')
    all_candidates.extend(items)
    time.sleep(REQUEST_DELAY)

    # 策略 2：如果短名結果太少或星數太低，加上作者姓氏
    if first_author and (not items or items[0].get('stargazers_count', 0) < 50):
        # 提取姓氏
        lastname = first_author.split()[-1] if first_author else ''
        if lastname and len(lastname) > 2:
            print(f'  搜尋 2："{short_name} {lastname}"')
            items2 = search_github_repos(f'{short_name} {lastname} in:name,description')
            all_candidates.extend(items2)
            time.sleep(REQUEST_DELAY)

    # 策略 3：如果仍沒好結果，用完整標題關鍵詞
    best_so_far = max((r.get('stargazers_count', 0) for r in all_candidates), default=0)
    if best_so_far < 20 and title:
        # 取標題前幾個有意義的詞
        words = re.sub(r'[^a-zA-Z0-9\s]', '', title).split()
        key_words = [w for w in words if len(w) > 3 and w.lower() not in
                     {'with', 'from', 'that', 'this', 'into', 'using', 'based',
                      'through', 'towards', 'toward', 'learning', 'deep', 'neural',
                      'network', 'networks', 'model', 'models', 'image', 'images',
                      'visual', 'vision', 'detection', 'recognition', 'approach'}][:4]
        if key_words:
            query = ' '.join(key_words)
            print(f'  搜尋 3："{query}"')
            items3 = search_github_repos(f'{query} in:name,description')
            all_candidates.extend(items3)
            time.sleep(REQUEST_DELAY)

    if not all_candidates:
        return None, []

    # 去重
    seen = set()
    unique = []
    for r in all_candidates:
        if r['full_name'] not in seen:
            seen.add(r['full_name'])
            if is_valid_repo(r, short_name):
                unique.append(r)

    if not unique:
        return None, all_candidates[:3]

    # 評分：短名出現在 repo 名中 + 星星數
    def score(r):
        name_lower = r['full_name'].lower().split('/')[-1]
        sn = short_name.lower().replace('-', '').replace('_', '')
        name_clean = name_lower.replace('-', '').replace('_', '')

        # 短名完全匹配或包含
        name_match = 0
        if sn == name_clean:
            name_match = 100
        elif sn in name_clean or name_clean in sn:
            name_match = 50
        elif any(sn in part for part in name_lower.split('-')):
            name_match = 30

        # 描述中包含短名
        desc = (r.get('description') or '').lower()
        if sn in desc.replace('-', '').replace('_', '').replace(' ', ''):
            name_match += 10

        stars = r.get('stargazers_count', 0)
        star_score = min(stars / 100, 50)  # 最多 50 分

        return name_match + star_score

    unique.sort(key=lambda r: -score(r))

    best = unique[0]
    # 如果最佳候選的分數太低（短名不匹配且星星少），視為未找到
    if score(best) < 10:
        return None, unique[:3]

    return best, unique[:5]


def get_all_paper_paths():
    """掃描所有論文 HTML 路徑"""
    patterns = [
        'cvpr/*/[!index]*.html',
        'iccv/*/[!index]*.html',
        'eccv/*/[!index]*.html',
        'classics/*.html',
    ]
    paths = []
    for pat in patterns:
        for p in glob(str(BASE / pat)):
            rel = os.path.relpath(p, BASE).replace('\\', '/')
            paths.append(rel)
    paths.sort()
    return paths


def main():
    resume = '--resume' in sys.argv

    arxiv_data = {}
    if ARXIV_JSON.exists():
        arxiv_data = json.loads(ARXIV_JSON.read_text(encoding='utf-8'))

    # 載入已有結果
    existing = {}
    if resume and OUTPUT_JSON.exists():
        try:
            existing = json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))
            # 只保留有 github_url 的（重跑找不到的）
            existing = {k: v for k, v in existing.items() if v.get('github_url')}
        except Exception:
            existing = {}

    all_paths = get_all_paper_paths()
    to_skip = set(existing.keys()) if resume else set()

    print(f'共 {len(all_paths)} 篇論文')
    if to_skip:
        print(f'續跑模式：跳過 {len(to_skip)} 篇已有結果')
    print(f'GitHub API 間隔：{REQUEST_DELAY} 秒/次')

    results = dict(existing)
    found = len(existing)
    not_found = 0

    for i, rel_path in enumerate(all_paths):
        if rel_path in to_skip:
            continue

        html_path = BASE / rel_path
        title, first_author = extract_info_from_html(html_path)
        arxiv_id = arxiv_data.get(rel_path, {}).get('arxiv_id')
        short_name = short_name_from_path(rel_path)

        print(f'\n[{i+1}/{len(all_paths)}] {rel_path} (短名: {short_name})')
        if title:
            t = title[:55] + '...' if len(title) > 55 else title
            print(f'  標題：{t}')

        best, candidates = find_best_repo(short_name, title, first_author)

        if best:
            found += 1
            stars = best.get('stargazers_count', 0)
            print(f'  => {best["html_url"]} ({stars} stars)')
            results[rel_path] = {
                'title': title,
                'arxiv_id': arxiv_id,
                'short_name': short_name,
                'github_url': best['html_url'],
                'github_name': best['full_name'],
                'stars': stars,
                'description': (best.get('description') or '')[:200],
                'language': best.get('language', ''),
            }
        else:
            not_found += 1
            cand_info = [{'url': c['html_url'] if isinstance(c, dict) and 'html_url' in c
                          else c.get('full_name',''), 'stars': c.get('stargazers_count',0)}
                         for c in (candidates or [])[:3] if isinstance(c, dict)]
            print(f'  => 未找到符合的 repo')
            results[rel_path] = {
                'title': title,
                'arxiv_id': arxiv_id,
                'short_name': short_name,
                'github_url': None,
                'stars': 0,
                'rejected_candidates': cand_info,
            }

        # 每 15 篇存檔
        if (i + 1) % 15 == 0:
            OUTPUT_JSON.write_text(
                json.dumps(results, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            print(f'\n--- 進度：{i+1}/{len(all_paths)}，有: {found}，無: {not_found} ---')

    # 最終存檔
    OUTPUT_JSON.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    with_repo = {k: v for k, v in results.items() if v.get('github_url')}
    without_repo = {k: v for k, v in results.items() if not v.get('github_url')}

    print(f'\n{"="*50}')
    print(f'查詢完成')
    print(f'有 GitHub repo：{len(with_repo)} 篇')
    print(f'無 GitHub repo：{len(without_repo)} 篇')
    print(f'{"="*50}')

    if with_repo:
        print(f'\n有 GitHub 連結的論文（按星星數排序）：')
        for k in sorted(with_repo.keys(), key=lambda x: -with_repo[x].get('stars', 0)):
            v = with_repo[k]
            print(f'  [{v["stars"]:>6}] {k}: {v["github_url"]}')

    print(f'\n結果已儲存至：{OUTPUT_JSON}')


if __name__ == '__main__':
    main()
