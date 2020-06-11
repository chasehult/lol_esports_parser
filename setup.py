import setuptools
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="lol_esports_parser",
    version="0.0.1",
    packages=['lol_esports_parser', 'lol_esports_parser/acs', 'lol_esports_parser/qq', 'lol_esports_parser/dto'],
    install_requires=["requests", "dateparser", "lol-id-tools", "riot-transmute", "lol-dto"],
    url="https://github.com/mrtolkien/lol_esports_parser",
    license="MIT",
    author='Gary "Tolki" Mialaret',
    author_email="gary.mialaret+pypi@gmail.com",
    description="A utility to query and transform LoL games from QQ and ACS into the LolGame DTO format.",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
