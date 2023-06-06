import os
import typing
import sublime_plugin


class python_repl(sublime_plugin.WindowCommand):
    """
    Starts a SublimeREPL, attempting to use project's specified
    python interpreter.
    """
    additional_args = []

    def run(self, open_file='$file', *args, **kwargs):
        """Called on project_venv_repl command"""
        cmd_list = [self.get_project_interpreter(), '-i']
        if kwargs.get('poetry'):
            cmd_list.extend(('-m', 'poetry', 'run', 'python'))
        if kwargs.get('pytest'):
            cmd_list.extend(['-m', 'pytest', '-vvv', '-s'])
            if kwargs.get('collect_only'):
                cmd_list.append("--collect-only")
            if kwargs.get('exit_first'):
                cmd_list.append("--exitfirst")
            if kwargs.get('approvals_update'):
                cmd_list.append("--approvals-update")

        if open_file:
            cmd_list.append(open_file)

        self.repl_open(cmd_list=cmd_list)

    def get_project_interpreter(self):
        """Return the project's specified python interpreter, if any"""
        settings = self.window.active_view().settings()
        return settings.get('python_interpreter', 'python3.11')

    def get_extra_envs(self):
        settings = self.window.active_view().settings()
        return settings.get('env', {})

    def repl_open(self, cmd_list):
        """Open a SublimeREPL using provided commands"""
        env = self.parse_dot_env()
        env.update(self.get_extra_envs())
        self.window.run_command(
            'repl_open', {
                'encoding': 'utf-8',
                'type': 'subprocess',
                'cmd': cmd_list,
                'cwd': '$file_path',
                "external_id": "REPL",
                'syntax': 'Packages/Python/Python.tmLanguage',
                "extend_env": env
            }
        )

    def parse_dot_env(self) -> typing.Dict[str, str]:
        result = {}
        variables = self.window.extract_variables()
        working_dir = variables.get('folder')
        if working_dir:
            path = os.path.join(working_dir, '.env')
            if os.path.exists(path):
                with open(path, 'r') as file:
                    for line in file:
                        if line and '=' in line and not line.startswith('#'):
                            values = line.split('=', 1)
                            if len(values) == 2:
                                key, value = values
                                result[key.strip()] = value.strip()
        # print("Parsed .env:", result)
        return result
