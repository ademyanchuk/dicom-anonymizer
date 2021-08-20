import random

import pydicom
import pytest

from dicomanonymizer import simpledicomanonymizer as smpd


def ui_element():
    return pydicom.DataElement(
        tag=(0x0020, 0x000D), VR="UI", value="1.2.826.0.1.3680043.2.594"
    )


def date_element():
    return pydicom.DataElement(tag=(0x0008, 0x0022), VR="DA", value="20170131")


def dt_element():
    return pydicom.DataElement(
        tag=(0x0008, 0x002A), VR="DT", value="20010203123415.123000+4560"
    )


def time_element():
    return pydicom.DataElement(tag=(0x0008, 0x0032), VR="TM", value="123456.78")


@pytest.fixture
def make_elem():
    created_elems = []

    def _make_elem(VR):
        elem = None
        if VR == "UI":
            elem = ui_element()
        elif VR == "DA":
            elem = date_element()
        elif VR == "DT":
            elem = dt_element()
        elif VR == "TM":
            elem = time_element()
        created_elems.append(elem)
        return elem

    yield _make_elem

    for elem in created_elems:
        del elem


def test_replace_element_UID(make_elem):
    random.seed(123)
    elem = make_elem("UI")
    smpd.replace_element_UID(elem)
    assert elem.value == "0.4.164.1.0.6885502.2.585"


def test_replace_element_UID_cache(make_elem):
    first = make_elem("UI")
    smpd.replace_element_UID(first)

    second = make_elem("UI")
    smpd.replace_element_UID(second)

    assert first.value == second.value


def test_replace_element_date(make_elem):
    date = make_elem("DA")
    smpd.replace_element_date(date)
    assert date.value == "00010101"


def test_replace_element_date_time(make_elem):
    dt = make_elem("DT")
    smpd.replace_element_date_time(dt)
    assert dt.value == "00010101010101.000000+0000"


def test_replace_element_time(make_elem):
    tm_elem = make_elem("TM")
    smpd.replace_element(tm_elem)
    assert tm_elem.value == "000000.00"
