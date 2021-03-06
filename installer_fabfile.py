"""Fabric file for Goldstone installation."""
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
from __future__ import print_function
from contextlib import contextmanager

import os
import platform

from django.core.exceptions import ObjectDoesNotExist
from fabric.api import task, local, run, settings as fab_settings
from fabric.colors import green, cyan
from fabric.utils import abort, fastprint
from fabric.operations import prompt
from fabric.context_managers import lcd
from fabric.contrib.files import upload_template, exists


# The Goldstone install dir
INSTALL_DIR = '/opt/goldstone'

# The Goldstone settings path, relative to the Goldstone root where we're
# executing from.
PROD_SETTINGS = "goldstone.settings.docker"


def _is_supported_centos7():
    """Return True if this is a CentOS 7.0 or 7.1 server."""

    try:
        dist = platform.linux_distribution()
        return dist[0] == 'CentOS Linux' and dist[1].startswith('7.')
    except Exception:  # pylint: disable=W0703
        return False


def _is_root_user():
    """Return True if the user is running as root."""
    import getpass

    return getpass.getuser() == "root"


def _django_manage(command,
                   target='',
                   proj_settings=None,
                   install_dir=INSTALL_DIR,
                   daemon=False):
    """Run manage.py <command>.

    :param command: The command to send to manage. E.g., test
    :type command: str
    :keyword target:A subcommand to send to manage. E.g., test user
    :type target: str
    :keyword proj_settings: The project settings to use
    :type proj_settings: str
    :keyword install_dir: The path to the Goldstone installation directory.
    :type install_dir: str
    :keyword daemon: True if the command should be run in a background process
    :type daemon: bool

    """

    # Create the --settings argument, if requested.
    settings_opt = '' if proj_settings is None \
                   else " --settings=%s " % proj_settings

    # Run this command as a background process, if requested.
    daemon_opt = "&" if daemon else ''

    with lcd(install_dir):
        local("python ./manage.py %s %s %s %s" %
              (command, target, settings_opt, daemon_opt))


@contextmanager
def _django_env(proj_settings, install_dir):
    """Load a new context into DJANGO_SETTINGS_MODULE."""
    import sys

    sys.path.append(install_dir)
    old_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
    os.environ['DJANGO_SETTINGS_MODULE'] = proj_settings

    # Yield control.
    yield

    # Restore state.
    sys.path.remove(install_dir)
    if old_settings is None:
        del os.environ['DJANGO_SETTINGS_MODULE']
    else:
        os.environ['DJANGO_SETTINGS_MODULE'] = old_settings


