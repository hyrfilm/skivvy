from setuptools import setup, find_packages

setup(
    name='skivvy',
    packages=find_packages(exclude=["*.json"]),
    version='0.401',
    description='A simple tool for testing JSON/HTTP APIs',
    author='Jonas Holmer',
    author_email='jonas.holmer@gmail.com',
    url='https://github.com/hyrfilm/skivvy',
    download_url='https://github.com/hyrfilm/skivvy/archive/0.1.tar.gz',
    keywords=['testing', 'automation', 'unit-testing', 'json', 'API', 'HTTP'],
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Developers',
                 'Topic :: Software Development :: Quality Assurance',
                 'Topic :: Software Development :: Testing',
                 'Programming Language :: Python'],
    install_requires=['pyopenssl', 'requests', 'docopt'],
    entry_points={
        "console_scripts": ['skivvy = skivvy.skivvy:run_skivvy']
    }
)