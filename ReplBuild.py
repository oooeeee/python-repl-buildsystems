import os
import sublime
import sublime_plugin


SETTINGS_FILE = "ReplBuild.sublime-settings"


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

    def get_setting_name(self, setting_name, default):
        settings = self.window.active_view().settings()
        value = settings.get(setting_name, None)
        if value is not None:
            print("Using '{}'='{}' from project settings".format(setting_name, value))
            return value
        settings = sublime.load_settings(SETTINGS_FILE)
        value = settings.get(setting_name, default)
        print("Using '{}'='{}' from common settings".format(setting_name, value))
        return value

    def get_python_path(self):
        return self.get_setting_name('replbuild.pythonPath', 'python3.11')

    def get_poetry_path(self):
        return self.get_setting_name('replbuild.poetryPath', 'poetry')

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

    def parse_dot_env(self):
        environment_file = self.get_setting_name('replbuild.envFile', '.env')
        result = {}
        variables = self.window.extract_variables()
        working_dir = variables.get('folder')
        if working_dir:
            path = os.path.join(working_dir, environment_file)
            if os.path.exists(path):
                with open(path, 'r') as file:
                    for line in file:
                        if line and '=' in line and not line.startswith('#'):
                            values = line.split('=', 1)
                            if len(values) == 2:
                                key, value = values
                                result[key.strip()] = value.strip()
            else:
                print("Environment file {} is not exists".format(path))
        # print("Parsed .env:", result)
        return result
