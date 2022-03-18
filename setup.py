#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

# with open("HISTORY.md") as history_file:
#     history = history_file.read()
history = ""

with open("requirements.txt") as req_file:
    requirements = req_file.read()

test_requirements = ["pytest>=3"]

setup(
    author="Florian Matter",
    author_email="florianmatter@gmail.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Combine different corpus annotators",
    entry_points={"console_scripts": ["pylacoan = pylacoan.__main__:main"]},
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="pylacoan",
    name="pylacoan",
    package_dir={"": "src"},
    packages=find_packages(where="src",include=["pylacoan", "pylacoan.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/fmatter/pylacoan",
    version="0.0.1",
    zip_safe=False,
)
