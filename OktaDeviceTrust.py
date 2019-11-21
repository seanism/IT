#!/usr/bin/python

#
# Copyright 2018-present, Okta Inc.
#
# macOS Device Registration Task

import sys
import platform
import subprocess
import os.path
import syslog
import random
import string
import base64
import json
import os
import re
import datetime
import pwd
from SystemConfiguration import SCDynamicStoreCopyConsoleUser

from OpenSSL import crypto

#####################################################################
# Org Configuration: Configure you organization URL and Token
ORG_TOKEN = '<<TOKEN>>'
URL = 'https://<<ORG>>.okta.com'
#####################################################################

#####################################################################
# OPTIONAL - Edit this field to specify the apps you want to whitelist so users are not prompted for their keychain password when accessing.
# These TeamIDs correspond to the following apps/developer
# Safari:'apple:' Microsoft:'UBF8T346G9' Google:'EQHXZ8M8AV' Box:'M683GB7CPW' Skype:'AL798K98FX' Slack:'BQR82RBBHL'
# 'apple-tool:' is needed for execution of commands this script needs like 'security cms'.
TEAM_IDS_TO_WHITELIST = 'apple-tool:,apple:,teamid:UBF8T346G9,teamid:EQHXZ8M8AV,teamid:M683GB7CPW,teamid:AL798K98FX,teamid:BQR82RBBHL'
#####################################################################

VERSION = '1.2.0'
LAUNCH_AGENT_INTERVAL_IN_SECONDS = 60 * 60 * 24
OKTA_KEY_CHAIN = 'okta.keychain'
DEVICE_TRUST_ALIAS = 'device_trust'
DEVICE_TRUST_COMMON_NAME = 'Okta MTLS'
NUMBER_OF_DAYS_BEFORE_RENEWAL = 30
VERBOSE_MODE = False

keychain_pass = ''
home_directory = ''
okta_dt_launch_agent_dir = ''
okta_dt_launch_agent = ''
okta_dt_launch_domain = ''
okta_dt_launch_directory = ''
okta_dt_launch_plist = ''
okta_dt_launch_plist_file = ''
okta_cert_auth_domain = ''
okta_cert_path = ''
current_user = ''


#########################
# System Log Utility
#########################


def set_logger():
    syslog.openlog('okta_device_registration')


def log_debug(message):
    if VERBOSE_MODE:
        print 'DEBUG:' + message
        syslog.syslog(syslog.LOG_ALERT, "Okta: " + str(message))


def log(message):
    print 'INFO: ' + message
    syslog.syslog(syslog.LOG_ALERT, "Okta: " + str(message))


def log_warn(message):
    print 'WARN: ' + message
    syslog.syslog(syslog.LOG_WARNING, "Okta: " + str(message))


def log_error(message):
    print 'ERROR: ' + message
    syslog.syslog(syslog.LOG_ERR, "Okta: " + str(message))


#########################
# Utility functions
#########################


def get_random():
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase
            + string.ascii_lowercase
            + string.digits) for _ in range(40))


def get_uuid():
    profile = get_cmd_output(['system_profiler', 'SPHardwareDataType'])
    return profile[profile.find('Hardware UUID:'):].split()[2]


def get_display_name():
    return get_cmd_output(['scutil', '--get', 'ComputerName']).strip()


def get_current_user():
    return current_user


def get_home_directory():
    return os.path.expanduser('~' + get_current_user())


def setup_global_variables():
    global home_directory
    global okta_dt_launch_agent_dir
    global okta_dt_launch_agent
    global okta_dt_launch_domain
    global okta_dt_launch_directory
    global okta_dt_launch_plist
    global okta_dt_launch_plist_file
    global okta_cert_path
    global current_user

    current_user = (
        SCDynamicStoreCopyConsoleUser(
            None, None, None) or [None])[0]
    current_user = [current_user, ""][current_user in [
        u"loginwindow", None, u"", u"root"]]
    home_directory = get_home_directory()
    okta_dt_launch_agent_dir = home_directory + '/Library/Okta/'
    okta_dt_launch_agent = okta_dt_launch_agent_dir + 'okta_device_trust.py'
    okta_dt_launch_domain = 'com.okta.devicetrust'
    okta_dt_launch_directory = home_directory + '/Library/LaunchAgents/'
    okta_dt_launch_plist = okta_dt_launch_domain + '.plist'
    okta_dt_launch_plist_file = okta_dt_launch_directory + okta_dt_launch_plist
    okta_cert_path = get_home_directory() + '/Library/Keychains/okta.keychain'


def execute_as_user(params):
    uid = pwd.getpwnam(get_current_user()).pw_uid
    run_as_user_cmd = [
        'launchctl',
        'asuser',
        str(uid),
        'sudo',
        '-u',
        get_current_user()]
    run_as_user_cmd.extend(params)
    if VERBOSE_MODE:
        return subprocess.call(run_as_user_cmd)
    else:
        with open(os.devnull, 'w') as DEVNULL:
            return subprocess.call(run_as_user_cmd, stdout=DEVNULL, stderr=DEVNULL)


