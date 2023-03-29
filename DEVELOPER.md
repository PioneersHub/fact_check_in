# DEVELOPER

## Setup development environment
Clone the repository and `cd` into it.
To install a local conda environment for the project:

```shell
conda env create -f environment.yml
```
Make sure you have selected the project's environment in your IDE when you run test or in the shell

```shell
# environment_name: use name in environment.yml
conda activate environment_name
```

# Deployment
The deployment procedure of a new release consists of the following steps
- Consolidate the repository (i.e. clean repo, everything committed, unit tests pass)
- Bump version identifier to release
- Bump version identifier to development state on the main (optional, recommended)
- Build documentation (optional)

## Versioning Schema
The versioning schema is `{major}.{minor}.{patch}[{release}{build}]` where the
latter part (release and build) is optional.
Release takes the following values:
- _null_
- _dev_ (to indicate a actively developed version)
- _a_ (alpha)
- _b_ (beta)
- _rc_ (release candidate)
- _post_ (post release hotfixes)

### Bump version identifier
It is recommended to do `--dry-run` prior to your actual run.
```bash
# increase version identifier
bump2version [major/minor/patch/release/build]  # --verbose --dry-run

# e.g.
bump2version minor  # e.g. 0.5.1 --> 0.6.0
bump2version minor --new-version 0.7.0  # e.g. 0.5.1 --> 0.7.0
```
After a successful release, the version identifier should be bumped to the `dev` state to indicate
that master/main is under development. The exact version does not matter to much, e.g. work that was
initially considered a patch could be bumped as a minor release upon release.
```bash
bump2version release --new-version 0.6.0dev1  # e.g. 0.5.1 --> 0.6.0dev1
```

# Guidelines for Doc Generation with Sphinx

We want to provide technical documentation in a standardized fashion across all libraries. 

Please familiarize yourself with the directories and files contained in `./docs`, see `./docs/README.md`.

---

# Generation of Sphinx Documentation 
To alter the documentation, edit the files in `./docs/sphinx/source`.
The documentation can be rendered to html with
```
sphinx-build -b html docs/sphinx/source docs/sphinx/build
```
To review the rendered html version locally, start a local webserver:
```shell
# python -m http.server [PORT] -d [relative/path/to/build], e.g.
python -m http.server 8000 -d docs/sphinx/build
```
The pages are available then at http://localhost:PORT/, e.g. [http://localhost:8000/](http://localhost:8000/)
