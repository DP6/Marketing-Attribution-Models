from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    # substitute relative image path by absolute ones
    long_description = long_description.replace(
        "readme-images/",
        "https://raw.githubusercontent.com/DP6/Marketing-Attribution-Models/master/readme-images/",
    )

__version__ = "1.0.10"
setup(
    name="marketing_attribution_models",
    version=__version__,
    description="Metodos de atribuicao de midia",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Andre Tocci",
    author_email="andre.tocci@dp6.com.br",
    url="https://github.com/DP6/Marketing-Attribution-Models",
    project_urls={"Source": "https://dp6.github.io/Marketing-Attribution-Models"},
    packages=["marketing_attribution_models"],
    install_requires=[
        "numpy",
        "pandas",
        "matplotlib",
        "seaborn",
    ],
    license="Apache License 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.5",
)