def get_cmd_output(params):
    uid = pwd.getpwnam(get_current_user()).pw_uid
    run_as_user_cmd = [
        'launchctl',
        'asuser',
        str(uid),
        'sudo',
        '-u',
        get_current_user()]
    run_as_user_cmd.extend(params)
    if VERBOSE_MODE:
        return subprocess.check_output(run_as_user_cmd)
    else:
        with open(os.devnull, 'w') as DEVNULL:
            return subprocess.check_output(run_as_user_cmd, stderr=DEVNULL)


#########################
# Configure Browsers for no certificate picker
#########################
def get_domain_from_url(url):
    url = url.rstrip('/')
    if url.startswith('https://'):
        url = url[len('https://'):]
    elif url.startswith('http://'):
        url = url[len('http://'):]
    return url


def get_cell():
    global URL
    domain = get_domain_from_url(URL)
    return domain[domain.find('.') + 1:]


def get_org_certificate_url():
    return '*.' + get_cell()


def get_metadata_url():
    return get_base_url() + '/api/internal/v1/device-trust/metadata?platform=macos'


def get_cert_auth_domain(url):
    global okta_cert_auth_domain
    if okta_cert_auth_domain is not '':
        return okta_cert_auth_domain
    try:
        response = get_cmd_output(['curl', '-sS', '-X', 'GET',
                                   '-H', 'User-Agent: ' + get_user_agent(),
                                   url])

        response_json = json.loads(response)
        if 'certAuthDomain' in response_json:
            domain = response_json.get('certAuthDomain')
            okta_cert_auth_domain = get_domain_from_url(domain)
            return okta_cert_auth_domain
        else:
            raise RuntimeError(response_json)
    except Exception as e:
        log_error('Failed to get server metadata : ' + str(e))
        return False


def configure_safari():
    global DEVICE_TRUST_COMMON_NAME
    log('Configuring the Safari browser.')
    cert_auth_domain = get_cert_auth_domain(get_metadata_url())
    if cert_auth_domain is False:
        return False
    try:
        execute_as_user(['security',
                         'set-identity-preference',
                         '-c',
                         DEVICE_TRUST_COMMON_NAME,
                         '-s',
                         cert_auth_domain,
                         OKTA_KEY_CHAIN])
        execute_as_user(['security',
                         'set-identity-preference',
                         '-c',
                         DEVICE_TRUST_COMMON_NAME,
                         '-s',
                         get_org_certificate_url(),
                         OKTA_KEY_CHAIN])
        return True
    except Exception:
        log_warn('Failed to configure the Safari browser')


def configure_chrome():
    log('Configuring the Chrome browser.')
    try:
        chrome_sys_configuration = get_cmd_output(
            [
                'defaults',
                'read',
                '/Library/Preferences/com.google.Chrome.plist',
                'AutoSelectCertificateForUrls'])
    except Exception:
        chrome_sys_configuration = ''

    try:
        chrome_user_configuration = get_cmd_output(
            [
                'defaults',
                'read',
                get_home_directory() + '/Library/Preferences/com.google.Chrome.plist',
                'AutoSelectCertificateForUrls'])

    except Exception:
        chrome_user_configuration = ''

    if get_cell() in chrome_sys_configuration:
        return True
    if get_cell() in chrome_user_configuration:
        return True
    else:
        try:
            cert_auth_domain = get_cert_auth_domain(get_metadata_url())
            if cert_auth_domain is False:
                return False
            execute_as_user(
                [
                    'defaults',
                    'write',
                    get_home_directory() + '/Library/Preferences/com.google.Chrome.plist',
                    'AutoSelectCertificateForUrls',
                    '-array-add',
                    '-string',
                    '{\"pattern\":\"https://'
                    + cert_auth_domain
                    + '\",'
                    + '\"filter\":{\"ISSUER\":{\"CN\":\"MTLS Certificate Authority\"}}    }'])
            return True
        except Exception:
            log_warn('Failed to configure the Chrome browser.')
            return False


def configure_browsers():
    safari = configure_safari()
    chrome = configure_chrome()
    return safari & chrome


#########################
# Enroll to Okta
#########################
def get_base_url():
    global URL
    if URL.startswith('https://'):
        url = URL
    else:
        url = 'https://' + URL
    return url.rstrip('/')


def get_enroll_url():
    return get_base_url() + '/api/internal/device-trust/ca/v1/enroll/macos'


def get_key():
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    return key


def get_pkcs10(key):
    global DEVICE_TRUST_COMMON_NAME
    req = crypto.X509Req()
    req.get_subject().CN = DEVICE_TRUST_COMMON_NAME
    req.get_subject().countryName = 'US'
    req.get_subject().stateOrProvinceName = 'CA'
    req.get_subject().organizationName = 'Okta'
    base_constraints = ([crypto.X509Extension('keyUsage',
                                              False,
                                              'Digital Signature, Non Repudiation, Key Encipherment'),
                         crypto.X509Extension('basicConstraints',
                                              False,
                                              'CA:FALSE'),
                         ])
    x509_extensions = base_constraints
    req.set_pubkey(key)
    req.sign(key, 'sha256')
    req.add_extensions(x509_extensions)
    csr = base64.b64encode(
        crypto.dump_certificate_request(
            crypto.FILETYPE_ASN1, req))
    return csr


