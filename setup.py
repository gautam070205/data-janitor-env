from setuptools import setup, find_packages

setup(
    name="data-janitor-env",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pandas==2.0.3",
        "numpy==1.24.3",
        "pydantic==2.0.0",
        "openai==1.3.0",
        "python-dotenv==1.0.0",
        "openenv-core>=0.2.0"
    ],
)