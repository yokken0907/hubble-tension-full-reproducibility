#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

HTS62_FILENAME = 'HTS62_RESULTS_FOR_REVIEW.zip'
HTS62_SHA256 = 'f51b60503ae20361c9fbcdff4d50b2bac74266b0a270545cb71fe60b582c7a18'
HTS66_FILENAME = 'HTS66_CORR_RESULTS_FOR_REVIEW.zip'
HTS66_SHA256 = '92556d7b755f4c7ff2bab1f4ab8cc568a384720cf860164c66810544cf89f54a'

ALIASES = {
    'omega_b': ['omega_b', 'ombh2', 'omegabh2'],
    'omega_c': ['omega_cdm', 'omega_c', 'omch2', 'omegach2'],
    'H0': ['H0', 'h0', 'H_0'],
    'Omega_m': ['Omega_m', 'omegam', 'omega_m'],
    'r_drag': ['rs_drag', 'r_drag', 'rdrag', 'rd', 'r_d'],
    'n_s': ['n_s', 'ns'],
    'tau': ['tau_reio', 'tau'],
    'sigma8': ['sigma8', 'sigma_8'],
    'S8': ['S_8', 'S8'],
    'logA': ['logA'],
}
PARAMS = ('omega_b', 'omega_c', 'H0', 'Omega_m', 'r_drag', 'n_s', 'tau', 'sigma8', 'S8', 'logA')
DESI_OM, DESI_SIG_OM = 0.297462, 0.008575
DESI_HRD, DESI_SIG_HRD = 101.5398, 0.7328
AXIS = np.array([0.535763581993669, -0.844368038363197], dtype=float)
AXIS /= np.linalg.norm(AXIS)
ORTH = np.array([-AXIS[1], AXIS[0]], dtype=float)

ROOT_TAILS = {
    'SPT_BASE': Path('ORIGINAL_FACTORIAL_SELECTED/LCDM/S1920lite_MPP_No_OLE'),
    'SPT_ACT': Path('ORIGINAL_FACTORIAL_SELECTED/LCDM/S1920lite_MPP_ACTDR6lite_actdr6lens_No_OLE'),
    'SPT_PR4': Path('ORIGINAL_FACTORIAL_SELECTED/LCDM/S1920lite_MPP_PlkPR4lens_No_OLE'),
    'FULL_ORIGINAL': Path('ORIGINAL_FACTORIAL_SELECTED/LCDM/S1920lite_MPP_PlkPR4lens_ACTDR6lite_actdr6lens_No_OLE'),
    'FULL_FIXED': Path('FIXED_FULL_SELECTED/LCDM/S1920lite_MPP_PACT_PR4lens_actdr6lens_No_OLE'),
}
EXPECTED_CHAINS = {'SPT_BASE': 6, 'SPT_ACT': 8, 'SPT_PR4': 6, 'FULL_ORIGINAL': 8, 'FULL_FIXED': 8}
ORDER = ('SPT_BASE', 'SPT_ACT', 'SPT_PR4', 'FULL_ORIGINAL', 'FULL_FIXED')

RELEASE_GRAPH_EDGES = (
    ('BASE_TO_ACT', 'SPT_BASE', 'SPT_ACT', 'STRICT_EXTENSION', 'Adds ACT primary plus joint ACT+Planck lensing.'),
    ('BASE_TO_PR4', 'SPT_BASE', 'SPT_PR4', 'STRICT_EXTENSION', 'Adds Planck primary plus Planck PR4 lensing.'),
    ('BASE_TO_FULL_ORIGINAL', 'SPT_BASE', 'FULL_ORIGINAL', 'UNMATCHED_RELEASE_ENDPOINT', 'Adds ACT and Planck primary likelihoods but not the lensing composition of either partial corner.'),
    ('BASE_TO_FULL_FIXED', 'SPT_BASE', 'FULL_FIXED', 'OFFICIAL_FIXED_FULL_ENDPOINT', 'Adds ACT and Planck primary likelihoods plus joint ACT+Planck lensing.'),
    ('ACT_TO_FULL_FIXED', 'SPT_ACT', 'FULL_FIXED', 'CONDITIONAL_EXTENSION', 'Adds the Planck primary likelihood family while retaining joint ACT+Planck lensing.'),
    ('PR4_TO_FULL_FIXED', 'SPT_PR4', 'FULL_FIXED', 'MIXED_EXTENSION', 'Adds ACT primary and replaces Planck-only lensing with joint ACT+Planck lensing.'),
    ('ORIGINAL_TO_FIXED_RELEASE', 'FULL_ORIGINAL', 'FULL_FIXED', 'RELEASE_ENDPOINT_CHANGE', 'Combines the official nuisance-prior correction with released likelihood-implementation/composition changes; not a bugfix-only contrast.'),
)