def get_request(csr):
    device = dict()
    device['uuid'] = get_uuid()
    device['displayName'] = get_display_name()
    data = dict()
    data['clientVersion'] = VERSION
    data['orgToken'] = ORG_TOKEN
    data['device'] = device
    data['csr'] = csr
    data['user'] = get_current_user()
    return json.dumps(data)


def get_user_agent():
    ver, build, proc = platform.mac_ver()
    ua = 'Okta Device Registration Task/' + VERSION + ' (Macintosh; ' + proc
    vernum = [int(x) for x in ver.split('.')]
    if isinstance(vernum, list) and len(vernum) > 0 and vernum[0] is 10:
        ua = ua + ' Mac OS X '
    # Okta Device Registration Task/1.0.0 (Macintosh; x86_64 OS X 10_11_6)
    ua = ua + ver.replace('.', '_') + ')'
    return ua


def enroll(url, data):
    log('Enrolling this device into Okta Device Trust.')
    try:
        response = get_cmd_output(['curl', '-sS', '-X', 'POST',
                                   '-H', 'accept: application/json',
                                   '-H', 'content-type: application/json',
                                   '-H', 'User-Agent: ' + get_user_agent(),
                                   '-d', data,
                                   url])

        response_json = json.loads(response)
        if 'issuedCertificate' in response_json:
            x509obj = crypto.load_certificate(
                crypto.FILETYPE_ASN1, base64.b64decode(
                    response_json.get('issuedCertificate')))
            return x509obj
        else:
            raise RuntimeError(response_json)
    except Exception as e:
        log_error('Error enrolling into Okta Device Trust : ' + str(e))
        return False


#########################
# Manage Okta key chain
#########################


def get_keychain_password():
    global keychain_pass
    if keychain_pass is '':
        try:
            keychain_pass = (get_cmd_output(['security', 'find-generic-password', '-l',
                                             DEVICE_TRUST_ALIAS, '-w'])).splitlines()[0]
        except Exception:
            log('Creating new keychain password')
            keychain_pass = get_random()
    return keychain_pass


def is_okta_keychain_exist():
    try:
        get_cmd_output(['security', 'show-keychain-info', OKTA_KEY_CHAIN])
        return True
    except Exception:
        log_debug('Okta keychain does not exist.')
        return False


def is_okta_password_exist():
    try:
        execute_as_user(['security', 'find-generic-password',
                         '-l', DEVICE_TRUST_ALIAS, '-w'])
        return True
    except Exception:
        log_debug('Okta password does not exist.')
        return False


def configure_key_chain_partitions():
    global TEAM_IDS_TO_WHITELIST
    try:
        # Always add apple-tool since we need it for running keychain commands by our script
        if 'apple-tool:' not in TEAM_IDS_TO_WHITELIST:
            TEAM_IDS_TO_WHITELIST += ',apple-tool:'
        log('Configure keychain partition: %s' % TEAM_IDS_TO_WHITELIST)
        # Sets the keychain so applications with the teamIDs listed have access to the okta keychain
        execute_as_user(['security',
                         'set-key-partition-list',
                         '-S',
                         TEAM_IDS_TO_WHITELIST,
                         '-s',
                         '-k',
                         get_keychain_password(),
                         OKTA_KEY_CHAIN])
        return True
    except Exception:
        log_error('Okta keychain does not support partition')
        return False


def list_existing_keychains_in_search_list():
    # get the list of keychains in the user's keychain search list
    keychains = []
    keychain_list = get_cmd_output(['security', 'list-keychain', '-d', 'user'])
    for keychain in keychain_list.splitlines():
        keychain = keychain.replace('"', '')
        name = keychain.split('/')
        keychains.append(name[-1:][0])
    return keychains


def add_okta_to_existing_keychain_list():
    existing_keychains = list_existing_keychains_in_search_list()
    okta_in_search_list = OKTA_KEY_CHAIN in existing_keychains

    # if okta keychain is NOT already in the search list, add it now
    if not okta_in_search_list:
        add_keychain_search_command_args = [
            'security', 'list-keychain', '-d', 'user', '-s']
        add_keychain_search_command_args.extend(existing_keychains)
        add_keychain_search_command_args.append(OKTA_KEY_CHAIN)
        execute_as_user(add_keychain_search_command_args)
        log('Okta keychain added to the keychain search list.')
    else:
        log('Okta keychain has already been added to the keychain search list.')


def configure_key_chain():
    log('Configuring Okta keychain.')
    if is_okta_keychain_exist() and is_okta_password_exist():
        log('Using existing keychain.')
        global keychain_pass
        keychain_pass = (get_cmd_output(["security", "find-generic-password", "-l",
                                         DEVICE_TRUST_ALIAS, "-w"])).splitlines()[0]
        return True
    try:
        log('Creating new keychain.')
        # cleanup to start with a fresh state
        execute_as_user(['security', 'delete-keychain', OKTA_KEY_CHAIN])
        execute_as_user(['security', 'delete-generic-password',
                         '-', 'l', DEVICE_TRUST_ALIAS])

        # setup keychain and password
        execute_as_user(['security', 'create-keychain', '-p',
                         get_keychain_password(), OKTA_KEY_CHAIN])
        execute_as_user(['security', 'set-keychain-settings', OKTA_KEY_CHAIN])

        # if okta keychain is NOT already in the search list, add it now
        add_okta_to_existing_keychain_list()

        # add a keychain password
        execute_as_user(['security', 'unlock-keychain', '-p',
                         get_keychain_password(), OKTA_KEY_CHAIN])
        # add-generic-password operation may fail if executed before login keychain
        # is unlocked.
        ret = execute_as_user(['security',
                               'add-generic-password',
                               '-a',
                               DEVICE_TRUST_ALIAS,
                               '-l',
                               DEVICE_TRUST_ALIAS,
                               '-s',
                               DEVICE_TRUST_ALIAS,
                               '-A',
                               '-w',
                               get_keychain_password()])
        if ret:
            log_error('Could not add-generic-password. Return status : ' + str(ret))
            return False
        return True
    except Exception as e:
        log_error('Failed to configure keychain. Error: ' + str(e))
        return False


