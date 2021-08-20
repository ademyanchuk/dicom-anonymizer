from pathlib import Path
import pytest

from dicomanonymizer import utils


def test_to_Path():
    assert isinstance(utils.to_Path("path"), Path)


def test_to_Path_buggy():
    with pytest.raises(TypeError):
        utils.to_Path(1.2)
