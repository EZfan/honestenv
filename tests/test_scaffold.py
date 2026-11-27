import inspect
import unittest
from dataclasses import fields
from pathlib import Path

import honestenv
from honestenv import CheckReport, CommandResult, GateReport, TaskPackage
from honestenv import cli, harbor_cli, package, types
from honestenv.gates import lint, schema


class ScaffoldTest(unittest.TestCase):
    def test_types(self):
        expected = {
            TaskPackage: {"root": Path, "content_hash": str},
            GateReport: {"name": str, "passed": bool, "details": str},
            CheckReport: {"package": TaskPackage, "gates": list[GateReport], "passed": bool},
            CommandResult: {"argv": list[str], "returncode": int, "stdout": str, "stderr": str, "reward": float | int | None},
        }
        for cls, annotations in expected.items():
            with self.subTest(cls=cls):
                self.assertIs(getattr(types, cls.__name__), cls)
                self.assertIn(cls.__name__, honestenv.__all__)
                self.assertEqual([(f.name, f.type) for f in fields(cls)], list(annotations.items()))

    def test_signatures(self):
        parameter = inspect.Parameter
        positional = parameter.POSITIONAL_OR_KEYWORD
        expected = [
            (package.load, [parameter("path", positional, annotation=Path)], TaskPackage),
            (package.content_hash, [parameter("package", positional, annotation=TaskPackage)], str),
            (harbor_cli.lint, [
                parameter("task_dir", positional, annotation=Path),
                parameter("extend_select_all", parameter.KEYWORD_ONLY, default=True, annotation=bool),
            ], CommandResult),
            (schema.check_schema, [parameter("package", positional, annotation=TaskPackage)], GateReport),
            (lint.check_lint, [parameter("package", positional, annotation=TaskPackage)], GateReport),
            (cli.main, [], None),
        ]
        for function, parameters, return_type in expected:
            with self.subTest(function=function.__name__):
                self.assertEqual(inspect.signature(function), inspect.Signature(parameters, return_annotation=return_type))


if __name__ == "__main__":
    unittest.main()
