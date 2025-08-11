"""Setup configuration for ohheycrypto package."""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read version from __version__.py
version = {}
with open("ohheycrypto/__version__.py") as fp:
    exec(fp.read(), version)

# Read requirements
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ohheycrypto",
    version=version["__version__"],
    author="Sean Nieuwoudt",
    author_email="sean@underwulf.com",
    description="A sophisticated cryptocurrency trading bot with advanced technical analysis and risk management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sn/ohheycrypto",
    project_urls={
        "Bug Tracker": "https://github.com/sn/ohheycrypto/issues",
        "Documentation": "https://github.com/sn/ohheycrypto#readme",
        "Source Code": "https://github.com/sn/ohheycrypto",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ohheycrypto=ohheycrypto.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ohheycrypto": ["example_config.json"],
    },
    zip_safe=False,
    keywords="cryptocurrency trading bot binance bitcoin btc technical-analysis rsi",
)
