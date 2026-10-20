"""Deploy only the public-site release to the existing authorized SSH target.

Run manually after explicit deployment authorization. Never commits or pushes.
Private SMTP values are sent over SSH stdin, not written to release artifacts.
"""
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'app/main.py', 'app/site_config.py', 'app/routers/site.py',
    'app/services/inquiries.py', 'app/services/site_content.py',
    'static/css/public.css', 'static/js/public.js', 'static/js/travel.js',
    'static/js/dashboard.js', 'scripts/prune_site_inquiries.py',
]
FILES += [p.relative_to(ROOT).as_posix() for directory in ('templates/site', 'static/fonts', 'static/images')
          for p in (ROOT / directory).rglob('*') if p.is_file()]

REMOTE = r'''
import sys,json,hashlib,tarfile,subprocess,time,os,pwd
from pathlib import Path
from datetime import datetime,timezone
data=json.load(sys.stdin)
root=Path('/srv/course-repo')
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
current=(root/'app/main.py').read_text().replace('\r\n','\n')
if hashlib.sha256(current.encode()).hexdigest()!=data['expected_main']:
    raise SystemExit('Deployment stopped: server main.py differs from the reviewed baseline.')
protected=[root/'.env',root/'app/config.py',root/'app/security.py',root/'app/routers/tdm.py',root/'app/services/predictor.py']
protected += [p for p in (root/'ml_artifacts').rglob('*') if p.is_file()]
before={str(p):digest(p) for p in protected if p.exists()}
stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
backup=Path('/home/ubuntu')/('saerong-public-backup-'+stamp+'.tar.gz')
existing=[x for x in data['files'] if (root/x).exists()]
if (root/'.site.env').exists():existing.append('.site.env')
with tarfile.open(backup,'w:gz') as tar:
    for name in existing:tar.add(root/name,arcname=name)
backup.chmod(0o600)
owner=pwd.getpwnam('ubuntu')
os.chown(backup,owner.pw_uid,owner.pw_gid)
try:
    with tarfile.open('/tmp/saerong-public-release.tar.gz') as tar:
        members=tar.getmembers()
        if any(m.name not in data['files'] or not m.isfile() for m in members):
            raise RuntimeError('Unexpected release member')
        tar.extractall(root,filter='data')
    for name,expected in data['hashes'].items():
        if digest(root/name)!=expected:raise RuntimeError('Release checksum mismatch')
    env=root/'.site.env'
    # Preserve other private configuration keys when updating SMTP settings.
    lines=env.read_text().splitlines() if env.exists() else []
    keys=set(data['private'])
    lines=[line for line in lines if line.split('=',1)[0].strip() not in keys]
    lines.extend(key+'='+json.dumps(str(value),ensure_ascii=False) for key,value in data['private'].items())
    env.write_text('\n'.join(lines)+'\n')
    env.chmod(0o600)
    os.chown(env,owner.pw_uid,owner.pw_gid)
    result=subprocess.run(['sudo','-u','ubuntu','/srv/venv/bin/python','-c','from app.main import app; print(len(app.routes))'],cwd=root,capture_output=True)
    if result.returncode:raise RuntimeError('Application import check failed')
    subprocess.run(['sudo','systemctl','restart','saerong'],check=True)
    import urllib.request
    healthy=False
    for _ in range(15):
        time.sleep(1)
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=3) as r:
                if r.read()==b'ok':healthy=True;break
        except Exception:pass
    if not healthy:raise RuntimeError('Health check failed')
    for path,expected in before.items():
        if digest(Path(path))!=expected:raise RuntimeError('Protected file changed')
    # Daily cleanup affects the new inbox only.
    old=subprocess.run(['crontab','-u','ubuntu','-l'],capture_output=True,text=True).stdout
    job='17 3 * * * /srv/venv/bin/python /srv/course-repo/scripts/prune_site_inquiries.py >/dev/null 2>&1 # saerong-inquiry-retention'
    if 'saerong-inquiry-retention' not in old:
        subprocess.run(['crontab','-u','ubuntu','-'],input=old.rstrip()+'\n'+job+'\n',text=True,check=True)
    Path('/tmp/saerong-public-release.tar.gz').unlink(missing_ok=True)
    print(json.dumps({'deployed':True,'backup':str(backup),'protected_files_unchanged':len(before),'release_files':len(data['files'])}))
except Exception as error:
    with tarfile.open(backup) as tar:tar.extractall(root,filter='data')
    subprocess.run(['sudo','systemctl','restart','saerong'])
    print('Release failed; previous files restored. Error type: '+type(error).__name__)
    raise SystemExit(1)
'''


def main():
    import sys
    old_main = ((ROOT / 'app/main.py').read_text(encoding='utf-8') if '--update-public-release' in sys.argv
                else subprocess.check_output(['git', 'show', 'origin/main:app/main.py'], cwd=ROOT).decode()).replace('\r\n', '\n')
    local = dotenv_values(ROOT / '.env')
    required = ['REVIEW_SMTP_HOST', 'REVIEW_SMTP_USER', 'REVIEW_SMTP_PASSWORD']
    if not all(local.get(key) for key in required):
        raise SystemExit('SMTP configuration unavailable; configure private settings before deployment.')
    # Recipient is supplied interactively through stdin; no personal address in source.
    import getpass
    recipient = getpass.getpass('Inquiry recipient (hidden): ').strip()
    if '@' not in recipient or '\n' in recipient:
        raise SystemExit('Invalid recipient')
    port = local.get('REVIEW_SMTP_PORT', '587')
    payload = dict(files=FILES, expected_main=hashlib.sha256(old_main.encode()).hexdigest(),
                   hashes={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES},
                   private={
                       'INQUIRY_TO': recipient,
                       'SMTP_HOST': local['REVIEW_SMTP_HOST'], 'SMTP_PORT': port,
                       'SMTP_USER': local['REVIEW_SMTP_USER'], 'SMTP_PASSWORD': local['REVIEW_SMTP_PASSWORD'],
                       'SMTP_FROM': local.get('REVIEW_MAIL_FROM') or local['REVIEW_SMTP_USER'],
                       'SMTP_SSL': str(port == '465').lower(),
                   })
    admin_settings = dotenv_values(ROOT / 'private_data' / 'admin.env')
    for key in ('SITE_ADMIN_USER', 'SITE_ADMIN_PASSWORD_HASH'):
        if admin_settings.get(key):
            payload['private'][key] = admin_settings[key]
    with tempfile.TemporaryDirectory(prefix='saerong-release-') as tmp:
        archive = Path(tmp) / 'release.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for name in FILES:
                tar.add(ROOT/name, arcname=name)
        subprocess.run(['scp', str(archive), 'saerong:/tmp/saerong-public-release.tar.gz'], check=True)
        # Python source and input have separate stdin layers; no shell interpolation of secrets.
        command = 'sudo -n /srv/venv/bin/python -c ' + __import__('shlex').quote(REMOTE)
        result = subprocess.run(['ssh', 'saerong', command], input=json.dumps(payload), text=True, capture_output=True)
        print(result.stdout)
        if result.returncode:
            detail = result.stderr
            for value in payload['private'].values():
                if value:
                    detail = detail.replace(value, '[private]')
            print(detail[-2000:])
            print('Deployment did not complete; inspect server safely without printing private settings.')
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
