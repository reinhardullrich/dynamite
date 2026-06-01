import numpy as np
from astropy import table

from conftest import DEV_TESTS_DIR
from dynamite.myrand import MyRand


def test_saved_random_sequence_matches_python_myrand():
    saved = np.loadtxt(DEV_TESTS_DIR / "data" / "randata-4242.txt")
    rng = MyRand(-4242)
    generated = np.array([rng.ran1() for _ in range(saved.size)])
    np.testing.assert_allclose(generated, saved, rtol=0.0, atol=1e-15)


def test_reference_losvd_fixture_contract():
    fixture = np.load(DEV_TESTS_DIR / "data" / "comparison_losvd.npz")
    xedg = fixture["xedg"]
    y = fixture["y"]

    assert xedg.shape == (204,)
    assert y.shape == (72, 203, 152)
    assert np.all(np.isfinite(xedg))
    assert np.all(np.isfinite(y))
    assert np.all(y >= 0.0)
    assert np.all(np.diff(xedg) > 0.0)


def test_nnls_chi2_reference_fixture_contract():
    ref = table.Table.read(
        DEV_TESTS_DIR / "data" / "chi2_compare_ml_654.dat",
        format="ascii",
    )
    assert list(ref.colnames) == ["model_id", "chi2", "kinchi2", "kinmapchi2"]
    assert len(ref) == 3
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        assert np.all(np.isfinite(ref[column]))
        assert np.all(ref[column] > 0.0)

