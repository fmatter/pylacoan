import pytest
from pylacoan.annotator import Segmentizer
import copy


def test_segments():
    prf = [{"Grapheme": "ü", "IPA": "ɨ"}, {"Grapheme": "b", "IPA": "β"}]
    a = Segmentizer(segments=copy.deepcopy(prf), tokenize=False)
    assert a.parse_string("üb bü") == "ɨβ βɨ"
    b = Segmentizer(segments=copy.deepcopy(prf), tokenize=True)
    assert b.parse_string("üb") == "ɨ β"
    c = Segmentizer(segments=copy.deepcopy(prf), tokenize=False, ignore="-")
    assert c.parse_string("ü-b") == "ɨ-β"
    d = Segmentizer(segments=copy.deepcopy(prf), tokenize=True, delete="#")
    assert d.parse_string("ü#b") == "ɨ β"
    e = Segmentizer(segments=copy.deepcopy(prf), tokenize=False, delete="#")
    assert e.parse_string("ü#b") == "ɨβ"
