# Developer Guide

## Deployment

### Release Process
1. Ensure clean repository (all changes committed, tests pass)
2. Bump version to release
3. Deploy
4. Bump version to development state

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
