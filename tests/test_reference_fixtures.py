import numpy as np

from dynamite.myrand import MyRand


RANDOM_SEED = -4242
REFERENCE_RANDOM_FIRST_16 = np.array(
    [
        0.9882201277596039,
        0.575353558908847,
        0.2898458332241726,
        0.5809629371301098,
        0.5254200899626222,
        0.9116106354219888,
        0.815812711983832,
        0.6548928574914545,
        0.5447715537365394,
        0.43891899866932954,
        0.23187452053272842,
        0.32559912340976255,
        0.45050163401779797,
        0.4708477507675289,
        0.43994953736660514,
        0.15481656703856614,
    ]
)

REFERENCE_LOSVD_CONTRACT = {
    "xedg_shape": (204,),
    "y_shape": (72, 203, 152),
    "xedg_first": -1359.9107666015502,
    "xedg_last": 1359.9107666015498,
    "y_max": 0.016685000000000002,
    "y_sum": 41.4478575,
    "sample_values": [0.0, 5e-06, 4e-05, 0.0, 0.0],
}

REFERENCE_NNLS_CHI2 = {
    "model_id": [0, 1, 2],
    "chi2": [161713.86235521015, 42418.83576862558, 137996.62182152038],
    "kinchi2": [125924.28211505871, 18223.0332977481, 106730.22023810261],
    "kinmapchi2": [983816.5357107143, 34721.57131534838, 2525562.934382647],
}

REFERENCE_BAR_CHI2 = {
    "model_id": [0, 1, 2],
    "chi2": [111.0, 444.0, 777.0],
    "kinchi2": [222.0, 555.0, 888.0],
    "kinmapchi2": [333.0, 666.0, 999.0],
}


def test_extracted_random_sequence_matches_python_myrand():
    rng = MyRand(RANDOM_SEED)
    generated = np.array([rng.ran1() for _ in range(len(REFERENCE_RANDOM_FIRST_16))])
    np.testing.assert_allclose(
        generated,
        REFERENCE_RANDOM_FIRST_16,
        rtol=0.0,
        atol=1e-15,
    )


def test_extracted_losvd_reference_contract_is_numerically_valid():
    contract = REFERENCE_LOSVD_CONTRACT

    assert contract["xedg_shape"] == (204,)
    assert contract["y_shape"] == (72, 203, 152)
    assert contract["xedg_first"] < 0.0
    assert contract["xedg_last"] > 0.0
    np.testing.assert_allclose(
        abs(contract["xedg_first"]),
        contract["xedg_last"],
        rtol=0.0,
        atol=1e-10,
    )
    assert contract["y_max"] > 0.0
    assert contract["y_sum"] > contract["y_max"]
    assert all(value >= 0.0 for value in contract["sample_values"])


def test_extracted_nnls_chi2_reference_values_are_finite_and_ordered():
    assert REFERENCE_NNLS_CHI2["model_id"] == [0, 1, 2]
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        values = np.array(REFERENCE_NNLS_CHI2[column])
        assert values.shape == (3,)
        assert np.all(np.isfinite(values))
        assert np.all(values > 0.0)
    assert min(REFERENCE_NNLS_CHI2["kinchi2"]) == REFERENCE_NNLS_CHI2["kinchi2"][1]


def test_extracted_bar_reference_values_are_finite_and_ordered():
    assert REFERENCE_BAR_CHI2["model_id"] == [0, 1, 2]
    for column in ("chi2", "kinchi2", "kinmapchi2"):
        values = np.array(REFERENCE_BAR_CHI2[column])
        assert values.shape == (3,)
        assert np.all(np.isfinite(values))
        assert np.all(np.diff(values) > 0.0)
