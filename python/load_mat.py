"""Loaders for MATLAB .mat files used by Slith3r-MM."""

from __future__ import annotations

import numpy as np
import scipy.io as sio


def load_angles_mat(path: str) -> list[dict]:
    """Load ANGLES from a .mat file into a list of layer dicts.

    Handles both:
    - Standalone ANGLES.mat  (struct with fields X, Y, U, V)
    - Combined .mat          (same, possibly multi-layer struct array)
    """
    raw = sio.loadmat(path, squeeze_me=False)

    # Find the ANGLES variable (key search, case-insensitive)
    key = next((k for k in raw if k.upper() == 'ANGLES' and not k.startswith('_')), None)
    if key is None:
        raise KeyError(f"No 'ANGLES' variable found in {path}")

    A = raw[key]

    # MATLAB struct array: shape (1, nLayers) with dtype.names = ('X','Y','U','V')
    if A.dtype.names is None:
        raise ValueError(f"ANGLES variable in {path} is not a struct array")

    n_layers = A.shape[1] if A.ndim > 1 else 1
    layers = []
    for i in range(n_layers):
        idx = (0, i) if A.ndim > 1 else (0,)
        layers.append({
            'X': np.asarray(A['X'][idx], dtype=float),
            'Y': np.asarray(A['Y'][idx], dtype=float),
            'U': np.asarray(A['U'][idx], dtype=float),
            'V': np.asarray(A['V'][idx], dtype=float),
        })
    return layers


def load_prt_opt_mat(path: str) -> dict:
    """Extract prtOpt from a combined .mat file into a plain Python dict."""
    raw = sio.loadmat(path, squeeze_me=True)
    key = next((k for k in raw if k.lower() == 'prtopt' and not k.startswith('_')), None)
    if key is None:
        return {}

    P = raw[key]
    result = {}
    for f in P.dtype.names:
        v = P[f].item() if P[f].ndim == 0 else P[f].flat[0]
        # Convert numpy types
        if hasattr(v, 'item'):
            try:
                v = v.item()
            except Exception:
                pass
        if isinstance(v, (bytes, np.bytes_)):
            v = v.decode()
        result[f] = v
    return result


def load_mesh_mat(path: str) -> dict:
    """Load mesh_data .mat file with centroids and element IDs.

    Returns dict with:
        centroids   : (N, 2) float array in physical coordinates
        bamboo_ids  : integer indices of bamboo elements (0-based)
        carbon_ids  : integer indices of carbon elements (0-based)
    """
    raw = sio.loadmat(path, squeeze_me=True)
    centroids = np.asarray(raw['centroids'], dtype=float)
    n_total = len(centroids)

    # Try common field names
    if 'bamboo_ids' in raw and 'carbon_ids' in raw:
        b_ids = np.asarray(raw['bamboo_ids'], dtype=int).ravel() - 1  # MATLAB 1-based
        c_ids = np.asarray(raw['carbon_ids'], dtype=int).ravel() - 1
    elif 'density_ids' in raw:
        # density_ids = bamboo (high density material); carbon = everything else
        b_ids = np.asarray(raw['density_ids'], dtype=int).ravel() - 1
        all_ids = np.arange(n_total)
        c_ids = np.setdiff1d(all_ids, b_ids)
    else:
        raise KeyError(f"Cannot find bamboo/carbon ID arrays in {path}")

    return {
        'centroids':  centroids,
        'bamboo_ids': b_ids,
        'carbon_ids': c_ids,
        'bamboo_pts': centroids[b_ids],
        'carbon_pts': centroids[c_ids],
    }
