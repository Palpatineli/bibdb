from setuptools import setup

setup(
    name='bibdb',
    version='0.1.1',
    packages=['bibdb'],
    url='https://github.com/Palpatineli/bibdb.git',
    entry_points={'console_scripts': ['bibdb=bibdb.main:parse_args',
                                      'bibdb-import=bibdb.actions.store_paper:import_bib',
                                      'bibdb-fix=bibdb.actions.store_paper:fix_authorship']},
    license='GPLv3.0',
    author='Keji Li',
    author_email='mail@keji.li',
    description='cross-platform management of bibliography from the command line',
    install_requires=['sqlalchemy', 'bibtexparser'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
