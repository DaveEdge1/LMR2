#!/usr/bin/env python3
"""
Convert LiPD zip archive to cfr.ProxyDatabase pickle.

Parses .lpd files directly as ZIP archives containing JSON-LD metadata.
No SPARQL or RDF ontology dependencies — works with any pylipd version.

Usage:
    python lipd_to_pdb.py <lipd_files.zip> <output_lipd_cfr.pkl>
"""

import sys
import os
import re
import math
import pickle
import zipfile
import json
import tempfile

import numpy as np
import cfr


# ── Proxy type mapping ────────────────────────────────────────────────────────
PTYPE_MAP = {
    ('tree',            'trw'):                      'tree.TRW',
    ('tree',            'tree ring width'):           'tree.TRW',
    ('tree',            'ringwidth'):                 'tree.TRW',
    ('tree',            'ring width'):                'tree.TRW',
    ('tree',            'mxd'):                       'tree.MXD',
    ('tree',            'maximum latewood density'):  'tree.MXD',
    ('wood',            'trw'):                       'tree.TRW',
    ('wood',            'ringwidth'):                 'tree.TRW',
    ('wood',            'ring width'):                'tree.TRW',
    ('wood',            'mxd'):                       'tree.MXD',
    ('coral',           'd18o'):                      'coral.d18O',
    ('coral',           'srca'):                      'coral.SrCa',
    ('coral',           'calcification'):             'coral.calc',
    ('sclerosponge',    'd18o'):                      'sclerosponge.d18O',
    ('sclerosponge',    'srca'):                      'sclerosponge.SrCa',
    ('ice core',        'd18o'):                      'ice.d18O',
    ('ice core',        'dd'):                        'ice.dD',
    ('ice core',        'd2h'):                       'ice.dD',
    ('ice core',        'melt'):                      'ice.melt',
    ('ice core',        'accumulation'):              'ice.accumulation',
    ('glacierice',      'd18o'):                      'ice.d18O',
    ('glacierice',      'dd'):                        'ice.dD',
    ('lake sediment',   'varve_thickness'):           'lake.varve_thickness',
    ('lake sediment',   'varve thickness'):           'lake.varve_thickness',
    ('lake sediment',   'varve_property'):            'lake.varve_property',
    ('lake sediment',   'chironomid'):                'lake.chironomid',
    ('lake sediment',   'midge'):                     'lake.midge',
    ('lake sediment',   'reflectance'):               'lake.reflectance',
    ('lake sediment',   'bsi'):                       'lake.BSi',
    ('lake sediment',   'accumulation'):              'lake.accumulation',
    ('lakesediment',    'chironomid'):                'lake.chironomid',
    ('lakesediment',    'reflectance'):               'lake.reflectance',
    ('lakesediment',    'bsi'):                       'lake.BSi',
    ('marine sediment', 'alkenone'):                  'marine.alkenone',
    ('marine sediment', 'uk37'):                      'marine.alkenone',
    ('marine sediment', 'mgca'):                      'marine.MgCa',
    ('marine sediment', 'mg/ca'):                     'marine.MgCa',
    ('marine sediment', 'tex86'):                     'marine.other',
    ('marine sediment', 'temperature'):               'marine.other',
    ('marinesediment',  'alkenone'):                  'marine.alkenone',
    ('marinesediment',  'uk37'):                      'marine.alkenone',
    ('marinesediment',  'mgca'):                      'marine.MgCa',
    ('borehole',        'temperature'):               'borehole',
    ('speleothem',      'd18o'):                      'speleothem.d18O',
    ('documents',       'temperature'):               'documents',
    ('bivalve',         'd18o'):                      'bivalve.d18O',
    ('molluskshell',    'd18o'):                      'bivalve.d18O',
}

