import setuptools
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="lol_esports_parser",
    version="0.0.1",
    packages=setuptools.find_packages(),
    install_requires=["requests", "dateparser", "lol-id-tools", "riot-transmute"],
    url="https://github.com/mrtolkien/lol_esports_parser",
    license="MIT",
    author='Gary "Tolki" Mialaret',
    author_email="gary.mialaret+pypi@gmail.com",
    description="A utility to transform LoL games data from both QQ and ACS into the LolGame DTO format.",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
