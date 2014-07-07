# Copyright 2014 Solinea, Inc.
#
# Licensed under the Solinea Software License Agreement (goldstone),
# Version 1.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at:
#
#     http://www.solinea.com/goldstone/LICENSE.pdf
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'John Stanford'

from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'whitelist', WhiteListNodeViewSet, base_name='white')
router.register(r'blacklist', BlackListNodeViewSet, base_name='black')
urlpatterns = router.urls