ARCHIVE_DEFAULTS = {
    'tree':             'tree.TRW',
    'wood':             'tree.TRW',
    'coral':            'coral.d18O',
    'ice core':         'ice.d18O',
    'glacierice':       'ice.d18O',
    'lake sediment':    'lake.other',
    'lakesediment':     'lake.other',
    'marine sediment':  'marine.other',
    'marinesediment':   'marine.other',
    'speleothem':       'speleothem.d18O',
    'borehole':         'borehole',
    'documents':        'documents',
    'sclerosponge':     'sclerosponge.d18O',
    'bivalve':          'bivalve.d18O',
    'molluskshell':     'bivalve.d18O',
    'hybrid':           'hybrid',
    'peat':             'lake.other',
    'terrestrialsediment': 'lake.other',
}


def create_ptype(archive_type, standard_name):
    arch = str(archive_type or '').lower().strip().replace(' ', '')
    std  = str(standard_name  or '').lower().strip()
    # Try exact match with spaces removed from archive
    for (a, s), ptype in PTYPE_MAP.items():
        a_norm = a.replace(' ', '')
        if a_norm == arch and s == std:
            return ptype
    # Original space-aware lookup
    arch_sp = str(archive_type or '').lower().strip()
    key = (arch_sp, std)
    if key in PTYPE_MAP:
        return PTYPE_MAP[key]
    # Partial match: same archive, standard_name contains a known key
    for (a, s), ptype in PTYPE_MAP.items():
        a_norm = a.replace(' ', '')
        if (a == arch_sp or a_norm == arch) and s and s in std:
            return ptype
    return ARCHIVE_DEFAULTS.get(arch_sp, ARCHIVE_DEFAULTS.get(arch, f'{arch_sp}.unknown'))


# ── Seasonality conversion ────────────────────────────────────────────────────
MONTH_ABBR = {
    'jan': 1, 'feb': 2, 'mar': 3,  'apr': 4,  'may': 5,  'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9,  'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'june': 6, 'july': 7, 'august': 8, 'september': 9,
    'october': 10, 'november': 11, 'december': 12,
}

ANNUAL = list(range(1, 13))


def convert_seasonality(seasonality_str, latitude=None):
    if not seasonality_str or (isinstance(seasonality_str, float) and math.isnan(seasonality_str)):
        return ANNUAL
    s = str(seasonality_str).strip().lower()
    if not s or s in ('nan', 'none', 'annual', 'annual (all)', 'year-round'):
        return ANNUAL

    nh = (latitude is None) or (float(latitude) >= 0)

    named = {
        'summer':         [6, 7, 8]         if nh else [12, 1, 2],
        'winter':         [12, 1, 2]        if nh else [6, 7, 8],
        'spring':         [3, 4, 5]         if nh else [9, 10, 11],
        'fall':           [9, 10, 11]       if nh else [3, 4, 5],
        'autumn':         [9, 10, 11]       if nh else [3, 4, 5],
        'warm season':    [6, 7, 8]         if nh else [12, 1, 2],
        'cold season':    [12, 1, 2]        if nh else [6, 7, 8],
        'growing season': [4, 5, 6, 7, 8, 9] if nh else [10, 11, 12, 1, 2, 3],
        'djf': [12, 1, 2], 'mam': [3, 4, 5], 'jja': [6, 7, 8], 'son': [9, 10, 11],
    }
    if s in named:
        return named[s]

    m = re.match(r'([a-z]+)[^a-z]+([a-z]+)', s)
    if m:
        m1, m2 = MONTH_ABBR.get(m.group(1)), MONTH_ABBR.get(m.group(2))
        if m1 and m2:
            return list(range(m1, m2 + 1)) if m1 <= m2 else list(range(m1, 13)) + list(range(1, m2 + 1))

    nums = re.findall(r'-?\d+', s)
    if nums:
        months = [abs(int(n)) for n in nums if 1 <= abs(int(n)) <= 12]
        if months:
            return months

    if s in MONTH_ABBR:
        return [MONTH_ABBR[s]]

    return ANNUAL


