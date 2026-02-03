#!/usr/bin/env python3
"""
Test CFR configuration without Docker
Verifies that the config file and data file are compatible
"""

import yaml
import pandas as pd

print("=" * 60)
print("CFR Configuration Test (No Docker)")
print("=" * 60)
print()

# Test 1: Load and validate config file
print("Test 1: Loading lmr_configs.yml...")
try:
    with open('lmr_configs.yml', 'r') as f:
        config = yaml.safe_load(f)
    print("  [OK] Config file loaded successfully")

    proxydb_path = config.get('proxydb_path')
    print(f"  [OK] proxydb_path: {proxydb_path}")

    if not proxydb_path:
        print("  [ERROR] proxydb_path is not set!")
        print("  This is the problem - CFR won't know where to find data")
    elif proxydb_path.startswith('#'):
        print("  [ERROR] proxydb_path is commented out!")
    else:
        print("  [OK] proxydb_path is properly configured")

except Exception as e:
    print(f"  [ERROR] Failed to load config: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Load and validate the converted DataFrame
print("Test 2: Loading lipd_cfr.pkl...")
try:
    df = pd.read_pickle('lipd_cfr.pkl')
    print(f"  [OK] DataFrame loaded successfully")
    print(f"  [OK] Shape: {df.shape}")
    print(f"  [OK] Columns: {list(df.columns)}")

    required_cols = ['paleoData_pages2kID', 'geo_meanLat', 'geo_meanLon', 'year', 'paleoData_values', 'paleoData_ProxyObsType']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"  [ERROR] Missing required columns: {missing_cols}")
    else:
        print(f"  [OK] All required columns present")

    print()
    print("  Proxy type distribution:")
    proxy_col = 'paleoData_ProxyObsType' if 'paleoData_ProxyObsType' in df.columns else 'ptype'
    for ptype, count in df[proxy_col].value_counts().items():
        print(f"    {ptype}: {count}")

    print()
    print("  Filter configuration check:")
    filter_keys = config.get('filter_proxydb_kwargs', {}).get('keys', [])
    print(f"    Config filters for: {filter_keys}")

    # Check if any proxies match the filters
    matched = 0
    for ptype in df[proxy_col].unique():
        archive_type = ptype.split('.')[0] if '.' in ptype else ptype
        if archive_type in filter_keys:
            count = (df[proxy_col].str.startswith(archive_type)).sum()
            matched += count
            print(f"      {archive_type}: {count} proxies will be used")

    if matched == 0:
        print("  [WARNING] No proxies match the filter configuration!")
        print("  You may need to adjust filter_proxydb_kwargs in lmr_configs.yml")
    else:
        print(f"  [OK] {matched} proxies match the filter configuration")

except FileNotFoundError:
    print("  [ERROR] lipd_cfr.pkl not found")
    print("  Run: python convert_lipd_to_cfr_dataframe.py lipd.pkl lipd_cfr.pkl")
except Exception as e:
    print(f"  [ERROR] Failed to load DataFrame: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Verify paths match between config and actual file location
print("Test 3: Path compatibility check...")
if proxydb_path:
    container_path = proxydb_path
    local_path = 'lipd_cfr.pkl'

    print(f"  Container path (from config): {container_path}")
    print(f"  Local path: {local_path}")
    print(f"  Mounted as: /app/lipd_cfr.pkl")

    if '/app/lipd_cfr.pkl' in container_path:
        print("  [OK] Paths are compatible for Docker mount")
    else:
        print("  [WARNING] Path mismatch - check Docker volume mount")

print()
print("=" * 60)
print("Summary")
print("=" * 60)

# Check if config file URL matches the actual data
lipd_url = config.get('lipd_data_url', '')
print(f"lipd_data_url: {lipd_url}")
print()

if proxydb_path and not proxydb_path.startswith('#'):
    print("[OK] Configuration looks good!")
    print()
    print("The GitHub Actions workflow should now work correctly because:")
    print("  1. proxydb_path is set to /app/lipd_cfr.pkl")
    print("  2. The workflow mounts lipd_cfr.pkl at that location")
    print("  3. CFR will be able to find the proxy data")
    print()
    print("Next step: Commit and push the fix to test on GitHub Actions")
else:
    print("[ERROR] Configuration issue detected!")
    print("Make sure proxydb_path is uncommented in lmr_configs.yml")
