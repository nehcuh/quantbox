from setuptools import setup, find_packages
import sys

# Define dependencies based on Python version
install_requires = [
    "tushare",
    "pandas",
    "pymongo",
    "toml",
    "numpy",
    "pyinstaller",  # For creating executables
    "PyQt6",  # For GUI
]

# Only add typing for Python < 3.5
if sys.version_info < (3, 5):
    install_requires.append('typing')

setup(
    name="quantbox",
    version="0.1.0",
    author="HuChen",
    description="A quantitative trading toolbox with multiple data source support",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "quantbox=quantbox.shell:main",
            "quantbox-save=quantbox.savers.data_saver:save_data",
            "quantbox-gui=scripts.run_gui:main",  # GUI entry point
        ]
    },
    install_requires=install_requires,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)
