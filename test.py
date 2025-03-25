#!/bin/env python3
import os
import subprocess
import sys
import shlex

# TODO: Use Colored logging

## Substitutable values; These values are substituted with the following values if found in BUILD_CMD or RUN_CMD

# - {test_name}  - name of the test.
# - {src_suffix} - suffix of the source files. (excluding the .)

# BUILD_CMD will be the command run when the `build` subcommand is ran.
BUILD_CMD="NOT SET"
# Same as the BUILD_CMD but run when the `run` command is ran.
RUN_CMD="NOT SET"
# The name of the directory all the tests live in. (Will chdir to this)
TESTS_DIR="NOT SET"
# Suffix of the source files the build command iw (if there is a . prefix, it will be removed
SRC_SUFFIX="NOT SET"

def get_env_variables():
    global BUILD_CMD, RUN_CMD, TESTS_DIR, SRC_SUFFIX
    BUILD_CMD = os.environ["BUILD_CMD"] if "BUILD_CMD" in os.environ else "NOT SET"
    RUN_CMD = os.environ["RUN_CMD"] if "RUN_CMD" in os.environ else "NOT SET"
    TESTS_DIR = os.environ["TESTS_DIR"] if "TESTS_DIR" in os.environ else "NOT SET"
    SRC_SUFFIX = os.environ["SRC_SUFFIX"] if "SRC_SUFFIX" in os.environ else "NOT SET"
    SRC_SUFFIX = SRC_SUFFIX.removeprefix(".")
    # SRC_SUFFIX = os.environ["SRC_SUFFIX"] if "SRC_SUFFIXsuffix" in os.environ else "NOT SET"


def get_cmd_substituted(cmd, tests, current_test):
    assert current_test in tests, "The test that you passed is not in the tests map!"
    cmd = cmd.replace("{test_name}", tests[current_test].name)
    cmd = cmd.replace("{src_suffix}", SRC_SUFFIX)

    return cmd

def check_crucial_envvar(var, var_name):
    if var == "NOT SET":
        print(f"[ERROR] `{var_name}` environment variable not set! please provide a value and run again!", file=sys.stderr)
        exit(1)

class Test:
    stdin = ''
    expected_stdout = ''
    expected_stderr = ''
    expected_returncode = -1

    build_stdin = ''
    build_expected_stdout = ''
    build_expected_stderr = ''
    build_expected_returncode = -1

    def __init__(self, name):
        self.name = name

        def read_or_create_expected_file(name: str) -> str:
            f = self.get_expected_filename(name)
            if not os.path.exists(f):
                with open(f, "w") as file:
                    pass
                    # NOTE: Why do we need to log this?
                    # print(f"[INFO] Created empty {self.name}.{name}.expected")
                return ""
            else:
                with open(f, "r") as file:
                     return file.read()

        self.stdin = read_or_create_expected_file("in")
        self.expected_stdout = read_or_create_expected_file("out")
        self.expected_stderr = read_or_create_expected_file("err")
        self.expected_returncode = read_or_create_expected_file("code")
        if self.expected_returncode == '':
            self.expected_returncode = -1
        else:
            self.expected_returncode = int(self.expected_returncode)

        self.build_stdin = read_or_create_expected_file("build.in")
        self.build_expected_stdout = read_or_create_expected_file("build.out")
        self.build_expected_stderr = read_or_create_expected_file("build.err")
        self.build_expected_returncode = read_or_create_expected_file("build.code")
        if self.build_expected_returncode == '':
            self.build_expected_returncode = -1
        else:
            self.build_expected_returncode = int(self.build_expected_returncode)

        # if self.expected_stdout: print(f"{self.name}.out.expected: {self.expected_stdout}")
        # if self.expected_stderr: print(f"{self.name}.err.expected: {self.expected_stderr}")
    def save_expected(self):
        def write_expected(name: str, content: str):
            f = self.get_expected_filename(name)
            with open(f, "w") as file:
                file.write(content)

        write_expected("in", self.stdin)
        write_expected("out", self.expected_stdout)
        write_expected("err", self.expected_stderr)
        write_expected("code", str(self.expected_returncode))

        write_expected("build.in", self.build_stdin)
        write_expected("build.out", self.build_expected_stdout)
        write_expected("build.err", self.build_expected_stderr)
        write_expected("build.code", str(self.build_expected_returncode))

    def get_expected_filename(self, name):
        if name not in [ "in", "out", "err", "code", "build.in", "build.out", "build.err", "build.code" ]:
            raise Exception("Please pass a valid name")
            
        return f".{self.name}.{name}.expected"

    def get_build_stdin_list(self):
            build_input_array = self.build_stdin.split(sep=' ')
            for i in range(len(build_input_array)-1, -1, -1):
                if len(build_input_array[i]) <= 0:
                    build_input_array.pop(i)
            return build_input_array

    def get_stdin_list(self):
            input_array = self.stdin.split(sep=' ')
            for i in range(len(input_array)-1, -1, -1):
                if len(input_array[i]) <= 0:
                    input_array.pop(i)
            return input_array

