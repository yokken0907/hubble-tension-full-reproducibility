#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib, sys
ROOT=Path(__file__).resolve().parent

def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f,delimiter='\t'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def fail(msg):
    print('FAIL:',msg);raise SystemExit(1)
a=rows(ROOT/'OFFICIAL_ARCHIVE_VERIFICATION.tsv')
if len(a)!=2: fail('archive rows != 2')
by={r['SOURCE']:r for r in a}
if by['ORIGINAL']['OVERALL_STATUS']!='PASS_WITH_SCOPE_RANGE_SELECTED_MEMBER_IDENTITY': fail('original status')
if by['ORIGINAL']['ETAG_MATCH']!='NO': fail('etag mismatch not recorded')
if by['ORIGINAL']['FULL_ARCHIVE_SHA256_STATUS']!='NOT_MATERIALIZED_NOT_CLAIMED': fail('original full archive boundary')
if by['ORIGINAL']['SELECTED_MEMBER_COUNT']!='40/40' or by['FIXED']['SELECTED_MEMBER_COUNT']!='11/11': fail('member counts')
if by['FIXED']['FULL_ARCHIVE_SHA256_STATUS']!='PASS': fail('fixed full hash')
s=rows(ROOT/'OFFICIAL_SELECTED_MEMBER_VERIFICATION_SUMMARY.tsv')
if {r['SOURCE']:r['STATUS'] for r in s}!={'ORIGINAL':'PASS','FIXED':'PASS','TOTAL':'PASS'}: fail('selected summary status')
raw=ROOT/'phase2c_network_execution/OFFICIAL_ARCHIVE_ACQUISITION_RAW.tsv'
if sha(raw)!='ec595c0cef21438c97be92e57b93e7b97a0919c0ea35a49a96198dd2a91a411b': fail('raw acquisition hash')
report=(ROOT/'phase2c_network_execution/PHASE2C_OFFICIAL_EMPTY_CACHE_FETCH_REPORT.md').read_text(encoding='utf-8')
for x in ['OFFICIAL_FETCH_EMPTY_CACHE = PASS','E002_FROM_OFFICIAL_EMPTY_CACHE = PASS','Repository modification: `NONE`']:
    if x not in report: fail('report missing '+x)
print('OFFICIAL_FETCH_PROVENANCE=PASS')
print('ORIGINAL_RANGE_SELECTED_MEMBERS=40/40_PASS')
print('FIXED_SELECTED_MEMBERS=11/11_PASS')
print('ORIGINAL_ETAG_MATCH=NO_RECORDED')
print('FULL_ORIGINAL_ARCHIVE_SHA256=NOT_MATERIALIZED_NOT_CLAIMED')
