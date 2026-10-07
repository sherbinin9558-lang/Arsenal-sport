import saas_admin


def test_platform_admin_module_exports_owner_console_helpers():
    assert callable(saas_admin.platform_admin_enabled)
    assert callable(saas_admin.platform_admin_snapshot)
    assert callable(saas_admin.platform_admin_set_tenant)
    assert callable(saas_admin.platform_admin_set_subscription)


def test_saas_core_keeps_owner_console_compatibility_imports():
    import saas_core

    assert saas_core.platform_admin_enabled is saas_admin.platform_admin_enabled
    assert saas_core.platform_admin_snapshot is saas_admin.platform_admin_snapshot