@task
def cloud_init(gs_tenant,
               stack_tenant,
               stack_user,
               stack_password,
               stack_auth_url,
               settings=PROD_SETTINGS,
               install_dir=INSTALL_DIR):
    """Create a single OpenStack cloud under the tenant.

    :keyword gs_tenant: The name of the tenant to be created. If not specified,
                        a default is used.
    :type gs_tenant: str
    :keyword stack_tenant: The openstack tenant to associate with this tenant
    :type stack_tenant: str
    :keyword stack_admin: The openstack username to authenticate with
    :type stack_admin: str
    :keyword stack_password: The openstack password to authenticate with
    :type stack_password: str
    :keyword stack_auth_url: The openstack auth url (without version)
    :type stack_auth_url: str
    :keyword settings: The path of the Django settings file to use.
    :type settings: str
    :keyword install_dir: The path to the Goldstone installation directory.
    :type install_dir: str

    """
    import re

    # The OpenStack identity authorization URL has a version number segment. We
    # use this version. It should not start with a slash.
    AUTH_URL_VERSION = "v3/"

    # This is used to detect a version segment at an authorization URL's end.
    AUTH_URL_VERSION_LIKELY = r'\/[vV]\d'

    with _django_env(settings, install_dir):
        from goldstone.tenants.models import Cloud

        # Ask for user for two of the necessary attributes if they're not
        # defined.
        if stack_tenant is None:
            stack_tenant = prompt(cyan("Enter Openstack tenant name: "),
                                  default='admin')
        if stack_user is None:
            stack_user = prompt(cyan("Enter Openstack user name: "),
                                default='admin')
        try:
            # Note: There's a db unique constraint on (tenant, tenant_name, and
            # username).
            Cloud.objects.get(tenant=gs_tenant,
                              tenant_name=stack_tenant,
                              username=stack_user)
        except ObjectDoesNotExist:
            # The row doesn't exist, so we have to create it. To do that, we
            # need two more pieces of information.
            if stack_password is None:
                stack_password = prompt(
                    cyan("Enter Openstack user password: "))

            if stack_auth_url is None:
                stack_auth_url = \
                    prompt(cyan("Enter OpenStack auth URL "
                                "(eg: http://10.10.10.10:5000/v2.0/): "))

                if re.search(AUTH_URL_VERSION_LIKELY, stack_auth_url[-9:]):
                    # The user shouldn't have included the version segment, but
                    # did anyway. Remove it.
                    version_index = re.search(AUTH_URL_VERSION_LIKELY,
                                              stack_auth_url)
                    stack_auth_url = stack_auth_url[:version_index.start()]

                # Append our version number to the base URL.
                stack_auth_url = os.path.join(stack_auth_url, AUTH_URL_VERSION)

            # Create the row!
            Cloud.objects.create(tenant=gs_tenant,
                                 tenant_name=stack_tenant,
                                 username=stack_user,
                                 password=stack_password,
                                 auth_url=stack_auth_url)
        else:
            fastprint("\nCloud entry already exists.")


@task
def django_admin_init(username='admin',
                      password=None,
                      email='root@localhost',
                      settings=PROD_SETTINGS,
                      install_dir=INSTALL_DIR):
    """Create the Django admin user.

    :keyword username: the django admin user name
    :type username: str
    :keyword password: the django admin password
    :type password: str
    :keyword email: the django admin email
    :type email: str
    :keyword settings: The path of the Django settings file to use.
    :type settings: str
    :keyword install_dir: The path to the Goldstone installation directory.
    :type install_dir: str

    """

    with _django_env(settings, install_dir):
        from django.contrib.auth import get_user_model

        try:
            get_user_model().objects.get(username=username)
        except ObjectDoesNotExist:
            fastprint(green("Creating Django admin account.\n"))
            if password is None:
                password = prompt(cyan("Enter Django admin password: "))

            get_user_model().objects.create_superuser(username,
                                                      email,
                                                      password)
            fastprint("done.\n")
        else:
            # The tenant_admin already exists. Print a message.
            fastprint("Account %s already exists. We will use it.\n" %
                      username)