EXPECTED_FAMILIES = {
    'SPT_BASE': {'SPT_PRIMARY', 'SPT_LENSING'},
    'SPT_ACT': {'SPT_PRIMARY', 'SPT_LENSING', 'ACT_PRIMARY', 'ACT_PLANCK_JOINT_LENSING'},
    'SPT_PR4': {'SPT_PRIMARY', 'SPT_LENSING', 'PLANCK_PRIMARY_HIGH_L', 'PLANCK_PRIMARY_LOW_L_TT', 'PLANCK_PR4_LENSING'},
    'FULL_ORIGINAL': {'SPT_PRIMARY', 'SPT_LENSING', 'ACT_PRIMARY', 'PLANCK_PRIMARY_HIGH_L', 'PLANCK_PRIMARY_LOW_L_TT'},
    'FULL_FIXED': {'SPT_PRIMARY', 'SPT_LENSING', 'ACT_PRIMARY', 'ACT_PLANCK_JOINT_LENSING', 'PLANCK_PRIMARY_HIGH_L', 'PLANCK_PRIMARY_LOW_L_TT'},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    names = fields or list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=names, delimiter='\t', lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def read_tsv_bytes(data: bytes) -> list[dict[str, str]]:
    text = data.decode('utf-8')
    return list(csv.DictReader(text.splitlines(), delimiter='\t'))


def norm(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())


def read_header(path: Path) -> list[str]:
    with path.open(errors='replace') as f:
        line = f.readline().strip()
    if not line.startswith('#'):
        raise RuntimeError(f'missing named header: {path}')
    header = line.lstrip('#').split()
    if len(header) < 3 or norm(header[0]) != 'weight':
        raise RuntimeError(f'invalid named header: {path}')
    return header


def resolve_columns(header: list[str]) -> dict[str, str]:
    lookup = {norm(x): x for x in header}
    out: dict[str, str] = {}
    for key, aliases in ALIASES.items():
        for alias in aliases:
            if norm(alias) in lookup:
                out[key] = lookup[norm(alias)]
                break
    return out


def chain_files(root: Path) -> list[Path]:
    rows: list[tuple[int, Path]] = []
    for path in root.glob('CLASS.*.txt'):
        m = re.fullmatch(r'CLASS\.(\d+)\.txt', path.name)
        if m:
            rows.append((int(m.group(1)), path))
    return [p for _, p in sorted(rows)]


def likelihood_names(path: Path) -> tuple[str, ...]:
    lines = path.read_text(errors='replace').splitlines()
    active = False
    base_indent: int | None = None
    child_indent: int | None = None
    names: list[str] = []
    for raw in lines:
        prefix = raw[:len(raw) - len(raw.lstrip())]
        if '\t' in prefix:
            raise RuntimeError(f'tab-indented YAML is unsupported: {path}')
        if not active:
            m = re.match(r'^(\s*)likelihood\s*:\s*(?:#.*)?$', raw)
            if m:
                active = True
                base_indent = len(m.group(1))
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        assert base_indent is not None
        if indent <= base_indent:
            break
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue
        content = raw[indent:]
        if content.startswith('-'):
            continue
        m = re.match(r'''(?:"([^"]+)"|'([^']+)'|([^:#][^:]*?))\s*:\s*(?:.*)?$''', content)
        if not m:
            continue
        key = next((x for x in m.groups() if x is not None), '').strip()
        if key:
            names.append(key)
    return tuple(sorted(dict.fromkeys(names)))


def semantic_families(names: set[str]) -> set[str]:
    fam: set[str] = set()
    for name in names:
        low = name.lower()
        if 'muse' in low:
            fam.add('SPT_LENSING')
        if 's1920' in low or ('spt3g' in low and 'muse' not in low):
            fam.add('SPT_PRIMARY')
        if 'act_dr6_cmbonly.actdr6cmbonly' in low or 'actdr6lite' in low or 'actdr6cmb' in low:
            fam.add('ACT_PRIMARY')
        if 'act_dr6_lenslike' in low or 'actdr6lens' in low:
            fam.add('ACT_PLANCK_JOINT_LENSING')
        if 'clipy_highl' in low or 'planckactcut' in low:
            fam.add('PLANCK_PRIMARY_HIGH_L')
        if 'clipy_lowl_tt' in low or 'planck_2018_lowl.tt' in low:
            fam.add('PLANCK_PRIMARY_LOW_L_TT')
        if 'planckpr4lensing' in low or 'planck_pr4_lensing' in low:
            fam.add('PLANCK_PR4_LENSING')
        if 'bao.desi_dr2' in low or 'desi_dr2' in low or 'baodr2' in low:
            fam.add('DESI_BAO')
    return fam


def validate_root(label: str, root: Path) -> list[dict[str, Any]]:
    expected = EXPECTED_CHAINS[label]
    files = chain_files(root)
    nums = [int(re.fullmatch(r'CLASS\.(\d+)\.txt', p.name).group(1)) for p in files]
    checks: list[dict[str, Any]] = [{
        'contract': label,
        'check': 'numbered_chain_inventory',
        'observed': ','.join(map(str, nums)),
        'required': ','.join(map(str, range(1, expected + 1))),
        'result': 'PASS' if nums == list(range(1, expected + 1)) else 'FAIL',
    }]
    for name in ('CLASS.input.yaml', 'CLASS.updated.yaml'):
        checks.append({
            'contract': label,
            'check': f'{name}_present',
            'observed': (root / name).is_file(),
            'required': True,
            'result': 'PASS' if (root / name).is_file() else 'FAIL',
        })
    if files:
        header = read_header(files[0])
        cols = resolve_columns(header)
        for param in PARAMS:
            checks.append({
                'contract': label,
                'check': f'direct_column_{param}',
                'observed': cols.get(param, ''),
                'required': 'present',
                'result': 'PASS' if param in cols else 'FAIL',
            })
    if (root / 'CLASS.input.yaml').is_file() and (root / 'CLASS.updated.yaml').is_file():
        names = set(likelihood_names(root / 'CLASS.input.yaml')) | set(likelihood_names(root / 'CLASS.updated.yaml'))
        fam = semantic_families(names)
        expected_fam = EXPECTED_FAMILIES[label]
        checks.append({
            'contract': label,
            'check': 'semantic_release_signature',
            'observed': json.dumps(sorted(fam)),
            'required': json.dumps(sorted(expected_fam)),
            'result': 'PASS' if fam == expected_fam else 'FAIL',
        })
        unknown = sorted(n for n in names if not semantic_families({n}))
        checks.append({
            'contract': label,
            'check': 'no_unclassified_top_level_likelihood',
            'observed': json.dumps(unknown),
            'required': '[]',
            'result': 'PASS' if not unknown else 'FAIL',
        })
    return checks


def _candidate_roots(store: Path, tail: Path) -> list[Path]:
    direct = store / 'HTS63' / tail
    candidates: list[Path] = [direct] if direct.is_dir() else []
    basename = tail.name
    if store.exists():
        for p in store.rglob(basename):
            if not p.is_dir():
                continue
            normalized = p.as_posix().rstrip('/')
            if normalized.endswith(tail.as_posix()) and p not in candidates:
                candidates.append(p)
    return candidates


def discover_cache_roots(store: Path) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    override = os.environ.get('HTS67_CACHE_ROOT_OVERRIDE')
    base = Path(override).resolve() if override else store.resolve()
    roots: dict[str, Path] = {}
    rows: list[dict[str, Any]] = []
    for label, tail in ROOT_TAILS.items():
        candidates = _candidate_roots(base, tail)
        preferred = [p for p in candidates if 'HTS63' in p.parts]
        chosen_pool = preferred if preferred else candidates
        if len(chosen_pool) != 1:
            raise RuntimeError(f'{label}: cache root not unique; candidates={[str(x) for x in candidates]}')
        chosen = chosen_pool[0].resolve()
        roots[label] = chosen
        rows.append({
            'contract': label,
            'selected_root': str(chosen),
            'relative_tail': tail.as_posix(),
            'candidate_count': len(candidates),
            'selection_rule': 'UNIQUE_HTS63_CANDIDATE' if preferred else 'UNIQUE_TAIL_CANDIDATE',
        })
    return roots, rows


def load_factor_root(root: Path, expected: int, burn: float):
    files = chain_files(root)
    nums = [int(re.fullmatch(r'CLASS\.(\d+)\.txt', p.name).group(1)) for p in files]
    if nums != list(range(1, expected + 1)):
        raise RuntimeError(f'{root}: expected chains 1..{expected}, got {nums}')
    arrays: list[np.ndarray] = []
    ids: list[str] = []
    header: list[str] | None = None
    for path in files:
        h = read_header(path)
        if header is None:
            header = h
        elif h != header:
            raise RuntimeError(f'header mismatch: {root}')
        arr = np.atleast_2d(np.loadtxt(path))
        arr = arr[int(math.floor(len(arr) * burn)):]
        if len(arr) < 2:
            raise RuntimeError(f'too few rows after burn: {path}')
        arrays.append(arr)
        ids.extend([path.name] * len(arr))
    assert header is not None
    arr = np.vstack(arrays)
    weights = arr[:, 0].astype(float)
    if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise RuntimeError(f'invalid weights: {root}')
    cols = resolve_columns(header)
    missing = [p for p in PARAMS if p not in cols]
    if missing:
        raise RuntimeError(f'missing direct columns {missing}: {root}')
    data = {p: arr[:, header.index(cols[p])].astype(float) for p in PARAMS}
    data['h_rdrag'] = data['H0'] * data['r_drag'] / 100.0
    z = np.column_stack([
        (data['Omega_m'] - DESI_OM) / DESI_SIG_OM,
        (data['h_rdrag'] - DESI_HRD) / DESI_SIG_HRD,
    ])
    data['tangent_DESI_sigma'] = z @ AXIS
    data['normal_DESI_sigma'] = z @ ORTH
    return data, weights, np.asarray(ids, dtype=object), header, cols, files


def kish(weights: np.ndarray) -> float:
    return float(np.sum(weights) ** 2 / np.sum(weights * weights))


def provenance_rows(roots: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in ORDER:
        root = roots[label]
        wanted = chain_files(root) + [root / 'CLASS.input.yaml', root / 'CLASS.updated.yaml']
        mean_path = root / 'CLASS_mean.txt'
        if mean_path.is_file():
            wanted.append(mean_path)
        for path in wanted:
            rows.append({
                'contract': label,
                'filename': path.name,
                'path': str(path),
                'bytes': path.stat().st_size,
                'sha256': sha256(path),
            })
    return rows


def find_exact_file(search_root: Path, filename: str, expected_sha256: str, override_env: str) -> Path:
    override = os.environ.get(override_env)
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).resolve())
    direct = search_root / filename
    if direct.is_file():
        candidates.append(direct)
    if search_root.exists():
        candidates.extend(p for p in search_root.rglob(filename) if p.is_file())
    seen: set[Path] = set()
    matches: list[Path] = []
    for p in candidates:
        try:
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            if sha256(rp) == expected_sha256:
                matches.append(rp)
        except OSError:
            continue
    if not matches:
        raise RuntimeError(f'exact source ZIP not found: {filename} sha256={expected_sha256}')
    return sorted(matches, key=lambda p: (len(p.parts), str(p)))[0]


