import setuptools

setuptools.setup(
    name='badcode',
    packages=setuptools.find_packages(exclude=['test']),
    entry_points={
        'console_scripts': [
            'badcode = badcode.cli:main'
        ],
    }
)