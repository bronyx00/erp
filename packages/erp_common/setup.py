from setuptools import setup, find_packages

setup(
    name="erp_common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "sqlalchemy",
        "asyncpg",
        "pydantic"
    ],
)