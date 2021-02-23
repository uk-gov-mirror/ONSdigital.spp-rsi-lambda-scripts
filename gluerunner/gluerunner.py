import boto3
import os
from es_aws_functions import general_functions

current_module = "spp-res_lam_glue_runner"

# Load environment variables
environment = os.environ.get("environment")
spark_glue_job_capacity = int(os.environ.get("spark_glue_job_capacity"))
ingest_glue_name = os.environ.get("ingest_glue_name")
emr_glue_name = os.environ.get("emr_glue_name")

# Set up logger with just environment at first
logger = general_functions.get_logger(None, current_module, environment, None)
glue = boto3.client("glue")


def start_glue_jobs(job_name, config):
    try:
        response = glue.start_job_run(
            JobName=job_name,
            Arguments=config,
            MaxCapacity=spark_glue_job_capacity,
        )
        logger.info(f"Started job {response['JobRunId']}")
    except Exception as e:
        logger.error(f"Error starting glue job {job_name}. Error: {e}")


def check_glue_job(glue_info):
    args_pass = {}

    if glue_info['detail']['state'] == "SUCCEEDED":
        logger.info(f"Job with Run Id {glue_info['detail']['jobRunId']} SUCCEEDED.")
        response = glue.get_job_run(
            JobName=glue_info["detail"]["jobName"],
            RunId=glue_info["detail"]["jobRunId"]
        )
        args_pass = response["JobRun"]["Arguments"]
    elif glue_info['detail']['state'] in ["FAILED", "STOPPED", "TIMEOUT"]:
        logger.error(
            f"{glue_info['detail']['jobName']} {glue_info['detail']['state']}. Error: {glue_info['detail']['message']}"
        )
    else:
        logger.error(f"Glue job {glue_info['detail']['jobName']} response does not contain state.")

    return args_pass


def handler(event, context):
    if "source" in event and event["source"] == "aws.glue":
        if event["detail"]["jobName"] == ingest_glue_name:
            config_to_pass = check_glue_job(event)
            if config_to_pass:
                start_glue_jobs(emr_glue_name, config_to_pass)
            else:
                # this means config_to_pass is empty
                logger.error("Failed to retrieve arguments from finished ingest glue")
        elif event["detail"]["jobName"] == emr_glue_name:
            config_to_pass = check_glue_job(event)
    else:
        # Initial config should be loaded correctly in api_handler.py
        start_glue_jobs(ingest_glue_name, event)