@task
def tenant_init(gs_tenant='default',
                gs_tenant_owner='None',
                gs_tenant_admin='gsadmin',
                gs_tenant_admin_password=None,
                settings=PROD_SETTINGS,
                install_dir=INSTALL_DIR):
    """Create a tenant and default_tenant_admin, or use existing ones.

    If the tenant doesn't exist, we create it.  If the admin doesn't exist, we
    create it as the default_tenant_admin, and the tenant's tenant_admin.

    If the tenant already exists, we print an informational message and leave
    it alone.

    If the admin already exists, we print an informational message. If he/she
    is not a tenant admin of the new tenant, we make him/her it. He/she gets
    made the (a) default_tenant_admin.

    :keyword gs_tenant: The name of the tenant to be created. If not specified,
                        a default is used.
    :type gs_tenant: str
    :keyword gs_tenant_owner: The tenant owner. If unspecified, a default is
                              used
    :type gs_tenant_owner: str
    :keyword gs_tenant_admin: The name of the tenant_admin to be created.  If
                              unspecified, a default is used
    :type gs_tenant_admin: str
    :keyword gs_tenant_admin_password: The admin account's password, *if* we
                                       create it
    :type gs_tenant_admin_password: str
    :keyword settings: The path of the Django settings file to use.
    :type settings: str
    :keyword install_dir: The path to the Goldstone installation directory.
    :type install_dir: str

    """

    print(green(
        "\nInitializing the Goldstone tenant and OpenStack connection."))

    with _django_env(settings, install_dir):
        # It's important to do these imports here, after DJANGO_SETTINGS_MODULE
        # has been changed!
        from django.contrib.auth import get_user_model
        from goldstone.tenants.models import Tenant

        # Process the tenant.
        try:
            tenant = Tenant.objects.get(name=gs_tenant)
            fastprint("\nTenant %s already exists.\n" % tenant)
        except ObjectDoesNotExist:
            # The tenant does not already exist. Create it.
            tenant = Tenant.objects.create(name=gs_tenant,
                                           owner=gs_tenant_owner)

        # Process the tenant admin.
        try:
            user = get_user_model().objects.get(username=gs_tenant_admin)
            # The tenant_admin already exists. Print a message.
            fastprint("\nAdmin account %s already exists.\n\n" %
                      gs_tenant_admin)
        except ObjectDoesNotExist:
            fastprint("Creating Goldstone tenant admin account.")
            if gs_tenant_admin_password is None:
                gs_tenant_admin_password = prompt(
                    cyan("\nEnter Goldstone admin password: "))

            user = get_user_model().objects.create_user(
                username=gs_tenant_admin, password=gs_tenant_admin_password)

        # Link the tenant_admin account to this tenant.
        user.tenant = tenant
        user.tenant_admin = True
        user.default_tenant_admin = True
        user.save()

    return tenant


@task
def docker_install():
    """Create Goldstone default tenant and initialize cloud, deriving values
    from environment variables provided in the Dockerfile.

    If env vars are not provided by the container, then the install will be
    made in a way that is configured for the goldstone developer environment.

    Supported env vars are:

    DJANGO_SETTINGS_MODULE (default: goldstone.settings.docker)
    GOLDSTONE_INSTALL_DIR (default: /app)
    DJANGO_ADMIN_USER (default: admin)
    DJANGO_ADMIN_PASSWORD (default: goldstone)
    DJANGO_ADMIN_EMAIL (default: root@localhost)
    GOLDSTONE_TENANT_ADMIN_PASSWORD (default: goldstone)
    OS_TENANT_NAME (default: admin)
    OS_USERNAME (default: admin)
    OS_PASSWORD (default: solinea)
    OS_AUTH_URL (default: http://172.24.4.100:5000/v2.0/)

    """

    # test to see that this really is a docker container.
    if not os.path.isfile('/.dockerinit'):
        print()
        abort('This Does not appear to be a docker container. Exiting.')

    # pull params out of the environment
    django_admin_user = os.environ.get('DJANGO_ADMIN_USER', 'admin')
    django_admin_password = os.environ.get(
        'DJANGO_ADMIN_PASSWORD', 'goldstone')
    django_admin_email = os.environ.get('DJANGO_ADMIN_EMAIL', 'root@localhost')
    gs_tenant = 'default'
    gs_tenant_owner = 'None'
    gs_tenant_admin = 'gsadmin'
    gs_tenant_admin_password = os.environ.get(
        'GOLDSTONE_TENANT_ADMIN_PASSWORD', 'goldstone')
    stack_tenant = os.environ.get('OS_TENANT_NAME', 'admin')
    stack_user = os.environ.get('OS_USERNAME', 'admin')
    stack_password = os.environ.get('OS_PASSWORD', 'solinea')
    stack_auth_url = os.environ.get(
        'OS_AUTH_URL', 'http://172.24.4.100:5000/v2.0/')
    django_settings = os.environ.get('DJANGO_SETTTINGS_MODULE',
                                     'goldstone.settings.docker')
    gs_install_dir = os.environ.get('GOLDSTONE_INSTALL_DIR', '/app')

    django_admin_init(
        username=django_admin_user,
        password=django_admin_password,
        email=django_admin_email,
        settings=django_settings,
        install_dir=gs_install_dir
    )

    tenant = tenant_init(
        gs_tenant,
        gs_tenant_owner,
        gs_tenant_admin,
        gs_tenant_admin_password,
        settings=django_settings,
        install_dir=gs_install_dir
    )

    cloud_init(
        tenant,
        stack_tenant,
        stack_user,
        stack_password,
        stack_auth_url,
        settings=django_settings,
        install_dir=gs_install_dir
    )


