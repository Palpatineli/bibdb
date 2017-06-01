from setuptools import setup

setup(
    name='bibdb',
    version='0.1',
    packages=['bibdb'],
    url='https://github.com/Palpatineli/bibdb.git',
    license='GPLv3.0',
    author='Keji Li',
    author_email='mail@keji.li',
    description='manages bibliography',
    install_requires=['sqlalchemy', 'bibtexparser', 'transitions']
)