#########################
# Manage Okta issued certificate
#########################


def is_valid_certificate_exist():
    try:
        certificate_pem = get_cmd_output(['security',
                                          'find-certificate',
                                          '-a',
                                          '-c',
                                          DEVICE_TRUST_COMMON_NAME,
                                          '-Z',
                                          '-p',
                                          OKTA_KEY_CHAIN])
        if certificate_pem == '' or certificate_pem == ' ':
            return False
        certificate = crypto.load_certificate(
            crypto.FILETYPE_PEM, certificate_pem)
        # Perform enrollment if certificate does not exist
        if not certificate:
            return False
        expiry = datetime.datetime.strptime(
            certificate.get_notAfter(), '%Y%m%d%H%M%SZ')
        remaining_number_of_days = expiry - datetime.datetime.utcnow()
        log("Certificate will expire in %s days" % str(remaining_number_of_days))
        # Prevent enrollment operation if
        # 1. Certificate exists and valid for more than 30 days
        # 2. Certificate exists and not valid beyond max 30 days
        # 3. Certificate expired
        return True
    except Exception:
        return False


def remove_expiring_certificate():
    global DEVICE_TRUST_COMMON_NAME
    try:
        execute_as_user(['security', 'delete-certificate',
                         '-c', DEVICE_TRUST_COMMON_NAME])
        return True
    except Exception:
        log_warn('Failed to remove expiring certificate from the keychain during initial setup')
        return False


def import_certificate(key, x509):
    if remove_expiring_certificate() is False:
        return False
    log('Importing certificate.')
    fname = get_home_directory() + '/tmpOktaCert.p12'
    remove_file(fname)
    try:
        p12 = crypto.PKCS12()
        p12.set_privatekey(key)
        p12.set_certificate(x509)

        with open(fname, 'w') as p12_file:
            p12_file.write(p12.export())
            p12_file.flush()
            execute_as_user(['security', 'unlock-keychain',
                             '-p', get_keychain_password(), okta_cert_path])
            log_debug(get_cmd_output(['security', 'import', str(os.path.abspath(
                p12_file.name)), '-x', '-A', '-k', str(okta_cert_path), '-P', '']))
        return True
    except Exception:
        log_error('Failed to import certificate into keychain')
        return False
    finally:
        remove_file(fname)


def remove_file(fname):
    try:
        os.remove(fname)
    except OSError:
        log_debug('file does not exist')


def configure_certificate():
    log('Configuring certificate.')
    if is_valid_certificate_exist() is True:
        return True

    key = get_key()
    csr = get_pkcs10(key)
    request = get_request(csr)

    # get a self signed rather than one from API, use
    # x509 = create_self_signed(key)
    x509 = enroll(get_enroll_url(), request)

    if x509 is False:
        return False

    if import_certificate(key, x509) is False:
        return False

    return True


#########################
# Manage Okta launch agent
# Always overwrite to enable easy plist update flow
#########################


def get_launch_agent_plist():
    """
    Run the task periodically and right after login. We run it with highest priority and interactively
    to make sure user does not get impacted by any delay after login to their device
    """

    plist = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
    <dict>
        <key>Label</key>
        <string>com.okta.devicetrust</string>
        <key>ProgramArguments</key>
        <array>
            <string>python</string>
            <string>""" + \
            os.path.expanduser(okta_dt_launch_agent) + \
            """</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
            <key>StartInterval</key>
            <integer>""" + \
            str(LAUNCH_AGENT_INTERVAL_IN_SECONDS) + \
            """</integer>
            <key>Nice</key>
            <integer>-20</integer>
            <key>ProcessType</key>
            <string>Interactive</string>
        </dict>
    </plist>"""
    return plist


def setup_launch_agent():
    global okta_dt_launch_directory
    global okta_dt_launch_plist_file
    log('Set Launch Agent')

    try:
        if not os.path.exists(os.path.expanduser(okta_dt_launch_directory)):
            os.makedirs(os.path.expanduser(okta_dt_launch_directory))

        if os.path.exists(os.path.expanduser(okta_dt_launch_plist_file)):
            log('Plist File already exists, we overwrite it!')
            execute_as_user(
                ['launchctl', 'unload', os.path.expanduser(okta_dt_launch_plist_file)])
            execute_as_user(['rm', '-rf', okta_dt_launch_plist_file])

        with open(os.path.expanduser(okta_dt_launch_plist_file), 'wt') as f:
            f.write(get_launch_agent_plist())
            f.close()
        # Following file permission operations are needed as open() is executed in root context
        subprocess.call(['chown', get_current_user(),
                         os.path.expanduser(okta_dt_launch_directory)])
        subprocess.call(['chown', get_current_user(),
                         os.path.expanduser(okta_dt_launch_plist_file)])
        execute_as_user(
            ['launchctl', 'load', os.path.expanduser(okta_dt_launch_plist_file)])
        return True
    except Exception as e:
        log_error('Error creating Okta launch agent : ' + str(e))
        return False


#########################
# setup periodic task file
# Always overwrite to enable easy update flow
#########################


def get_device_trust_launcher_code():
    dt = """#!/usr/bin/python

