from app_mode import local_services_enabled


def test_local_services_are_disabled_by_default():
    assert local_services_enabled({}) is False


def test_local_services_can_be_explicitly_enabled():
    assert local_services_enabled({"CROPSHIELD_LOCAL_MODE": "true"}) is True
    assert local_services_enabled({"CROPSHIELD_LOCAL_MODE": " YES "}) is True
    assert local_services_enabled({"CROPSHIELD_LOCAL_MODE": "1"}) is True


def test_unrecognized_local_mode_value_fails_closed():
    assert local_services_enabled({"CROPSHIELD_LOCAL_MODE": "enabled"}) is False


def test_cloud_marker_does_not_enable_local_services():
    assert local_services_enabled({"IS_STREAMLIT_CLOUD": "true"}) is False
