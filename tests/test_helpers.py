import pytest
from pylacoan.helpers import get_morph_id
from pylacoan.helpers import sort_uniparser_ids


def test_get_morph_id():

    # missing ID in id_dict
    with pytest.raises(ValueError):
        get_morph_id(["1"], {"2": "test"}, "test")

    assert (
        get_morph_id(["morpheme1", "morpheme2"], {"morpheme1": {"form": "morpheme1-1"}, "morpheme2": {"nothing": "morpheme2-1"}}, obj="form")
        == "morpheme1-1"
    )

    assert (
        get_morph_id(
            ["id1", "id2", "id3"],
            {"id1": {"form:meaning": "morph1"}, "id2": {"nothing:l": "morph2"}, "id3": {"none": "morph3"}},
            obj="form",
            gloss="meaning",
        )
        == "morph1"
    )


def test_sort_uniparser_ids():
    assert sort_uniparser_ids(
        id_list=["imp", "sapsuf", "putv", "3t"],
        id_dic={
            "imp": {"kə:IMP": "imp"},
            "3t": {"t:3P": "3t"},
            "sapsuf": {"tə:SAP.PL": "sapsuf-1"},
            "putv": {"ɨrɨ:place": "putv"},
        },
        obj="t-ɨrɨ-tə-kə",
        gloss="3P-place-SAP.PL-IMP",
    ) == ["3t", "putv", "sapsuf-1", "imp"]