#
# Copyright 2018-present, Okta Inc.
#

# macOS Keychain Unlock / Certificate Renewal Task


import subprocess
import platform
import os.path
import random
import string
import base64
import json
import syslog
import tempfile

from calendar import timegm
from datetime import timedelta
from datetime import datetime

from OpenSSL import crypto
from SystemConfiguration import SCDynamicStoreCopyConsoleUser

VERSION = '1.2.0'
URL = 'URL_FROM_MASTER_FILE'
OKTA_KEY_CHAIN = 'okta.keychain'
DEVICE_TRUST_ALIAS = 'device_trust'
DEVICE_TRUST_COMMON_NAME = 'Okta MTLS'
NUMBER_OF_DAYS_BEFORE_RENEWAL = 30

# Will be populated by registration task
TEAM_IDS_TO_WHITELIST = 'TEAM_IDS_TO_WHITELIST_FROM_MASTER_FILE'

home_directory = ''
key_chain_password = ''
okta_cert_auth_domain = ''
okta_cert_path = ''
current_user = ''

syslog.openlog('okta_device_registration')


def log(message):
    syslog.syslog(syslog.LOG_ALERT, "Okta: " + str(message))


def log_error(message):
    syslog.syslog(syslog.LOG_ERR, "Okta: " + str(message))


def configure():
    global home_directory
    global okta_cert_path
    global current_user
    current_user = (
        SCDynamicStoreCopyConsoleUser(
            None, None, None) or [None])[0]
    current_user = [current_user, ""][current_user in [
        u"loginwindow", None, u"", u"root"]]
    home_directory = get_home_directory()
    okta_cert_path = get_home_directory() + '/Library/Keychains/okta.keychain'


def get_home_directory():
    return os.path.expanduser('~' + get_current_user())


def get_current_user():
    return current_user


def get_uuid():
    profile = subprocess.check_output(['system_profiler', 'SPHardwareDataType'])
    return profile[profile.find('Hardware UUID:'):].split()[2]


def get_display_name():
    return subprocess.check_output(['scutil', '--get', 'ComputerName']).strip()


def get_domain_from_url(url):
    url = url.rstrip('/')
    if url.startswith('https://'):
        url = url[len('https://'):]
    elif url.startswith('http://'):
        url = url[len('http://'):]
    return url


def get_base_url():
    global URL
    if URL.startswith('https://'):
        url = URL
    else:
        url = 'https://' + URL
    return url.rstrip('/')


def get_renew_url():
    return get_base_url() + '/api/internal/device-trust/ca/v1/renew/macos'


def get_cell():
    global URL
    domain = get_domain_from_url(URL)
    return domain[domain.find('.') + 1:]


def get_metadata_url():
    return get_base_url() + '/api/internal/v1/device-trust/metadata?platform=macos'


def get_cert_auth_domain(url):
    global okta_cert_auth_domain
    if okta_cert_auth_domain is not '':
        return okta_cert_auth_domain
    try:
        response = subprocess.check_output(['curl', '-sS', '-X', 'GET',
                                            '-H', 'User-Agent: ' + get_user_agent(),
                                            url])

        response_json = json.loads(response)
        if 'certAuthDomain' in response_json:
            domain = response_json.get('certAuthDomain')
            okta_cert_auth_domain = get_domain_from_url(domain)
            return okta_cert_auth_domain
        else:
            raise RuntimeError(response_json)
    except Exception as e:
        log('Failed to get server metadata : ' + str(e))
        return False


def issued_at():
    return timegm(datetime.utcnow().utctimetuple())


def not_before():
    return timegm((datetime.utcnow() - timedelta(minutes=5)).utctimetuple())


def expires_at():
    return timegm((datetime.utcnow() + timedelta(hours=1)).utctimetuple())


def get_random():
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase
            + string.ascii_lowercase
            + string.digits) for _ in range(40))


def certificate_needs_renewal():
    try:
        certificate_pem = subprocess.check_output(
            [
                'security',
                'find-certificate',
                '-a',
                '-c',
                DEVICE_TRUST_COMMON_NAME,
                '-Z',
                '-p',
                OKTA_KEY_CHAIN])
        if certificate_pem == '' or certificate_pem == ' ':
            log('A valid Okta certificate does not exist. Skipping the renewal operation.')
            return False
        certificate = crypto.load_certificate(
            crypto.FILETYPE_PEM, certificate_pem)
        expiry = datetime.strptime(certificate.get_notAfter(), '%Y%m%d%H%M%SZ')
        remaining_number_of_days = expiry - datetime.utcnow()
        return remaining_number_of_days < timedelta(
            days=NUMBER_OF_DAYS_BEFORE_RENEWAL)
    except Exception:
        log('Okta certificate does not require renewal.')
        return False


