import random

import pydicom
import pytest

from dicomanonymizer import simpledicomanonymizer as smpd

random.seed(123)


# tags for those elements are checked to be of respective VR

dcm_elements = {
    "UI": dict(tag=(0x0020, 0x000D), VR="UI", value="1.2.826.0.1.3680043.2.594"),
    "DA": dict(tag=(0x0008, 0x0022), VR="DA", value="20170131"),
    "DT": dict(tag=(0x0008, 0x002A), VR="DT", value="20010203123415.123000+4560"),
    "TM": dict(tag=(0x0008, 0x0032), VR="TM", value="123456.78"),
    "LO": dict(tag=(0x0008, 0x0080), VR="LO", value="Uni Name Ü"),
    "SH": dict(tag=(0x0008, 0x0050), VR="SH", value="ABC123"),
    "PN": dict(tag=(0x0008, 0x0090), VR="PN", value="Demyanchuk^Alexey"),
    "CS": dict(tag=(0x0010, 0x0040), VR="CS", value="M"),
    "IS": dict(tag=(0x0028, 0x0034), VR="IS", value=["1", "1"]),
}

expected = {
    "UI": "0.4.164.1.0.6885502.2.585",
    "DA": "00010101",
    "DT": "00010101010101.000000+0000",
    "TM": "000000.00",
    "LO": "Anonymized",
    "SH": "Anonymized",
    "PN": "Anonymized",
    "CS": "Anonymized",
    "IS": [0, 0],
}


@pytest.fixture
def make_elem():
    created_elems = []

    def _make_elem(VR):
        elem = pydicom.DataElement(**dcm_elements[VR])
        created_elems.append(elem)
        return elem

    yield _make_elem
    # will clean creted elements after finishing test
    for elem in created_elems:
        del elem


def test_replace_element_UID_cache(make_elem):
    first = make_elem("UI")
    smpd.replace_element_UID(first)

    second = make_elem("UI")
    smpd.replace_element_UID(second)

    assert first.value == second.value


@pytest.mark.parametrize("vr", dcm_elements)
def test_replace_element(make_elem, vr):
    elem = make_elem(vr)
    smpd.replace_element(elem)
    assert elem.value == expected[vr]


@pytest.mark.parametrize("vr", dcm_elements)
def test_replace_element_value_types(make_elem, vr):
    elem = make_elem(vr)
    type_pre = type(elem.value)
    smpd.replace_element(elem)
    assert isinstance(elem.value, type_pre)