def time_to_year_ce(arr, var_name):
    """Convert time axis to year CE. Age BP → 1950 − age; age ka → 1950 − age*1000."""
    v = str(var_name or '').lower()
    if 'ka' in v:
        return 1950.0 - arr * 1000.0
    if 'age' in v or 'bp' in v:
        return 1950.0 - arr
    return arr  # already year CE


# ── LiPD JSON helpers ─────────────────────────────────────────────────────────
# Variable names that indicate a time axis
_TIME_LOWER = {
    'year', 'age', 'yearce', 'agebp', 'ageka', 'yearad', 'year_ad', 'year_bp',
    'age_bp', 'age_ka', 'years', 'ages', 'time', 'yearrounded', 'yearb2k',
    'ybp', 'ka', 'yearensemble', 'ageoriginal', 'agemedian', 'agebchron',
    'agecopra', 'agebacon', 'agelinreg', 'agelininterp', 'ageoxcal',
}

# Variables that are metadata / non-proxy
_SKIP_LOWER = {
    'depth', 'depthtop', 'depthbottom', 'depthcomposite',
    'section', 'core', 'sampleid', 'notes', 'material',
    'deletethis', 'needstobechanged', 'latitude', 'longitude', 'elevation',
}


def _is_time(vname):
    v = vname.strip().lower().replace(' ', '').replace('-', '').replace('_', '')
    return (v in _TIME_LOWER or v.startswith('age') or v.startswith('year'))


def _is_skip(vname):
    v = vname.strip().lower()
    return v in _SKIP_LOWER or v.startswith('depth') or v.startswith('uncertainty')


def _str(val):
    """Flatten a possibly-nested {name: ...} JSON-LD object to a plain string."""
    if val is None:
        return ''
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        for k in ('name', '@value', 'label', '@id'):
            if k in val:
                s = val[k]
                if isinstance(s, str):
                    return s.strip()
                if isinstance(s, dict):
                    return _str(s)
    return str(val).strip()


def _get_values(col, lpd_zip):
    """
    Extract a numeric numpy array from a column dict.
    Handles inline 'values'/'hasValues' lists and external CSV files.
    """
    vals = col.get('values') or col.get('hasValues')
    if vals is not None and vals != 'None' and vals != '':
        try:
            arr = np.array(list(vals) if not isinstance(vals, list) else vals, dtype=float)
            if arr.ndim > 0 and arr.size > 0 and np.any(np.isfinite(arr)):
                return arr
        except (TypeError, ValueError):
            pass

    # External CSV (values stored in a separate file inside the ZIP)
    fname = col.get('filename')
    if fname:
        try:
            with lpd_zip.open(fname) as f:
                content = f.read().decode('utf-8', errors='replace')
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            if len(lines) < 2:
                return None
            col_idx = max(0, int(col.get('number', 1)) - 1)
            vals_out = []
            for line in lines[1:]:  # skip header row
                parts = line.split(',')
                try:
                    cell = parts[col_idx].strip() if col_idx < len(parts) else ''
                    vals_out.append(float(cell) if cell and cell.lower() != 'nan' else float('nan'))
                except ValueError:
                    vals_out.append(float('nan'))
            if vals_out:
                return np.array(vals_out, dtype=float)
        except Exception as e:
            pass

    return None


def _get_geo(data):
    """Extract (lat, lon, elev) from a LiPD dataset dict with multiple fallbacks."""
    lat = lon = elev = 0.0
    geo = data.get('geo') or data.get('collectedFrom') or {}

    # GeoJSON format: coordinates = [lon, lat, elev?]
    geom = geo.get('geometry', {}) if isinstance(geo, dict) else {}
    if isinstance(geom, dict):
        coords = geom.get('coordinates')
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            try:
                lon = float(coords[0])
                lat = float(coords[1])
                if len(coords) >= 3 and coords[2] is not None:
                    elev = float(coords[2])
                return lat, lon, elev
            except (TypeError, ValueError):
                pass

    # Properties dict (may be nested or flat)
    if isinstance(geo, dict):
        props = geo.get('properties') or geo
        if not isinstance(props, dict):
            props = geo

        for k in ('meanLat', 'latitude', 'lat', 'wgs84:lat'):
            if k in props:
                try: lat = float(props[k]); break
                except: pass
        for k in ('meanLon', 'longitude', 'lon', 'long', 'wgs84:long'):
            if k in props:
                try: lon = float(props[k]); break
                except: pass
        for k in ('meanElev', 'elevation', 'elev', 'altitude', 'alt', 'wgs84:alt'):
            if k in props:
                try: elev = float(props[k]); break
                except: pass

    return lat, lon, elev


