from pylacoan.annotator import pad_ex


def test_padding():
    assert (
        pad_ex("ɨ-pɨre ekaro-ase e-ja", "1-gun.PERT give-REC 3-OBL")
        == "ɨ-pɨre      ekaro-ase  e-ja\n1-gun.PERT  give-REC   3-OBL"
    )
