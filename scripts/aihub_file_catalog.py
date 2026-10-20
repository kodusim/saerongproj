"""List the four approved-source file catalogs without downloading private records.

AIHub's API downloads files, not realtime recommendation responses.
Requires no API secret for public catalog listing. Use the official aihubshell
only after approval, and select CSV/label files rather than all image archives.
"""
import urllib.request

DATASETS = (71776, 71778, 71779, 71780)

if __name__ == '__main__':
    for dataset in DATASETS:
        print(f'\n--- dataset {dataset} ---')
        with urllib.request.urlopen(f'https://api.aihub.or.kr/info/{dataset}.do', timeout=30) as response:
            print(response.read().decode('utf-8'))
