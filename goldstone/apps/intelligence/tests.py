# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
# Copyright 2014 Solinea, Inc.
#

from django.test.client import Client
from django.test.client import RequestFactory
from django.test import TestCase
from django.conf import settings

from .views import IntelSearchView
from .models import *
import os
import json
from datetime import *
import pytz
import gzip
import logging

logger = logging.getLogger(__name__)


class LogDataModel(TestCase):
    maxDiff = None
    INDEX_NAME = 'logstash-test'
    DOCUMENT_TYPE = 'logs'
    TOTAL_DOCS = 1000
    conn = Elasticsearch(settings.ES_SERVER)

    def setUp(self):

        template_f = gzip.open(os.path.join(os.path.dirname(__file__), "..",
                                            "..", "..", "test_data",
                                            "data.json.gz"), 'rb')
        template = json.load(template_f)

        try:
            self.conn.indices.delete("_all")
        finally:
            {}

        self.conn.indices.create(self.INDEX_NAME, body=template)

        q = {"query": {"match_all": {}}}
        data_f = gzip.open(os.path.join(os.path.dirname(__file__), "..", "..",
                                        "..", "test_data",
                                        "data.json.gz"))
        data = json.load(data_f)
        for dataset in data:
            for event in dataset['hits']['hits']:
                rv = self.conn.index(self.INDEX_NAME, self.DOCUMENT_TYPE,
                                     event['_source'])

        self.conn.indices.refresh([self.INDEX_NAME])
        q = {"query": {"match_all": {}}}
        rs = self.conn.search(body=q, index="_all")
        self.assertEqual(rs['hits']['total'], self.TOTAL_DOCS)

    def tearDown(self):
        try:
            self.conn.indices.delete("_all")
        finally:
            {}

    def test_get_connection(self):
        q = dict(query={"match_all": {}})
        test_conn = LogData.get_connection("localhost")
        rs = test_conn.search(index="_all", body=q)
        self.assertEqual(rs['hits']['total'], self.TOTAL_DOCS)
        test_conn = LogData.get_connection("localhost:9200")
        rs = test_conn.search(index="_all", body=q)
        self.assertEqual(rs['hits']['total'], self.TOTAL_DOCS)
        test_conn = LogData.get_connection(["localhost"])
        rs = test_conn.search(index="_all", body=q)
        self.assertEqual(rs['hits']['total'], self.TOTAL_DOCS)

    def test_get_components(self):
        test_q = {
            "query": {
                "match_all": {}
            },
            "facets": {
                "components": {
                    "terms": {
                        "field": "component",
                        "all_terms": True
                    }
                }
            }
        }
        test_response = self.conn.search(index="_all", body=test_q)
        control = [d['term'] for d in
                   test_response['facets']['components']['terms']]

        comps = LogData().get_components(self.conn)
        self.assertEqual(sorted(comps), sorted(control))

    def test_get_loglevels(self):
        test_q = {
            "query": {
                "match_all": {}
            },
            "facets": {
                "loglevels": {
                    "terms": {
                        "field": "loglevel",
                        "all_terms": True
                    }
                }
            }
        }
        test_response = self.conn.search(index="_all", body=test_q)
        control = [d['term'] for d in
                   test_response['facets']['loglevels']['terms']]

        comps = LogData().get_loglevels(self.conn)
        self.assertEqual(sorted(comps), sorted(control))

    def test_subtract_months(self):
        d = LogData()._subtract_months(datetime(2014, 1, 1), 1)
        self.assertEqual(d, datetime(2013, 12, 1, 0, 0))
        d = LogData()._subtract_months(datetime(2013, 12, 1), 2)
        self.assertEqual(d, datetime(2013, 10, 1, 0, 0))
        d = LogData()._subtract_months(datetime(2013, 12, 1), 12)
        self.assertEqual(d, datetime(2012, 12, 1, 0, 0))

    def test_calc_start(self):
        d = LogData()._calc_start(datetime(2013, 12, 10, 12, 0, 0), 'hour')
        self.assertEqual(d, datetime(2013, 12, 10, 11, 0, tzinfo=pytz.utc))
        d = LogData()._calc_start(datetime(2013, 12, 10, 12, 0, 0), 'day')
        self.assertEqual(d, datetime(2013, 12, 9, 12, 0, tzinfo=pytz.utc))
        d = LogData()._calc_start(datetime(2013, 12, 10, 12, 0, 0), 'week')
        self.assertEqual(d, datetime(2013, 12, 3, 12, 0, tzinfo=pytz.utc))
        d = LogData()._calc_start(datetime(2013, 12, 10, 12, 0, 0), 'month')
        self.assertEqual(d, datetime(2013, 11, 10, 12, 0, tzinfo=pytz.utc))

    def test_range_filter_facet(self):
        def test_scenario():
            test_q = {'query': {'range': {
                '@timestamp': {'gte': start.isoformat(),
                               'lte': end.isoformat()}}}, 'facets': {
                facet_field: {
                    'facet_filter': {'term': {filter_field: filter_value}},
                    'terms': {'field': facet_field, 'all_terms': True,
                              'order': 'term'}}}}
            control = self.conn.search(index="_all", body=test_q)
            result = LogData().range_filter_facet(self.conn, start, end,
                                                  filter_field, filter_value,
                                                  facet_field)
            self.assertEqual(result['hits'], control['hits'])

        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)

        filter_field = 'component'
        filter_value = 'nova'
        facet_field = 'loglevel'
        test_scenario()
        filter_field = 'loglevel'
        filter_value = 'info'
        facet_field = 'component'
        test_scenario()

    def test_aggregate_facets(self):

        def test_scenario():
            control = {}
            for filter_value in filter_list:
                test_q = {'query': {'range': {
                    '@timestamp': {'gte': start.isoformat(),
                                   'lte': end.isoformat()}}}, 'facets': {
                    facet_field: {'facet_filter': {'term': {
                        filter_field: filter_value}},
                        'terms': {'field': facet_field,
                                  'all_terms': True,
                                  'order': 'term'}}}}
                r = self.conn.search(index="_all", body=test_q)
                control[filter_value] = r['facets']

            result = LogData().aggregate_facets(self.conn, start, end,
                                                filter_field, filter_list,
                                                facet_field)
            self.assertEqual(result, control)

        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)
        filter_field = 'component'
        filter_list = LogData().get_components(self.conn)
        facet_field = 'loglevel'
        test_scenario()

        filter_field = 'loglevel'
        filter_list = LogData().get_loglevels(self.conn)
        facet_field = 'component'
        test_scenario()

    def test_err_and_warn_hist(self):
        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)
        interval = 'hour'
        test_q = {"query": {"range": {
            "@timestamp": {"gte": start,
                           "lte": end}}}, "facets": {
            "err_facet": {
                "date_histogram": {"field": "@timestamp",
                                   "interval": interval},
                "facet_filter": {"or": [{"term": {"loglevel": "error"}},
                                        {"term": {"loglevel": "fatal"}}]}},
            "warn_facet": {
                "date_histogram": {"field": "@timestamp",
                                   "interval": interval},
                "facet_filter": {"term": {"loglevel": "warning"}}}}}
        control = self.conn.search(index="_all", body=test_q)['facets']
        result = LogData().err_and_warn_hist(self.conn, start, end, interval,
                                             query_filter=None)['facets']
        self.assertEqual(result, control)

    def test_err_and_warn_hist_filtered(self):
        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)
        interval = 'hour'
        test_q = {"query": {"range": {
            "@timestamp": {"gte": start.isoformat(),
                           "lte": end.isoformat()}}}, "facets": {
            "err_facet": {
                "date_histogram": {"field": "@timestamp",
                                   "interval": interval},
                "facet_filter": {"and": [
                    {"or": [{"term": {"loglevel": "error"}},
                            {"term": {"loglevel": "fatal"}}]},
                    {"term": {"component": "ceilometer"}}]}},
            "warn_facet": {
                "date_histogram": {"field": "@timestamp",
                                   "interval": interval},
                "facet_filter": {"and": [
                    {"term": {"loglevel": "warning"}},
                    {"term": {"component": "ceilometer"}}]}}}}
        control = self.conn.search(index="_all", body=test_q)['facets']
        f = LogData._term_filter('component', 'ceilometer')
        result = LogData().err_and_warn_hist(self.conn, start, end, interval,
                                             query_filter=f)['facets']
        self.assertEqual(result, control)

    def test_get_err_and_warn_hists(self):
        def test_scenario():
            interval_mapper = {"minute": "second", "hour": "minute",
                               "day": "hour", "month": "day"}
            test_q = {"query": {"range": {
                "@timestamp": {"gte": start,
                               "lte": end}}}, "facets": {
                "err_facet": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "interval": interval_mapper.get(interval, "hour")},
                    "facet_filter": {"or": [{"term": {"loglevel": "error"}},
                                            {"term": {"loglevel": "fatal"}}]}},
                "warn_facet": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "interval": interval_mapper.get(interval, "hour")},
                    "facet_filter": {"term": {"loglevel": "warning"}}}}}
            control = self.conn.search(index="_all", body=test_q)['facets']
            result = LogData().get_err_and_warn_hists(self.conn, start, end,
                                                      interval)
            self.assertEqual(result, control)

        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)
        interval = 'minute'
        test_scenario()
        interval = 'hour'
        test_scenario()
        interval = 'day'
        test_scenario()
        interval = 'month'
        test_scenario()
        interval = None
        test_scenario()
        interval = 'xyz'
        test_scenario()

    def test_get_err_and_warn_range(self):

        def test_scenario(sort='', global_filter_text=None):
            test_q = {'query': {'filtered': {'query': {'range': {
                '@timestamp': {'gte': start.isoformat(),
                               'lte': end.isoformat()}}}}}}
            loglevel_filt = {'or': [{'term': {'loglevel': 'error'}},
                                    {'term': {'loglevel': 'fatal'}},
                                    {'term': {'loglevel': 'warning'}}]}
            global_filt = {'term': {'_all': global_filter_text.lower()}} \
                if global_filter_text and global_filter_text != '' else None
            f1 = loglevel_filt if not global_filt \
                else {'and': [loglevel_filt, global_filt]}

            test_q['query']['filtered']['filter'] = f1
            control = self.conn.search(index="_all", body=test_q, sort=sort)
            result = LogData().get_err_and_warn_range(self.conn, start, end,
                                                      0, 10, sort,
                                                      global_filter_text)
            self.assertEqual(result['hits'], control['hits'])

        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=52)

        test_scenario()
        test_scenario(sort={'loglevel': {'order': 'asc'}})
        test_scenario(sort={'loglevel': {'order': 'desc'}})
        test_scenario(global_filter_text="keystone.common.wsgi")
        test_scenario(sort={'loglevel': {'order': 'asc'}},
                      global_filter_text="keystone.common.wsgi")

    def test_get_new_and_missing_nodes(self):
        short_lookback = datetime(2013, 12, 14, 0, 0, 0, tzinfo=pytz.utc)
        long_lookback = datetime(2013, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)

        test_q1 = {'query': {'range': {
            '@timestamp': {'gte': long_lookback.isoformat(),
                           'lte': short_lookback.isoformat()}}}, 'facets': {
            'host_facet': {
                'terms': {'field': 'host.raw', 'all_terms': False,
                          'order': 'term'}}}}
        test_q2 = {'query': {'range': {
            '@timestamp': {'gte': short_lookback.isoformat(),
                           'lte': end.isoformat()}}}, 'facets': {
            'host_facet': {
                'terms': {'field': 'host.raw', 'all_terms': False,
                          'order': 'term'}}}}
        r1 = self.conn.search(index="_all", body=test_q1)
        r2 = self.conn.search(index="_all", body=test_q2)
        s1 = set([fac['term'] for fac in
                  r1['facets']['host_facet']['terms']])
        s2 = set([fac['term'] for fac in
                  r2['facets']['host_facet']['terms']])
        new_nodes = s2.difference(s1)
        missing_nodes = s1.difference(s2)
        control = {
            "missing_nodes": list(missing_nodes),
            "new_nodes": list(new_nodes)
        }
        result = LogData().get_new_and_missing_nodes(self.conn, long_lookback,
                                                     short_lookback, end)
        self.assertEqual(result, control)

    def test_get_hypervisor_stats(self):
        '''
        all tests should look at data after 2014-02-04 20:03:01 UTC.  There
        were some different data formats prior to that date that made it into
        the dev ES database.
        '''

        start = datetime(2014, 2, 1, 0, 0, 0, 0, pytz.utc)
        end = datetime(2014, 3, 1, 0, 0, 0, 0, pytz.utc)

        test_q = {
            "query": {
                "filtered": {
                    "filter": {
                        "term": {
                            "type": "goldstone_nodeinfo"
                        }
                    },
                    "query": {
                        "range": {
                            "@timestamp": {
                                "gte": start.isoformat(),
                                "lte": end.isoformat()
                            }
                        }
                    }
                }
            }
        }

        sort = {'@timestamp': {'order': 'asc'}}
        control = self.conn.search(index="_all", body=test_q, sort=sort)
        result = LogData().get_hypervisor_stats(self.conn, start, end,
                                                0, 10, sort)
        self.assertEqual(result['hits'], control['hits'])


class IntelViewTest(TestCase):
    """Lease list view tests"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_search_template(self):
        response = self.client.get('/intelligence/search')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'search.html')

    def test_log_cockpit_summary(self):
        end = datetime(2013, 12, 31, 23, 59, 59, tzinfo=pytz.utc)
        start = end - timedelta(weeks=4)
        end_ts = calendar.timegm(end.utctimetuple())
        start_ts = calendar.timegm(start.utctimetuple())
        response = self.client.get('/intelligence/log/cockpit?start_time' +
                                   str(start_ts) + "&end_time=" + str(end_ts))
        self.assertEqual(response.status_code, 200)