def get_token():
    device = dict()
    device['uuid'] = get_uuid()
    device['displayName'] = get_display_name()
    data = dict()
    data['device'] = device
    data['iat'] = issued_at()
    data['exp'] = expires_at()
    data['nbf'] = not_before()
    return json.dumps(data)


def get_signed_token():
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w') as token:
            with tempfile.NamedTemporaryFile(suffix='.pb7', mode='w+r+b') as signedToken:
                token.write(str(get_token()))
                token.flush()
                subprocess.call(['security',
                                 'cms',
                                 '-S',
                                 '-H',
                                 'SHA256',
                                 '-k',
                                 okta_cert_path,
                                 '-N',
                                 DEVICE_TRUST_COMMON_NAME,
                                 '-i',
                                 token.name,
                                 '-o',
                                 signedToken.name])
                data = signedToken.read()
                return data.encode('base64')
    except Exception:
        log_error('Failed to create a signed token.')
        return False


def get_key():
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    return key


def get_pkcs10(key):
    global DEVICE_TRUST_COMMON_NAME
    req = crypto.X509Req()
    req.get_subject().CN = DEVICE_TRUST_COMMON_NAME
    req.get_subject().countryName = 'US'
    req.get_subject().stateOrProvinceName = 'CA'
    req.get_subject().organizationName = 'Okta'
    base_constraints = ([crypto.X509Extension('keyUsage',
                                              False,
                                              'Digital Signature, Non Repudiation, Key Encipherment'),
                         crypto.X509Extension('basicConstraints',
                                              False,
                                              'CA:FALSE'),
                         ])
    x509_extensions = base_constraints
    req.set_pubkey(key)
    req.sign(key, 'sha256')
    req.add_extensions(x509_extensions)
    csr = base64.b64encode(
        crypto.dump_certificate_request(
            crypto.FILETYPE_ASN1, req))
    return csr


def get_request(csr):
    signed_token = get_signed_token()
    if signed_token is False:
        return False

    device = dict()
    device['uuid'] = get_uuid()
    device['displayName'] = get_display_name()
    data = dict()
    data['clientVersion'] = VERSION
    data['deviceRenewalToken'] = signed_token
    data['device'] = device
    data['csr'] = csr
    data['user'] = get_current_user()
    return json.dumps(data)


def os_ver_greater_than_or_equal(ver_to_check):
    cur_os_ver, build, proc = platform.mac_ver()
    ver1 = [int(x) for x in cur_os_ver.split('.')]
    ver2 = [int(x) for x in ver_to_check.split('.')]

    if isinstance(ver1, list) and len(ver1) == 3:
        if ver1[0] == ver2[0] and ver1[1] == ver2[1] and ver1[2] == ver2[2]:
            return True
        if (ver1[0] > ver2[0] or (ver1[0] == ver2[0] and ver1[1] > ver2[1]) or (
                ver1[0] == ver2[0] and ver1[1] == ver2[1] and ver1[2] > ver2[2])):
            return True

    return False


def get_user_agent():
    ver, build, proc = platform.mac_ver()
    ua = 'Okta Device Registration Task/' + VERSION + ' (Macintosh; ' + proc
    vernum = [int(x) for x in ver.split('.')]
    if isinstance(vernum, list) and len(vernum) > 0 and vernum[0] is 10:
        ua = ua + ' Mac OS X '
    # Okta Device Registration Task/1.0.0 (Macintosh; x86_64 OS X 10_11_6)
    ua = ua + ver.replace('.', '_') + ')'
    return ua


def renew(url, data):
    try:
        response = subprocess.check_output(['curl',
                                            '-X',
                                            'POST',
                                            '-H',
                                            'accept: application/json',
                                            '-H',
                                            'content-type: application/json',
                                            '-H',
                                            'User-Agent: ' + get_user_agent(),
                                            '-d',
                                            data,
                                            url])
        response_json = json.loads(response)
        if 'issuedCertificate' in response_json:
            x509obj = crypto.load_certificate(
                crypto.FILETYPE_ASN1, base64.b64decode(
                    response_json.get('issuedCertificate')))
            return x509obj
        else:
            raise RuntimeError(response_json)
    except Exception as e:
        log_error('Error renewing Okta Device Trust enrollment : ' + str(e))
        return False


def remove_expiring_certificate():
    global DEVICE_TRUST_COMMON_NAME
    try:
        if os_ver_greater_than_or_equal('10.12.4'):
            # the following command only works on MacOS 10.12.4 and above.
            # this deletes the private key and the certificate
            subprocess.call(['security', 'delete-identity',
                             '-c', DEVICE_TRUST_COMMON_NAME])
        else:
            subprocess.call(['security', 'delete-certificate',
                             '-c', DEVICE_TRUST_COMMON_NAME])
        return True
    except Exception:
        log('Failed to remove the expiring Okta certificate from the Okta keychain.')
        return False


