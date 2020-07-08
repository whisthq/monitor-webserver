from app.imports import *
from app.logger import *
from app.helpers.sql import *


def deleteLogsInS3(connection_id, devEnv="prod"):
    def S3Delete(file_name):
        bucket = "fractal-protocol-logs"

        # remove url, keep filename only
        file_name = file_name.replace(
            "https://fractal-protocol-logs.s3.amazonaws.com/", ""
        )

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

    dbUrl = (
        os.getenv("STAGING_DATABASE_URL")
        if devEnv == "staging"
        else os.getenv("DATABASE_URL")
    )

    ENGINE = sqlalchemy.create_engine(dbUrl, echo=False, pool_pre_ping=True)

    with ENGINE.connect() as conn:
        command = text(
            """
			SELECT * FROM logs WHERE "connection_id" = :connection_id
			"""
        )

        params = {"connection_id": connection_id}
        logs_found = (cleanFetchedSQL(conn.execute(command, **params).fetchall()))[0]
        success_serverlogs = None

        # delete server log for this connection ID
        if logs_found["server_logs"]:
            success_serverlogs = S3Delete(logs_found["server_logs"])
            if success_serverlogs:
                sendInfo("Successfully deleted log: " + str(logs_found["server_logs"]))
            else:
                sendInfo("Could not delete log: " + str(logs_found["server_logs"]))

        # delete the client logs
        if logs_found["client_logs"]:
            # sendInfo(logs_found["client_logs"])
            success_clientlogs = S3Delete(logs_found["client_logs"])
            if success_clientlogs:
                sendInfo("Successfully deleted log: " + str(logs_found["client_logs"]))
            else:
                sendInfo("Could not delete log: " + str(logs_found["client_logs"]))

        command = text(
            """
			DELETE FROM logs WHERE "connection_id" = :connection_id
			"""
        )

        params = {"connection_id": connection_id}
        conn.execute(command, **params)

        conn.close()
        return 1
    return -1
