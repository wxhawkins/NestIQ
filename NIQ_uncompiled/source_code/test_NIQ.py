import pytest
import niq_core
import niq_misc
import niq_classes
import niq_hmm

# @pytest.fixture
# def gui():
#     return niq_core.GUIClass()
gui = niq_core.GUIClass()

def test_foo():
    assert gui.data_point_col == 0

def test_config_load():
    config_path = "../testing/test_config.ini"

    with open(config_path, "r") as f:
        print(f.readlines())
    gui.load_config(config_file_=config_path)
    # assert int(gui.dur_thresh_E.get()) == 4