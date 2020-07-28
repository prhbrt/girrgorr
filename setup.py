from setuptools import setup

setup(
    name='girrgorr',
    version=__import__('girrgorr').__version__,
    author='Herbert Kruitbosch',
    author_email='H.T.Kruitbosch@rug.nl',
    description=('Python implementation of GGIR for processing wearable accelerometer data.'),
    license='BSD',
    packages=[
        'girrgorr'
    ],
    include_package_data=True,
    install_requires=[
        'numpy',
        'pandas',
        'tqdm',
    ],
    extras_require={},
    zip_safe=True,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
