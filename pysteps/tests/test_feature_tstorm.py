import numpy as np
import pytest

from pysteps.feature.tstorm import detection
from pysteps.utils import to_reflectivity
from pysteps.tests.helpers import get_precipitation_fields

try:
    from pandas import DataFrame
except ModuleNotFoundError:
    pass

arg_names = ("source", "output_feat", "dry_input")

arg_values = [
    ("mch", False, False),
    ("mch", True, False),
    ("mch", False, True),
]


@pytest.mark.parametrize(arg_names, arg_values)
def test_feature_tstorm_detection(source, output_feat, dry_input):

    pytest.importorskip("skimage")
    pytest.importorskip("pandas")

    if not dry_input:
        input, metadata = get_precipitation_fields(0, 0, True, True, None, source)
        input = input.squeeze()
        input, __ = to_reflectivity(input, metadata)
    else:
        input = np.zeros((50, 50))

    time = "000"
    output = detection(input, time=time, output_feat=output_feat)

    if output_feat:
        assert isinstance(output, np.ndarray)
        assert output.ndim == 2
        assert output.shape[1] == 2
    else:
        assert isinstance(output, tuple)
        assert len(output) == 2
        assert isinstance(output[0], DataFrame)
        assert isinstance(output[1], np.ndarray)
        assert output[0].shape[1] == 8
        assert list(output[0].columns) == [
            "ID",
            "time",
            "x",
            "y",
            "cen_x",
            "cen_y",
            "max_ref",
            "cont",
        ]
        assert (output[0].time == time).all()
        assert output[1].ndim == 2
        assert output[1].shape == input.shape
        if not dry_input:
            assert output[0].shape[0] > 0
            assert list(output[0].ID) == list(np.unique(output[1]))[1:]
        else:
            assert output[0].shape[0] == 0
            assert output[1].sum() == 0
