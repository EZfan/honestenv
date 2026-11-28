import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from honestenv import trusted_runner


FIXTURES = Path(__file__).parent / "fixtures" / "scoring"


class TrustedScoringTest(unittest.TestCase):
    def test_submission_must_return_a_correct_result(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            with patch.object(trusted_runner, "_APP_DIR", str(app)), patch.object(trusted_runner, "_IDENTITY", {}):
                call = trusted_runner.call("reservation", "is_reserved")
                for name in ("early_exit", "empty", "abnormal"):
                    (app / "reservation.py").write_bytes((FIXTURES / "negative" / f"{name}.py").read_bytes())
                    with self.subTest(name=name), self.assertRaises(AssertionError):
                        call(10, 20, 30)
                (app / "reservation.py").write_bytes((FIXTURES / "negative" / "incorrect.py").read_bytes())
                self.assertNotEqual(call(10, 20, 30), False)
                (app / "reservation.py").write_bytes((FIXTURES / "reservation-window" / "reservation.py").read_bytes())
                self.assertIs(call(10, 20, 30), False)
                self.assertIs(call(25, 20, 30), True)

    def test_tuple_arguments_are_preserved(self):
        with patch.object(trusted_runner, "_APP_DIR", str(FIXTURES / "invoice-cents")), patch.object(trusted_runner, "_IDENTITY", {}):
            total = trusted_runner.call("invoice", "invoice_total")
            self.assertEqual(total([(113, 3), (10, 2)]), 359)


if __name__ == "__main__":
    unittest.main()