def _set_single_value_configs(file_name, edits_list):
    """
    Edits StrOpt entries in a config file.

    :param file_name: the config file name
    :param edits_list: the list of edits to make
    :return: None
    """

    if exists(file_name, use_sudo=True, verbose=True):
        print(green("\tEditing %s" % file_name))

        for config_entry in edits_list:
            cmd = "crudini --existing=file --set %s %s %s %s" % \
                  (file_name, config_entry['section'],
                   config_entry['parameter'], config_entry['value'])
            run(cmd)

            print(green("\tSet %s:%s to %s" %
                        (config_entry['section'], config_entry['parameter'],
                         config_entry['value'])))
    else:
        raise IOError("File not found: %s" % file_name)


def _set_multi_value_configs(file_name, edits_list):
    """
    Edits MultiStrOpt entries in a config file.  Currently only supports adding
    a new parameter.

    :param file_name: the config file name
    :param edits_list: the list of edits to make
    :return: None
    """

    from fabric.contrib.files import contains, sed

    if exists(file_name, use_sudo=True, verbose=True):
        print(green("\tEditing %s" % file_name))

        for config_entry in edits_list:
            # hopefully match all forms of key = [other_val] val [other_val]
            # while avoiding key = [other_val] xvalx [other_val]
            # pylint: disable=W1401
            empty_setting_regex = '^%s[\s]*=[\s]*$' % \
                                  (config_entry['parameter'])
            setting_regex = '^[\s]*%s[\s]*=.*(?<=\s|=)%s(?!\S).*$' % \
                            (config_entry['parameter'], config_entry['value'])
            empty_setting_exists = contains(
                file_name, empty_setting_regex, escape=False)
            setting_exists = contains(
                file_name, setting_regex, escape=False)

            if not setting_exists and empty_setting_exists:
                print(green("\tReplacing empty %s entry" %
                            (config_entry['parameter'])))
                sed(file_name,
                    '^%s[\s]*=[\s]*$' % (config_entry['parameter']),
                    '%s = %s' % (config_entry['parameter'],
                                 config_entry['value']),
                    backup='.gsbak')
                # we have our own backup, so delete the one that sed made
                run("rm %s.gsbak" % file_name)
            elif not setting_exists:
                # add a new line to the appropriate section
                print(green("\tAdding new %s entry" %
                            (config_entry['parameter'])))
                sed(file_name,
                    '^\[%s\][\s]*$' % (config_entry['section']),
                    '\[%s\]\\n%s = %s' % (config_entry['section'],
                                          config_entry['parameter'],
                                          config_entry['value']),
                    backup='.gsbak')
                # we have our own backup, so delete the one that sed made
                run("rm %s.gsbak" % file_name)
            else:
                print(green("\tNo changes required for %s" %
                            (config_entry['parameter'])))

    else:
        raise IOError("File not found: %s" % file_name)


def _backup_config_file(file_name, backup_postfix, previously_backed_up):
    """Back up a configuration file if it hasn't been backed up already.

    :param file_name: name of file
    :param backup_postfix: postfix to append
    :param previously_backed_up: list of already backed up files
    :return: updated previously backed up files
    """
    if file_name not in previously_backed_up and \
            exists(file_name, use_sudo=True, verbose=True):

        backup_file = file_name + "." + str(backup_postfix)
        run("cp " + file_name + " " + backup_file)
        previously_backed_up.append(file_name)

    return previously_backed_up


