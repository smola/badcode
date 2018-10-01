from setuptools import setup

setup(
    name='badcode',
    entry_points={
        'console_scripts': [
            'badcode = badcode.main:main',
            'badcode-eval = badcode.eval:main',
            'badcode-postprocess = badcode.postprocess:main'
        ],
    }
)