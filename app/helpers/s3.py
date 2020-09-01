from app.imports import *
from app.logger import (
    sendInfo,
    sendDebug,
    sendError,
)
from app.helpers.sql import *


def deleteLogsInS3(log, devEnv="prod"):
    """Delete a specified log file in AWS S3

    Args:
        log (JSON): JSON object of a protocol log file
        devEnv (string): production or staging

    Returns:
        int: 1 if successfully deleted log, else -1
    """

    def S3Delete(file_name):
        bucket = "fractal-protocol-logs"

        # remove url, keep filename only
        file_name = file_name.replace("https://fractal-protocol-logs.s3.amazonaws.com/", "",)

        s3 = boto3.resource(
            "s3",
            region_name="us-east-1",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
        )

        try:
            sendInfo("Deleting log with filename: " + str(file_name))
            s3.Object(bucket, file_name).delete()
            return True
        except Exception as e:
            sendError("Error deleting log: " + str(e))
            return False

    dbUrl = os.getenv("STAGING_DATABASE_URL") if devEnv == "staging" else os.getenv("DATABASE_URL")

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True,)

    with ENGINE.connect() as conn:
        success_serverlogs = None

        # delete server log for this connection ID
        if log["server_logs"]:
            success_serverlogs = S3Delete(log["server_logs"])
            if success_serverlogs:
                sendInfo("Successfully deleted log: " + str(log["server_logs"]))
            else:
                sendInfo("Could not delete log: " + str(log["server_logs"]))

        # delete client logs
        if log["client_logs"]:
            # sendInfo(logs_found["client_logs"])
            success_clientlogs = S3Delete(log["client_logs"])
            if success_clientlogs:
                sendInfo("Successfully deleted log: " + str(log["client_logs"]))
            else:
                sendInfo("Could not delete log: " + str(log["client_logs"]))

        command = text(
            """
			DELETE FROM logs WHERE "connection_id" = :connection_id
			"""
        )

        params = {"connection_id": log["connection_id"]}
        conn.execute(command, **params)

        conn.close()
        return 1
    return -1
