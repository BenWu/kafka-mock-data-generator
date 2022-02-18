from pathlib import Path
from unittest import TestCase

from kafka_mock_data_generator.data_generator import data_generator

CONFIG_DIR = Path(__file__).parent / "config"


class TestDataGenerator(TestCase):
    def test_generate_from_config(self):
        tables = data_generator.parse_config(CONFIG_DIR / "test_table_config.yaml", seed=123)

        self.assertEqual(len(tables), 2)

        expected_client_fields = {'id', 'first_name', 'last_name', 'middle_name', 'prefix', 'user_id', 'created_at', 'updated_at', 'title', 'group', 'company_id', 'account_id', 'email_address_id', 'phone_number', 'outstanding_balance', 'notes'}
        expected_event_fields = {'user_id', 'created_at', 'updated_at', 'object_id', 'type'}

        for table in tables:
            generated_data = table.generate_value()
            if table.name == "client":
                self.assertSetEqual(expected_client_fields, set(generated_data.keys()))
            elif table.name == "event":
                self.assertSetEqual(expected_event_fields, set(generated_data.keys()))
