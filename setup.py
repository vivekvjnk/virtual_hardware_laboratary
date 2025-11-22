
from setuptools import setup, find_packages

setup(
    name='virtual_hardware_lab',
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
    description='A Virtual Hardware Lab package for deterministic and reproducible ngspice simulations.',
    url='https://github.com/vivekvjnk/virtual_hardware_lab',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.7',
)
