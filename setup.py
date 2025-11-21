
from setuptools import setup, find_packages

setup(
    name='ngspice_simulator_package',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # List your project's dependencies here.
        # For example:
        'fastapi',
        'jinja2',
        'matplotlib',
        'numpy',
        'pydantic',
        'uvicorn',
        'PyYAML',
    ],
    author='Your Name',
    author_email='your.email@example.com',
    description='A package for ngspice simulations',
    url='https://github.com/vivekvjnk/ngspice_simulator',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
