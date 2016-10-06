import os.path
from setuptools import setup, find_packages


HERE = os.path.abspath(os.path.dirname(__file__))
PACKAGE = os.path.join(HERE, 'src', 'git_whatsup')
DESCRIPTION = ('Tool to list up remote branches that '
               'conflict with the current working copy.')
__version__ = None
with open(os.path.join(PACKAGE, 'version.py')) as f:
    exec(f.read())


if __name__ == "__main__":
    setup(
        name='git-whatsup',
        version=__version__,
        description=DESCRIPTION,
        long_description=open('README.md').read(),
        url='https://github.com/NoRedInk/git-whatsup',
        author='Marica Odagaki',
        author_email='marica@noredink.com',
        license='MIT',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: POSIX',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Topic :: Software Development',
        ],
        keywords='git development',
        packages=find_packages(exclude=['tests*'], where='src'),
        package_dir={'': 'src'},
        install_requires=[
            'pygit2',
        ],
        entry_points={
            'console_scripts': [
                'git-whatsup=git_whatsup:main',
            ],
        },
    )
