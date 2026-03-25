#!/usr/bin/env python3
"""
Convert LiPD pickle file to NetCDF format for CFR analysis.

Usage:
    python convert_pickle_to_netcdf.py <input_pickle_file> <output_netcdf_file>

Example:
    python convert_pickle_to_netcdf.py lipd.pkl lipd_cfr.nc
"""

import sys
import pickle
import xarray as xr
import pandas as pd
import numpy as np


def examine_pickle_structure(pkl_file):
    """Load and examine the structure of the pickle file."""
    print(f"Loading pickle file: {pkl_file}")
    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)

    print(f"\nPickle file type: {type(data)}")

    if isinstance(data, dict):
        print(f"Dictionary keys: {list(data.keys())[:10]}")
        if len(data.keys()) > 10:
            print(f"... and {len(data.keys()) - 10} more keys")
    elif isinstance(data, (list, tuple)):
        print(f"Length: {len(data)}")
        if len(data) > 0:
            print(f"First element type: {type(data[0])}")

    return data


def convert_to_netcdf(data, output_file):
    """Convert the pickle data to NetCDF format."""

    # Check if it's already an xarray Dataset
    if isinstance(data, xr.Dataset):
        print("Data is already an xarray Dataset")
        data.to_netcdf(output_file)
        print(f"Successfully saved to {output_file}")
        return

    # Check if it's a dictionary that can be converted to Dataset
    if isinstance(data, dict):
        print("Converting dictionary to xarray Dataset...")

        # Try to create Dataset from dictionary
        try:
            ds = xr.Dataset(data)
            ds.to_netcdf(output_file)
            print(f"Successfully saved to {output_file}")
            return
        except Exception as e:
            print(f"Direct conversion failed: {e}")
            print("\nAttempting custom conversion based on structure...")

            # Custom conversion for proxy database format
            # This is a common structure for CFR proxy databases
            if 'pid' in data or 'proxyid' in data or 'lat' in data:
                ds = convert_proxy_database(data)
                ds.to_netcdf(output_file)
                print(f"Successfully saved to {output_file}")
                return

    print("ERROR: Unable to automatically convert this pickle format.")
    print("Please examine the structure and create a custom conversion.")
    return None


def convert_proxy_database(data):
    """
    Convert a proxy database dictionary to xarray Dataset.
    Assumes data has structure like: {key: [values...]} where values are per-proxy.
    """
    print("Attempting proxy database conversion...")

    # Determine the number of proxies
    n_proxies = None
    for key, value in data.items():
        if isinstance(value, (list, np.ndarray)):
            n_proxies = len(value)
            break

    if n_proxies is None:
        raise ValueError("Could not determine number of proxies")

    print(f"Found {n_proxies} proxies")

    # Create coordinate
    proxy_dim = np.arange(n_proxies)

    # Convert each key to a DataArray
    data_vars = {}
    coords = {}

    for key, value in data.items():
        if isinstance(value, (list, np.ndarray)):
            # Handle different data types
            if isinstance(value, list):
                # Check if list contains strings
                if value and isinstance(value[0], str):
                    # Convert strings to object dtype
                    arr = np.array(value, dtype=object)
                else:
                    arr = np.array(value)
            else:
                arr = value

            # Create DataArray
            if len(arr.shape) == 1 and len(arr) == n_proxies:
                data_vars[key] = xr.DataArray(arr, dims=['proxy'])
            elif len(arr.shape) == 2:
                # 2D array, add time dimension
                data_vars[key] = xr.DataArray(arr, dims=['proxy', 'time'])

    # Create the Dataset
    ds = xr.Dataset(data_vars, coords={'proxy': proxy_dim})

    return ds


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        # Load and examine the pickle file
        data = examine_pickle_structure(input_file)

        print("\n" + "="*60)
        print("Attempting conversion to NetCDF...")
        print("="*60 + "\n")

        # Convert to NetCDF
        convert_to_netcdf(data, output_file)

        # Verify the output
        print("\n" + "="*60)
        print("Verifying output file...")
        print("="*60 + "\n")

        ds = xr.open_dataset(output_file)
        print("Successfully loaded NetCDF file!")
        print(f"\nDataset info:")
        print(ds)

    except FileNotFoundError:
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