def usage(program: str):
    print(f"Usage: {program} <subcmd> [flags]")

# NOTE: We named this hhelp because help is a builtin python function
def hhelp():
    print('''
    Subcommands:
        help            - Prints this help message.
        build           - Builds all the tests.
        run             - Runs all the tests.
        record          - Records the expected behaviour of all the tests.
        record_build    - Records the expected build behaviour of all the tests.

    Flags:
        -h      - Same as the help subcommand.
        -V      - Verbose output.
        -x      - Stop on first error.
          ''')

def vlog(verbose_output, msg):
    if verbose_output:
        print(msg)

def main():
    program = sys.argv.pop(0)

    if len(sys.argv) <= 0:
        print("[ERROR] Please provide at least one subcommand!", file=sys.stderr)
        usage(program)
        hhelp()
        exit(1)


    flags = []

    # FLAG_VALUES
    verbose_output = False
    stop_on_error  = False

    subcmds = []

    while len(sys.argv) > 0:
        arg = sys.argv.pop(0)

        if arg.startswith('-') or arg.startswith('/'):
            flags.append(arg)
        else:
            subcmds.append(arg)

    # Parse flags
    for flag_with_prefix in flags:
        flag = flag_with_prefix[1:]
        if flag == 'h':
            hhelp()
            exit(0)
        elif flag == 'V':
            verbose_output = True
        elif flag == 'x':
            stop_on_error = True
        else:
            print(f"[ERROR] Invalid flag '{flag}'", file=sys.stderr)
            exit(1)

    if len(subcmds) <= 0:
        print("[ERROR] Please provide at least one subcommand!", file=sys.stderr)
        usage(program)
        hhelp()
        exit(1)

    get_env_variables()

    check_crucial_envvar(TESTS_DIR, "TESTS_DIR")
    check_crucial_envvar(SRC_SUFFIX, "SRC_SUFFIX")

    os.chdir(TESTS_DIR)
    vlog(verbose_output, f"[INFO] Changed cwd to {os.getcwd()}")

    tests = {}

    for e in sorted(os.listdir(os.getcwd())):
        if not e.endswith("." + SRC_SUFFIX): continue
        base_name = e.removesuffix("." + SRC_SUFFIX)
        if not tests.get(base_name):
            tests[base_name] = Test(base_name)

    # print(f"BUILD_CMD: {BUILD_CMD}")
    # print(f"RUN_CMD: {RUN_CMD}")
    # print(f"TESTS_DIR: {TESTS_DIR}")
    # print(f"SRC_SUFFIX: {SRC_SUFFIX}")

    for subcmd in subcmds:
        total_tests_count = len(tests)
        current_test_id = 0
        passing_tests_count = 0

        if subcmd == "help":
            hhelp()
            exit(0)
        elif subcmd == "build":
            check_crucial_envvar(BUILD_CMD, "BUILD_CMD")
            print(f'----- [BUILD] -----')
            for test_name in tests:
                print(f'+ Building {test_name} [{current_test_id+1}/{total_tests_count}]...')
                current_test_id += 1
                test = tests[test_name]

                if test.build_expected_returncode == -1:
                    print(f"[WARNING] Test doesn't have any expected build returncode!")
                    print(f"[WARNING] Please record the expected build behaviour of the test using the 'record_build' subcommand!")
                    print(f"[SKIPPING]...")
                    if stop_on_error: exit(1)
                    continue

                cmd = shlex.split(get_cmd_substituted(BUILD_CMD, tests, test_name))
                build_stdin_list = test.get_build_stdin_list()
                if len(build_stdin_list) > 0: cmd.extend(build_stdin_list)
                vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run(cmd, capture_output = True, text = True)
                if res.returncode != 0:
                    print("[FAILED] ", end='')
                    if res.stderr:
                        print(f"{res.stderr}")
                    else:
                        print('')
                    if stop_on_error: exit(1)
                    else: continue
                else:
                    if res.stdout != test.build_expected_stdout:
                        print('[FAILED]', file=sys.stderr)
                        print(f"build_Expected: >>>{test.build_expected_stdout}>>>")
                        print(f"But Got: >>>{res.stdout}>>>")
                        if stop_on_error: exit(1)
                    if res.stderr != test.build_expected_stderr:
                        print('[FAILED]', file=sys.stderr)
                        print(f"build_Expected: >>>{test.build_expected_stderr}>>>")
                        print(f"But Got: >>>{res.stderr}>>>")
                        if stop_on_error: exit(1)
                    passing_tests_count += 1
                    print("[PASS] ", end='')
                    o = False
                    if verbose_output and res.stdout:
                        print(f"{res.stdout}")
                        o = True
                    if verbose_output and res.stderr:
                        print(f"{res.stderr}")
                        o = True
                    if not o: print('')

                print(f"Build {passing_tests_count}/{total_tests_count} tests")
        elif subcmd == "run":
            check_crucial_envvar(RUN_CMD, "RUN_CMD")
            print(f'----- [RUN] -----')
            for test_name in tests:
                print(f'+ Running {test_name} [{current_test_id+1}/{total_tests_count}]...')
                current_test_id += 1
                test = tests[test_name]

                res = None
                try:
                    cmd = shlex.split(get_cmd_substituted(RUN_CMD, tests, test_name))
                    vlog(verbose_output, f"[CMD] {cmd}")
                    res = subprocess.run(cmd, capture_output = True, text = True)
                except Exception as e:
                    print(f"[ERROR] Failed to run ./{test_name}: {e}")
                    if stop_on_error: exit(1)
                    else: continue

                if test.expected_returncode == -1:
                    print(f"[WARNING] Test doesn't have any expected returncode!")
                    print(f"[WARNING] Please record the expected behaviour of the test using the 'record' subcommand!")

                if res.stdout != test.expected_stdout:
                    print('[FAILED]', file=sys.stderr)
                    print(f"Expected: >>>{test.expected_stdout}>>>")
                    print(f"But Got: >>>{res.stdout}>>>")
                    if stop_on_error: exit(1)
                    else: continue
                passing_tests_count += 1
                print('[PASS]')

            print(f"PASSED {passing_tests_count}/{total_tests_count}")
        elif subcmd == "record":
            check_crucial_envvar(RUN_CMD, "RUN_CMD")
            print(f'----- [RECORD] -----')
            for test_name in tests:
                print(f"+ Recording expected behaviour for '{test_name}'...")
                test = tests[test_name]

                cmd = shlex.split(get_cmd_substituted(RUN_CMD, tests, test_name))
                stdin_list = test.get_stdin_list()
                if len(stdin_list) > 0: cmd.extend(stdin_list)
                vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run([f"./{test_name}"], capture_output = True, text = True)

                print(f"stdout: {res.stdout}")
                print(f"stderr: {res.stderr}")
                print(f"returncode: {res.returncode}")

                prompt_msg = "Record current behaviour as the expected one? [y/N]"
                ans = input(prompt_msg)

                if ans.lower() == "y":
                    tests[test_name].expected_stdout = res.stdout
                    tests[test_name].expected_stderr = res.stderr
                    tests[test_name].expected_returncode = res.returncode
                    tests[test_name].save_expected()
                    print('[SUCCESS] Recorded expected behaviour')
                else:
                    print('[SKIP]')
        elif subcmd == "record_build":
            check_crucial_envvar(BUILD_CMD, "BUILD_CMD")
            print(f'----- [RECORD_BUILD] -----')
            for test_name in tests:
                print(f"+ Recording expected build behaviour for '{test_name}'...")
                test = tests[test_name]

                if len(test.build_stdin) > 0:
                    print(f"[INFO] Test already has build_input '{test.build_stdin}'...")
                    ans = input("Do you want to change the build_input? [y/N]")
                    if ans.lower() == 'y':
                        test.build_stdin = input("What is the input passed? ")
                    else:
                        print("[SKIPPING]...")
                        continue
                else:
                    test.build_stdin = input("What is the input passed? ")

                cmd = shlex.split(get_cmd_substituted(BUILD_CMD, tests, test_name))
                build_stdin_list = test.get_build_stdin_list()
                if len(build_stdin_list) > 0: cmd.extend(build_stdin_list)
                vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run(cmd, capture_output = True, text = True)

                print(f"stdout: {res.stdout}")
                print(f"stderr: {res.stderr}")
                print(f"returncode: {res.returncode}")

                prompt_msg = "Record current build behaviour as the expected one? [y/N]"
                ans = input(prompt_msg)

                if ans.lower() == "y":
                    tests[test_name].build_expected_stdout = res.stdout
                    tests[test_name].build_expected_stderr = res.stderr
                    tests[test_name].build_expected_returncode = res.returncode
                    tests[test_name].save_expected()
                    print('[SUCCESS] Recorded expected behaviour')
                else:
                    print('[SKIP]')

        else:
            print(f"[ERROR] Invalid subcommand '{subcmd}'", file=sys.stderr)
            exit(1)

if __name__ == "__main__":
    main()
