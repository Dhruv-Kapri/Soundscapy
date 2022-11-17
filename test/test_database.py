import pandas as pd
from pytest import approx
import pytest
import soundscapy
import soundscapy.surveys as db
from pytest import raises

basic_test_df = pd.DataFrame(
    {
        "RecordID": ["EX1", "EX2"],
        "PAQ1": [4, 2],
        "PAQ2": [4, 3],
        "PAQ3": [4, 5],
        "PAQ4": [2, 5],
        "PAQ5": [1, 5],
        "PAQ6": [3, 5],
        "PAQ7": [3, 3],
        "PAQ8": [4, 1],
    }
)

name_test_df = pd.DataFrame(
    {
        "RecordID": ["EX1", "EX2"],
        "pleasant": [4, 2],
        "vibrant": [4, 3],
        "eventful": [4, 5],
        "chaotic": [2, 5],
        "annoying": [1, 5],
        "monotonous": [3, 5],
        "uneventful": [3, 3],
        "calm": [4, 1],
    }
)


def test_load_isd_dataset_wrong_version():
    with raises(ValueError):
        df = soundscapy.isd.load_isd_dataset(version="v0.1.0")


def test_load_isd_dataset():
    df = soundscapy.isd.load_isd_dataset(version="v0.2.1")
    assert df.shape == (1909, 77)


def test_rename_descriptors():
    df = db.rename_paqs(name_test_df)
    assert df.columns.tolist() == [
        "RecordID",
        "PAQ1",
        "PAQ2",
        "PAQ3",
        "PAQ4",
        "PAQ5",
        "PAQ6",
        "PAQ7",
        "PAQ8"]


# write a test for db.rename_paqs that checks that the columns are renamed correctly
def test_rename_paqs():
    vals = {
        "RecordID": ["EX1", "EX2"],
        "pl": [4, 2],
        "ch": [4, 3],
        "ca": [4, 5],
        "v": [2, 5],
        "ev": [1, 5],
        "un": [3, 5],
        "ann": [3, 3],
        "m": [4, 1],
    }
    df = pd.DataFrame(vals)
    df = db.rename_paqs(df,
                        paq_aliases={"pl": "PAQ1", "ch": "PAQ4", "ca": "PAQ8", "v": "PAQ2", "ev": "PAQ3", "un": "PAQ7",
                                     "ann": "PAQ5", "m": "PAQ6"})
    assert df.columns.tolist() == [
        "RecordID",
        "PAQ1",
        "PAQ4",
        "PAQ8",
        "PAQ2",
        "PAQ3",
        "PAQ7",
        "PAQ5",
        "PAQ6"]


def test_calculate_paq_coords():
    coords = db.calculate_paq_coords(basic_test_df)
    assert coords[0][0] == approx(0.53, abs=0.05) and coords[0][1] == approx(
        -0.75, abs=0.05
    )  # ISOPleasant coords
    assert coords[1][0] == approx(0.03, abs=0.05) and coords[1][1] == approx(
        0.35, abs=0.05
    )  # ISOEventful coords


def test_return_paqs():
    df = basic_test_df
    df['add1'] = df['PAQ1'] + df['PAQ2']  # Just add some random columns to test
    df['add2'] = df['PAQ3'] + df['PAQ4']

    assert db.return_paqs(df).columns.tolist() == [
        "RecordID",
        "PAQ1",
        "PAQ2",
        "PAQ3",
        "PAQ4",
        "PAQ5",
        "PAQ6",
        "PAQ7",
        "PAQ8"]

    assert db.return_paqs(df, incl_ids=False, other_cols=['add1']).columns.tolist() == [
        "PAQ1",
        "PAQ2",
        "PAQ3",
        "PAQ4",
        "PAQ5",
        "PAQ6",
        "PAQ7",
        "PAQ8",
        "add1"]


def test_calculate_paq_coords_val_range():
    df = basic_test_df.copy()
    df = df * 10
    coords = db.calculate_paq_coords(df, val_range=(0, 100))
    assert coords[0][0] == approx(0.21, abs=0.05) and coords[0][1] == approx(
        -0.30, abs=0.05
    )  # ISOPleasant coords
    assert coords[1][0] == approx(0.01, abs=0.05) and coords[1][1] == approx(
        0.14, abs=0.05
    )  # ISOEventful coords


def test_paq_data_quality():
    df = basic_test_df.copy()
    wrong_data = pd.DataFrame(
        {"RecordID": ["EX3"], "PAQ1": [4], "PAQ2": [4], "PAQ3": [4], "PAQ4": [4], "PAQ5": [4], "PAQ6": [4], "PAQ7": [4],
         "PAQ8": [4]})
    df = df.append(wrong_data)
    l = db.paq_data_quality(df)
    assert l == [2]


def test_calculate_paq_coords_min_max():
    # first is max pleasant, second is max eventful, third is min pleasant, fourth is min eventful
    vals = {
        "RecordID": ["maxpl", "maxev", "minpl", "minev"],
        "pleasant": [5, 3, 1, 3],
        "vibrant": [5, 5, 1, 1],
        "eventful": [3, 5, 3, 1],
        "chaotic": [1, 5, 5, 1],
        "annoying": [1, 3, 5, 3],
        "monotonous": [1, 1, 5, 5],
        "uneventful": [3, 1, 3, 5],
        "calm": [5, 1, 1, 5],
    }
    df = pd.DataFrame(vals)
    df = db.rename_paqs(df)
    ISOPl, ISOEv = db.calculate_paq_coords(df)
    assert ISOPl[0] == approx(1, abs=0.01) and ISOPl[2] == approx(
        -1, abs=0.01
    )  # ISOPleasant coords
    assert ISOEv[1] == approx(1, abs=0.01) and ISOEv[3] == approx(
        -1, abs=0.01
    )  # ISOEventful coords


def test_calculate_paq_coords_val_range_min_max():
    # first is max pleasant, second is max eventful, third is min pleasant, fourth is min eventful
    vals = {
        "RecordID": ["maxpl", "maxev", "minpl", "minev"],
        "pleasant": [50, 0, -50, 0],
        "vibrant": [50, 50, -50, -50],
        "eventful": [0, 50, 0, -50],
        "chaotic": [-50, 50, 50, -50],
        "annoying": [-50, 0, 50, 0],
        "monotonous": [-50, -50, 50, 50],
        "uneventful": [0, -50, 0, 50],
        "calm": [50, -50, -50, 50],
    }
    df = pd.DataFrame(vals)
    df = db.rename_paqs(df)
    ISOPl, ISOEv = db.calculate_paq_coords(df, val_range=(-50, 50))
    assert ISOPl[0] == approx(1, abs=0.01) and ISOPl[2] == approx(
        -1, abs=0.01
    )  # ISOPleasant coords
    assert ISOEv[1] == approx(1, abs=0.01) and ISOEv[3] == approx(
        -1, abs=0.01
    )  # ISOEventful coords


def test_simulation():
    df = db.simulation(n=200)
    assert df.shape == (200, 8)

    df = db.simulation(n=200, add_paq_coords=True)
    assert df.shape == (200, 10)

    df = db.simulation(n=200, add_paq_coords=True)
    assert df.columns.tolist() == [
        "PAQ1",
        "PAQ2",
        "PAQ3",
        "PAQ4",
        "PAQ5",
        "PAQ6",
        "PAQ7",
        "PAQ8",
        "ISOPleasant",
        "ISOEventful",
    ]


if __name__ == "__main__":
    pytest.main()

# %%
