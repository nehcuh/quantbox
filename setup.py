from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="quantbox",
    version="0.1.0",
    author="huchen",
    description="A comprehensive quantitative investment research platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nehcuh/quantbox",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "pymongo>=4.0.0",
        "redis>=4.5.0",
        "tushare>=1.2.89",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "tomli>=2.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "quantbox": ["example.config.toml"],
    },
)
