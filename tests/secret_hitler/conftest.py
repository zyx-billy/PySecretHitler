import pytest


def pytest_addoption(parser):
    parser.addoption("--seed", action="store", default=None, help="set the seed for the PRNG")
    parser.addoption("--repeat", action="store", default=1, help="number of times to repeat the test")


@pytest.fixture
def cmdseedopt(request):
    return request.config.getoption("--seed")


@pytest.fixture
def repeat_id(request):
    return request.config.getoption("--request")


def pytest_generate_tests(metafunc):
    # optionally repeat tests that involve randomness
    repeat = int(metafunc.config.getoption("repeat"))
    if "repeat_id" in metafunc.fixturenames:
        metafunc.parametrize("repeat_id", range(1, repeat + 1))
