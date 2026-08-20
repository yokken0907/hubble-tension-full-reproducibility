#!/usr/bin/env python3
from __future__ import annotations
import contextlib, csv, hashlib, io, json, math, os, re, shutil, struct, time, urllib.error, urllib.request, zipfile
from collections import OrderedDict
from pathlib import Path
import numpy as np

ORIGINAL_URL='https://lambda.gsfc.nasa.gov/data/suborbital/SPT/spt_3g_d1/chains_ttteee_winter1920.zip'
ORIGINAL_FILENAME='chains_ttteee_winter1920.zip'
FIXED_URL='https://lambda.gsfc.nasa.gov/data/suborbital/SPT/spt_3g_d1/CMB_SPA_DESI_Fixed.zip'
FIXED_FILENAME='CMB_SPA_DESI_Fixed.zip'
FIXED_BYTES=828_322_572
FIXED_SHA256='47c7e6ebe8df320cc4b9c81b180bd10025f194cab588e71ea71a515d7d2236a0'
FIXED_ROOTS={
 'CMB':'LCDM/S1920lite_MPP_PACT_PR4lens_actdr6lens_No_OLE',
 'DESI':'LCDM/S1920lite_MPP_PACT_PR4lens_actdr6lens_BAODR2_No_OLE',
}
# Backward-compatible alias used only where the fixed-release paths are intended.
ROOTS=FIXED_ROOTS
def original_target_family_match(path_text:str)->bool:
 low=path_text.lower()
 # Original CMB-SPA roots use the release-era spelling
 # PlkPR4lens_ACTDR6lite_actdr6lens, whereas the bug-fixed roots use
 # PACT_PR4lens_actdr6lens. Original discovery must not impose the fixed alias.
 return (
  all(tok in low for tok in ('s1920lite','mpp','plkpr4lens','actdr6lite','actdr6lens'))
  and not any(tok in low for tok in ('no_tau','notau','no-tau'))
 )
ALIASES={
 'omega_b':['omega_b','ombh2','omegabh2'],
 'omega_c':['omega_cdm','omega_c','omch2','omegach2'],
 'H0':['H0','h0','H_0'],
 'Omega_m':['Omega_m','omegam','omega_m'],
 'r_drag':['rs_drag','r_drag','rdrag','rd','r_d'],
 'n_s':['n_s','ns'],
 'tau':['tau_reio','tau'],
 'sigma8':['sigma8','sigma_8'],
 'S8':['S_8','S8'],
 'logA':['logA'],
}
PARAMS=('omega_b','omega_c','H0','Omega_m','r_drag','n_s','tau','sigma8','S8','logA')
DESI_OM,DESI_SIG_OM=0.297462,0.008575
DESI_HRD,DESI_SIG_HRD=101.5398,0.7328
AXIS=np.array([0.535763581993669,-0.844368038363197],float);AXIS/=np.linalg.norm(AXIS)
ORTH=np.array([-AXIS[1],AXIS[0]],float)


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def bytes_sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def write_tsv(path:Path,rows:list[dict],fields:list[str]|None=None):
 if not rows:path.write_text('',encoding='utf-8');return
 names=fields or list(rows[0])
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=names,delimiter='\t',lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows)

def norm(s:str)->str:return re.sub(r'[^a-z0-9]','',s.lower())

def read_header(path:Path)->list[str]:
 with path.open(errors='replace') as f:line=f.readline().strip()
 if not line.startswith('#'):raise RuntimeError(f'missing named header: {path}')
 h=line.lstrip('#').split()
 if len(h)<3 or norm(h[0])!='weight':raise RuntimeError(f'invalid named header: {path}')
 return h

def resolve_columns(header:list[str])->dict[str,str]:
 lookup={norm(x):x for x in header};out={}
 for key,aliases in ALIASES.items():
  for a in aliases:
   if norm(a) in lookup:out[key]=lookup[norm(a)];break
 return out

def chain_files(root:Path)->list[Path]:
 xs=[]
 for p in root.glob('CLASS.*.txt'):
  m=re.fullmatch(r'CLASS\.(\d+)\.txt',p.name)
  if m:xs.append((int(m.group(1)),p))
 return [p for _,p in sorted(xs)]

def likelihood_names(path:Path)->tuple[str,...]:
 """Return only direct children of the top-level ``likelihood:`` mapping.

 The previous parser accepted any line beginning with at least two spaces,
 which incorrectly promoted nested configuration keys such as ``params``,
 ``crop`` and ``TT`` to likelihood names.
 """
 lines=path.read_text(errors='replace').splitlines()
 active=False;base_indent=None;child_indent=None;names=[]
 for raw in lines:
  prefix=raw[:len(raw)-len(raw.lstrip())]
  if '\t' in prefix:
   raise RuntimeError(f'tab-indented YAML is unsupported for contract parsing: {path}')
  if not active:
   m=re.match(r'^(\s*)likelihood\s*:\s*(?:#.*)?$',raw)
   if m:
    active=True;base_indent=len(m.group(1))
   continue
  stripped=raw.strip()
  if not stripped or stripped.startswith('#'):continue
  indent=len(raw)-len(raw.lstrip(' '))
  if indent<=base_indent:break
  if child_indent is None:child_indent=indent
  if indent!=child_indent:continue
  content=raw[indent:]
  if content.startswith('-'):continue
  m=re.match(r'''(?:"([^"]+)"|'([^']+)'|([^:#][^:]*?))\s*:\s*(?:.*)?$''',content)
  if not m:continue
  key=next((x for x in m.groups() if x is not None),'').strip()
  if key:names.append(key)
 return tuple(sorted(dict.fromkeys(names)))


def likelihood_inventory(root:Path)->dict[str,tuple[str,...]]:
 out={}
 for fn in ('CLASS.input.yaml','CLASS.updated.yaml'):
  p=root/fn
  if not p.exists():raise RuntimeError(f'missing YAML: {p}')
  out[fn]=likelihood_names(p)
 return out


def semantic_families(names:set[str])->set[str]:
 """Map released top-level likelihood implementations to explicit data families.

 This intentionally separates Planck primary, Planck-only lensing, and the
 joint ACT+Planck lensing likelihood. The prior CORR1 classifier merged these
 distinctions and therefore could not represent the observed release graph.
 """
 fam=set()
 for name in names:
  low=name.lower()
  if 'muse' in low:
   fam.add('SPT_LENSING')
  if ('s1920' in low or ('spt3g' in low and 'muse' not in low)):
   fam.add('SPT_PRIMARY')
  if ('act_dr6_cmbonly.actdr6cmbonly' in low or 'actdr6lite' in low or 'actdr6cmb' in low):
   fam.add('ACT_PRIMARY')
  if ('act_dr6_lenslike' in low or 'actdr6lens' in low):
   fam.add('ACT_PLANCK_JOINT_LENSING')
  if ('clipy_highl' in low or 'planckactcut' in low):
   fam.add('PLANCK_PRIMARY_HIGH_L')
  if ('clipy_lowl_tt' in low or 'planck_2018_lowl.tt' in low):
   fam.add('PLANCK_PRIMARY_LOW_L_TT')
  if ('planckpr4lensing' in low or 'planck_pr4_lensing' in low):
   fam.add('PLANCK_PR4_LENSING')
  if ('bao.desi_dr2' in low or 'desi_dr2' in low or 'baodr2' in low):
   fam.add('DESI_BAO')
 return fam


def contract_check(root:Path,label:str)->list[dict]:
 rows=[];files=chain_files(root)
 rows.append({'era':'','contract':label,'check':'eight_numbered_chains','observed':len(files),'required':8,'result':'PASS' if len(files)==8 else 'FAIL'})
 if not files:return rows
 h=read_header(files[0]);cols=resolve_columns(h)
 for p in PARAMS:
  rows.append({'era':'','contract':label,'check':f'direct_column_{p}','observed':cols.get(p,''),'required':'present','result':'PASS' if p in cols else 'FAIL'})
 y=root/'CLASS.input.yaml';likes=likelihood_names(y) if y.exists() else ()
 low='|'.join(likes).lower();desi=('bao.desi_dr2' in low or 'desi_dr2' in low)
 rows.append({'era':'','contract':label,'check':'DESI_contract','observed':desi,'required':label=='DESI','result':'PASS' if desi==(label=='DESI') else 'FAIL'})
 forbidden=any(x in low for x in ('shoes','pantheon','union3','desy5','supernova'))
 rows.append({'era':'','contract':label,'check':'no_SH0ES_or_SN','observed':forbidden,'required':False,'result':'PASS' if not forbidden else 'FAIL'})
 return rows

