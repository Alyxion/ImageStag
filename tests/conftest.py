"""
Pytest fixtures for ImageStag tests
"""

import pytest

from imagestag.media.samples import STAG_PATH


@pytest.fixture(scope="module")
def stag_image_data() -> bytes:
    """
    Returns the stag image data for testing.
    :return: The jpeg data
    """
    with open(STAG_PATH, "rb") as f:
        yield f.read()
