from setuptools import setup

setup(
    name="navee_logging",
    packages=["navee_logging"],
    description="Helper functions for logging",
    version="1.3.0",
    url="https://gitlab.com/navee.ai/packages/navee_logging",
    author="Navee devs",
    author_email="developers@navee.co",
    keywords=["pip", "navee", "logging"],
    install_requires=["boto3", "botocore", "python-dotenv", "sentry-sdk"],
)
