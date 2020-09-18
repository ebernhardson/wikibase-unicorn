import json
import os
import pytest


@pytest.fixture(scope='session')
def fixture_dir():
    return os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture(scope='session')
def get_fixture(fixture_dir):
    def fn(group, name):
        with open(os.path.join(fixture_dir, group, name), 'rt') as f:
            return f.read()
    return fn


def on_disk_fixture(path):
    def compare(other):
        if os.path.exists(path):
            with open(path, 'r') as f:
                expect = json.load(f)
            assert expect == other
        elif os.environ.get('REBUILD_FIXTURES') == 'yes':
            with open(path, 'w') as f:
                json.dump(other, f, indent=4, sort_keys=True)
            pytest.skip('Rebuilt fixture')
        else:
            raise Exception('No fixture[{}] and REBUILD_FIXTURES != yes'.format(path))
    return compare


@pytest.fixture(scope='session')
def fixture_factory(fixture_dir):
    def factory(group, fixture_id):
        path = os.path.join(fixture_dir, group, fixture_id, group, fixture_id + '.expected')
        return on_disk_fixture(path)
    return factory
