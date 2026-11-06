"""Inventory Disney Infinity archives via QuickBMS list mode; never reimport.
No archive members are written. SQLite checkpoints allow resume.
"""
import argparse,csv,hashlib,json,re,sqlite3,subprocess,tempfile,time
from pathlib import Path
MEMBER=re.compile(r'^\s*([0-9a-fA-F]{8,16})\s+(\d+)\s+(.+?)\s*$')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('root',type=Path);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--quickbms',type=Path,required=True);p.add_argument('--bms',type=Path,required=True)
 p.add_argument('--mapping',type=Path);p.add_argument('--limit',type=int,default=0)
 p.add_argument('--timeout',type=int,default=180);p.add_argument('--retry-failed',action='store_true')
 a=p.parse_args();root=a.root.resolve();out=a.output.resolve()
 if not root.is_dir():p.error('Root must be a directory')
 if out==root or root in out.parents:p.error('Output must be outside source tree')
 if not a.quickbms.is_file() or not a.bms.is_file():p.error('QuickBMS or BMS script missing')
 out.mkdir(parents=True,exist_ok=True);logs=out/'logs';logs.mkdir(exist_ok=True)
 mapping={}
 if a.mapping and a.mapping.is_file():
  for r in csv.DictReader(a.mapping.open(encoding='utf-8-sig')):
   key=r['source_path'].replace('\\','/').lower();mapping.setdefault(key,set()).add(r['path'])
 candidates=[]
 for f in root.rglob('*'):
  if not f.is_file() or f.is_symlink():continue
  rel=f.relative_to(root).as_posix();low=rel.lower();low=('assets/'+low) if root.name.lower()=='assets' else low;parts=low.split('/')
  key=low[low.index('assets/'):] if 'assets' in parts else low
  names=mapping.get(key,set());name=next(iter(names)) if len(names)==1 else None
  # ZIPs plus hash-named console ASSETS files. Other files are not assumed archives.
  if f.suffix.lower()=='.zip' or ('assets' in parts and re.fullmatch('[0-9a-fA-F]{8}',f.name)):
   candidates.append((f,rel,name))
 candidates.sort(key=lambda x:(x[0].stat().st_size,x[1]))
 db=sqlite3.connect(out/'inventory.sqlite');db.executescript('''CREATE TABLE IF NOT EXISTS archives(path TEXT PRIMARY KEY, size INTEGER, mtime INTEGER, decoder TEXT, status TEXT, logical_path TEXT, members TEXT, log TEXT);''')
 script=a.bms.read_text(encoding='utf-8-sig');fingerprint=hashlib.sha256(b'crawler-v2'+script.encode()+str(a.quickbms.stat().st_mtime_ns).encode()).hexdigest()
 marker='get FILE_NAME basename'
 if marker not in script:p.error('BMS script lacks expected basename assignment')
 processed=0;skipped=0;total=len(candidates);start=time.monotonic()
 try:
  for index,(f,rel,logical) in enumerate(candidates,1):
   stat=f.stat();old=db.execute('select size,mtime,decoder,status,logical_path from archives where path=?',(rel,)).fetchone()
   if old and old[:3]==(stat.st_size,stat.st_mtime_ns,fingerprint) and old[4]==logical and (not a.retry_failed or old[3]=='listed'):
    skipped+=1;continue
   if a.limit and processed>=a.limit:break
   # Correct basename matters: the community script selects a different key for psx_.
   basename=Path(logical).stem if logical else f.stem
   if not re.fullmatch(r'[A-Za-z0-9_. -]+',basename):basename=f.stem
   patched=script.replace(marker,marker+'\nset FILE_NAME string "'+basename+'"',1)
   status='failed';members=[];log=''
   with tempfile.TemporaryDirectory(prefix='di_list_',dir=out) as tmp:
    bms=Path(tmp)/'list.bms';bms.write_text(patched,encoding='utf-8')
    try:
     run=subprocess.run([str(a.quickbms.resolve()),'-l',str(bms),str(f)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=a.timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
     log=run.stdout.decode('utf-8',errors='replace')
     for line in log.splitlines():
      m=MEMBER.match(line)
      if m:members.append(dict(name=m[3],size=int(m[2]),offset=m[1]))
     found=re.search(r'-\s*(\d+) files found',log)
     if run.returncode==0 and found and int(found[1])==len(members) and members:
      # Script fallback emits a single opaque file; do not call that an archive inventory.
      status='opaque_fallback' if len(members)==1 and members[0]['name'].replace('\\','/').split('/')[-1] in (basename, basename+'.', basename+'.dat') and members[0]['size']==stat.st_size else 'listed'
    except subprocess.TimeoutExpired as e:
     status='timeout';log=(e.stdout or b'').decode('utf-8',errors='replace')+'\nTIMEOUT'
   logname=hashlib.sha256(rel.encode()).hexdigest()[:24]+'.txt';(logs/logname).write_text(log,encoding='utf-8')
   db.execute('insert or replace into archives values(?,?,?,?,?,?,?,?)',(rel,stat.st_size,stat.st_mtime_ns,fingerprint,status,logical,json.dumps(members),'logs/'+logname));db.commit();processed+=1
   elapsed=time.monotonic()-start;remaining=total-index;eta=remaining*elapsed/processed
   print(f'[{index}/{total}] {status}: {rel} ({len(members)} members) | remaining {remaining}, estimated {eta/60:.1f} min',flush=True)
 except KeyboardInterrupt:print('Interrupted; completed archives are checkpointed.',flush=True)
 finally:
  counts=dict(db.execute('select status,count(*) from archives group by status'))
  with (out/'members.jsonl').open('w',encoding='utf-8') as dest:
   for rel,logical,status,raw in db.execute('select path,logical_path,status,members from archives order by path'):
    for member in json.loads(raw):dest.write(json.dumps(dict(archive=rel,logical_archive=logical,status=status,**member))+'\n')
  (out/'summary.json').write_text(json.dumps(dict(root=str(root),candidates=total,processed_this_run=processed,skipped=skipped,status_counts=counts),indent=2))
  db.close();print(json.dumps(counts),flush=True)
if __name__=='__main__':main()