def import_certificate(key, x509):
    try:
        p12 = crypto.PKCS12()
        p12.set_privatekey(key)
        p12.set_certificate(x509)
        with tempfile.NamedTemporaryFile(suffix='.p12', mode='w') as p12_file:
            p12_file.write(p12.export())
            p12_file.flush()
            with open(os.devnull, 'w') as DEVNULL:
                subprocess.call(['security', 'unlock-keychain',
                                 '-p', key_chain_password, okta_cert_path], stdout=DEVNULL, stderr=DEVNULL)
            log(subprocess.check_output(['security', 'import', str(os.path.abspath(
                p12_file.name)), '-x', '-A', '-k', str(okta_cert_path), '-P', '']))
        return True
    except Exception:
        log_error('Failed to import the Okta certificate into the Okta keychain.')
        return False


def renew_certificate():
    log('Renew certificate')

    key = get_key()
    csr = get_pkcs10(key)

    request = get_request(csr)
    if request is False:
        return False

    x509 = renew(get_renew_url(), request)
    if x509 is False:
        return False

    if remove_expiring_certificate() is False:
        return False

    if import_certificate(key, x509) is False:
        return False

    return True


def configure_key_chain_partitions():
    global TEAM_IDS_TO_WHITELIST
    global key_chain_password
    try:
        subprocess.call(['security',
                         'set-key-partition-list',
                         '-S',
                         TEAM_IDS_TO_WHITELIST,
                         '-s',
                         '-k',
                         key_chain_password,
                         OKTA_KEY_CHAIN])
        return True
    except Exception:
        log('The Okta Keychain does not support partition')
        return False


def configure_safari():
    global DEVICE_TRUST_COMMON_NAME
    log('Configuring the Safari browser')
    cert_auth_domain = get_cert_auth_domain(get_metadata_url())
    if cert_auth_domain is False:
        return False
    try:
        subprocess.call(['security',
                         'set-identity-preference',
                         '-c',
                         DEVICE_TRUST_COMMON_NAME,
                         '-s',
                         cert_auth_domain,
                         OKTA_KEY_CHAIN])
        subprocess.call(['security',
                         'set-identity-preference',
                         '-c',
                         DEVICE_TRUST_COMMON_NAME,
                         '-s',
                         '*.' + get_cell()])
        return True
    except Exception:
        log('Failed to configure the Safari browser.')


def configure_chrome():
    log('Configuring the Chrome browser.')
    try:
        chrome_sys_configuration = subprocess.check_output(
            ['sudo', '-u', get_current_user(),
             'defaults',
             'read',
             '/Library/Preferences/com.google.Chrome.plist',
             'AutoSelectCertificateForUrls'])
    except Exception:
        chrome_sys_configuration = ''

    try:
        chrome_user_configuration = subprocess.check_output(
            ['sudo', '-u', get_current_user(),
             'defaults',
             'read',
             get_home_directory() + '/Library/Preferences/com.google.Chrome.plist',
             'AutoSelectCertificateForUrls'])

    except Exception:
        chrome_user_configuration = ''

    if get_cell() in chrome_sys_configuration:
        return True
    if get_cell() in chrome_user_configuration:
        return True
    else:
        try:
            cert_auth_domain = get_cert_auth_domain(get_metadata_url())
            if cert_auth_domain is False:
                return False
            subprocess.call(
                ['sudo', '-u', get_current_user(),
                 'defaults',
                 'write',
                 'com.google.Chrome',
                 'AutoSelectCertificateForUrls',
                 '-array-add',
                 '-string',
                 '{\"pattern\":\"https://'
                 + cert_auth_domain
                 + '\",'
                 + '\"filter\":{\"ISSUER\":{\"CN\":\"MTLS Certificate Authority\"}}}'])
            return True
        except Exception:
            log('Failed to configure the Chrome browser')
            return False


def configure_browsers():
    safari = configure_safari()
    chrome = configure_chrome()
    return safari & chrome


def skip_renewal():
    log('Skipping Okta certificate renewal.')
    exit(0)


def main():
    global key_chain_password
    configure()

    try:
        with open(os.devnull, 'w') as DEVNULL:
            key_chain_password = (subprocess.check_output(
                ['security', 'find-generic-password', '-l', DEVICE_TRUST_ALIAS, '-w'], stderr=DEVNULL)).splitlines()[0]
    except Exception:
        log('The Okta keychain does not exist.')
        skip_renewal()

    try:
        subprocess.call(['security', 'unlock-keychain', '-p',
                         key_chain_password, OKTA_KEY_CHAIN])
        log('Unlocked the Okta keychain.')
    except Exception:
        log('Failed to unlock the Okta keychain.')
        skip_renewal()

    if certificate_needs_renewal():
        if renew_certificate() is True:
            configure_browsers()
            configure_key_chain_partitions()
            log('Successfully renewed expiring Okta certificate.')
        else:
            log_error('Failed to renew expiring Okta certificate.')


if __name__ == "__main__":
    main()
