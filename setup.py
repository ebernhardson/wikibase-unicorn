import os
from setuptools import find_packages, setup

setup(
    name='unicorn',
    version='0.0.1',
    license='MIT',
    entry_points={
        'console_scripts': [
            'unicorn = unicorn.__main__:main',
        ],
    },
    packages=find_packages(),
    install_requires=[
        'elasticsearch>=6.0.0,<7.0.0'
    ],
    extras_require={
        'web': ['hug', 'jinja2'],
        'test': ['pytest'],
    },
)