def _configure_service(service_name, backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files):
    """
    Configure a service as defined in the supplied params.
    :param service_name: eg: Nova
    :param single_value_edits: dict of configuration instructions
    :param multi_value_edits: dict of configuration instructions
    :param template_dir: directory on calling host where templates are found
    :param template_files: dict of configuration instructions
    :return:
    """

    backed_up_files = []

    with fab_settings(warn_only=True, user="root"):

        print(green("\nConfiguring %s" % service_name))

        # process config changes for single value entries
        for entry in single_value_edits.items():
            file_name = entry[0]
            backed_up_files = _backup_config_file(
                file_name, backup_postfix, backed_up_files)

            # set StrOpt values
            try:
                _set_single_value_configs(file_name, entry[1])
            except IOError:
                pass

        # process config changes for multi value entries
        for entry in multi_value_edits.items():
            file_name = entry[0]
            backed_up_files = _backup_config_file(
                file_name, backup_postfix, backed_up_files)

        # set MultiStrOpt values
            try:
                _set_multi_value_configs(file_name, entry[1])
            except IOError:
                pass

        # upload template files
        for entry in template_files:
            file_name = entry['file']
            template_name = entry['template']
            template_context = entry['context'] if 'context' in entry else {}
            backed_up_files = _backup_config_file(
                file_name, backup_postfix, backed_up_files)

            upload_template(
                template_name,
                file_name,
                context=template_context,
                template_dir=template_dir,
                backup=False)


