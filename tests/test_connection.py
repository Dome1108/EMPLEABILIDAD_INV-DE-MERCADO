import unittest
from unittest.mock import MagicMock, patch

from data_access import connect


class ConnectionConfiguration(unittest.TestCase):
    def test_internal_certificate_defaults_and_explicit_overrides(self):
        cases = [
            ({}, 'yes'),
            ({'server': 'SNBI03'}, 'yes'),
            ({'server': 'OTHER-SERVER'}, 'no'),
            ({'server': 'SNBI03', 'trust_server_certificate': False}, 'no'),
        ]
        for config, expected in cases:
            with self.subTest(config=config), \
                 patch('data_access.pyodbc.drivers', return_value=['ODBC Driver 17 for SQL Server']), \
                 patch('data_access.pyodbc.connect', return_value=MagicMock()) as odbc:
                connect(config)
                connection_string = odbc.call_args.args[0]
                self.assertIn(f'TrustServerCertificate={expected};', connection_string)
                self.assertIn('Encrypt=yes;', connection_string)
                self.assertIn('Trusted_Connection=yes', connection_string)


if __name__ == '__main__':
    unittest.main()
