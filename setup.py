from setuptools import setup, find_packages

setup(
    name="quantbox",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "save-all=future_toolbox.cli:main"
        ]
    },
    install_requires=[
        "tushare"
    ]
)
