import random

import pydicom
import pytest
from dicomanonymizer import simpledicomanonymizer as smpd


@pytest.fixture
def data_element():
    element = pydicom.DataElement(
        tag=(0x0020, 0x000D), VR="UI", value="1.2.826.0.1.3680043.2.594"
    )
    yield element
    del element


def test_replace_element_UID(data_element):
    random.seed(123)
    smpd.replace_element_UID(data_element)
    assert data_element.value == "0.4.164.1.0.6885502.2.585"


def test_replace_element_UID_cache(data_element):
    original = data_element.value
    smpd.replace_element_UID(data_element)
    first = data_element.value

    data_element.value = original
    smpd.replace_element_UID(data_element)

    assert first == data_element.value
