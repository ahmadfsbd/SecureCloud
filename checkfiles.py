import paramiko
import os
import time
import commands
import re
import json

import getnodes

checks = {"keystone": {"owner_checks": ['''sudo stat -L -c "%U %g" /var/lib/config-data/puppet-generated/keystone/etc/keystone/keystone.conf | egrep "root 42425"''',
                                        '''sudo docker exec keystone bash -c "stat -L -c '%U %g' /etc/keystone/keystone.conf | egrep 'root 42425'"''',
                                        '''sudo docker exec keystone bash -c "stat -L -c '%U %g' /etc/keystone/keystone-paste.ini | egrep 'root 42425'"''',
                                        '''sudo docker exec keystone bash -c "stat -L -c '%U %g' /etc/keystone/policy.json | egrep 'root 42425'"''',
                                        '''sudo docker exec keystone bash -c "stat -L -c '%U %g' /etc/keystone/logging.conf | egrep 'root 42425'"'''] ,
                        "permission_checks": ['''sudo stat -L -c '%a' /var/lib/config-data/puppet-generated/keystone/etc/keystone/keystone.conf''',
                                                '''sudo docker exec keystone bash -c "stat -L -c '%a' /etc/keystone/keystone.conf"''',
                                                '''sudo docker exec keystone bash -c "stat -L -c '%a' /etc/keystone/keystone-paste.ini"''',
                                                '''sudo docker exec keystone bash -c "stat -L -c '%a' /etc/keystone/policy.json"''',
                                                '''sudo docker exec keystone bash -c "stat -L -c '%a' /etc/keystone/logging.conf"''']
                        },
            "neutron_api": {"owner_checks": ['''sudo stat -L -c "%U %g" /var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf | egrep "root 42435"''',
                                                '''sudo docker exec neutron_api bash -c "stat -L -c '%U %g' /etc/neutron/neutron.conf | egrep 'root 42435'"''',
                                                '''sudo docker exec neutron_api bash -c "stat -L -c '%U %g' /etc/neutron/plugin.ini | egrep 'root 42435'"''',
                                                '''sudo docker exec neutron_api bash -c "stat -L -c '%U %g' /etc/neutron/policy.json | egrep 'root 42435'"''',
                                                '''sudo docker exec neutron_api bash -c "stat -L -c '%U %G' /etc/neutron/rootwrap.conf | egrep 'root root'"'''],
                            "permission_checks": ['''sudo stat -L -c '%a' /var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf''',
                                                    '''sudo docker exec neutron_api bash -c "stat -L -c '%a' /etc/neutron/neutron.conf"''',
                                                    '''sudo docker exec neutron_api bash -c "stat -L -c '%a' /etc/neutron/plugin.ini"''',
                                                    '''sudo docker exec neutron_api bash -c "stat -L -c '%a' /etc/neutron/policy.json"''',
                                                    '''sudo docker exec neutron_api bash -c "stat -L -c '%a' /etc/neutron/rootwrap.conf"''']
                            },
            "cinder_api": {"owner_checks": ['''sudo stat -L -c "%U %g" /var/lib/config-data/puppet-generated/cinder/etc/cinder/cinder.conf | egrep "root 42407"''',
                                                '''sudo docker exec cinder_api bash -c "stat -L -c '%U %g' /etc/cinder/cinder.conf | egrep 'root 42407'"''',
                                                '''sudo docker exec cinder_api bash -c "stat -L -c '%U %g' /etc/cinder/api-paste.ini | egrep 'root 42407'"''',
                                                '''sudo docker exec cinder_api bash -c "stat -L -c '%U %g' /etc/cinder/rootwrap.conf | egrep 'root 42407'"'''],
                            "permission_checks": ['''sudo stat -L -c '%a' /var/lib/config-data/puppet-generated/cinder/etc/cinder/cinder.conf''',
                                                    '''sudo docker exec cinder_api bash -c "stat -L -c '%a' /etc/cinder/cinder.conf"''',
                                                    '''sudo docker exec cinder_api bash -c "stat -L -c '%a' /etc/cinder/api-paste.ini"''',
                                                    '''sudo docker exec cinder_api bash -c "stat -L -c '%a' /etc/cinder/rootwrap.conf"''']
                            },
            "nova_api": {"owner_checks": ['''sudo stat -L -c "%U %g" /var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf | egrep "root 42436"''',
                                            '''sudo docker exec nova_api bash -c "stat -L -c '%U %g' /etc/nova/nova.conf | egrep 'root 42436'"''',
                                            '''sudo docker exec nova_api bash -c "stat -L -c '%U %g' /etc/nova/api-paste.ini | egrep 'root 42436'"''',
                                            '''sudo docker exec nova_api bash -c "stat -L -c '%U %g' /etc/nova/policy.json | egrep 'root 42436'"''',
                                            '''sudo docker exec nova_api bash -c "stat -L -c '%U %g' /etc/nova/rootwrap.conf | egrep 'root 42436'"'''],
                            "permission_checks": ['''sudo stat -L -c '%a' /var/lib/config-data/puppet-generated/nova/etc/nova/nova.conf''',
                                                    '''sudo docker exec nova_api bash -c "stat -L -c '%a' /etc/nova/nova.conf"''',
                                                    '''sudo docker exec nova_api bash -c "stat -L -c '%a' /etc/nova/api-paste.ini"''',
                                                    '''sudo docker exec nova_api bash -c "stat -L -c '%a' /etc/nova/policy.json"''',
                                                    '''sudo docker exec nova_api bash -c "stat -L -c '%a' /etc/nova/rootwrap.conf"''']
                            },
            "nova_compute": {"owner_checks": ['''sudo stat -L -c "%U %g" /var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf | egrep "root 42436"''',
                                                '''sudo docker exec nova_compute bash -c "stat -L -c '%U %g' /etc/nova/nova.conf | egrep 'root 42436'"''',
                                                '''sudo docker exec nova_compute bash -c "stat -L -c '%U %g' /etc/nova/api-paste.ini | egrep 'root 42436'"''',
                                                '''sudo docker exec nova_compute bash -c "stat -L -c '%U %g' /etc/nova/policy.json | egrep 'root 42436'"''',
                                                '''sudo docker exec nova_compute bash -c "stat -L -c '%U %g' /etc/nova/rootwrap.conf | egrep 'root 42436'"'''],
                                "permission_checks": ['''sudo stat -L -c '%a' /var/lib/config-data/puppet-generated/nova_libvirt/etc/nova/nova.conf''',
                                                        '''sudo docker exec nova_compute bash -c "stat -L -c '%a' /etc/nova/nova.conf"''',
                                                        '''sudo docker exec nova_compute bash -c "stat -L -c '%a' /etc/nova/api-paste.ini"''',
                                                        '''sudo docker exec nova_compute bash -c "stat -L -c '%a' /etc/nova/policy.json"''',
                                                        '''sudo docker exec nova_compute bash -c "stat -L -c '%a' /etc/nova/rootwrap.conf"''']
                                }
        } # end of dictionary
