import os

from setuptools import find_namespace_packages, setup

version = "1.0"

with open("requirements.txt") as f:
    install_requires = f.readlines()

setup(
    name="slim-parsl",
    version=version,
    packages=find_namespace_packages(include=["parsl", "parsl.*"]),
    description="Slim Parsl that will work with AWS Lambda",
    install_requires=install_requires,
    python_requires=">=3.6.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering",
    ],
    keywords=["funcX", "FaaS", "Function Serving"],
    author="funcX team",
    author_email="labs@globus.org",
    license="Apache License, Version 2.0",
    url="https://github.com/funcx-faas/funcx",
)
