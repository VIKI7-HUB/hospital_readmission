import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
n = 20000
pat = rng.integers(0, 14000, n)
_latent = rng.normal(size=n)
_p_true = 1 / (1 + np.exp(-(_latent * 0.6 - 2.2)))
y = (rng.random(n) < _p_true).astype(int)
raw = np.clip(_p_true * 2.2 + rng.normal(0, 0.03, n), 0.001, 0.99)


def frame() -> pd.DataFrame:
    g = rng.choice(["A", "B", "C"], size=n, p=[0.6, 0.38, 0.02])
    return pd.DataFrame({"y_true": y, "p_cal": raw, "grp": g, "patient_nbr": pat})