class HTTPRangeFile(io.RawIOBase):
 def __init__(self,url:str,block_size:int=8*1024*1024,max_blocks:int=12):
  super().__init__();self.url=url;self.block_size=block_size;self.max_blocks=max_blocks;self.pos=0;self.cache=OrderedDict();self.requests=0;self.bytes_fetched=0
  self.headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity'}
  self.size,self.etag,self.last_modified,self.accept_ranges=self._probe()
 def _open(self,start:int,end:int):
  hd=dict(self.headers);hd['Range']=f'bytes={start}-{end}'
  req=urllib.request.Request(self.url,headers=hd)
  r=urllib.request.urlopen(req,timeout=120);status=getattr(r,'status',200)
  cr=r.headers.get('Content-Range','')
  if status!=206 or not cr.lower().startswith('bytes '):
   r.close();raise RuntimeError(f'HTTP Range unsupported or ignored: status={status}, Content-Range={cr!r}')
  return r
 def _probe(self):
  size=None;etag='';lm='';ar=''
  try:
   req=urllib.request.Request(self.url,headers=self.headers,method='HEAD')
   with urllib.request.urlopen(req,timeout=60) as r:
    if r.headers.get('Content-Length'):size=int(r.headers['Content-Length'])
    etag=r.headers.get('ETag','');lm=r.headers.get('Last-Modified','');ar=r.headers.get('Accept-Ranges','')
  except Exception:pass
  with self._open(0,0) as r:
   cr=r.headers.get('Content-Range','');m=re.search(r'/([0-9]+)$',cr)
   if not m:raise RuntimeError(f'cannot determine remote ZIP size from {cr!r}')
   r.read();size2=int(m.group(1));size=size or size2
   if size!=size2:raise RuntimeError('HEAD and Content-Range size mismatch')
   etag=etag or r.headers.get('ETag','');lm=lm or r.headers.get('Last-Modified','');ar=ar or r.headers.get('Accept-Ranges','')
  return int(size),etag,lm,ar
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=io.SEEK_SET):
  if whence==io.SEEK_SET:new=offset
  elif whence==io.SEEK_CUR:new=self.pos+offset
  elif whence==io.SEEK_END:new=self.size+offset
  else:raise ValueError('invalid whence')
  if new<0:raise ValueError('negative seek')
  self.pos=new;return self.pos
 def _block(self,idx:int)->bytes:
  if idx in self.cache:
   b=self.cache.pop(idx);self.cache[idx]=b;return b
  start=idx*self.block_size;end=min(self.size-1,start+self.block_size-1)
  with self._open(start,end) as r:b=r.read()
  if len(b)!=(end-start+1):raise RuntimeError(f'short HTTP range read at {start}: {len(b)}')
  self.requests+=1;self.bytes_fetched+=len(b);self.cache[idx]=b
  while len(self.cache)>self.max_blocks:self.cache.popitem(last=False)
  return b
 def read_at(self,start:int,n:int)->bytes:
  if start<0 or n<0 or start+n>self.size:raise ValueError(f'invalid absolute read: start={start}, n={n}, size={self.size}')
  parts=[];pos=start;left=n
  while left:
   idx=pos//self.block_size;off=pos%self.block_size;b=self._block(idx);take=min(left,len(b)-off)
   if take<=0:raise RuntimeError(f'zero-length block slice at absolute offset {pos}')
   parts.append(b[off:off+take]);pos+=take;left-=take
  return b''.join(parts)
 def read(self,n=-1):
  if self.pos>=self.size:return b''
  if n is None or n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos);data=self.read_at(self.pos,n);self.pos+=len(data);return data
 def readinto(self,b):
  data=self.read(len(b));b[:len(data)]=data;return len(data)


class RangeSlice(io.RawIOBase):
 """Independent seekable view onto a byte range of an HTTPRangeFile."""
 def __init__(self,base:HTTPRangeFile,start:int,size:int):
  super().__init__();self.base=base;self.start=int(start);self.size=int(size);self.pos=0
  if self.start<0 or self.size<0 or self.start+self.size>self.base.size:raise ValueError('slice outside parent')
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=io.SEEK_SET):
  if whence==io.SEEK_SET:new=offset
  elif whence==io.SEEK_CUR:new=self.pos+offset
  elif whence==io.SEEK_END:new=self.size+offset
  else:raise ValueError('invalid whence')
  if new<0:raise ValueError('negative seek')
  self.pos=new;return self.pos
 def read(self,n=-1):
  if self.pos>=self.size:return b''
  if n is None or n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos);data=self.base.read_at(self.start+self.pos,n);self.pos+=len(data);return data
 def readinto(self,b):
  data=self.read(len(b));b[:len(data)]=data;return len(data)


def _stored_member_data_offset(base:HTTPRangeFile,info:zipfile.ZipInfo)->int:
 hdr=base.read_at(info.header_offset,30)
 if len(hdr)!=30 or hdr[:4]!=b'PK\x03\x04':raise RuntimeError(f'invalid local ZIP header for {info.filename}')
 fields=struct.unpack('<IHHHHHIIIHH',hdr)
 name_len,extra_len=fields[-2],fields[-1]
 return int(info.header_offset+30+name_len+extra_len)


def zip_inventory_fingerprint(zf:zipfile.ZipFile)->tuple[str,int]:
 rows=[]
 for i in zf.infolist():
  rows.append({'filename':i.filename,'CRC':i.CRC,'file_size':i.file_size,'compress_size':i.compress_size,'header_offset':i.header_offset,'compress_type':i.compress_type,'flag_bits':i.flag_bits,'date_time':i.date_time})
 data='\n'.join(json.dumps(x,sort_keys=True,separators=(',',':')) for x in rows).encode()
 return bytes_sha256(data),len(rows)


def _join_member(root:str,name:str)->str:
 return f'{root}/{name}' if root else name

def _candidate_root_inventory(zf:zipfile.ZipFile,context:str='')->list[dict]:
 names=[n.rstrip('/') for n in zf.namelist() if n and not n.endswith('/')]
 by_root={}
 for n in names:
  root,base=n.rsplit('/',1) if '/' in n else ('',n)
  rec=by_root.setdefault(root,{'files':set(),'chains':set()})
  rec['files'].add(base)
  m=re.fullmatch(r'CLASS\.(\d+)\.txt',base)
  if m:rec['chains'].add(int(m.group(1)))
 rows=[];required_chains=set(range(1,9))
 for root,rec in sorted(by_root.items()):
  combined='/'.join(x for x in (context,root) if x)
  components=[x.lower() for x in combined.split('/')]
  low=combined.lower()
  has_lcdm='lcdm' in components or any('lcdm'==x.replace('_','').replace('-','') for x in components)
  stem_match=original_target_family_match(combined)
  eight=(rec['chains']==required_chains)
  has_input='CLASS.input.yaml' in rec['files'];has_updated='CLASS.updated.yaml' in rec['files'];has_mean='CLASS_mean.txt' in rec['files']
  no_tau=any(x in low for x in ('no_tau','notau','no-tau'))
  desi_path=any(x in low for x in ('baodr2','desi_dr2','desidr2'))
  # Author mean products are useful cross-checks but are not part of the
  # posterior contract. The original DESI root legitimately lacks CLASS_mean.
  eligible=has_lcdm and stem_match and eight and has_input and has_updated and not no_tau
  rows.append({
   'archive_context':context,'root':root,'has_LCDM_component':has_lcdm,'target_stem_match':stem_match,
   'numbered_chain_count':len(rec['chains']),'exact_chains_1_to_8':eight,
   'has_input_yaml':has_input,'has_updated_yaml':has_updated,'has_author_mean':has_mean,
   'path_marks_no_tau':no_tau,'path_marks_DESI':desi_path,'eligible_before_YAML':eligible,
  })
 return rows

