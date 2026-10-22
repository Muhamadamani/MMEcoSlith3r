"""Generate example angle fields (port of angleFieldINPUT.m examples).

Each function returns a dict with keys 'X', 'Y', 'U', 'V' and physical
dimensions (dimx, dimy).
"""

import numpy as np


def _grid(dimx: float, dimy: float, scale: float = 1.0):
    Nx = int(dimx / scale)
    Ny = int(dimy / scale)
    x  = np.linspace(-dimx / 2, dimx / 2, Nx)
    y  = np.linspace(-dimy / 2, dimy / 2, Ny)
    X, Y = np.meshgrid(x, y)
    return X, Y


def vortex(dimx: float = 30, dimy: float = 30, S: float = 1.0, V: float = -3.0):
    X, Y = _grid(dimx, dimy)
    Z = X + 1j * Y
    W = (S + 1j * V) / (2 * np.pi * Z)
    U = np.real(W)
    Vf = -np.imag(W)
    return {'X': X, 'Y': Y, 'U': U, 'V': Vf}, dimx, dimy


def radial(dimx: float = 30, dimy: float = 30, D: float = 1.0, V: float = 0.0):
    X, Y = _grid(dimx, dimy)
    Z = X + 1j * Y
    W = (D - 1j * V) / (2 * np.pi * Z)
    U = np.real(W)
    Vf = -np.imag(W)
    return {'X': X, 'Y': Y, 'U': U, 'V': Vf}, dimx, dimy


def hyperbolic(dimx: float = 30, dimy: float = 30):
    X, Y = _grid(dimx, dimy)
    W = X + 1j * Y
    U = np.real(W)
    Vf = -np.imag(W)
    return {'X': X, 'Y': Y, 'U': U, 'V': Vf}, dimx, dimy


def figure1(dimx: float = 30, dimy: float = 30, a: float = 1.0):
    X, Y = _grid(dimx, dimy)
    lam = dimy / 3
    W = a * (np.cos(X / lam) + 1j * np.cos(Y / lam))
    U = np.real(W)
    Vf = -np.imag(W)
    return {'X': X, 'Y': Y, 'U': U, 'V': Vf}, dimx, dimy


def uniform(dimx: float = 30, dimy: float = 30, angle_deg: float = 0.0):
    """Uniform direction field — useful for simple test cases."""
    X, Y = _grid(dimx, dimy)
    theta = np.deg2rad(angle_deg)
    U = np.full_like(X, np.cos(theta))
    Vf = np.full_like(Y, np.sin(theta))
    return {'X': X, 'Y': Y, 'U': U, 'V': Vf}, dimx, dimy


def orthogonal(angles: dict) -> dict:
    """Return the flow field orthogonal to *angles* (rotate 90°)."""
    return {
        'X': angles['X'],
        'Y': angles['Y'],
        'U': -angles['V'],
        'V':  angles['U'],
    }
