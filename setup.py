from setuptools import setup, find_packages

setup(
    name="etl_toolkit",
    version="1.0.0",
    description="Standardized in-house ETL framework: cleaning, data quality, loaders, orchestration, reporting.",
    packages=find_packages(include=["etl_toolkit", "etl_toolkit.*"]),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=1.5",
        "numpy>=1.23",
        "pyodbc>=4.0",
        "sqlalchemy>=1.4",
        "psycopg2-binary>=2.9",
        "mysql-connector-python>=8.0",
        "PyYAML>=6.0",
        "python-dotenv>=1.0",
        "requests>=2.28",
        "openpyxl>=3.1",
    ],
    entry_points={
        "console_scripts": [
            "etl-run=etl_toolkit.orchestration.cli:main",
        ],
    },
)