def _yaml_contract_flags(text:str)->dict:
 low=text.lower()
 return {
  'yaml_has_DESI': any(x in low for x in ('bao.desi_dr2','desi_dr2','baodr2')),
  'yaml_has_SH0ES_or_SN': any(x in low for x in ('shoes','pantheon','union3','desy5','supernova')),
  'yaml_has_ACT_DR6': ('act_dr6' in low or 'actdr6' in low),
  'yaml_has_ACT_DR6_PRIMARY': any(x in low for x in ('act_dr6_cmbonly','actdr6lite','actdr6cmb')),
  'yaml_has_ACT_DR6_LENSING': any(x in low for x in ('act_dr6_lenslike','actdr6lens')),
  'yaml_has_SPT_D1': ('s1920' in low or 'spt3g' in low or 'spt_3g' in low),
  'yaml_has_SPT_LENSING': ('muse3glike' in low or 'muse' in low),
  'yaml_has_GAUSSIAN_TAU': (
    'tau_reio' in low and 'dist: norm' in low and
    re.search(r'loc:\s*0\.051(?:0+)?\b',low) is not None and
    re.search(r'scale:\s*0\.006(?:0+)?\b',low) is not None
  ),
 }

def _annotate_candidate_rows(zf:zipfile.ZipFile,context:str='')->list[dict]:
 rows=_candidate_root_inventory(zf,context=context)
 for row in rows:
  row.update({'yaml_has_DESI':'','yaml_has_SH0ES_or_SN':'','yaml_has_ACT_DR6':'','yaml_has_ACT_DR6_PRIMARY':'','yaml_has_ACT_DR6_LENSING':'','yaml_has_SPT_D1':'','yaml_has_SPT_LENSING':'','yaml_has_GAUSSIAN_TAU':'','contract_label':'','selection_result':'REJECT','yaml_error':''})
  if not row['eligible_before_YAML']:continue
  try:
   text=zf.read(_join_member(row['root'],'CLASS.input.yaml')).decode('utf-8','replace');row.update(_yaml_contract_flags(text))
  except Exception as e:
   row['selection_result']='REJECT_YAML_READ_FAILED';row['yaml_error']=str(e);continue
  if row['yaml_has_SH0ES_or_SN']:
   row['selection_result']='REJECT_FORBIDDEN_DATA';continue
  required=(
   row['yaml_has_ACT_DR6'] and row['yaml_has_ACT_DR6_PRIMARY'] and
   row['yaml_has_ACT_DR6_LENSING'] and row['yaml_has_SPT_D1'] and
   row['yaml_has_SPT_LENSING'] and row['yaml_has_GAUSSIAN_TAU']
  )
  if not required:
   row['selection_result']='REJECT_TARGET_LIKELIHOOD_OR_TAU_CONTRACT_MISSING';continue
  row['contract_label']='DESI' if row['yaml_has_DESI'] else 'CMB';row['selection_result']='CANDIDATE'
 return rows

def _select_unique_rows(rows:list[dict])->dict[str,dict]:
 selected={}
 for label in ('CMB','DESI'):
  xs=[r for r in rows if r.get('contract_label')==label and r.get('selection_result')=='CANDIDATE']
  if len(xs)==1:
   selected[label]=xs[0];xs[0]['selection_result']='SELECTED'
  elif len(xs)>1:
   for r in xs:r['selection_result']='AMBIGUOUS'
 return selected

def discover_original_roots(zf:zipfile.ZipFile,diagnostic_path:Path|None=None,context:str='')->tuple[dict[str,str],list[dict]]:
 rows=_annotate_candidate_rows(zf,context=context);selected_rows=_select_unique_rows(rows);selected={k:v['root'] for k,v in selected_rows.items()}
 if diagnostic_path is not None:
  diagnostic_path.parent.mkdir(parents=True,exist_ok=True);write_tsv(diagnostic_path,rows)
 if set(selected)!= {'CMB','DESI'}:
  counts={lab:sum(r.get('contract_label')==lab and r.get('selection_result') in ('CANDIDATE','AMBIGUOUS') for r in rows) for lab in ('CMB','DESI')}
  raise RuntimeError(f'original root discovery was not unique: selected={selected}, candidate_counts={counts}; see HTS50_ORIGINAL_ROOT_DISCOVERY.tsv')
 return selected,rows

def extract_selected_from_zip(zf:zipfile.ZipFile,dest:Path,roots:dict[str,str],source_prefix:str='')->list[dict]:
 dest.mkdir(parents=True,exist_ok=True);names=set(zf.namelist());wanted=[]
 for label,root in roots.items():
  for k in range(1,9):wanted.append((label,_join_member(root,f'CLASS.{k}.txt')))
  for fn in ('CLASS.input.yaml','CLASS.updated.yaml'):wanted.append((label,_join_member(root,fn)))
  mean_name=_join_member(root,'CLASS_mean.txt')
  if mean_name in names:wanted.append((label,mean_name))
 missing=[n for _,n in wanted if n not in names]
 if missing:raise RuntimeError('selected members absent from ZIP: '+', '.join(missing[:12]))
 rows=[]
 for label,n in wanted:
  info=zf.getinfo(n);target=dest/n;target.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();written=0
  with zf.open(info) as src,target.open('wb') as out:
   while True:
    b=src.read(1024*1024)
    if not b:break
    out.write(b);h.update(b);written+=len(b)
  if written!=info.file_size:raise RuntimeError(f'extracted size mismatch: {n}')
  rel=f'{source_prefix}!{n}' if source_prefix else n
  rows.append({'era':'','contract':label,'relative_path':rel,'materialized_path':n,'bytes':written,'compressed_bytes':info.compress_size,'CRC32':f'{info.CRC:08x}','sha256':h.hexdigest()})
 return rows

def _archive_member_score(name:str)->int:
 low=name.lower();score=0
 for tok,val in [('lcdm',50),('cmb',10),('spa',10),('desi',10),('chain',5),('compressed',1)]:score += val if tok in low else 0
 for tok in ('ede','w0wa','mnu','neff','modrec','omegak','omk','alp','yp'):score -= 20 if tok in low else 0
 return score

def _outer_archive_inventory(zf:zipfile.ZipFile)->list[dict]:
 rows=[]
 for i in zf.infolist():
  if i.is_dir():continue
  rows.append({'filename':i.filename,'suffix':Path(i.filename).suffix.lower(),'bytes':i.file_size,'compressed_bytes':i.compress_size,'compress_type':i.compress_type,'CRC32':f'{i.CRC:08x}','header_offset':i.header_offset,'archive_score':_archive_member_score(i.filename),'is_nested_zip':i.filename.lower().endswith('.zip')})
 return rows

@contextlib.contextmanager
def _open_nested_member(outer:zipfile.ZipFile,info:zipfile.ZipInfo,cache:Path,remote_base:HTTPRangeFile|None=None):
 """Open a ZIP member as a seekable nested ZIP without fetching the 6.19 GB outer archive."""
 mode='';local_path=None;slice_obj=None
 if remote_base is not None and info.compress_type==zipfile.ZIP_STORED and info.file_size==info.compress_size:
  start=_stored_member_data_offset(remote_base,info);slice_obj=RangeSlice(remote_base,start,info.file_size);mode='REMOTE_STORED_MEMBER_SLICE'
  z=zipfile.ZipFile(slice_obj)
 else:
  nested_dir=cache/'NESTED_ARCHIVES';nested_dir.mkdir(parents=True,exist_ok=True)
  tag=hashlib.sha256(info.filename.encode()).hexdigest()[:16];local_path=nested_dir/f'{tag}_{Path(info.filename).name}'
  valid=local_path.is_file() and local_path.stat().st_size==info.file_size and zipfile.is_zipfile(local_path)
  if not valid:
   part=Path(str(local_path)+'.part');part.unlink(missing_ok=True)
   with outer.open(info) as src,part.open('wb') as out:
    copied=0
    while True:
     b=src.read(1024*1024)
     if not b:break
     out.write(b);copied+=len(b)
   if copied!=info.file_size:raise RuntimeError(f'nested member materialization size mismatch: {info.filename}')
   part.replace(local_path)
  mode='MATERIALIZED_NESTED_MEMBER';z=zipfile.ZipFile(local_path)
 try:
  yield z,{'nested_open_mode':mode,'nested_local_path':str(local_path or ''),'outer_member':info.filename,'outer_member_bytes':info.file_size,'outer_member_compressed_bytes':info.compress_size,'outer_member_compress_type':info.compress_type,'outer_member_CRC32':f'{info.CRC:08x}'}
 finally:
  z.close()
  if slice_obj is not None:slice_obj.close()

