from setuptools import setup

setup(
    name="navee_utils",
    packages=["navee_utils", "navee_utils.app_base"],
    description="Helper functions",
    version="1.0.1",
    url="https://gitlab.com/navee.ai/packages/navee-utils.git",
    author="Navee devs",
    author_email="developers@navee.co",
    keywords=["pip", "navee", "utils"],
    install_requires=[
        "Pillow==9.5.0",
        "pillow-avif-plugin==1.3.1",
        "requests==2.28.1",
        "tldextract==3.4.4",
        "numpy==1.24.2",
        "imagehash==4.3.1",
        "boto3==1.25.1",
    ],
)
