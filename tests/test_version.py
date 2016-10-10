import subprocess

import git_whatsup


def test_pip_version_matches_module_version():
    installed_version = subprocess.check_output(
        'pip show git-whatsup | grep ^Version: | cut -d: -f2', shell=True)
    assert installed_version.strip().decode('utf8') == git_whatsup.__version__