def discover_nested_original_sources(outer:zipfile.ZipFile,cache:Path,remote_base:HTTPRangeFile|None=None)->tuple[dict[str,dict],list[dict],list[dict],list[dict]]:
 outer_rows=_outer_archive_inventory(outer)
 nested_infos=[i for i in outer.infolist() if not i.is_dir() and i.filename.lower().endswith('.zip')]
 # Stored nested ZIPs can be inspected by direct byte slices. Compressed members
 # are inspected only when reasonably bounded or strongly target-like.
 nested_infos.sort(key=lambda i:(i.compress_type!=zipfile.ZIP_STORED,-_archive_member_score(i.filename),i.file_size))
 candidate_rows=[];nested_rows=[]
 max_materialize=int(os.environ.get('HTS50_MAX_NESTED_MEMBER_BYTES',str(2_500_000_000)))
 for info in nested_infos:
  score=_archive_member_score(info.filename)
  if info.compress_type!=zipfile.ZIP_STORED and info.file_size>max_materialize:
   nested_rows.append({'outer_member':info.filename,'status':'SKIP_COMPRESSED_MEMBER_OVER_LIMIT','bytes':info.file_size,'compressed_bytes':info.compress_size,'compress_type':info.compress_type,'score':score,'nested_entry_count':'','nested_inventory_sha256':'','error':f'limit={max_materialize}'});continue
  try:
   with _open_nested_member(outer,info,cache,remote_base) as (inner,open_meta):
    # Do not call testzip() here: it would read every file in the nested
    # archive and defeat selective Range materialization. Each selected
    # member is CRC-verified by ZipExtFile during extraction.
    fp,n=zip_inventory_fingerprint(inner)
    rows=_annotate_candidate_rows(inner,context=info.filename)
    for r in rows:r.update({'nested_archive_member':info.filename,'nested_inventory_sha256':fp,'nested_entry_count':n,**open_meta})
    candidate_rows+=rows
    nested_rows.append({'outer_member':info.filename,'status':'OPENED','bytes':info.file_size,'compressed_bytes':info.compress_size,'compress_type':info.compress_type,'score':score,'nested_entry_count':n,'nested_inventory_sha256':fp,'error':'',**open_meta})
  except Exception as e:
   nested_rows.append({'outer_member':info.filename,'status':'OPEN_FAILED','bytes':info.file_size,'compressed_bytes':info.compress_size,'compress_type':info.compress_type,'score':score,'nested_entry_count':'','nested_inventory_sha256':'','error':str(e)})
 selected_rows=_select_unique_rows(candidate_rows)
 return selected_rows,candidate_rows,nested_rows,outer_rows


def extract_nested_selected(outer:zipfile.ZipFile,cache:Path,dest:Path,selected_rows:dict[str,dict],remote_base:HTTPRangeFile|None=None)->tuple[list[dict],dict[str,dict]]:
 shutil.rmtree(dest,ignore_errors=True);dest.mkdir(parents=True)
 grouped={}
 for label,row in selected_rows.items():grouped.setdefault(row['nested_archive_member'],{})[label]=row['root']
 provenance=[];selection={}
 info_by_name={i.filename:i for i in outer.infolist()}
 for member,roots in grouped.items():
  info=info_by_name[member]
  with _open_nested_member(outer,info,cache,remote_base) as (inner,meta):
   rows=extract_selected_from_zip(inner,dest,roots,source_prefix=member);provenance+=rows
   for label,root in roots.items():selection[label]={'nested_archive_member':member,'root':root,'nested_open_mode':meta['nested_open_mode']}
 return provenance,selection


