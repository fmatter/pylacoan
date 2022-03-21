from pylacoan.helpers import get_morph_id, sort_uniparser_ids
import pytest


def test_get_morph_id():

    # missing ID in id_dict
    with pytest.raises(ValueError):
        get_morph_id(["1"], {"2": "test"}, "test")

    assert (
        get_morph_id(["id1", "id2"], {"id1": "form", "id2": "nothing"}, obj="form")
        == "id1"
    )

    assert (
        get_morph_id(
            ["id1", "id2", "id3"],
            {"id1": "form:meaning", "id2": "nothing:l", "id3": "none"},
            obj="form",
            gloss="meaning",
        )
        == "id1"
    )


def test_sort_uniparser_ids():
    assert sort_uniparser_ids(
        id_list=["imp", "sapsuf", "putv", "3t"],
        id_dic={
            "imp": "kə:IMP",
            "3t": "t:3P",
            "sapsuf": "tə:SAP.PL",
            "putv": "ɨrɨ:place",
        },
        obj="t-ɨrɨ-tə-kə",
        gloss="3P-place-SAP.PL-IMP",
    ) == ["3t", "putv", "sapsuf", "imp"]
