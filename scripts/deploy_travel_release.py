"""Deploy an explicitly authorized travel release without touching site secrets/TDM.

Requires --baseline (the reviewed Git revision currently deployed for these files).
Use --check first. Credentials stay in the SSH identity file, never in this archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'app/routers/site.py', 'app/site_config.py', 'app/services/travel.py',
    'templates/site/base.html', 'templates/site/index.html', 'templates/site/travel.html',
    'templates/site/destination.html', 'templates/site/travel_place.html',
    'static/css/travel.css', 'static/js/travel.js',
    'static/vendor/leaflet/leaflet.css', 'static/vendor/leaflet/leaflet.js',
    'static/vendor/leaflet/LICENSE', 'private_data/travel/catalog.json',
]

REMOTE = r'''
import hashlib,json,os,pwd,subprocess,sys,tarfile,tempfile,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
data=json.load(sys.stdin)
root=Path('/srv/course-repo')
def digest(path,normalized=False):
    raw=path.read_bytes()
    return hashlib.sha256(raw.replace(b'\r\n',b'\n') if normalized else raw).hexdigest()
for name,expected in data['baseline'].items():
    path=root/name
    if not path.resolve().is_relative_to(root):raise SystemExit('Unsafe release path')
    actual=digest(path,True) if path.exists() else None
    if actual!=expected:raise SystemExit('Baseline mismatch: '+name)
if digest(root/'app/main.py',True)!=data['main_hash']:
    raise SystemExit('Main application differs from reviewed version')
if not data['deploy']:
    print(json.dumps({'preflight':True,'files_checked':len(data['baseline']),'main_matches':True}))
    raise SystemExit(0)
protected=[root/name for name in ['.env','.site.env','app/main.py','app/config.py','app/security.py',
 'app/db.py','app/models.py','app/routers/tdm.py','app/services/predictor.py',
 'app/services/inquiries.py','app/services/site_content.py']]
for folder in ['ml_artifacts','migrations','templates/tdm','static/css','static/js/tdm']:
    protected.extend(p for p in (root/folder).rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in data['files'] and '__pycache__' not in p.parts)
before={str(p):digest(p) for p in protected if p.exists()}
stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
backup=Path('/home/ubuntu')/('saerong-travel-backup-'+stamp+'.tar.gz')
existing=[name for name in data['files'] if (root/name).exists()]
new=[name for name in data['files'] if name not in existing]
owner=pwd.getpwnam('ubuntu')
with tarfile.open(backup,'w:gz') as tar:
    for name in existing:tar.add(root/name,arcname=name)
backup.chmod(0o600)
os.chown(backup,owner.pw_uid,owner.pw_gid)
changed=False
try:
    with tempfile.TemporaryDirectory(prefix='saerong-travel-stage-') as stage:
        with tarfile.open(data['archive']) as tar:
            members=tar.getmembers()
            if sorted(m.name for m in members)!=sorted(data['files']) or any(not m.isfile() for m in members):
                raise RuntimeError('Unexpected archive contents')
            tar.extractall(stage,filter='data')
        for name,expected in data['hashes'].items():
            if digest(Path(stage)/name)!=expected:raise RuntimeError('Archive checksum mismatch')
        catalog=json.loads((Path(stage)/'private_data/travel/catalog.json').read_text())
        if len(catalog['places'])!=data['place_count']:raise RuntimeError('Catalog validation failed')
        for name in data['files']:
            destination=root/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            temporary=destination.with_name(destination.name+'.travel-release-tmp')
            temporary.write_bytes((Path(stage)/name).read_bytes())
            temporary.chmod(0o600 if name.startswith('private_data/') else 0o644)
            os.chown(temporary,owner.pw_uid,owner.pw_gid)
            changed=True
            temporary.replace(destination)
        private_dir=root/'private_data/travel'
        private_dir.chmod(0o700)
        os.chown(private_dir,owner.pw_uid,owner.pw_gid)
    check=subprocess.run(['sudo','-u','ubuntu','/srv/venv/bin/python','-c',
        'from app.main import app; from app.services.travel import catalog; assert catalog()["available"]'],
        cwd=root,capture_output=True)
    if check.returncode:raise RuntimeError('Application/catalog import failed')
    subprocess.run(['systemctl','restart','saerong'],check=True)
    healthy=False
    for _ in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=3) as r:
                if r.read()==b'ok':healthy=True;break
        except Exception:pass
        time.sleep(1)
    if not healthy:raise RuntimeError('Health check failed')
    with urllib.request.urlopen('http://127.0.0.1:8000/api/travel/places',timeout=10) as r:
        result=json.load(r)
        if result['total']!=data['place_count']:raise RuntimeError('Live catalog mismatch')
    for path,expected in before.items():
        if digest(Path(path))!=expected:raise RuntimeError('Protected file changed')
    Path(data['archive']).unlink(missing_ok=True)
    print(json.dumps({'deployed':True,'backup':str(backup),'protected_files_unchanged':len(before),
                      'release_files':len(data['files']),'places':result['total'],'source_commit':data['commit']}))
except Exception as error:
    if changed:
        with tarfile.open(backup) as tar:tar.extractall(root,filter='data')
        for name in new:(root/name).unlink(missing_ok=True)
        subprocess.run(['systemctl','restart','saerong'])
    print('Release failed; previous files restored. Error type: '+type(error).__name__)
    raise SystemExit(1)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--identity', required=True, type=Path)
    parser.add_argument('--baseline', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--deploy', action='store_true')
    args = parser.parse_args()
    baseline = {}
    for name in FILES:
        result = subprocess.run(['git','show',f'{args.baseline}:{name}'],cwd=ROOT,capture_output=True)
        baseline[name] = hashlib.sha256(result.stdout.replace(b'\r\n',b'\n')).hexdigest() if result.returncode == 0 else None
    data = {'baseline':baseline,'files':FILES,'deploy':args.deploy,
            'main_hash':hashlib.sha256((ROOT/'app/main.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    options = ['-i',str(args.identity),'-o','BatchMode=yes','-o','ConnectTimeout=15']
    if args.deploy:
        data['hashes'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}
        data['place_count'] = len(json.loads((ROOT/'private_data/travel/catalog.json').read_text(encoding='utf-8'))['places'])
        remote = '/home/ubuntu/saerong-travel-release-' + uuid.uuid4().hex + '.tar.gz'
        data['archive'] = remote
        with tempfile.TemporaryDirectory(prefix='saerong-travel-') as folder:
            archive = Path(folder)/'release.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                for name in FILES:tar.add(ROOT/name,arcname=name)
            subprocess.run(['scp',*options,str(archive),args.host+':'+remote],check=True)
    command = 'sudo -n /srv/venv/bin/python -c ' + shlex.quote(REMOTE)
    result = subprocess.run(['ssh',*options,args.host,command],input=json.dumps(data),text=True,capture_output=True)
    print(result.stdout.strip())
    if result.returncode:
        # The remote program never reads private configuration into its output.
        print(result.stderr[-2000:])
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
