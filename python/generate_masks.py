"""Generate bamboo and carbon B&W mask images from topology-optimisation data.

Supports:
  - .mat file with 'centroids' + 'density_ids' (bamboo element indices)
  - .vtu file (VTK unstructured grid with 'density' cell data per material)

Output masks: white = material present, black = void.
The physical domain is derived from centroid extents or the ANGLES field.
"""

from __future__ import annotations

import struct, zlib
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, generate_binary_structure


def _voronoi_masks(
    pts_a: np.ndarray, pts_b: np.ndarray,
    x_range: tuple, y_range: tuple,
    img_w: int, img_h: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Assign each image pixel to material A or B by nearest-centroid (Voronoi).

    Returns two bool masks (mask_a, mask_b) with mask_a | mask_b == True everywhere.
    No dilation needed — the two masks partition the domain cleanly.
    """
    from scipy.spatial import KDTree

    x_min, x_max = x_range
    y_min, y_max = y_range
    Lx, Ly = x_max - x_min, y_max - y_min

    # Build pixel grid in physical coordinates
    cols = np.linspace(x_min, x_max, img_w)
    rows = np.linspace(y_max, y_min, img_h)  # flipped: row 0 = top = high Y
    gx, gy = np.meshgrid(cols, rows)          # (img_h, img_w)
    pixels = np.column_stack([gx.ravel(), gy.ravel()])  # (img_h*img_w, 2)

    # KDTree query: which centroid (A or B) is nearer?
    tree_a = KDTree(pts_a)
    tree_b = KDTree(pts_b)
    dist_a, _ = tree_a.query(pixels, k=1)
    dist_b, _ = tree_b.query(pixels, k=1)

    is_a = (dist_a <= dist_b).reshape(img_h, img_w)
    return is_a, ~is_a


def _rasterize_with_dilation(pts: np.ndarray, x_range: tuple, y_range: tuple,
                              img_w: int, img_h: int, dilation_mm: float) -> np.ndarray:
    """Render point cloud to binary image with physically-isotropic dilation.

    Use this only when the point cloud does NOT cover the full domain
    (e.g. material elements that exclude void regions).
    """
    x_min, x_max = x_range
    y_min, y_max = y_range
    Lx = x_max - x_min
    Ly = y_max - y_min

    col = np.clip(np.round((pts[:, 0] - x_min) / Lx * (img_w - 1)).astype(int), 0, img_w - 1)
    row = np.clip((img_h - 1) - np.round((pts[:, 1] - y_min) / Ly * (img_h - 1)).astype(int),
                  0, img_h - 1)

    bw = np.zeros((img_h, img_w), dtype=bool)
    bw[row, col] = True

    px_per_mm_x = (img_w - 1) / Lx
    px_per_mm_y = (img_h - 1) / Ly
    rx = max(1, int(round(dilation_mm * px_per_mm_x)))
    ry = max(1, int(round(dilation_mm * px_per_mm_y)))
    yy, xx = np.ogrid[-ry:ry + 1, -rx:rx + 1]
    kernel = ((xx / rx) ** 2 + (yy / ry) ** 2) <= 1.0
    from scipy.ndimage import binary_dilation as _bd
    return _bd(bw, structure=kernel)


# ─── .mat reader ────────────────────────────────────────────────────────────

def _auto_img_size(x_range: tuple, y_range: tuple, px_per_mm: int = 20) -> tuple[int, int]:
    """Return (width, height) in pixels for a given physical domain at px_per_mm resolution."""
    Lx = x_range[1] - x_range[0]
    Ly = y_range[1] - y_range[0]
    return (int(round(Lx * px_per_mm)), int(round(Ly * px_per_mm)))


def masks_from_mat(
    mat_path: str,
    x_range: tuple | None = None,
    y_range: tuple | None = None,
    img_size: tuple[int, int] | None = None,
    dilation_mm: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (bamboo_mask, carbon_mask) bool arrays from a .mat mesh file.

    The mat file must have:
      centroids   : (N, 2) all element centroids
      density_ids : 1-based indices of bamboo elements

    Returns
    -------
    bamboo_mask, carbon_mask : (img_h, img_w) bool arrays.
    """
    import scipy.io as sio
    m = sio.loadmat(mat_path)
    cents = m['centroids']                       # (N, 2)
    bam_ids = m['density_ids'].ravel() - 1       # 0-indexed

    all_ids = np.arange(len(cents))
    cf_ids  = np.setdiff1d(all_ids, bam_ids)

    bam_pts = cents[bam_ids]
    cf_pts  = cents[cf_ids]

    if x_range is None:
        x_range = (cents[:, 0].min(), cents[:, 0].max())
    if y_range is None:
        y_range = (cents[:, 1].min(), cents[:, 1].max())

    if img_size is None:
        img_size = _auto_img_size(x_range, y_range, px_per_mm=20)
    img_w, img_h = img_size

    # If all elements together cover the full domain (full-density beam), use
    # Voronoi partitioning: each pixel goes to whichever material is nearer.
    # Otherwise fall back to dilation-based rasterization for sparse regions.
    full_coverage = (len(bam_pts) + len(cf_pts)) == len(cents)
    if full_coverage:
        print("  Using Voronoi partitioning (full-density mesh) …", flush=True)
        bam_mask, cf_mask = _voronoi_masks(
            bam_pts, cf_pts, x_range, y_range, img_w, img_h
        )
    else:
        bam_mask = _rasterize_with_dilation(bam_pts, x_range, y_range, img_w, img_h, dilation_mm)
        cf_mask  = _rasterize_with_dilation(cf_pts,  x_range, y_range, img_w, img_h, dilation_mm)

    return bam_mask, cf_mask


# ─── .vtu reader ────────────────────────────────────────────────────────────

def _parse_vtu_binary(path: str) -> dict:
    """Parse a binary-appended, zlib-compressed VTU file.

    Returns dict with numpy arrays: 'points', 'connectivity', 'offsets',
    'types', and any CellData arrays by name.
    """
    raw = Path(path).read_bytes()

    # Split XML header from binary payload
    sep = raw.find(b'<AppendedData encoding="raw">')
    if sep < 0:
        raise ValueError("Cannot find AppendedData section in VTU file")
    # Binary payload starts after the underscore marker
    payload_start = raw.index(b'_', sep) + 1
    payload = raw[payload_start:]

    # Build valid XML from the header only (everything before <AppendedData>),
    # then close the root element.  Do NOT add </VTKFile> twice.
    import xml.etree.ElementTree as ET
    xml_str = raw[:sep].decode('utf-8', errors='replace') + '</VTKFile>'
    root = ET.fromstring(xml_str)
    piece = root.find('.//Piece')
    n_pts   = int(piece.attrib['NumberOfPoints'])
    n_cells = int(piece.attrib['NumberOfCells'])

    def read_block(offset: int) -> np.ndarray:
        """Read one zlib-compressed block at *offset* in the payload."""
        # Header: 8-byte uint64 = compressed size, 8-byte uint64 = uncompressed size
        pos = offset
        # VTK uses a 4-field header when compressor is active: nBlocks, blockSize, lastBlockSize, compressedSizes
        # Simplified: for single-block, first 4 uint64s then data
        n_blocks, = struct.unpack_from('<Q', payload, pos); pos += 8
        block_size, = struct.unpack_from('<Q', payload, pos); pos += 8
        last_size, = struct.unpack_from('<Q', payload, pos); pos += 8
        comp_sizes = []
        for _ in range(n_blocks):
            sz, = struct.unpack_from('<Q', payload, pos); pos += 8
            comp_sizes.append(sz)
        data = b''
        for sz in comp_sizes:
            data += zlib.decompress(payload[pos:pos+sz])
            pos += sz
        return data

    def da_array(da, n) -> np.ndarray:
        offset = int(da.attrib['offset'])
        raw_data = read_block(offset)
        dt_map = {'Float64': np.float64, 'Float32': np.float32,
                  'Int64': np.int64, 'Int32': np.int32, 'UInt8': np.uint8}
        dt = dt_map[da.attrib['type']]
        nc = int(da.attrib.get('NumberOfComponents', 1))
        return np.frombuffer(raw_data, dtype=dt).reshape(n, nc).squeeze()

    result = {}

    pts_da = piece.find('Points/DataArray')
    result['points'] = da_array(pts_da, n_pts)[:, :2]  # drop Z

    for da in piece.find('Cells'):
        if da.attrib['Name'] == 'connectivity':
            result['connectivity'] = da_array(da, -1)
        elif da.attrib['Name'] == 'offsets':
            result['offsets'] = da_array(da, n_cells)

    for da in piece.find('CellData'):
        result[da.attrib['Name']] = da_array(da, n_cells)

    return result


def masks_from_vtu(
    vtu_path: str,
    material_key: str = 'density',
    threshold: float = 0.5,
    x_range: tuple | None = None,
    y_range: tuple | None = None,
    img_size: tuple[int, int] | None = None,
    dilation_mm: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (material1_mask, material2_mask) from a two-material VTU file.

    The VTU must have a per-cell scalar field named *material_key*.
    Cells with value > threshold go to material1; the rest go to material2.

    Returns
    -------
    mat1_mask, mat2_mask : (img_h, img_w) bool arrays.
    """
    data = _parse_vtu_binary(vtu_path)
    pts  = data['points']          # node coordinates
    offsets = data['offsets']      # end-index of each cell in connectivity
    conn    = data['connectivity'] # flat node-index list
    dens    = data[material_key]   # per-cell scalar

    # Compute cell centroids from connectivity / offsets
    starts = np.concatenate([[0], offsets[:-1]])
    centroids = np.array([
        pts[conn[s:e]].mean(axis=0)
        for s, e in zip(starts, offsets)
    ])

    if x_range is None:
        x_range = (centroids[:, 0].min(), centroids[:, 0].max())
    if y_range is None:
        y_range = (centroids[:, 1].min(), centroids[:, 1].max())

    if img_size is None:
        img_size = _auto_img_size(x_range, y_range, px_per_mm=20)
    mask1 = dens > threshold
    img_w, img_h = img_size

    m1 = _rasterize(centroids[mask1],  x_range, y_range, img_w, img_h, dilation_mm)
    m2 = _rasterize(centroids[~mask1], x_range, y_range, img_w, img_h, dilation_mm)

    return m1, m2


# ─── save helpers ────────────────────────────────────────────────────────────

def save_mask(mask: np.ndarray, path: str) -> None:
    """Save a bool mask to a greyscale PNG (white = True)."""
    img = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
    img.save(path)
    print(f"  Saved mask → {path}  ({mask.sum()} white px, {100*mask.mean():.1f}%)")


def generate_and_save(
    source_path: str,
    out_dir: str = '.',
    prefix: str = 'mask',
    img_size: tuple[int, int] = (4000, 4000),
    dilation_mm: float = 2.5,
    x_range: tuple | None = None,
    y_range: tuple | None = None,
) -> tuple[str, str]:
    """High-level helper: read source (.mat or .vtu), save two PNGs.

    Returns (mat1_path, mat2_path).
    """
    p = Path(source_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if p.suffix == '.mat':
        m1, m2 = masks_from_mat(source_path, x_range=x_range, y_range=y_range,
                                  img_size=img_size, dilation_mm=dilation_mm)
        names = ('bamboo', 'carbon')
    elif p.suffix == '.vtu':
        m1, m2 = masks_from_vtu(source_path, x_range=x_range, y_range=y_range,
                                  img_size=img_size, dilation_mm=dilation_mm)
        names = ('mat1', 'mat2')
    else:
        raise ValueError(f"Unsupported source: {p.suffix}")

    p1 = str(out / f'{prefix}_{names[0]}.png')
    p2 = str(out / f'{prefix}_{names[1]}.png')
    save_mask(m1, p1)
    save_mask(m2, p2)
    return p1, p2