def download_full(url:str,dest:Path)->str:
 dest.parent.mkdir(parents=True,exist_ok=True);part=Path(str(dest)+'.part')
 for attempt in range(1,6):
  try:
   start=part.stat().st_size if part.exists() else 0;hd={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity'}
   if start:hd['Range']=f'bytes={start}-'
   with urllib.request.urlopen(urllib.request.Request(url,headers=hd),timeout=120) as r:
    status=getattr(r,'status',200)
    if start and status!=206:part.unlink(missing_ok=True);return download_full(url,dest)
    total=start;mode='ab' if start else 'wb'
    with part.open(mode) as f:
     while True:
      b=r.read(1024*1024)
      if not b:break
      before=total;f.write(b);total+=len(b)
      if total//(256*1024*1024)!=before//(256*1024*1024):print(f'  {dest.name}: {total/2**30:.2f} GiB',flush=True)
   part.replace(dest);return 'DOWNLOADED_FULL'
  except urllib.error.HTTPError as e:
   if 400<=e.code<500:raise RuntimeError(f'permanent HTTP error: {e}') from e
   print(f'  retry {attempt}/5: {e}',flush=True)
  except Exception as e:print(f'  retry {attempt}/5: {e}',flush=True)
  time.sleep(min(30,2**attempt))
 raise RuntimeError('full download failed')

def find_local_original(downloads:Path,cache:Path)->Path|None:
 override=os.environ.get('HTS50_ORIGINAL_ARCHIVE_OVERRIDE')
 if override:return Path(override).resolve()
 candidates=[cache/ORIGINAL_FILENAME,downloads/ORIGINAL_FILENAME]
 for stage in ('HTS44','HTS45','HTS46','HTS47','HTS48','HTS49','HTS50'):candidates.append(downloads/f'{stage}_CHAIN_CACHE'/ORIGINAL_FILENAME)
 return next((p for p in candidates if p.is_file() and zipfile.is_zipfile(p)),None)

def _materialize_from_outer_zip(z:zipfile.ZipFile,cache:Path,dest:Path,remote_base:HTTPRangeFile|None=None):
 cache.mkdir(parents=True,exist_ok=True)
 fp,n=zip_inventory_fingerprint(z)
 outer_rows=_outer_archive_inventory(z)
 write_tsv(cache/'HTS50_ORIGINAL_OUTER_INVENTORY.tsv',outer_rows)
 # First permit a direct, non-nested release layout.
 direct_rows=_annotate_candidate_rows(z,context='')
 direct_sel=_select_unique_rows(direct_rows)
 if set(direct_sel)=={'CMB','DESI'}:
  write_tsv(cache/'HTS50_ORIGINAL_ROOT_DISCOVERY.tsv',direct_rows)
  write_tsv(cache/'HTS50_ORIGINAL_NESTED_ARCHIVES.tsv',[])
  roots={k:v['root'] for k,v in direct_sel.items()}
  shutil.rmtree(dest,ignore_errors=True);rows=extract_selected_from_zip(z,dest,roots)
  selection={k:{'nested_archive_member':'','root':v,'nested_open_mode':'DIRECT_OUTER_ZIP'} for k,v in roots.items()}
  return fp,n,rows,roots,selection,'DIRECT_OUTER_ZIP'
 selected,candidate_rows,nested_rows,_=discover_nested_original_sources(z,cache,remote_base)
 write_tsv(cache/'HTS50_ORIGINAL_ROOT_DISCOVERY.tsv',candidate_rows)
 write_tsv(cache/'HTS50_ORIGINAL_NESTED_ARCHIVES.tsv',nested_rows)
 if set(selected)!={'CMB','DESI'}:
  counts={lab:sum(r.get('contract_label')==lab and r.get('selection_result') in ('CANDIDATE','AMBIGUOUS') for r in candidate_rows) for lab in ('CMB','DESI')}
  opened=sum(r.get('status')=='OPENED' for r in nested_rows)
  raise RuntimeError(f'nested original root discovery was not unique: selected_labels={sorted(selected)}, candidate_counts={counts}, nested_archives_opened={opened}; see HTS50_ORIGINAL_OUTER_INVENTORY.tsv, HTS50_ORIGINAL_NESTED_ARCHIVES.tsv and HTS50_ORIGINAL_ROOT_DISCOVERY.tsv')
 rows,selection=extract_nested_selected(z,cache,dest,selected,remote_base)
 roots={label:rec['root'] for label,rec in selection.items()}
 return fp,n,rows,roots,selection,'NESTED_ZIP_RANGE_SELECTION'


def materialize_original_selected(downloads:Path,cache:Path,test:bool=False):
 dest=cache/'ORIGINAL_SELECTED';local=find_local_original(downloads,cache)
 rows=[];meta={};roots={};selection={}
 if local:
  with zipfile.ZipFile(local) as z:
   bad=z.testzip()
   if bad:raise RuntimeError(f'original ZIP CRC failure: {bad}')
   fp,n,rows,roots,selection,layout=_materialize_from_outer_zip(z,cache,dest,None)
  meta={'mode':'LOCAL_FULL_ARCHIVE_'+layout,'url':ORIGINAL_URL,'archive_path':str(local),'archive_bytes':local.stat().st_size,'archive_sha256':sha256(local),'inventory_sha256':fp,'entry_count':n,'etag':'','last_modified':'','range_requests':0,'range_bytes_fetched':0,'selected_roots_json':json.dumps(selection,sort_keys=True)}
 else:
  try:
   rf=HTTPRangeFile(ORIGINAL_URL)
   with zipfile.ZipFile(rf) as z:
    fp,n,rows,roots,selection,layout=_materialize_from_outer_zip(z,cache,dest,rf)
   meta={'mode':'REMOTE_HTTP_RANGE_'+layout,'url':ORIGINAL_URL,'archive_path':'','archive_bytes':rf.size,'archive_sha256':'NOT_MATERIALIZED','inventory_sha256':fp,'entry_count':n,'etag':rf.etag,'last_modified':rf.last_modified,'range_requests':rf.requests,'range_bytes_fetched':rf.bytes_fetched,'selected_roots_json':json.dumps(selection,sort_keys=True)}
  except Exception as e:
   if os.environ.get('HTS50_ALLOW_FULL_DOWNLOAD','0')!='1':raise RuntimeError('selective nested HTTP Range materialization/root discovery failed; full 6.19 GB fallback disabled: '+str(e)) from e
   full=cache/ORIGINAL_FILENAME;download_full(ORIGINAL_URL,full)
   with zipfile.ZipFile(full) as z:
    bad=z.testzip()
    if bad:raise RuntimeError(f'original ZIP CRC failure: {bad}')
    fp,n,rows,roots,selection,layout=_materialize_from_outer_zip(z,cache,dest,None)
   meta={'mode':'DOWNLOADED_FULL_ARCHIVE_'+layout,'url':ORIGINAL_URL,'archive_path':str(full),'archive_bytes':full.stat().st_size,'archive_sha256':sha256(full),'inventory_sha256':fp,'entry_count':n,'etag':'','last_modified':'','range_requests':0,'range_bytes_fetched':0,'selected_roots_json':json.dumps(selection,sort_keys=True)}
 for r in rows:r['era']='ORIGINAL'
 return dest,meta,rows,roots


def valid_fixed(p:Path)->bool:return p.is_file() and p.stat().st_size==FIXED_BYTES and sha256(p)==FIXED_SHA256

def materialize_fixed_selected(downloads:Path,cache:Path,test:bool=False):
 override=os.environ.get('HTS50_FIXED_ARCHIVE_OVERRIDE');candidates=[]
 if override:candidates.append(Path(override).resolve())
 candidates += [cache/FIXED_FILENAME,downloads/FIXED_FILENAME]
 for stage in ('HTS44','HTS45','HTS46','HTS47','HTS48','HTS49','HTS50'):candidates.append(downloads/f'{stage}_CHAIN_CACHE'/FIXED_FILENAME)
 p=next((x for x in candidates if x.is_file() and (test or valid_fixed(x))),None)
 if p is None:
  p=cache/FIXED_FILENAME;download_full(FIXED_URL,p)
  if not valid_fixed(p):raise RuntimeError('fixed archive identity mismatch')
 dest=cache/'FIXED_SELECTED';shutil.rmtree(dest,ignore_errors=True);dest.mkdir(parents=True)
 with zipfile.ZipFile(p) as z:
  bad=z.testzip()
  if bad:raise RuntimeError(f'fixed ZIP CRC failure: {bad}')
  fp,n=zip_inventory_fingerprint(z);rows=extract_selected_from_zip(z,dest,ROOTS)
 for r in rows:r['era']='FIXED'
 meta={'mode':'OVERRIDE_TEST' if test else 'FROZEN_FULL_ARCHIVE','url':FIXED_URL,'archive_path':str(p),'archive_bytes':p.stat().st_size,'archive_sha256':sha256(p),'inventory_sha256':fp,'entry_count':n,'etag':'','last_modified':'','range_requests':0,'range_bytes_fetched':0}
 return dest,meta,rows,FIXED_ROOTS

def load_root(root:Path,burn:float):
 files=chain_files(root)
 if len(files)!=8:raise RuntimeError(f'{root}: expected 8 chains, got {len(files)}')
 arrays=[];ids=[];header=None
 for p in files:
  h=read_header(p)
  if header is None:header=h
  elif h!=header:raise RuntimeError(f'header mismatch: {root}')
  a=np.atleast_2d(np.loadtxt(p));a=a[int(math.floor(len(a)*burn)):]
  if len(a)<2:raise RuntimeError(f'too few rows after burn: {p}')
  arrays.append(a);ids.extend([p.name]*len(a))
 a=np.vstack(arrays);w=a[:,0].astype(float)
 if np.any(~np.isfinite(w)) or np.any(w<=0):raise RuntimeError(f'invalid weights: {root}')
 cols=resolve_columns(header);missing=[p for p in PARAMS if p not in cols]
 if missing:raise RuntimeError(f'missing direct columns {missing}: {root}')
 d={p:a[:,header.index(cols[p])].astype(float) for p in PARAMS}
 d['h_rdrag']=d['H0']*d['r_drag']/100
 z=np.c_[(d['Omega_m']-DESI_OM)/DESI_SIG_OM,(d['h_rdrag']-DESI_HRD)/DESI_SIG_HRD]
 d['tangent_DESI_sigma']=z@AXIS;d['normal_DESI_sigma']=z@ORTH
 return d,w,np.array(ids,object),header,cols,files

def wmean(x,w):return float(np.sum(x*w)/np.sum(w))
def wvar(x,w):
 m=wmean(x,w);return float(np.sum(w*(x-m)**2)/np.sum(w))
def wsd(x,w):return math.sqrt(max(wvar(x,w),0.0))

def summarize_root(era,label,root,burn):
 d,w,ids,h,cols,files=load_root(root,burn);rows=[]
 for p,x in d.items():rows.append({'era':era,'contract':label,'burn_fraction_per_chain':burn,'parameter':p,'mean':wmean(x,w),'sd':wsd(x,w),'weight_sum':float(w.sum()),'mode':'DIRECT_POSTERIOR_COLUMN' if p in PARAMS else 'DERIVED_FIXED_FORMULA','source_column':cols.get(p,'direct H0, Omega_m, r_drag; frozen geometry')})
 chain=[]
 for f in sorted(set(ids)):
  m=ids==f;row={'era':era,'contract':label,'burn_fraction_per_chain':burn,'chain_file':f,'weight_share':float(w[m].sum()/w.sum())}
  for p in ('omega_c','H0','Omega_m','r_drag','tau','tangent_DESI_sigma','normal_DESI_sigma'):row[p+'_mean']=wmean(d[p][m],w[m])
  chain.append(row)
 return rows,chain,h,files

def parse_author_mean(root:Path,header:list[str]):
 p=root/'CLASS_mean.txt'
 if not p.exists():return {}
 vals=[]
 for line in p.read_text(errors='replace').splitlines():
  try:vals.append(float(line.strip()))
  except Exception:pass
 names=header[2:]
 if len(vals)<len(names):return {}
 lookup=dict(zip(names,vals[:len(names)]));cols=resolve_columns(header)
 return {k:lookup[v] for k,v in cols.items() if v in lookup}

def make_zip(out:Path,zp:Path):
 lines=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name!='SHA256SUMS.txt':lines.append(f'{sha256(p)}  {p.name}')
 (out/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
 with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(out.iterdir()):
   if p.is_file():z.write(p,p.name)
 Path(str(zp)+'.sha256').write_text(f'{sha256(zp)}  {zp.name}\n')

# ===================== HTS59 reused source-materialization layer =====================
FACTOR_ROOTS_ORIGINAL={
 'SPT_BASE':'LCDM/S1920lite_MPP_No_OLE',
 'SPT_ACT':'LCDM/S1920lite_MPP_ACTDR6lite_actdr6lens_No_OLE',
 'SPT_PR4':'LCDM/S1920lite_MPP_PlkPR4lens_No_OLE',
 'FULL_ORIGINAL':'LCDM/S1920lite_MPP_PlkPR4lens_ACTDR6lite_actdr6lens_No_OLE',
}
FACTOR_EXPECTED_CHAINS={'SPT_BASE':6,'SPT_ACT':8,'SPT_PR4':6,'FULL_ORIGINAL':8}
FACTOR_ROOT_FIXED={'FULL_FIXED':FIXED_ROOTS['CMB']}
FACTOR_EXPECTED_CHAINS_FIXED={'FULL_FIXED':8}

def recursive_candidates(store:Path, filename:str)->list[Path]:
 out=[]
 if store.exists():
  try:
   out=[p for p in store.rglob(filename) if p.is_file()]
  except Exception:
   out=[]
 return sorted(out,key=lambda p:(len(p.parts),str(p)))

def find_exact_archive(store:Path,downloads:Path,filename:str,bytes_expected:int|None=None,sha_expected:str|None=None)->Path|None:
 override=os.environ.get('HTS62_'+('FIXED' if filename==FIXED_FILENAME else 'ORIGINAL')+'_ARCHIVE_OVERRIDE')
 cand=[]
 if override:cand.append(Path(override).resolve())
 cand.extend(recursive_candidates(store,filename))
 p0=downloads/filename
 if p0.is_file():cand.append(p0)
 seen=set()
 for p in cand:
  try:
   rp=p.resolve()
   if rp in seen:continue
   seen.add(rp)
   if not p.is_file() or not zipfile.is_zipfile(p):continue
   if bytes_expected is not None and p.stat().st_size!=bytes_expected:continue
   if sha_expected is not None and sha256(p)!=sha_expected:continue
   return p
  except Exception:continue
 return None

def _variable_wanted(zf:zipfile.ZipFile,roots:dict[str,str],counts:dict[str,int])->list[tuple[str,str]]:
 names=set(zf.namelist());wanted=[]
 for label,root in roots.items():
  n=int(counts[label])
  for k in range(1,n+1):wanted.append((label,_join_member(root,f'CLASS.{k}.txt')))
  for fn in ('CLASS.input.yaml','CLASS.updated.yaml'):wanted.append((label,_join_member(root,fn)))
  mn=_join_member(root,'CLASS_mean.txt')
  if mn in names:wanted.append((label,mn))
 missing=[n for _,n in wanted if n not in names]
 if missing:raise RuntimeError('selected members absent: '+', '.join(missing[:20]))
 return wanted

def extract_variable_selected(zf:zipfile.ZipFile,dest:Path,roots:dict[str,str],counts:dict[str,int],source_prefix:str='')->list[dict]:
 dest.mkdir(parents=True,exist_ok=True);rows=[]
 for label,n in _variable_wanted(zf,roots,counts):
  info=zf.getinfo(n);target=dest/n;target.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();written=0
  with zf.open(info) as src,target.open('wb') as out:
   while True:
    b=src.read(1024*1024)
    if not b:break
    out.write(b);h.update(b);written+=len(b)
  if written!=info.file_size:raise RuntimeError(f'extracted size mismatch: {n}')
  rel=f'{source_prefix}!{n}' if source_prefix else n
  rows.append({'source':'ORIGINAL','contract':label,'relative_path':rel,'materialized_path':n,'bytes':written,'compressed_bytes':info.compress_size,'CRC32':f'{info.CRC:08x}','sha256':h.hexdigest()})
 return rows

def _open_original_outer(store:Path,downloads:Path,stage_cache:Path,test:bool=False):
 local=find_exact_archive(store,downloads,ORIGINAL_FILENAME)
 if local is not None:
  z=zipfile.ZipFile(local)
  return z,None,{'mode':'LOCAL_FULL_ARCHIVE','archive_path':str(local),'archive_bytes':local.stat().st_size,'archive_sha256':sha256(local),'etag':'','last_modified':''}
 rf=HTTPRangeFile(ORIGINAL_URL)
 z=zipfile.ZipFile(rf)
 return z,rf,{'mode':'REMOTE_HTTP_RANGE_NESTED_ZIP','archive_path':'','archive_bytes':rf.size,'archive_sha256':'NOT_MATERIALIZED','etag':rf.etag,'last_modified':rf.last_modified}

def materialize_original_factorial(downloads:Path,store:Path,stage_cache:Path,test:bool=False):
 override=os.environ.get('HTS_SELECTED_CACHE_OVERRIDE')
 if override:
  src=Path(override).resolve()/'ORIGINAL'
  if not src.is_dir():raise RuntimeError(f'preverified ORIGINAL selected cache missing: {src}')
  dest=stage_cache/'ORIGINAL_FACTORIAL_SELECTED';shutil.rmtree(dest,ignore_errors=True)
  def _link_or_copy(s,d):
   try:os.link(s,d)
   except OSError:shutil.copy2(s,d)
  shutil.copytree(src,dest,copy_function=_link_or_copy)
  roots=FACTOR_ROOTS_ORIGINAL;inv=[];rows=[]
  for lab,relroot in roots.items():
   r=dest/relroot
   nums=sorted(int(m.group(1)) for p in r.glob('CLASS.*.txt') if (m:=re.fullmatch(r'CLASS\.(\d+)\.txt',p.name)))
   expected=list(range(1,FACTOR_EXPECTED_CHAINS[lab]+1))
   inv.append({'contract':lab,'root':relroot,'observed_chain_numbers':','.join(map(str,nums)),'expected_chain_numbers':','.join(map(str,expected)),'has_input_yaml':(r/'CLASS.input.yaml').is_file(),'has_updated_yaml':(r/'CLASS.updated.yaml').is_file(),'has_author_mean':(r/'CLASS_mean.txt').is_file()})
   if nums!=expected:raise RuntimeError(f'{lab}: preverified selected cache chain inventory mismatch {nums}')
   for p in sorted(r.iterdir()):
    if not p.is_file():continue
    rel=p.relative_to(dest).as_posix()
    rows.append({'source':'ORIGINAL','contract':lab,'relative_path':'PREVERIFIED_SELECTED_CACHE!'+rel,'materialized_path':rel,'bytes':p.stat().st_size,'compressed_bytes':'','CRC32':'','sha256':sha256(p)})
  stage_num=re.search(r'hts(\d+)_common',Path(__file__).stem).group(1)
  write_tsv(stage_cache/f'HTS{stage_num}_ORIGINAL_ROOT_INVENTORY.tsv',inv)
  fp=hashlib.sha256('\n'.join(f"{r['materialized_path']}\t{r['bytes']}\t{r['sha256']}" for r in sorted(rows,key=lambda x:x['materialized_path'])).encode()).hexdigest()
  meta={'mode':'PREVERIFIED_HASH_FIXED_SELECTED_CACHE','archive_path':'','archive_bytes':'','archive_sha256':'NOT_REREAD_IN_STAGE','outer_inventory_sha256':'','outer_entry_count':'','nested_archive_member':'','nested_inventory_sha256':fp,'nested_entry_count':len(rows),'nested_open_mode':'PORTABLE_HARDLINK_OR_COPY_VIEW','range_requests':0,'range_bytes_fetched':0,'selected_roots_json':json.dumps(roots,sort_keys=True),'selected_cache_path':str(src)}
  return dest,meta,rows,roots
 dest=stage_cache/'ORIGINAL_FACTORIAL_SELECTED';shutil.rmtree(dest,ignore_errors=True)
 outer,rf,meta=_open_original_outer(store,downloads,stage_cache,test)
 try:
  ofp,on=zip_inventory_fingerprint(outer);meta['outer_inventory_sha256']=ofp;meta['outer_entry_count']=on
  infos={i.filename:i for i in outer.infolist()}
  member='Compressed_Chains/LCDM.zip'
  if member not in infos:
   # test archives may wrap the same basename.
   xs=[i for i in outer.infolist() if i.filename.endswith('/LCDM.zip') or i.filename=='LCDM.zip']
   if len(xs)!=1:raise RuntimeError(f'LCDM nested archive not uniquely found: {len(xs)}')
   info=xs[0];member=info.filename
  else:info=infos[member]
  with _open_nested_member(outer,info,stage_cache,rf) as (inner,open_meta):
   ifp,inn=zip_inventory_fingerprint(inner)
   roots=FACTOR_ROOTS_ORIGINAL
   # exact roots and chain counts
   names=set(inner.namelist())
   inv=[]
   for lab,root in roots.items():
    nums=sorted(int(m.group(1)) for n in names if (m:=re.fullmatch(re.escape(root)+r'/CLASS\.(\d+)\.txt',n)))
    inv.append({'contract':lab,'root':root,'observed_chain_numbers':','.join(map(str,nums)),'expected_chain_numbers':','.join(map(str,range(1,FACTOR_EXPECTED_CHAINS[lab]+1))),'has_input_yaml':_join_member(root,'CLASS.input.yaml') in names,'has_updated_yaml':_join_member(root,'CLASS.updated.yaml') in names,'has_author_mean':_join_member(root,'CLASS_mean.txt') in names})
    if nums!=list(range(1,FACTOR_EXPECTED_CHAINS[lab]+1)):raise RuntimeError(f'{lab}: chain inventory mismatch {nums}')
   rows=extract_variable_selected(inner,dest,roots,FACTOR_EXPECTED_CHAINS,source_prefix=member)
   write_tsv(stage_cache/'HTS62_ORIGINAL_ROOT_INVENTORY.tsv',inv)
   meta.update({'nested_archive_member':member,'nested_inventory_sha256':ifp,'nested_entry_count':inn,**open_meta})
  if rf is not None:
   meta['range_requests']=rf.requests;meta['range_bytes_fetched']=rf.bytes_fetched
  else:
   meta['range_requests']=0;meta['range_bytes_fetched']=0
  meta['selected_roots_json']=json.dumps(roots,sort_keys=True)
  return dest,meta,rows,roots
 finally:
  outer.close()
  if rf is not None:rf.close()

def materialize_fixed_full(downloads:Path,store:Path,stage_cache:Path,test:bool=False):
 override=os.environ.get('HTS_SELECTED_CACHE_OVERRIDE')
 if override:
  src=Path(override).resolve()/'FIXED'
  if not src.is_dir():raise RuntimeError(f'preverified FIXED selected cache missing: {src}')
  dest=stage_cache/'FIXED_FULL_SELECTED';shutil.rmtree(dest,ignore_errors=True)
  def _link_or_copy(s,d):
   try:os.link(s,d)
   except OSError:shutil.copy2(s,d)
  shutil.copytree(src,dest,copy_function=_link_or_copy)
  rows=[]
  for lab,relroot in FACTOR_ROOT_FIXED.items():
   r=dest/relroot
   nums=sorted(int(m.group(1)) for p in r.glob('CLASS.*.txt') if (m:=re.fullmatch(r'CLASS\.(\d+)\.txt',p.name)))
   expected=list(range(1,FACTOR_EXPECTED_CHAINS_FIXED[lab]+1))
   if nums!=expected:raise RuntimeError(f'{lab}: preverified selected cache chain inventory mismatch {nums}')
   for p in sorted(r.iterdir()):
    if not p.is_file():continue
    rel=p.relative_to(dest).as_posix()
    rows.append({'source':'FIXED','contract':lab,'relative_path':'PREVERIFIED_SELECTED_CACHE!'+rel,'materialized_path':rel,'bytes':p.stat().st_size,'compressed_bytes':'','CRC32':'','sha256':sha256(p)})
  fp=hashlib.sha256('\n'.join(f"{r['materialized_path']}\t{r['bytes']}\t{r['sha256']}" for r in sorted(rows,key=lambda x:x['materialized_path'])).encode()).hexdigest()
  meta={'mode':'PREVERIFIED_HASH_FIXED_SELECTED_CACHE','archive_path':'','archive_bytes':'','archive_sha256':'NOT_REREAD_IN_STAGE','inventory_sha256':fp,'entry_count':len(rows),'selected_cache_path':str(src)}
  return dest,meta,rows,FACTOR_ROOT_FIXED
 p=find_exact_archive(store,downloads,FIXED_FILENAME,None if test else FIXED_BYTES,None if test else FIXED_SHA256)
 if p is None:
  p=stage_cache/FIXED_FILENAME;download_full(FIXED_URL,p)
  if not test and not valid_fixed(p):raise RuntimeError('fixed archive identity mismatch')
 dest=stage_cache/'FIXED_FULL_SELECTED';shutil.rmtree(dest,ignore_errors=True);dest.mkdir(parents=True)
 with zipfile.ZipFile(p) as z:
  bad=z.testzip()
  if bad:raise RuntimeError(f'fixed ZIP CRC failure: {bad}')
  fp,n=zip_inventory_fingerprint(z)
  rows=extract_variable_selected(z,dest,FACTOR_ROOT_FIXED,FACTOR_EXPECTED_CHAINS_FIXED)
 for r in rows:r['source']='FIXED'
 meta={'mode':'FROZEN_FULL_ARCHIVE','archive_path':str(p),'archive_bytes':p.stat().st_size,'archive_sha256':sha256(p),'inventory_sha256':fp,'entry_count':n}
 return dest,meta,rows,FACTOR_ROOT_FIXED

def root_chain_files(root:Path,expected:int)->list[Path]:
 xs=chain_files(root);nums=[int(re.fullmatch(r'CLASS\.(\d+)\.txt',p.name).group(1)) for p in xs]
 if nums!=list(range(1,expected+1)):raise RuntimeError(f'{root}: expected chains 1..{expected}, got {nums}')
 return xs

def load_factor_root(root:Path,expected:int,burn:float):
 files=root_chain_files(root,expected);arrays=[];ids=[];header=None
 for p in files:
  h=read_header(p)
  if header is None:header=h
  elif h!=header:raise RuntimeError(f'header mismatch: {root}')
  a=np.atleast_2d(np.loadtxt(p));a=a[int(math.floor(len(a)*burn)):]
  if len(a)<2:raise RuntimeError(f'too few rows after burn: {p}')
  arrays.append(a);ids.extend([p.name]*len(a))
 a=np.vstack(arrays);w=a[:,0].astype(float)
 if np.any(~np.isfinite(w)) or np.any(w<=0):raise RuntimeError(f'invalid weights: {root}')
 cols=resolve_columns(header);missing=[p for p in PARAMS if p not in cols]
 if missing:raise RuntimeError(f'missing direct columns {missing}: {root}')
 d={p:a[:,header.index(cols[p])].astype(float) for p in PARAMS}
 d['h_rdrag']=d['H0']*d['r_drag']/100
 z=np.c_[(d['Omega_m']-DESI_OM)/DESI_SIG_OM,(d['h_rdrag']-DESI_HRD)/DESI_SIG_HRD]
 d['tangent_DESI_sigma']=z@AXIS;d['normal_DESI_sigma']=z@ORTH
 return d,w,np.array(ids,object),header,cols,files

def summarize_factor_root(source:str,label:str,root:Path,expected:int,burn:float):
 d,w,ids,h,cols,files=load_factor_root(root,expected,burn);rows=[];chain=[]
 for p,x in d.items():
  rows.append({'source':source,'contract':label,'burn_fraction_per_chain':burn,'parameter':p,'mean':wmean(x,w),'sd':wsd(x,w),'weight_sum':float(w.sum()),'chain_count':expected,'mode':'DIRECT_POSTERIOR_COLUMN' if p in PARAMS else 'DERIVED_FIXED_FORMULA','source_column':cols.get(p,'direct H0, Omega_m, r_drag; frozen geometry')})
 for f in sorted(set(ids)):
  m=ids==f;row={'source':source,'contract':label,'burn_fraction_per_chain':burn,'chain_file':f,'weight_share':float(w[m].sum()/w.sum())}
  for p in ('omega_c','H0','Omega_m','r_drag','tau','tangent_DESI_sigma','normal_DESI_sigma'):row[p+'_mean']=wmean(d[p][m],w[m])
  chain.append(row)
 return rows,chain,h

def likelihood_set(root:Path)->set[str]:
 inv=likelihood_inventory(root)
 # Use the union of input and resolved/updated YAML names. This prevents a
 # resolver-added top-level likelihood from being silently omitted.
 return set(inv['CLASS.input.yaml']) | set(inv['CLASS.updated.yaml'])


def factor_contract_rows(all_roots:dict[str,Path]):
 """Validate the five released endpoints as a contract-labelled response graph.

 CORR2 does not force the original full endpoint to be the 2x2 union corner.
 The observed original full YAML omits both released lensing implementations
 used by the ACT-only and PR4-only partial corners. That endpoint is preserved
 as an unmatched release endpoint, while the official fixed full endpoint is
 the corrected full endpoint.
 """
 inventories={k:likelihood_inventory(v) for k,v in all_roots.items()}
 likes={k:(set(inv['CLASS.input.yaml'])|set(inv['CLASS.updated.yaml'])) for k,inv in inventories.items()}
 families={k:semantic_families(v) for k,v in likes.items()}
 rows=[]
 union=sorted(set().union(*likes.values()))
 for name in union:
  row={'likelihood':name}
  for k in all_roots:
   row[k]=name in likes[k]
   row[k+'_input']=name in inventories[k]['CLASS.input.yaml']
   row[k+'_updated']=name in inventories[k]['CLASS.updated.yaml']
  rows.append(row)

 fam_union=sorted(set().union(*families.values()))
 family_rows=[]
 for fam in fam_union:
  row={'semantic_family':fam}
  for k in all_roots:row[k]=fam in families[k]
  family_rows.append(row)

 expected={
  'SPT_BASE':{'SPT_PRIMARY','SPT_LENSING'},
  'SPT_ACT':{'SPT_PRIMARY','SPT_LENSING','ACT_PRIMARY','ACT_PLANCK_JOINT_LENSING'},
  'SPT_PR4':{'SPT_PRIMARY','SPT_LENSING','PLANCK_PRIMARY_HIGH_L','PLANCK_PRIMARY_LOW_L_TT','PLANCK_PR4_LENSING'},
  # Observed original-release full endpoint. It is not accepted as a
  # factorial union corner and is retained only as an unmatched endpoint.
  'FULL_ORIGINAL':{'SPT_PRIMARY','SPT_LENSING','ACT_PRIMARY','PLANCK_PRIMARY_HIGH_L','PLANCK_PRIMARY_LOW_L_TT'},
  # Official corrected full endpoint: ACT primary + Planck primary and the
  # joint ACT+Planck lensing likelihood.
  'FULL_FIXED':{'SPT_PRIMARY','SPT_LENSING','ACT_PRIMARY','ACT_PLANCK_JOINT_LENSING','PLANCK_PRIMARY_HIGH_L','PLANCK_PRIMARY_LOW_L_TT'},
 }
 checks=[];ok=True
 for label in all_roots:
  observed=families[label];exp=expected[label];passed=(observed==exp)
  ok &= passed
  checks.append({
   'check':f'{label}_release_endpoint_signature',
   'observed':json.dumps(sorted(observed)),
   'required':json.dumps(sorted(exp)),
   'result':'PASS' if passed else 'FAIL',
  })

 unknown={}
 for label,names in likes.items():
  known={n for n in names if semantic_families({n})}
  unknown[label]=sorted(names-known);passed=not unknown[label];ok &= passed
  checks.append({
   'check':f'{label}_no_unclassified_top_level_likelihood',
   'observed':json.dumps(unknown[label]),
   'required':'[]',
   'result':'PASS' if passed else 'FAIL',
  })

 # Explicit anti-factorial boundary: the original full endpoint must not be
 # silently treated as the union of the ACT-only and PR4-only corners.
 partial_union=families['SPT_ACT']|families['SPT_PR4']
 original_is_union=(families['FULL_ORIGINAL']==partial_union)
 checks.append({
  'check':'FULL_ORIGINAL_not_used_as_factorial_union_corner',
  'observed':str(original_is_union),
  'required':'False',
  'result':'PASS' if not original_is_union else 'FAIL',
 })
 ok &= (not original_is_union)

 raw_checks=[
  {'diagnostic':'SPT_ACT_raw_names','value':json.dumps(sorted(likes['SPT_ACT']))},
  {'diagnostic':'SPT_PR4_raw_names','value':json.dumps(sorted(likes['SPT_PR4']))},
  {'diagnostic':'FULL_ORIGINAL_raw_names','value':json.dumps(sorted(likes['FULL_ORIGINAL']))},
  {'diagnostic':'FULL_FIXED_raw_names','value':json.dumps(sorted(likes['FULL_FIXED']))},
  {'diagnostic':'FULL_ORIGINAL_missing_vs_partial_union','value':json.dumps(sorted(partial_union-families['FULL_ORIGINAL']))},
  {'diagnostic':'FULL_FIXED_missing_vs_partial_union','value':json.dumps(sorted(partial_union-families['FULL_FIXED']))},
 ]
 return rows,likes,family_rows,families,ok,checks,raw_checks


def chain_header_likelihood_rows(all_roots:dict[str,Path])->list[dict]:
 """Record likelihood/prior-related direct chain header columns.

 These columns are diagnostic only; they are not used to invent a likelihood
 contract that is absent from the released YAML.
 """
 rows=[]
 pat=re.compile(r'(chi2|minuslog|logpost|logprior|prior)',re.I)
 for label,root in all_roots.items():
  files=chain_files(root)
  if not files:continue
  header=read_header(files[0])
  for idx,name in enumerate(header):
   if pat.search(name):
    rows.append({'contract':label,'column_index':idx,'column_name':name})
 return rows


RELEASE_GRAPH_EDGES=(
 ('BASE_TO_ACT','SPT_BASE','SPT_ACT','STRICT_EXTENSION','Adds ACT primary plus joint ACT+Planck lensing.'),
 ('BASE_TO_PR4','SPT_BASE','SPT_PR4','STRICT_EXTENSION','Adds Planck primary plus Planck PR4 lensing.'),
 ('BASE_TO_FULL_ORIGINAL','SPT_BASE','FULL_ORIGINAL','UNMATCHED_RELEASE_ENDPOINT','Adds ACT and Planck primary likelihoods but not the lensing composition of either partial corner.'),
 ('BASE_TO_FULL_FIXED','SPT_BASE','FULL_FIXED','OFFICIAL_FIXED_FULL_ENDPOINT','Adds ACT and Planck primary likelihoods plus joint ACT+Planck lensing.'),
 ('ACT_TO_FULL_FIXED','SPT_ACT','FULL_FIXED','CONDITIONAL_EXTENSION','Adds the Planck primary likelihood family while retaining joint ACT+Planck lensing.'),
 ('PR4_TO_FULL_FIXED','SPT_PR4','FULL_FIXED','MIXED_EXTENSION','Adds ACT primary and replaces Planck-only lensing with joint ACT+Planck lensing.'),
 ('ORIGINAL_TO_FIXED_RELEASE','FULL_ORIGINAL','FULL_FIXED','RELEASE_ENDPOINT_CHANGE','Combines the official nuisance-prior correction with released likelihood-implementation/composition changes; not a bugfix-only contrast.'),
)
