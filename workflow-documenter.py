#!/usr/bin/env python
"""
The following exit status codes have meaning:
0 - Success
1 - File not found
2 - Not Required but no default
3 - Required and has default
4 - No description
5 - No type
"""

# Stdlib imports
import os
import sys
import json
import time
import argparse
import subprocess

# 3rd party imports
import yaml


class WorkflowParser:
    def __init__(self, fn=False):
        self._ast = {"inputs": [], "secrets": []}
        self._top = True
        self._valid = True
        self._input = None
        self._otput = None

        if fn and os.path.isfile(fn):
            self._input = fn
            self._otput = f"{os.path.basename(fn).split('.ya')[0]}.md"
            self._data = yaml.safe_load(open(fn, "r").read())
            if "name" not in self._data.keys():
                raise DocumentError(
                    "No name element in this workflow. If indeed, that is what it is."
                )

            if "on" in self._data.keys() and True not in self._data.keys():
                self._top = "on"
            elif True in self._data.keys() and "on" not in self._data.keys():
                self._top = True

            # Validate secrets and inputs if they are present
            # separate the inputs and secrets if they're there
            for k, v in {"inputs": {}, "secrets": {}}.items():
                if (
                    type(self._data[self._top]) == dict
                    and k in self._data[self._top]["workflow_call"].keys()
                ):
                    for k2, v2 in self._data[self._top]["workflow_call"][k].items():
                        _td = {
                            "name": k2,
                            "description": v2.get("description", False),
                            "type": v2.get("type", False),
                            "default": v2.get("default", False),
                            "required": v2.get("required", False),
                        }
                        if not _td.get("description"):
                            raise WorkflowError(
                                f"{self._input}:on->workflow_call->{k}->{_td['name']} has no description."
                            )
                        if k == "inputs" and not _td.get("type"):
                            raise WorkflowError(
                                f"{self._input}:on->workflow_call->{k}->{_td['name']} has no type."
                            )
                        # print(_td)
                        self._ast[k].append(_td)

    def __str__(self):
        return str(self._ast)

    def __repr__(self):
        return self.__str__()

    @property
    def name(self):
        return self._data["name"]

    @property
    def valid(self):
        return self._valid

    @property
    def input(self):
        return self._input

    @property
    def output(self):
        return self._otput

    def to_markdown(self):
        def input_value(i):
            if i["type"] == "string":
                return f"      {i['name']}: \"{i['description']}\""
            elif i["type"] == "bool":
                return f"      {i['name']}: {i['default']}"
            else:
                return f"      {i['name']}: {i['default']}"

        def dump_input(i, d):
            retv = [f"## {i}", ""]
            for itm in d:
                retv.append(f"### {itm['name']}")
                retv.append("")
                for k, v in itm.items():
                    if k != "name":
                        retv.append(f"- **{k}**: {v}")
                retv.append("")
            return retv

        retv = []
        retv.append(f"# ({self._input}) {self.name}")
        retv.append("")
        retv.append("## Example")
        retv.append("")
        retv.append("```yaml")
        retv.append("name: ExampleService-DEV")
        retv.extend("on:\n  push:\n    branches: [main]".split("\n"))
        retv.extend("jobs:\n  build:".split("\n"))
        retv.append(
            f"    uses: aplaceformom/workflows/.github/workflows/{self._input}@main"
        )
        # if any inputs are required, put them in the example
        reqd = []
        for i in self._ast["inputs"]:
            if "required" in i.keys() and i["required"]:
                reqd.append(input_value(i))
            elif i["type"] == "bool":
                reqd.append(input_value(i))
        if len(reqd) > 0:
            retv.append("    with:")
            retv.extend(reqd)
        retv.append("```")
        retv.append("")
        for items in self._ast.keys():
            retv.extend(dump_input(items, self._ast[items]))
        return "\n".join(retv)


class WorkflowError(Exception):
    pass


class DocumentError(Exception):
    pass


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        parser = argparse.ArgumentParser(
            prog=os.path.basename(sys.argv[0]),
            description="Generates documentation for Github Actions Re-usable Workflows",
        )
        parser.add_argument(
            "-d",
            "--outdir",
            help="Specify the output directory (default: `./docs/`).",
            default="./docs",
        )
        parser.add_argument(
            "inputs",
            metavar="inputs",
            type=str,
            nargs="+",
            help="The space separated list of files to parse.",
        )
        args = parser.parse_args()
        args.inputs.sort()
        care_about = []

        if len(args.inputs) <= 0:
            p = subprocess.run(
                "git diff --cached --name-only",
                shell=True,
                check=True,
                capture_output=True,
            )
            for change in p.stdout.decode("utf-8").split("\n"):
                if change.startswith(".github/workflows/") and change.endswith(".yaml"):
                    care_about.append(change)
        else:
            care_about = args.inputs
            # Now that we've parsed any commandline args, we can parse all of our workflows and build
            # a list of objects to dump to individual files. That's the fun part.
            flows = []
            for arg in care_about:
                obj = WorkflowParser(arg)
                # Check to see if the output already exists
                if os.path.isfile(f"{args.outdir}/{obj.output}"):
                    print(time.time() - os.stat(f"{args.outdir}/{obj.output}").st_mtime)
                    # and if it was regenerated within the last minute
                    if (
                        time.time() - os.stat(f"{args.outdir}/{obj.output}").st_mtime
                    ) <= 30:
                        continue
                if args.outdir and os.path.isdir(args.outdir):
                    with open(f"{args.outdir}/{obj.output}", "w+") as fp:
                        print(f"Processed: {obj.input} -> {args.outdir}/{obj.output}")
                        fp.write(obj.to_markdown())