@task
def _configure_nova(backup_postfix, restart='yes'):
    """Configures nova on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/nova/nova.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL0"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "instance_usage_audit",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "instance_usage_audit_period",
                "value": "hour"
            },
            {
                "section": "DEFAULT",
                "parameter": "notify_on_state_change",
                "value": "vm_and_task_state"
            },
        ]
    }

    # config lines that accept multiple values per line
    multi_value_edits = {
        "/etc/nova/nova.conf": [
            {
                "section": "DEFAULT",
                "parameter": "notification_driver",
                "value": "messagingv2"
            }
        ]
    }

    template_dir = os.path.join(os.getcwd(), "external/nova")
    template_files = [
        {
            "file": "/etc/nova/api-paste.ini",
            "template": "api-paste.ini.template"
        },
        {
            "file": "/etc/nova/nova_api_audit_map.conf",
            "template": "nova_api_audit_map.conf.template"
        }
    ]

    _configure_service('Nova', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Nova service."))
        run("openstack-service restart nova")
    else:
        print(green("\nRestart Nova to apply changes."))


@task
def _configure_cinder(backup_postfix, restart='yes'):
    """Configures cinder on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/cinder/cinder.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL5"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "control_exchange",
                "value": "cinder"
            }
        ]
    }

    # config lines that accept multiple values per line
    multi_value_edits = {
        "/etc/cinder/cinder.conf": [
            {
                "section": "DEFAULT",
                "parameter": "notification_driver",
                "value": "messagingv2"
            }
        ]
    }

    template_dir = os.path.join(os.getcwd(), "external/cinder")
    template_files = [
        {
            "file": "/etc/cinder/api-paste.ini",
            "template": "api-paste.ini.template"
        },
        {
            "file": "/etc/cinder/cinder_api_audit_map.conf",
            "template": "cinder_api_audit_map.conf.template"
        }
    ]

    _configure_service('Cinder', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Cinder service."))
        run("openstack-service restart cinder")
    else:
        print(green("\nRestart Cinder to apply changes."))


@task
def _configure_keystone(backup_postfix, restart='yes'):
    """Configures keystone on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/keystone/keystone.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL6"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "notification_format",
                "value": "cadf"
            },

        ]
    }

    # config lines that accept multiple values per line
    multi_value_edits = {
        "/etc/keystone/keystone.conf": [
            {
                "section": "DEFAULT",
                "parameter": "notification_driver",
                "value": "messaging"
            }
        ]
    }

    template_dir = os.path.join(os.getcwd(), "external/keystone")
    template_files = []

    _configure_service('Keystone', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Keystone service."))
        run("systemctl restart httpd")
    else:
        print(green("\nRestart Keystone to apply changes."))


@task
def _configure_neutron(backup_postfix, restart='yes'):
    """Configures neutron on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/neutron/neutron.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL2"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            }
        ]
    }

    # config lines that accept multiple values per line
    multi_value_edits = {}

    template_dir = os.path.join(os.getcwd(), "external/neutron")
    template_files = [
        {
            "file": "/etc/neutron/api-paste.ini",
            "template": "api-paste.ini.template"
        },
        {
            "file": "/etc/neutron/neutron_api_audit_map.conf",
            "template": "neutron_api_audit_map.conf.template"
        }
    ]

    _configure_service('Neutron', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Neutron service."))
        run("openstack-service restart neutron")
    else:
        print(green("\nRestart Neutron to apply changes."))


@task
def _configure_glance(backup_postfix, restart='yes'):
    """Configures glance on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/glance/glance-cache.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL1"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            }
        ],
        "/etc/glance/glance-api.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL1"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            }
        ],
        "/etc/glance/glance-registry.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL1"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            }
        ],
        "/etc/glance/glance-scrubber.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL1"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            }
        ],
    }

    # config lines that accept multiple values per line
    multi_value_edits = {
        "/etc/glance/glance-api.conf": [
            {
                "section": "DEFAULT",
                "parameter": "notification_driver",
                "value": "messagingv2"
            }
        ],
        "/etc/glance/glance-registry.conf": [
            {
                "section": "DEFAULT",
                "parameter": "notification_driver",
                "value": "messagingv2"
            }
        ]
    }

    template_dir = os.path.join(os.getcwd(), "external/glance")
    template_files = [
        {
            "file": "/etc/glance/glance-api-paste.ini",
            "template": "glance-api-paste.ini.template"
        },
        {
            "file": "/etc/glance/glance_api_audit_map.conf",
            "template": "glance_api_audit_map.conf.template"
        }
    ]

    _configure_service('Glance', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Glance service."))
        run("openstack-service restart glance")
    else:
        print(green("\nRestart Glance to apply changes."))


@task
def _configure_ceilometer(backup_postfix, goldstone_addr, restart='yes'):
    """Configures ceilometer on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param goldstone_addr: IP address of the goldstone server
    :type goldstone_addr: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    single_value_edits = {
        "/etc/ceilometer/ceilometer.conf": [
            {
                "section": "DEFAULT",
                "parameter": "syslog_log_facility",
                "value": "LOG_LOCAL3"},
            {
                "section": "DEFAULT",
                "parameter": "use_syslog",
                "value": str(True)
            },
            {
                "section": "DEFAULT",
                "parameter": "verbose",
                "value": str(True)
            },
            {
                "section": "event",
                "parameter": "definitions_cfg_file",
                "value": "event_definitions.yaml"
            },
            {
                "section": "event",
                "parameter": "drop_unmatched_notifications",
                "value": str(False)
            },
            {
                "section": "notification",
                "parameter": "store_events",
                "value": str(True)
            },
            {
                "section": "notification",
                "parameter": "disable_non_metric_meters",
                "value": str(True)
            },
            {
                "section": "database",
                "parameter": "event_connection",
                "value": "es://%s:9200" % goldstone_addr
            },
        ]
    }

    # config lines that accept multiple values per line
    multi_value_edits = {}

    template_dir = os.path.join(os.getcwd(), "external/ceilometer")
    template_files = [
        {
            "file": "/etc/ceilometer/pipeline.yaml",
            "template": "pipeline.yaml.template",
            "context": {"goldstone_addr": goldstone_addr}
        },
        {
            "file": "/etc/ceilometer/event_pipeline.yaml",
            "template": "event_pipeline.yaml.template"
        },
        {
            "file": "/etc/ceilometer/event_definitions.yaml",
            "template": "event_definitions.yaml.template"
        },
        {
            "file": "/etc/ceilometer/api_paste.ini",
            "template": "api_paste.ini.template"
        },
    ]

    _configure_service('Ceilometer', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Ceilometer service."))
        run("openstack-service restart ceilometer")
    else:
        print(green("\nRestart Ceilometer to apply changes."))


@task
def _configure_rsyslog(backup_postfix, goldstone_addr, restart='yes'):
    """Configures neutron on OpenStack hosts.

    :param backup_postfix: A string to append to any config files that are
                           backed up (a timestamp would be nice).
    :type backup_postfix: str
    :param restart: restart the service? (yes/no)
    :type restart: str
    """

    # config lines that accept single values per line
    single_value_edits = {}

    # config lines that accept multiple values per line
    multi_value_edits = {}

    template_dir = os.path.join(os.getcwd(), "external/rsyslog")
    template_files = [
        {
            "file": "/etc/rsyslog.conf",
            "template": "rsyslog.conf.template"
        },
        {
            "file": "/etc/rsyslog.d/10-goldstone.conf",
            "template": "10-goldstone.conf.template",
            "context": {"goldstone_addr": goldstone_addr}
        }
    ]

    _configure_service('Rsyslog', backup_postfix, single_value_edits,
                       multi_value_edits, template_dir, template_files)

    if restart == 'yes':
        print(green("\nRestarting Rsyslog service."))
        run("service rsyslog restart")
    else:
        print(green("\nRestart Rsyslog to apply changes."))


@task
def configure_stack(goldstone_addr=None, restart_services=None, accept=False):
    """Configures syslog and ceilometer parameters on OpenStack hosts.

    :param goldstone_addr: Goldstone server's hostname or IP accessible to
                           OpenStack hosts
    :type goldstone_addr: str
    :param restart_services: After completion, do you want to restart
                             openstack?
    :type restart_services: boolean
    :param accept: Do you understand that this will change your openstack and
                   syslog configs?
    :type accept: boolean

    """
    import arrow

    if not accept:
        accepted = prompt(cyan(
            "This utility will modify configuration files on the hosts\n"
            "supplied via the -H parameter, and optionally restart\n"
            "OpenStack and syslog services.\n\n"
            "Do you want to continue (yes/no)?"),
            default='yes', validate='yes|no')
    else:
        accepted = 'yes'

    if accepted != 'yes':
        return 0

    if restart_services is None:
        restart_services = prompt(cyan("Restart OpenStack and syslog services "
                                       "after configuration changes(yes/no)?"),
                                  default='yes', validate='yes|no')

    if goldstone_addr is None:
        goldstone_addr = prompt(cyan("Goldstone server's hostname or IP "
                                     "accessible to OpenStack hosts?"))

    backup_timestamp = arrow.utcnow().timestamp

    with fab_settings(warn_only=True, user="root"):

        _configure_rsyslog(
            backup_timestamp,
            goldstone_addr,
            restart=restart_services)

        _configure_ceilometer(
            backup_timestamp,
            goldstone_addr,
            restart=restart_services)

        _configure_nova(
            backup_timestamp,
            restart=restart_services)

        _configure_neutron(
            backup_timestamp,
            restart=restart_services)

        _configure_cinder(
            backup_timestamp,
            restart=restart_services)

        _configure_glance(
            backup_timestamp,
            restart=restart_services)

        _configure_keystone(
            backup_timestamp,
            restart=restart_services)

        print(green("\nFinshed"))
