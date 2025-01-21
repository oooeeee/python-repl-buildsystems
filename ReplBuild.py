import pathlib
import typing

import sublime
import sublime_plugin

SETTINGS_FILE = "ReplBuild.sublime-settings"


def _print(msg):
    print(f"[ReplBuildsystems] {msg}")


class python_repl(sublime_plugin.WindowCommand):
    """
    Starts a SublimeREPL, parses `.env` file, and attempting to use project's specified
    python interpreter. Can replace some placeholders `$replbuild.*` like `$replbuild.pythonPath`
    """

    additional_args = []
    variables_prefix = "$replbuild."

    def run(self, *args, **kwargs):
        """Called on project_venv_repl command"""
        command = self.build_command(kwargs)
        command = self.replace_placeholders(command)
        self.repl_open(cmd_list=command)

    def build_command(self, kwargs) -> typing.List[typing.AnyStr]:
        command = []
        passed_cmd = kwargs.get("command")
        passed_args = kwargs.get("args")

        if passed_cmd:
            if isinstance(passed_cmd, str):
                command.extend(passed_cmd.split(" "))
            elif isinstance(passed_cmd, list):
                command.extend(passed_cmd)
            else:
                _print(f"Unknown command passed: {passed_cmd}")

        if passed_args:
            if isinstance(passed_args, list):
                command.extend(passed_args)
            else:
                _print(f"Unknown args passed: {passed_args}")

        return command

    def replace_placeholders(self, args: typing.List[typing.AnyStr]) -> typing.List[typing.AnyStr]:
        args = args.copy()
        for index, value in enumerate(args):
            if isinstance(value, str) and value.startswith(self.variables_prefix):
                resolved_value = self.get_setting_by_name(value.lstrip("$"), default=None)
                if not isinstance(resolved_value, str):
                    raise ValueError(f"Unknown value type for placeholder '{value}': {resolved_value}")
                args[index] = resolved_value
        return args

    def get_setting_by_name(self, setting_name: str, default):
        settings = self.window.active_view().settings()
        value = settings.get(setting_name, None)
        if value is not None:
            _print(f"Using '{setting_name}'='{value}' from project settings")
            return value
        settings = sublime.load_settings(SETTINGS_FILE)
        value = settings.get(setting_name, default)
        _print(f"Using '{setting_name}'='{value}' from common settings")
        return value

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
            self.get_setting_by_name("replbuild.envFile", ".env")
        )
        if environment_file.is_absolute():
            return environment_file
        variables = self.window.extract_variables()
        file_path = variables.get("file_path")
        if not file_path:
            _print(f"Unknown opened file {file_path}")
            return None
        folder = variables.get("folder")
        if folder and folder in file_path:
            return pathlib.Path(folder).joinpath(environment_file)
        project = self.window.project_data()
        folders = project.get("folders") or []
        for folder in folders:
            path = folder["path"]
            if path and path in file_path:
                return pathlib.Path(path).joinpath(environment_file)
        _print(
            f"Opened file {file_path} not found in any project-related folder, using {environment_file} near opened file"
        )
        return pathlib.Path(file_path).parent.joinpath(environment_file)

    def parse_dot_env(self, filepath: pathlib.Path):
        result = {}
        _print(f"Using env file {filepath}")
        if filepath.exists():
            file_content = filepath.read_text()
            for line in file_content.splitlines(keepends=False):
                if line and "=" in line and not line.startswith("#"):
                    key, value = map(str.strip, line.split("=", 1))
                    if value and (
                        (value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")
                    ):
                        value = value[1:-1]
                    result[key] = value
        else:
            _print(f"Environment file {filepath} does not exist")
        return result

    def find_and_load_dotenv(self) -> typing.Dict[typing.AnyStr, typing.AnyStr]:
        env_file_path = self.find_dotenv_file()
        if not env_file_path:
            return {}
        return self.parse_dot_env(env_file_path)
