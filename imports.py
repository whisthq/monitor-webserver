import time
import threading
import traceback
from datetime import datetime, timedelta
import os
import sqlalchemy
from sqlalchemy.sql import text

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail

from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import DiskCreateOption
from msrestazure.azure_exceptions import CloudError