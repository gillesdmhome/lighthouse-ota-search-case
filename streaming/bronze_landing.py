"""
Apache Beam streaming pipeline: Pub/Sub → bronze landing (BigQuery + GCS).

Deploy as a Dataflow Flex Template on GCP.
Run locally with DirectRunner for development:

    python streaming/bronze_landing.py \\
        --runner DirectRunner \\
        --input_subscription projects/PROJECT/subscriptions/ota-searches-sub \\
        --output_table lighthouse-dev:ota_bronze.raw_ota_searches \\
        --output_path gs://lighthouse-ota-bronze/raw/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions


class ParseAndEnrichFn(beam.DoFn):
    """Parse Pub/Sub message, compute metadata, route valid/invalid records."""

    def process(self, element):
        try:
            raw = element.decode("utf-8") if isinstance(element, bytes) else element
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            yield beam.pvalue.TaggedOutput("invalid", {"error": str(exc), "raw": str(element)[:500]})
            return

        dedup_key = hashlib.sha256(
            f"{data.get('hotel_id')}|{data.get('timestamp')}|"
            f"{data.get('user_country')}|{data.get('arrival_date')}".encode()
        ).hexdigest()

        record = {
            "event_id": str(uuid.uuid4()),
            "dedup_key": dedup_key,
            "ingestion_time": datetime.now(timezone.utc).isoformat(),
            "payload": json.dumps(data),
            "hotel_id": data.get("hotel_id"),
            "search_timestamp": data.get("timestamp"),
        }

        if not data.get("hotel_id") or not data.get("timestamp"):
            yield beam.pvalue.TaggedOutput("invalid", {"error": "missing required fields", "record": record})
            return

        yield record


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_subscription", required=True, help="Pub/Sub subscription path")
    parser.add_argument("--output_table", required=True, help="BigQuery table spec project:dataset.table")
    parser.add_argument("--output_path", required=True, help="GCS path prefix for raw JSON archive")
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(StandardOptions).streaming = True

    with beam.Pipeline(options=pipeline_options) as pipeline:
        parsed = (
            pipeline
            | "ReadPubSub" >> beam.io.ReadFromPubSub(subscription=known_args.input_subscription)
            | "ParseAndEnrich" >> beam.ParDo(ParseAndEnrichFn()).with_outputs("invalid", main="valid")
        )

        parsed.valid | "WriteBigQuery" >> beam.io.WriteToBigQuery(
            known_args.output_table,
            schema={
                "fields": [
                    {"name": "event_id", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "dedup_key", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "ingestion_time", "type": "TIMESTAMP", "mode": "REQUIRED"},
                    {"name": "payload", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "hotel_id", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "search_timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
                ]
            },
            write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
            create_disposition=beam.io.BigQueryDisposition.CREATE_NEVER,
        )

        parsed.valid | "FormatJSON" >> beam.Map(lambda r: json.dumps(r)) | "WriteGCS" >> beam.io.WriteToText(
            known_args.output_path,
            file_suffix=".jsonl",
            num_shards=1,
        )

        parsed.invalid | "LogInvalid" >> beam.Map(
            lambda r: json.dumps({"level": "ERROR", "detail": r})
        )


if __name__ == "__main__":
    run()
