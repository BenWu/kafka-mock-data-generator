#!/usr/bin/env python3

import json
import random
import sys
import time
from pathlib import Path
from typing import Dict

import click
from confluent_kafka import KafkaError, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from kafka_mock_data_generator.data_generator import data_generator

delivered_records = 0


def read_ccloud_config(config_file):
    """Read Confluent Cloud configuration for librdkafka clients

    Configs: https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
    """

    conf = {}
    with open(config_file) as fh:
        for line in fh:
            line = line.strip()
            if len(line) != 0 and line[0] != "#":
                parameter, value = line.strip().split("=", 1)
                conf[parameter] = value.strip()

    return conf


def get_table_config(config_path: Path):
    return data_generator.parse_config(config_path)


def acked(err, msg):
    global delivered_records

    if err is not None:
        print(f"Failed to deliver message: {err}")
    else:
        delivered_records += 1


def create_topic(
    config: Dict, topic: str, partition_count: int, replication_factor: int
):
    client = AdminClient(config)

    topics = client.create_topics(
        [
            NewTopic(
                topic,
                num_partitions=partition_count,
                replication_factor=replication_factor,
            )
        ]
    )
    for topic, future in topics.items():
        try:
            future.result()
            print("Topic {} created".format(topic))
        except Exception as e:
            if e.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                print(f"Failed to create topic {topic}: {e}")
                sys.exit(1)


def start_producer(
    table_config: Path,
    kafka_config: Path,
    topic_template: str,
    autocreate_topic: bool,
    topic_replication_factor: int,
    topic_partition_count: int,
    verbose: bool,
):
    tables = get_table_config(table_config)

    producer_config = read_ccloud_config(kafka_config)

    producer = Producer(producer_config)

    for table in tables:
        topic_name = topic_template.format(name=table.name)
        if autocreate_topic:
            create_topic(
                producer_config,
                topic_name,
                topic_partition_count,
                topic_replication_factor,
            )

    try:
        while True:
            for table in tables:
                data = table.generate_value()

                topic_name = topic_template.format(name=table.name)
                record_key = table.name
                record_value = json.dumps(data)

                if verbose:
                    print(f"Producing record: {record_key}\t\t{record_value}")

                producer.produce(
                    topic_name, key=record_key, value=record_value, on_delivery=acked
                )

                # pause for log normal distributed random time
                time.sleep(random.lognormvariate(0, 0.2))

    except KeyboardInterrupt:
        pass
    finally:
        producer.flush()
        print(f"{delivered_records} messages sent")


@click.command()
@click.option("--table-config", required=True, type=Path, help="Path to mock table data config")
@click.option(
    "--kafka-config", required=True, type=Path, help="Path to Confluent Cloud configuration file"
)
@click.option(
    "--topic-template",
    default="{name}",
    help="Template string for topic name where {name} is the table name",
)
@click.option(
    "--autocreate-topic/--no-autocreate-topic",
    default=False,
    type=bool,
    help="Whether topic is autocreated",
)
@click.option(
    "--topic-replication-factor",
    default=1,
    type=int,
    help="Topic replication factor for autocreation",
)
@click.option(
    "--topic-partition-count",
    default=1,
    type=int,
    help="Topic partition count for autocreation",
)
@click.option(
    "--verbose/-no-verbose", default=False, type=bool, help="Verbose log output"
)
def entrypoint(
    table_config,
    kafka_config,
    topic_template,
    autocreate_topic,
    topic_replication_factor,
    topic_partition_count,
    verbose,
):
    start_producer(
        table_config,
        kafka_config,
        topic_template,
        autocreate_topic,
        topic_replication_factor,
        topic_partition_count,
        verbose,
    )


if __name__ == "__main__":
    entrypoint()
