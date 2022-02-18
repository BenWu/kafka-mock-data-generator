import re
import random
import string
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import click
import yaml

# Types are based on MySQL and Debezium
# From https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-data-types
INTEGER_TYPES = {"TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT"}

FLOAT_TYPES = {"REAL", "FLOAT", "DOUBLE", "DECIMAL"}

STRING_TYPES = {
    "CHAR",
    "VARCHAR",
    "TINYTEXT",
    "TEXT",
    "MEDIUMTEXT",
    "LONGTEXT",
    "TINYBLOB",
    "BLOB",
    "MEDIUMBLOB",
    "LONGBLOB",
    "JSON",
}

DATETME_TYPES = {"DATETIME", "TIMESTAMP"}


class TableField(ABC):
    def __init__(self, name: str):
        self.name = name
        super().__init__()

    def __str__(self):
        return self.name

    @abstractmethod
    def generate(self):
        pass

    def unrecognized_option(self, option):
        if option != "type":
            print(f"Unrecognized option {option} for {self.__class__} {self.name}")


class IntegerField(TableField):
    min_val = -1_000_00
    max_val = 1_000_000

    def __init__(self, name: str, options: Dict[str, str]):
        super().__init__(name)

        for option, value in options.items():
            if option == "min":
                assert isinstance(value, int)
                self.min_val = value
            elif option == "max":
                assert isinstance(value, int)
                self.max_val = value
            else:
                self.unrecognized_option(option)

    def generate(self) -> int:
        return random.randint(self.min_val, self.max_val)


class FloatField(TableField):
    min_val = -1_000_00
    max_val = 1_000_000

    def __init__(self, name: str, options: Dict[str, str]):
        super().__init__(name)

        for option, value in options.items():
            if option == "min":
                assert isinstance(value, int) or isinstance(value, float)
                self.min_val = value
            elif option == "max":
                assert isinstance(value, int) or isinstance(value, float)
                self.max_val = value
            else:
                self.unrecognized_option(option)

    def generate(self) -> float:
        return random.uniform(self.min_val, self.max_val)


class StringField(TableField):
    min_len = 1
    max_len = 10
    allowed_chars = string.ascii_letters
    allowed_values = None  # allowed values takes precedence over other options

    allowed_chars_map = {
        "letters": string.ascii_letters,
        "lower": string.ascii_lowercase,
        "upper": string.ascii_uppercase,
        "ascii": string.ascii_letters + string.punctuation + string.digits + " ",
        "numbers": string.digits,
        "alphanumeric": string.ascii_letters + string.digits,
    }

    def __init__(self, name: str, options: Dict[str, str]):
        super().__init__(name)

        for option, value in options.items():
            if option == "min":
                assert isinstance(value, int)
                self.min_len = value
            elif option == "max":
                assert isinstance(value, int)
                self.max_len = value
            elif option == "chars":
                try:
                    self.allowed_chars = self.allowed_chars_map[value]
                except KeyError:
                    raise ValueError(
                        f"Character type {value} for {self.name} not found, "
                        f"must be one of {', '.join(self.allowed_chars_map.values())}."
                    )
            elif option == "enum":
                assert isinstance(value, list)
                for v in value:
                    assert isinstance(v, str)
                self.allowed_values = value
            else:
                self.unrecognized_option(option)

    def generate(self) -> str:
        if self.allowed_values is not None and len(self.allowed_values) > 0:
            return random.choice(self.allowed_values)
        else:
            return "".join(
                random.choice(self.allowed_chars)
                for _ in range(random.randint(self.min_len, self.max_len))
            )


class DatetimeField(TableField):
    min_date = "2020-01-01"
    max_date = "2022-12-31"
    min_val = 0
    max_val = 0

    def __init__(self, name: str, options: Dict[str, str]):
        super().__init__(name)

        for option, value in options.items():
            if option == "min":
                self.min_date = str(value)
            elif option == "max":
                self.max_date = str(value)
            else:
                self.unrecognized_option(option)

        self.min_val = int(datetime.fromisoformat(self.min_date).timestamp() * 1000)
        self.max_val = int(datetime.fromisoformat(self.max_date).timestamp() * 1000)

    def generate(self) -> int:
        return random.randint(self.min_val, self.max_val)


class TableSchema:
    fields: List[TableField] = []

    def __init__(self, name: str):
        self.name = name

    def add_field(self, field: TableField):
        self.fields.append(field)

    def generate_value(self):
        return {field.name: field.generate() for field in self.fields}

    def __str__(self):
        return f"{self.name}: {[f.name for f in self.fields]}"


@click.command()
@click.option(
    "--schema-file",
    required=True,
    type=Path,
    help="Path to config file containing table definitions",
)
@click.option("--seed", type=int, help="Optional seed for random number generator")
def parse_config(schema_file, seed):
    with open(schema_file, "r") as f:
        config = yaml.safe_load(f)

    tables = []

    for table_name, fields in config.items():
        table_schema = TableSchema(table_name)

        for field_name, field_options in fields.items():
            try:
                # match varchar, varchar(20), float(20,10), etc.
                type_value = re.findall(
                    r"^([a-zA-Z]+)(?:\([0-9]*(?:,[0-9]+)?\))?$", field_options["type"]
                )[0]
            except KeyError:
                raise ValueError(f"Type value not found for {table_name} {field_name}")
            except IndexError:
                raise ValueError(
                    f"Unrecognized type value {field_options[type]} found for {table_name} {field_name}"
                )

            type_value = type_value.upper()
            if type_value in INTEGER_TYPES:
                field = IntegerField(field_name, field_options)
            elif type_value in FLOAT_TYPES:
                field = FloatField(field_name, field_options)
            elif type_value in STRING_TYPES:
                field = StringField(field_name, field_options)
            elif type_value in DATETME_TYPES:
                field = DatetimeField(field_name, field_options)
            else:
                raise ValueError(
                    f"Unrecognized type value {field_options[type]} found for {table_name} {field_name}"
                )

            table_schema.add_field(field)

        tables.append(table_schema)
    pass
    return tables


if __name__ == "__main__":
    parse_config()
