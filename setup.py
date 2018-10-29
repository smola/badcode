import setuptools

setuptools.setup(
    name='badcode',
    packages=setuptools.find_packages(exclude=['test']),
    entry_points={
        'console_scripts': [
            'badcode = badcode.main:main',
            'badcode-eval = badcode.eval:main',
            'badcode-postprocess = badcode.postprocess:main',
            'badcode-analyzer = badcode.analyzer:main'
        ],
    }
)