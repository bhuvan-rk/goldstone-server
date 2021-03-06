"""User add-ons views."""
# Copyright 2015 Solinea, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Addon


class DateTimeEncoder(json.JSONEncoder):
    """A JSON encoder that understands Python datetime objects."""

    def default(self, obj):                       # pylint: disable=E0202
        """Return a JSON-encoded form of obj."""
        import datetime

        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()
        else:
            return super(DateTimeEncoder, self).default(obj)


# Our API documentation extracts this docstring.
@api_view()
def addons(_):
    """Return information about the installed add-ons."""

    # Fetch the table rows as dicts.
    result = list(Addon.objects.all().values())

    # Delete each row's pk, and convert the datetimes to JSON.
    for entry in result:
        del entry["id"]
        entry["updated_date"] = DateTimeEncoder().encode(entry["updated_date"])
        entry["installed_date"] = \
            DateTimeEncoder().encode(entry["installed_date"])

    return Response(result)


# Our API documentation extracts this docstring.
@api_view()
def verify(_):
    """Verify the integrity of the installable apps table, and report on any
    rows with invalid url_roots.

    The Django 1.6 hooks for running code at project startup, or after a
    database syncdb, aren't sufficient to reliably run this when Goldstone
    starts. So we let the client decide when to check the table, and how to
    report table problems.

    To fix bad rows, either the Goldstone admin should delete the table row(s),
    or install the missing add-on(s).

    This returns a 200 if the table is OK, or a 400 if there's >= one bad
    table row. The response text will contain the bad rows' names.

    """
    from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK

    # Verify the table. The call returns bad rows found in the table, so we
    # return 400 if the result isn't empty.
    _, result = Addon.objects.check_table()
    status = HTTP_400_BAD_REQUEST if result else HTTP_200_OK

    return Response(result, status=status)