"""
    return dt


def configure_device_trust_launcher_code():
    global TEAM_IDS_TO_WHITELIST
    replace_text_in_launch_agent('TEAM_IDS_TO_WHITELIST_FROM_MASTER_FILE', TEAM_IDS_TO_WHITELIST)
    replace_text_in_launch_agent('URL_FROM_MASTER_FILE', URL)


def replace_text_in_launch_agent(pattern, text):
    subprocess.call(['sed',
                     '-i',
                     '',
                     's/' + pattern + '/' + re.escape(text) + '/g',
                     os.path.expanduser(okta_dt_launch_agent)])


def configure_device_trust_agent():
    global okta_dt_launch_agent_dir
    global okta_dt_launch_agent
    log('Create DT client and set launch agent')
    try:
        if not os.path.exists(os.path.expanduser(okta_dt_launch_agent_dir)):
            os.makedirs(os.path.expanduser(okta_dt_launch_agent_dir))

        if os.path.exists(os.path.expanduser(okta_dt_launch_agent)):
            log('Device Trust launcher already exists, overwrite it.')

        with open(os.path.expanduser(okta_dt_launch_agent), 'w') as f:
            f.write(get_device_trust_launcher_code())
            f.close()

        # Following file permission operations are needed as open() is executed in root context
        subprocess.call(
            ['chmod', '700', os.path.expanduser(okta_dt_launch_agent)])
        configure_device_trust_launcher_code()
        subprocess.call(
            ['chmod', '500', os.path.expanduser(okta_dt_launch_agent)])
        subprocess.call(['chown', get_current_user(),
                         os.path.expanduser(okta_dt_launch_agent_dir)])
        subprocess.call(['chown', get_current_user(),
                         os.path.expanduser(okta_dt_launch_agent)])
        return True
    except Exception as e:
        log_error('Failed to configure Device Trust launcher : ' + str(e))
        return False


#########################
# Cleanup routines
#########################


def cleanup_identity_preference():
    execute_as_user(['security', 'set-identity-preference',
                     '-n', '-s', get_org_certificate_url()])
    cert_auth_domain = get_cert_auth_domain(get_metadata_url())
    if cert_auth_domain is not False:
        execute_as_user(['security', 'set-identity-preference',
                         '-n', '-s', cert_auth_domain])


def cleanup_key_chain():
    execute_as_user(['security', 'delete-keychain', OKTA_KEY_CHAIN])
    execute_as_user(['security', 'delete-generic-password',
                     '-l', DEVICE_TRUST_ALIAS])


def cleanup_files_and_agent():
    log('Clean the Okta launch agent and files.')
    execute_as_user(['launchctl', 'remove', okta_dt_launch_domain])
    execute_as_user(['rm', '-rf', okta_dt_launch_agent_dir])
    execute_as_user(['rm', '-rf', okta_dt_launch_plist_file])


def cleanup():
    log('Clean up Okta keychain.')
    cleanup_identity_preference()
    cleanup_key_chain()


def uninstall():
    log('Device Trust uninstalling..')
    cleanup()
    cleanup_files_and_agent()


#########################
# Main routines
#########################


def create_self_signed(key):
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "CA"
    cert.get_subject().O = "Contoso"  # noqa: E741
    cert.get_subject().CN = "Okta MTLS"
    cert.set_serial_number(123)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    return cert


def report_error_and_exit():
    sys.stderr.write("Okta Device Trust returning ERROR.")
    sys.exit(1)


def main():
    log_debug('Running main()')
    try:
        # create Okta keychain
        if configure_key_chain() is False:
            log_error('Failed to configure Keychain!!')
            cleanup()
            report_error_and_exit()

        # Enroll to Okta and get a Device Trust certificate
        if configure_certificate() is False:
            log_error('Failed to enroll!!')
            cleanup()
            report_error_and_exit()

        # configure browsers to present the certificate silently
        if configure_browsers() is False:
            log_error('Failed to configure browsers!!')
            cleanup()
            report_error_and_exit()

        # whitelist the latest applications
        if configure_key_chain_partitions() is False:
            log_error('Failed to whitelist applications!!')
            cleanup()
            report_error_and_exit()

        # Configure periodic device trust task that unlocks keychain and renews
        # certificate
        if configure_device_trust_agent() is False:
            log_error('Failed to configure device trust agent!!')
            cleanup()
            report_error_and_exit()

        # Configure launch agent to run device trust registration task
        # periodically and on user log-in
        if setup_launch_agent() is False:
            log_error('Failed to configure launch agent!!')
            cleanup()
            report_error_and_exit()

        log('This device is now successfully setup for Okta Device Trust.')
    except Exception as e:
        log_error('Failed to configure Device Trust : ' + str(e))
        cleanup()
        report_error_and_exit()


def set_token(org_token, url):
    global ORG_TOKEN
    global URL
    ORG_TOKEN = org_token
    URL = url


def execute_script(org_token, url):
    set_token(org_token, url)
    main()


if __name__ == "__main__":
    set_logger()
    setup_global_variables()

    log('Registering trusted device with Okta, for user : ' + get_current_user())
    log('Using home directory : ' + get_home_directory())
    if not get_current_user():
        log_error(
            'Running as [%s], not a user context. Exiting.' %
            get_current_user())
        report_error_and_exit()

    if not URL:
        log_error('Please set the org url')
        report_error_and_exit()

    if len(sys.argv) > 1:
        # jamf is known to add additional parameters to the script commandline
        # https://www.jamf.com/jamf-nation/articles/146/script-parameters
        for x in sys.argv[1:]:
            if x.lower() == "uninstall":
                uninstall()
                log('Device Trust uninstall completed successfully.')
                exit(0)
            if x.lower() == "verbose":
                VERBOSE_MODE = True

    if not ORG_TOKEN:
        log_error('Please set the org token')
        report_error_and_exit()

    main()
    exit(0)
