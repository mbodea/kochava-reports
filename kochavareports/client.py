from __future__ import absolute_import
import requests
import json
import time

from .constant import ReportCategory
from .exception import (
    HttpException, ApiException, ApiResponseException,
    ApiResponseException,
    PollMaxRetryException
)
from . import request as client_request
from . import response as client_response


class Credentials(object):
    def __init__(self, api_key=None, app_guid=None):
        self.api_key = api_key
        self.app_guid = app_guid

    def __str__(self):
        return str(self.__dict__)

    def __unicode__(self):
        return unicode(self.__dict__)

    def __repr__(self):
        return 'KochavaCredentials(**' + str(self.__dict__) + ')'

    def to_dict(self):
        return self.__dict__

DEFAULT_API_VERSION = 'v1.2'
API_ENDPOINT = 'https://reporting.api.kochava.com/'


class RequestEndpoint(object):
    GROUPING_FIELDS = 'grouping'
    FILTERING_FIELDS = 'filtering'
    TIMEZONES = 'timezones'
    REPORT_TEMPLATES = 'templates'
    APPS = 'getapps'
    SCHEDULE_REPORT = 'schedule'
    REPORT_TOKENS = 'tokens'
    REPORT_COLUMNS = 'reportcolumns'
    REPORT_PROGRESS = 'progress'


class Client(object):
    """
        Kochava client can be used to generate reports and query for metadata.
        The implemented functionality is not exhaustive and is focused on
        generating reports. Sample code below.

        1. Creating a report:

        time_start = "2017-01-25"
        time_end = "2017-02-07"
        traffic = ['click', 'install']
        traffic_grouping = ['network', 'campaign']
        time_series = '1'
        token = client.create_report(time_start=time_start, time_end=time_end,
                                     traffic=traffic,
                                     traffic_grouping=traffic_grouping,
                                     time_series=time_series)
        print token

        Report parameters list and examples can be found here:
        https://support.kochava.com/analytics-reports-api/api-v1-2-requesting-and-scheduling-reports
        https://support.kochava.com/analytics-reports-api/api-v1-2-call-structure

        2. Getting the report progress and read it, if completed:

        response = client.get_report_progress(token)
        if response.is_completed():
            report_data = client.read_report(response.get_report_url())
            print report_data
        else:
            print response.progress

        3. Polling until the report is completed:

        result = client.poll_report(token, retry_interval_seconds=1,
                                    start_delay_seconds=15, max_retries=30)
        print result
    """
    def __init__(self, credentials=None, api_version=DEFAULT_API_VERSION):
        self.credentials = credentials
        self.api_version = api_version

    def _get_url(self, endpoint):
        return API_ENDPOINT + self.api_version + '/' + endpoint

    def _get_data(self, url):
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            raise HttpException(e)
        except ValueError:
            raise ApiException("Empty data returned by Kochava.")

    def _post_data(self, url, data={}):
        try:
            r = requests.post(url, data=json.dumps(data))
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            raise HttpException(e)
        except ValueError:
            raise ApiException("Empty data returned by Kochava.")

    def get_valid_grouping_fields(self):
        url = self._get_url(RequestEndpoint.GROUPING_FIELDS)
        data = self._get_data(url)
        response = client_response.GetValidFieldsResponse(data)
        return response.valid_fields

    def get_valid_filtering_fields(self):
        url = self._get_url(RequestEndpoint.FILTERING_FIELDS)
        data = self._get_data(url)
        response = client_response.GetValidFieldsResponse(data)
        return response.valid_fields

    def get_valid_timezones(self):
        url = self._get_url(RequestEndpoint.TIMEZONES)
        data = self._get_data(url)
        response = client_response.GetValidFieldsResponse(data)
        return response.valid_fields

    def get_report_templates(self):
        url = self._get_url(RequestEndpoint.REPORT_TEMPLATES)
        data = self._get_data(url)
        response = client_response.GetTemplatesResponse(data)
        return response.template_values

    def get_report_columns(self, traffic):
        url = self._get_url(RequestEndpoint.REPORT_COLUMNS)
        request = client_request.GetReportColumnsRequest(self.credentials,
                                                         traffic)
        data = self._post_data(url, request.data)
        response = client_response.GetTemplatesResponse(data)
        return response.template_values

    def get_apps(self):
        url = self._get_url(RequestEndpoint.APPS)
        return self._post_data(url, self.credentials.to_dict())

    def create_report(self, reportCategory=ReportCategory.SUMMARY, **kwargs):
        request = client_request.CreateReportRequest(self.credentials,
                                                     reportCategory,
                                                     **kwargs)
        url = self._get_url(request.reportCategory)
        data = self._post_data(url, request.data)
        response = client_response.CreateReportResponse(data)
        return response.report_token

    def get_report_progress(self, token):
        request = client_request.GetReportProgressRequest(self.credentials,
                                                          token=token)
        url = self._get_url(RequestEndpoint.REPORT_PROGRESS)
        data = self._post_data(url, request.data)
        return client_response.GetReportProgressResponse(data)

    def read_report(self, url):
        return self._get_data(url)

    def wait_for_report(self, token, retry_interval_seconds=1,
                        start_delay_seconds=15, max_retries=60):
        if start_delay_seconds:
            time.sleep(start_delay_seconds)
        for x in range(0, max_retries):
            response = self.get_report_progress(token)
            if response.is_completed():
                return self.read_report(response.get_report_url())
            if retry_interval_seconds:
                time.sleep(retry_interval_seconds)
        raise PollMaxRetryException(
            'Max retry reached while polling request:' + str(max_retries))
