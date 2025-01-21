import pathlib
import typing

import sublime
import sublime_plugin

SETTINGS_FILE = "ReplBuild.sublime-settings"


def _print(msg):
    print(f"[ReplBuildsystems] {msg}")


class python_repl(sublime_plugin.WindowCommand):
    """
    Starts a SublimeREPL, attempting to use project's specified
    python interpreter. Can replace some placeholders:
    - $REPL_PYTHON to replbuild.pythonPath
    - $REPL_POETRY to replbuild.poetryPath
    also parsed .env file from project root (or from defined replbuild.envFile)
    """

    additional_args = []

    def run(self, *args, **kwargs):
        """Called on project_venv_repl command"""
        command = []
        passed_cmd = kwargs.get("command")
        passed_args = kwargs.get("args")
        if passed_cmd:
            if isinstance(passed_cmd, str):
                command.extend(kwargs["command"].split(" "))
            elif isinstance(passed_cmd, list):
                command.extend(passed_cmd)
            else:
                _print(f"Unknown command passed: {passed_cmd}")
        if passed_args:
            if isinstance(passed_args, list):
                command.extend(passed_args)
            else:
                _print(f"Unknown args passed: {passed_args}")

        command = self.replace_placeholders(command)
        self.repl_open(cmd_list=command)

    def replace_placeholders(self, args: typing.List[typing.AnyStr]):
        known = {
            "$REPL_PYTHON": self.get_python_path,
            "$REPL_POETRY": self.get_poetry_path,
        }
        args = args.copy()
        for index, value in enumerate(args):
            if value in known:
                if callable(known[value]):
                    known[value] = known[value]()
                assert isinstance(known[value], str), (
                    f"Unknown value type for placeholder '{value}': {type(value)}"
                )
                args[index] = known[value]
        return args

    def get_setting_name(self, setting_name, default):
        settings = self.window.active_view().settings()
        value = settings.get(setting_name, None)
        if value is not None:
            _print(f"Using '{setting_name}'='{value}' from project settings")
            return value
        settings = sublime.load_settings(SETTINGS_FILE)
        value = settings.get(setting_name, default)
        _print(f"Using '{setting_name}'='{value}' from common settings")
        return value

    def get_python_path(self):
        return self.get_setting_name("replbuild.pythonPath", "python3.11")

    def get_poetry_path(self):
        return self.get_setting_name("replbuild.poetryPath", "poetry")

    def get_extra_envs(self):
        settings = self.window.active_view().settings()
        return settings.get("env", {})

    def repl_open(self, cmd_list):
        """Open a SublimeREPL using provided commands"""
        env = self.get_extra_envs()
        env.update(self.find_and_load_dotenv())
        self.window.run_command(
            "repl_open",
            {
                "encoding": "utf-8",
                "type": "subprocess",
                "cmd": cmd_list,
                "cwd": "$file_path",
                "external_id": "REPL",
                "syntax": "Packages/Python/Python.tmLanguage",
                "extend_env": env,
            },
        )

    def find_dotenv_file(self) -> typing.Union[pathlib.Path, None]:
        environment_file = pathlib.Path(
            self.get_setting_name("replbuild.envFile", ".env")
        )
        if environment_file.is_absolute():
            return environment_file
        variables = self.window.extract_variables()
        file = variables.get("file_path")
        if not file:
            _print(f"Unknown opened file {file}")
        folder = variables.get("folder")
        if folder and folder in file:
            return pathlib.Path(folder).joinpath(environment_file)
        project = self.window.project_data()
        folders = project.get("folders") or []
        for folder in folders:
            path = folder["path"]
            if path and path in file:
                return pathlib.Path(path).joinpath(environment_file)
        _print(
            f"Opened file {file} not found in any project-related folder, using .env near opened file"
        )
        return pathlib.Path(file).parent.joinpath(environment_file)

    def parse_dot_env(self, filepath: pathlib.Path):
        result = {}
        _print(f"Using env file {filepath}")
        if filepath.exists():
            file = filepath.read_text()
            for line in file.splitlines(keepends=False):
                if line and "=" in line and not line.startswith("#"):
                    values = line.split("=", 1)
                    if len(values) == 2:
                        key, value = values
                        value = value.strip()
                        if value and (
                            (value[0] == '"' and value[-1] == '"')
                            or (value[0] == "'" and value[-1] == "'")
                        ):
                            value = value[1:-1]
                        result[key.strip()] = value
        else:
            _print(f"Environment file {filepath} is not exists")
        return result

    def find_and_load_dotenv(self) -> typing.Dict[typing.AnyStr, typing.AnyStr]:
        env_file_path = self.find_dotenv_file()
        if not env_file_path:
            return {}
        return self.parse_dot_env(env_file_path)
