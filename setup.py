from setuptools import setup, find_packages

setup(
    name="pylabcontrol",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "pyvisa",
        "pint",
        "toml",
    ],
)