def verify_zip_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    got = sha256(path)
    if got != expected_sha256:
        raise RuntimeError(f'outer SHA256 mismatch for {path}: {got}')
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC failure in {path}: {bad}')
        names = set(zf.namelist())
        if 'SHA256SUMS.txt' not in names:
            raise RuntimeError(f'missing SHA256SUMS.txt: {path}')
        manifest = zf.read('SHA256SUMS.txt').decode('utf-8').splitlines()
        count = 0
        for line in manifest:
            if not line.strip():
                continue
            expected, member = line.split(None, 1)
            member = member.strip()
            if member not in names:
                raise RuntimeError(f'manifest member missing in {path}: {member}')
            observed = bytes_sha256(zf.read(member))
            if observed != expected:
                raise RuntimeError(f'internal SHA256 mismatch in {path}: {member}')
            count += 1
        return {'outer_sha256': got, 'entry_count': len(zf.infolist()), 'manifest_verified_count': count}


def read_zip_member(path: Path, member: str) -> bytes:
    with zipfile.ZipFile(path) as zf:
        return zf.read(member)


def make_zip(out: Path, zip_path: Path) -> None:
    lines = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != 'SHA256SUMS.txt':
            lines.append(f'{sha256(p)}  {p.name}')
    (out / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(out.iterdir()):
            if p.is_file():
                zf.write(p, p.name)
    Path(str(zip_path) + '.sha256').write_text(f'{sha256(zip_path)}  {zip_path.name}\n', encoding='utf-8')
