from saas_config import PLAN_LIMITS, cfg, demo_mode_enabled, public_app_url, saas_enabled, supabase_config


def test_plan_limits_and_config_helpers_are_stable():
    assert PLAN_LIMITS["trial"]["products"] == 100
    assert PLAN_LIMITS["starter"]["products"] == 7000
    assert callable(cfg)
    assert callable(supabase_config)
    assert callable(saas_enabled)
    assert callable(demo_mode_enabled)
    assert callable(public_app_url)