def _get_archive(data):
    """Extract archive type string from a LiPD dataset dict."""
    for key in ('proxyArchiveType', 'archiveType', 'archive'):
        val = data.get(key)
        if val:
            s = _str(val)
            if s:
                return s.lower().strip()
    return ''


def _iter_columns(paleo_data):
    """
    Yield (column_dict) for every measurement column across all paleoData tables.
    Handles both list and dict forms of measurementTable / columns.
    """
    if isinstance(paleo_data, dict):
        paleo_data = list(paleo_data.values())
    for paleo in (paleo_data or []):
        if not isinstance(paleo, dict):
            continue
        tables = paleo.get('measurementTable') or paleo.get('measurementTables') or []
        if isinstance(tables, dict):
            tables = list(tables.values())
        elif not isinstance(tables, list):
            tables = [tables]
        for table in tables:
            if not isinstance(table, dict):
                continue
            cols = table.get('columns') or []
            if isinstance(cols, dict):
                cols = list(cols.values())
            yield from (c for c in cols if isinstance(c, dict))


def _parse_lpd(lpd_path):
    """
    Parse a single .lpd file (ZIP archive containing JSON-LD + optional CSVs).
    Returns list of dicts ready to become cfr.ProxyRecord objects.
    """
    records = []
    try:
        with zipfile.ZipFile(lpd_path, 'r') as lpd_zip:
            names = lpd_zip.namelist()

            # Find the main JSON/JSON-LD metadata file
            def _rank(n):
                n_lc = n.lower()
                if n_lc.endswith('.jsonld'):
                    return 0
                if n_lc.endswith('.json') and 'bagit' not in n_lc and 'metadata' not in n_lc:
                    return 1
                if n_lc.endswith('.json'):
                    return 2
                return 99

            json_files = sorted(
                [n for n in names if n.lower().endswith(('.json', '.jsonld'))
                 and not n.startswith('__')],
                key=_rank
            )
            if not json_files:
                return records

            with lpd_zip.open(json_files[0]) as f:
                data = json.load(f)

            ds_name = _str(data.get('dataSetName')) or os.path.splitext(os.path.basename(lpd_path))[0]
            lat, lon, elev = _get_geo(data)
            archive = _get_archive(data)

            # Group columns by their parent table (same JSON object → same table)
            # We walk paleoData tables one at a time so time/proxy pairing is correct.
            paleo_data = data.get('paleoData', [])
            if isinstance(paleo_data, dict):
                paleo_data = list(paleo_data.values())

            for paleo in (paleo_data or []):
                if not isinstance(paleo, dict):
                    continue
                tables = paleo.get('measurementTable') or paleo.get('measurementTables') or []
                if isinstance(tables, dict):
                    tables = list(tables.values())
                elif not isinstance(tables, list):
                    tables = [tables]

                for table in tables:
                    if not isinstance(table, dict):
                        continue
                    cols = table.get('columns') or []
                    if isinstance(cols, dict):
                        cols = list(cols.values())

                    time_cols   = []
                    proxy_cols  = []
                    for col in cols:
                        if not isinstance(col, dict):
                            continue
                        vname = _str(col.get('variableName'))
                        if not vname:
                            continue
                        if _is_time(vname):
                            time_cols.append((vname, col))
                        elif not _is_skip(vname):
                            proxy_cols.append((vname, col))

                    if not time_cols or not proxy_cols:
                        continue

                    # Pick the best time column (prefer 'year' variants over 'age')
                    time_arr  = None
                    time_vname = ''
                    for vn, tc in sorted(time_cols,
                                         key=lambda x: (0 if 'year' in x[0].lower() else 1)):
                        arr = _get_values(tc, lpd_zip)
                        if arr is not None and np.any(np.isfinite(arr)):
                            time_arr   = arr
                            time_vname = vn
                            break

                    if time_arr is None:
                        continue

                    time_ce = time_to_year_ce(time_arr, time_vname)

                    for vname, pc in proxy_cols:
                        val_arr = _get_values(pc, lpd_zip)
                        if val_arr is None:
                            continue

                        n = min(len(time_ce), len(val_arr))
                        t, v = time_ce[:n], val_arr[:n]
                        mask = np.isfinite(t) & np.isfinite(v)
                        if not mask.any():
                            continue
                        t, v = t[mask], v[mask]
                        idx = np.argsort(t)
                        t, v = t[idx], v[idx]

                        std_name   = _str(pc.get('standardVariable'))
                        proxy      = _str(pc.get('proxy') or pc.get('proxyGeneral'))
                        seasonality = _str(pc.get('seasonality'))
                        units      = _str(pc.get('units')) or 'unknown'

                        tsid = _str(pc.get('TSid') or pc.get('TSID') or pc.get('tsId'))
                        if not tsid:
                            tsid = f"{ds_name}.{vname}"

                        ptype = create_ptype(archive, std_name or proxy or vname)
                        seas  = convert_seasonality(seasonality, lat)

                        records.append({
                            'pid': tsid,
                            'lat': lat, 'lon': lon, 'elev': elev,
                            'time': t, 'value': v,
                            'ptype': ptype,
                            'seasonality': seas,
                            'value_name': vname,
                            'value_unit': units,
                        })

    except Exception as e:
        print(f"  Warning: failed to parse {os.path.basename(lpd_path)}: {e}")

    return records


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    zip_path    = sys.argv[1]
    output_path = sys.argv[2]
    print(f"Input:  {zip_path}")
    print(f"Output: {output_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nUnzipping {zip_path} ...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)

        lpd_files = sorted(
            os.path.join(tmpdir, f)
            for f in os.listdir(tmpdir)
            if f.lower().endswith('.lpd')
        )
        print(f"Found {len(lpd_files)} .lpd files")

        # Build ProxyDatabase
        pdb    = cfr.ProxyDatabase()
        n_ok   = 0
        n_skip = 0

        for lpd_path in lpd_files:
            recs = _parse_lpd(lpd_path)
            for rec in recs:
                try:
                    record = cfr.ProxyRecord(
                        pid=rec['pid'],
                        lat=rec['lat'], lon=rec['lon'], elev=rec['elev'],
                        time=rec['time'],
                        value=rec['value'],
                        ptype=rec['ptype'],
                        seasonality=rec['seasonality'],
                        value_name=rec['value_name'],
                        value_unit=rec['value_unit'],
                    )
                    pdb   += record
                    n_ok  += 1
                except Exception as e:
                    print(f"  Warning: ProxyRecord failed for {rec['pid']}: {e}")
                    n_skip += 1

    print(f"\nProxy records: {n_ok} added, {n_skip} skipped")

    if n_ok == 0:
        raise RuntimeError("No proxy records were added — check .lpd file structure")

    # Ptype breakdown
    ptypes = {}
    for pid, rec in pdb.records.items():
        ptypes[rec.ptype] = ptypes.get(rec.ptype, 0) + 1
    print("\nProxy type breakdown:")
    for pt, cnt in sorted(ptypes.items()):
        print(f"  {pt:<40} {cnt:>4} records")

    print(f"\nSaving ProxyDatabase to {output_path} ...")
    with open(output_path, 'wb') as fh:
        pickle.dump(pdb, fh, protocol=4)
    print("Done.")


if __name__ == '__main__':
    main()
