#!/usr/bin/env python3
"""
Convert LiPD zip archive to cfr.ProxyDatabase pickle.

Reads .lpd files from a zip archive, extracts proxy time series via pylipd
SPARQL queries, maps archive type + standard name to CFR proxy types, converts
seasonality strings to CFR month lists, and saves a cfr.ProxyDatabase pickle.

Based on LinkedEarth notebook C01_c_db_assembly_LiPDverse.ipynb.

Usage:
    python lipd_to_pdb.py <lipd_files.zip> <output_lipd_cfr.pkl>
"""

import sys
import os
import re
import math
import pickle
import zipfile
import tempfile

import numpy as np
import pandas as pd
from pylipd.lipd import LiPD
import cfr


# ── Proxy type mapping ────────────────────────────────────────────────────────
# (archive_lower, standard_name_lower) → cfr ptype string
PTYPE_MAP = {
    ('tree',            'trw'):                      'tree.TRW',
    ('tree',            'tree ring width'):           'tree.TRW',
    ('tree',            'ringwidth'):                 'tree.TRW',
    ('tree',            'mxd'):                       'tree.MXD',
    ('tree',            'maximum latewood density'):  'tree.MXD',
    ('coral',           'd18o'):                      'coral.d18O',
    ('coral',           'srca'):                      'coral.SrCa',
    ('coral',           'calcification'):             'coral.calc',
    ('sclerosponge',    'd18o'):                      'sclerosponge.d18O',
    ('sclerosponge',    'srca'):                      'sclerosponge.SrCa',
    ('ice core',        'd18o'):                      'ice.d18O',
    ('ice core',        'dd'):                        'ice.dD',
    ('ice core',        'melt'):                      'ice.melt',
    ('ice core',        'accumulation'):              'ice.accumulation',
    ('lake sediment',   'varve_thickness'):           'lake.varve_thickness',
    ('lake sediment',   'varve_property'):            'lake.varve_property',
    ('lake sediment',   'chironomid'):                'lake.chironomid',
    ('lake sediment',   'midge'):                     'lake.midge',
    ('lake sediment',   'reflectance'):               'lake.reflectance',
    ('lake sediment',   'bsi'):                       'lake.BSi',
    ('lake sediment',   'accumulation'):              'lake.accumulation',
    ('marine sediment', 'alkenone'):                  'marine.alkenone',
    ('marine sediment', 'uk37'):                      'marine.alkenone',
    ('marine sediment', 'mgca'):                      'marine.MgCa',
    ('marine sediment', 'tex86'):                     'marine.other',
    ('marine sediment', 'temperature'):               'marine.other',
    ('borehole',        'temperature'):               'borehole',
    ('speleothem',      'd18o'):                      'speleothem.d18O',
    ('documents',       'temperature'):               'documents',
    ('bivalve',         'd18o'):                      'bivalve.d18O',
}

ARCHIVE_DEFAULTS = {
    'tree':             'tree.TRW',
    'coral':            'coral.d18O',
    'ice core':         'ice.d18O',
    'lake sediment':    'lake.other',
    'marine sediment':  'marine.other',
    'speleothem':       'speleothem.d18O',
    'borehole':         'borehole',
    'documents':        'documents',
    'sclerosponge':     'sclerosponge.d18O',
    'bivalve':          'bivalve.d18O',
    'hybrid':           'hybrid',
}


def create_ptype(archive_type, standard_name):
    arch = str(archive_type or '').lower().strip()
    std  = str(standard_name  or '').lower().strip()
    key  = (arch, std)
    if key in PTYPE_MAP:
        return PTYPE_MAP[key]
    # Partial match: same archive, standard_name contains a known key
    for (a, s), ptype in PTYPE_MAP.items():
        if a == arch and s and s in std:
            return ptype
    return ARCHIVE_DEFAULTS.get(arch, f'{arch}.unknown')


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

    nh = (latitude is None) or (float(latitude) >= 0)  # northern hemisphere by default

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

    # Month range: "Jun-Aug", "June–August"
    m = re.match(r'([a-z]+)[^a-z]+([a-z]+)', s)
    if m:
        m1, m2 = MONTH_ABBR.get(m.group(1)), MONTH_ABBR.get(m.group(2))
        if m1 and m2:
            return list(range(m1, m2 + 1)) if m1 <= m2 else list(range(m1, 13)) + list(range(1, m2 + 1))

    # Numeric list: "1 2 3" or "6,7,8" or negative SH convention
    nums = re.findall(r'-?\d+', s)
    if nums:
        months = [abs(int(n)) for n in nums if 1 <= abs(int(n)) <= 12]
        if months:
            return months

    # Single month name
    if s in MONTH_ABBR:
        return [MONTH_ABBR[s]]

    return ANNUAL


