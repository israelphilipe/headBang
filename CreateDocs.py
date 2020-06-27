import os
import json
import markdown

COMMANDS_PATH = os.path.abspath(os.path.realpath(f'./commands.json'))


def create_commands_md():
    file = open("commands.json")
    commands_json = json.load(file)
    string = "# Commands :\n"
    with open("README.md", "w", encoding="utf-8", errors="xmlcharrefreplace") as output_file:
        for command in commands_json:
            string += f"## {command['name']}\n##### {command['description']}\n"
            if 'args' in command:
                string += f"* Arguments : {command['args']}\n"
        md = markdown.markdown(string)
        output_file.write(md)


create_commands_md()
