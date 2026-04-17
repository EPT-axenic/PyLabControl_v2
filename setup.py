from setuptools import setup, find_packages

setup(
    name="pylabcontrol_v2",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic",
        "pint",
        "pyvisa",
        "toml",
    ],
)