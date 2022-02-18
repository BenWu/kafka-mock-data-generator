# Kafka Mock Data Generator

Config-based mock data generator and associated Kafka producer.
Types are roughly based on MySQL and the 
[Debezium connector](https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-data-types) for MySQL.
Random number generation uses a uniform distribution.

## Usage

### Data Generator

The data generator uses a yaml config ([example](./config/source_config.yaml)) to create a table
with associated fields to generate random data for.

Example usage:
```sh
./kafka_mock_data_generator/data_generator/data_generator.py \
  --schema-file config/source_config.yaml
```

See available options with:
```sh
./kafka_mock_data_generator/data_generator/data_generator.py --help
```

Supported types are integers, floats, strings, and datetime/timestamps.  
Datetime and timestamps are represented as an integer of milliseconds since epoch.

Supported configs: 
- Integers and floats support `min` and `max` options as numbers.
- Datetime and timestamps support `min` and `max` options as an ISO8601 date value.
- Strings support:
  - `min` and `max` which specifies the length
  - `chars` which specifies the character set to use 
    (options are `ascii`, `letters`, `lower`, `upper`, `alphanumeric`, `numbers`)
  - `enum` which takes a list a predefined list of possible values, this takes
    precedence over other options

### Kafka Producer

The Kafka producer uses the data generator to send records to topics in a Kafka cluster.
This uses librdkafka and configurations must be provided with a config file ([example](./config/producer.local.config)).
Available configurations can be found at https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md.

Example usage:
```sh
./kafka_mock_data_generator/kafka_producer/producer.py \
  --table-config config/source_config.yaml \
  --kafka-config=config/producer.local.config \
  --topic-template mock_test1.{name} \
  --autocreate-topic \
  --verbose
```

See available options with:
```sh
./kafka_mock_data_generator/kafka_producer/producer.py --help
```

## Development

Setup:
```sh
pip install -r requirements.txt
pip install -e .
```
