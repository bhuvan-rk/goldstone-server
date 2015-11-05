"""Oauth2 views."""
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
from django.contrib.auth.models import Group
from rest_framework import permissions, serializers, viewsets
from oauth2_provider.ext.rest_framework import TokenHasReadWriteScope, \
    TokenHasScope

from goldstone.user.models import User


# first we define the serializers
class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    class Meta:            # pylint: disable=C0111,W0232,C1001
        model = User


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for the Group model."""

    class Meta:            # pylint: disable=C0111,W0232,C1001
        model = Group


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    """Provide CRUD views to the User model."""

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """Provide CRUD views to the Group model."""

    permission_classes = [permissions.IsAuthenticated, TokenHasScope]
    required_scopes = ['groups']
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
