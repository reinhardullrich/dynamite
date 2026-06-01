import setuptools

# this loads the version number from the dynamite/version.py module
ver_file = open("dynamite/_version.py")
version = ver_file.readlines()[-1].split()[-1].strip("\"'")
ver_file.close()

# load the readme as long description
with open("README.md", "r") as fh:
    long_description = fh.read()

# load the package requirements from requirements.txt
with open("requirements.txt", "r") as fp:
    required = fp.read().splitlines()

orblib_fortran = [
    "../orblib_fortran/bin/orbitstart",
    "../orblib_fortran/bin/orbitstart_bar",
    "../orblib_fortran/bin/orblib_new_mirror",
    "../orblib_fortran/bin/orblib_bar",
    "../orblib_fortran/bin/triaxmass",
    "../orblib_fortran/bin/triaxmass_bar",
    "../orblib_fortran/bin/triaxmassbin",
    "../orblib_fortran/bin/triaxmassbin_bar"
]

setuptools.setup(
    name="dynamite",
    version=version,
    author="DYNAMITE Core Team (Vienna)",
    author_email="prashin.jethwa@univie.ac.at",
    description="dynamics, age and metallicity indicators tracing evolution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://dynamics.univie.ac.at/dynamite_docs/index.html",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    project_urls={
        "Source": "https://github.com/dynamics-of-stellar-systems/dynamite/",
        "Documentation": "https://dynamics.univie.ac.at/dynamite_docs/index.html",
    },
    python_requires=">=3.10",
    # use the already parsed requirements from requirements.txt
    install_requires=required,
    package_data={
        "dynamite": orblib_fortran
    },
    # extra requirements for testing
    extras_require={
        "cvxopt":
            "cvxopt>=1.2.6",
        "testing": [
            "pytest",
            "coverage",
        ]
    }
)
