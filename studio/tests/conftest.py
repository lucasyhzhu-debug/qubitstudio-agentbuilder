def pytest_configure(config):
    config.addinivalue_line("markers", "integration: opt-in tests that spawn the real claude CLI")
