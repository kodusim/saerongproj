"""Download only approved 2023 travel CSV archives; keep credentials out of output."""
import argparse
import os
from pathlib import Path
import tarfile
import urllib.error
import urllib.request
import zipfile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {71776: (539784, 539787), 71778: (539795, 539798),
            71779: (539804, 539807), 71780: (541667, 541670)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', action='store_true')
    parser.add_argument('--dataset', type=int, choices=list(DATASETS))
    parser.add_argument('--extract-only', action='store_true')
    args = parser.parse_args()
    if args.catalog and args.extract_only:
        parser.error('--catalog and --extract-only cannot be combined')
    config = dotenv_values(ROOT / '.env')
    key = os.getenv('AIHUB_API_KEY') or config.get('AIHUB_API_KEY') or config.get('AI_HUB_API_KEY')
    if not args.catalog and not args.extract_only and not key:
        raise SystemExit('AIHUB_API_KEY is not configured.')
    folder = ROOT / 'private_data' / 'travel' / 'raw'
    folder.mkdir(parents=True, exist_ok=True)
    for dataset, files in DATASETS.items():
        if args.dataset and dataset != args.dataset:
            continue
        if args.catalog:
            url = f'https://api.aihub.or.kr/info/{dataset}.do'
        else:
            url = f'https://api.aihub.or.kr/down/0.6/{dataset}.do?fileSn=' + ','.join(map(str, files))
        request = urllib.request.Request(url, headers={} if args.catalog or not key else {'apikey': key})
        response = None
        if not args.extract_only and (args.catalog or not (folder / str(dataset) / 'csv.tar').exists()):
            try:
                response = urllib.request.urlopen(request, timeout=90)
            except urllib.error.HTTPError as error:
                # AIHub sometimes returns valid catalogs/files with status 502.
                response = error
            except urllib.error.URLError:
                raise SystemExit(f'{dataset}: connection failed; retry with network access.') from None
        if args.catalog:
            body = response.read()
            (folder / f'{dataset}-catalog.txt').write_bytes(body)
            print(dataset, body.decode('utf-8', errors='replace'), flush=True)
            continue
        target = folder / str(dataset)
        target.mkdir(exist_ok=True)
        archive = target / 'csv.tar'
        if not archive.exists():
            if response is None:
                raise SystemExit('No local archive; download first.')
            part = archive.with_suffix('.partial')
            size = 0
            with part.open('wb') as stream:
                while block := response.read(1024 * 1024):
                    stream.write(block)
                    size += len(block)
                    if size % (10 * 1024 * 1024) == 0:
                        print(f'{dataset}: {size // 1024 // 1024} MB', flush=True)
            if not tarfile.is_tarfile(part):
                # Do not echo server bodies which could contain credential information.
                raise SystemExit(f'{dataset}: response is not a tar archive (HTTP {response.status}, {size} bytes).')
            part.replace(archive)
        with tarfile.open(archive) as bundle:
            bundle.extractall(target, filter='data')
        for first in target.rglob('*.zip.part0'):
            combined = first.with_suffix('')
            parts = sorted(first.parent.glob(combined.name + '.part*'),
                           key=lambda p: int(p.suffix.removeprefix('.part')))
            with combined.open('wb') as stream:
                for part in parts:
                    stream.write(part.read_bytes())
            output = combined.parent / combined.stem
            with zipfile.ZipFile(combined) as bundle:
                for member in bundle.infolist():
                    if member.is_dir():
                        continue
                    # AIHub CSV ZIP members start with '/'; treat as archive-root paths.
                    destination = (output / member.filename.lstrip('/')).resolve()
                    if not destination.is_relative_to(output.resolve()):
                        raise ValueError('Archive path escapes output directory')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(bundle.read(member))
        print(f'{dataset}: archive verified and extracted', flush=True)


if __name__ == '__main__':
    main()