# ── SPARQL query ──────────────────────────────────────────────────────────────
SPARQL = """
PREFIX le:    <http://linked.earth/ontology#>
PREFIX wgs84: <http://www.w3.org/2003/01/geo/wgs84_pos#>

SELECT ?dataSetName ?archiveType ?geo_meanLat ?geo_meanLon ?geo_meanElev
       ?paleoData_variableName ?paleoData_standardName
       ?paleoData_proxy ?paleoData_proxyGeneral
       ?paleoData_seasonality ?paleoData_interpName ?paleoData_interpRank
       ?TSID ?paleoData_values ?paleoData_units
       ?time_variableName ?time_standardName ?time_values ?time_units
WHERE {
    ?ds a le:Dataset ;
        le:name ?dataSetName .

    OPTIONAL {
        ?ds le:collectedFrom ?geo .
        ?geo wgs84:lat  ?geo_meanLat ;
             wgs84:long ?geo_meanLon .
        OPTIONAL { ?geo wgs84:alt ?geo_meanElev }
    }
    OPTIONAL { ?ds le:proxyArchiveType ?archiveType }

    ?ds le:hasPaleoData / le:hasMeasurementTable ?table .
    ?table le:hasVariable ?var .
    ?var le:variableName ?paleoData_variableName ;
         le:hasValues    ?paleoData_values .

    OPTIONAL { ?var le:hasStandardVariable / le:name ?paleoData_standardName }
    OPTIONAL { ?var le:hasUnits / le:name ?paleoData_units }
    OPTIONAL { ?var le:TSID ?TSID }
    OPTIONAL { ?var le:proxy ?paleoData_proxy }
    OPTIONAL { ?var le:proxyGeneral ?paleoData_proxyGeneral }
    OPTIONAL { ?var le:seasonality ?paleoData_seasonality }
    OPTIONAL { ?var le:interpretation / le:name ?paleoData_interpName }
    OPTIONAL { ?var le:interpretation / le:rank ?paleoData_interpRank }

    ?table le:hasVariable ?timeVar .
    ?timeVar le:variableName ?time_variableName ;
             le:hasValues    ?time_values .
    OPTIONAL { ?timeVar le:hasStandardVariable / le:name ?time_standardName }
    OPTIONAL { ?timeVar le:hasUnits / le:name ?time_units }

    FILTER (?time_variableName IN ("year", "age", "Year", "Age", "yearCE", "ageBP", "ageKa"))
    FILTER (?paleoData_variableName != ?time_variableName)
    FILTER (?paleoData_variableName NOT IN ("depth", "Depth", "age", "year", "Age", "Year"))
}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def to_float_array(val):
    if val is None:
        return None
    try:
        arr = np.array(val, dtype=float)
        if arr.ndim == 0 or arr.size == 0 or not np.any(np.isfinite(arr)):
            return None
        return arr
    except (ValueError, TypeError):
        return None


def time_to_year_ce(arr, var_name, std_name):
    """Convert time axis to year CE. Age BP → 1950 − age; age ka → 1950 − age*1000."""
    v = str(var_name or '').lower()
    s = str(std_name  or '').lower()
    if 'ka' in v or 'ka' in s:
        return 1950.0 - arr * 1000.0
    if 'age' in v or 'age' in s or 'bp' in s:
        return 1950.0 - arr
    return arr  # already year CE


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
        n_files = sum(1 for f in os.listdir(tmpdir) if f.endswith('.lpd'))
        print(f"Extracted {n_files} .lpd files")

        print("\nLoading with pylipd ...")
        L = LiPD()
        L.load_from_dir(tmpdir)
        all_ds = L.get_all_dataset_names()
        print(f"Loaded {len(all_ds)} datasets")

        print("\nRunning SPARQL query ...")
        _, df = L.query(SPARQL)
        n_ds = df['dataSetName'].nunique() if 'dataSetName' in df.columns else '?'
        print(f"Query returned {len(df)} rows across {n_ds} datasets")

        if df.empty:
            raise RuntimeError(
                "SPARQL returned no rows — check ontology property paths against pylipd version"
            )

        print(f"Columns present: {list(df.columns)}")

    # ── Build ProxyDatabase ───────────────────────────────────────────────────
    pdb    = cfr.ProxyDatabase()
    n_ok   = 0
    n_skip = 0

    for _, row in df.iterrows():
        # Time
        t_raw = to_float_array(row.get('time_values'))
        if t_raw is None:
            n_skip += 1
            continue
        time_arr = time_to_year_ce(t_raw, row.get('time_variableName'), row.get('time_standardName'))

        # Values
        val_arr = to_float_array(row.get('paleoData_values'))
        if val_arr is None:
            n_skip += 1
            continue

        # Align lengths, remove NaNs, sort ascending
        n = min(len(time_arr), len(val_arr))
        time_arr, val_arr = time_arr[:n], val_arr[:n]
        mask = np.isfinite(time_arr) & np.isfinite(val_arr)
        if not mask.any():
            n_skip += 1
            continue
        time_arr, val_arr = time_arr[mask], val_arr[mask]
        idx = np.argsort(time_arr)
        time_arr, val_arr = time_arr[idx], val_arr[idx]

        # Coordinates
        try:
            lat  = float(row.get('geo_meanLat')  or 0)
            lon  = float(row.get('geo_meanLon')  or 0)
            elev = float(row.get('geo_meanElev') or 0)
        except (TypeError, ValueError):
            n_skip += 1
            continue

        # Proxy type — prefer paleoData_standardName, fall back to variableName
        ptype = create_ptype(
            row.get('archiveType'),
            row.get('paleoData_standardName') or row.get('paleoData_variableName'),
        )

        # Seasonality
        seasonality = convert_seasonality(row.get('paleoData_seasonality'), lat)

        # Record ID
        pid = str(row.get('TSID') or row.get('dataSetName') or f'record_{n_ok}')

        try:
            record = cfr.ProxyRecord(
                pid=pid,
                lat=lat, lon=lon, elev=elev,
                time=time_arr,
                value=val_arr,
                ptype=ptype,
                seasonality=seasonality,
                value_name=str(row.get('paleoData_variableName') or 'unknown'),
                value_unit=str(row.get('paleoData_units')        or 'unknown'),
            )
            pdb   += record
            n_ok  += 1
        except Exception as e:
            print(f"  Warning: ProxyRecord failed for {pid}: {e}")
            n_skip += 1

    print(f"\nProxy records: {n_ok} added, {n_skip} skipped")

    if n_ok == 0:
        raise RuntimeError("No proxy records were added — cannot produce a usable ProxyDatabase")

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
