# Testing

Unit testing script made using python.

This script uses environment variables to specify variables.

## Envars:
- BUILD_CMD  -  This is the command that will run on building(compiling) the test.
- RUN_CMD    -  Same as BUILD_CMD but will run on "running" the test.
- TESTS_DIR  -  The directory all the test files reside.
- SRC_SUFFIX -  Suffix of the test source files. Eg: .c for C source files.

## Usage

First you record the expected behaviour when building the tests using the `record_build` subcommand.
Then you can build the tests using the `build` subcommand.
Like when building, you first have to record the expected behaviour when running the tests using the `record` subcommand.
Then you can run the tests using the `run` subcommand.

```console
$ TESTS_DIR=<YOUR_TESTS_DIR> BUILD_CMD="<YOUR_BUILD_CMD"> SRC_SUFFIX=<YOUR_SRC_SUFFIX> ./test.py record_build -x
$ TESTS_DIR=<YOUR_TESTS_DIR> BUILD_CMD="<YOUR_BUILD_CMD"> SRC_SUFFIX=<YOUR_SRC_SUFFIX> ./test.py build -x
$ TESTS_DIR=<YOUR_TESTS_DIR> RUN_CMD="<YOUR_RUN_CMD"> SRC_SUFFIX=<YOUR_SRC_SUFFIX> ./test.py record -x
$ TESTS_DIR=<YOUR_TESTS_DIR> RUN_CMD="<YOUR_RUN_CMD"> SRC_SUFFIX=<YOUR_SRC_SUFFIX> ./test.py run -x
```
