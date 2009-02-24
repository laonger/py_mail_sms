#!/usr/bin/env python
# -*- coding: utf8 -*-

import binascii
import hashlib
import re
import StringIO
import urllib
import urllib2
import uuid
import xml.etree.ElementTree as ET

from getpass import getpass
from optparse import OptionParser

from account import account

FETION_URL = 'http://221.130.45.203/ht/sd.aspx'
FETION_SIPC = '221.130.45.203:8080'
FETION_LOGIN_URL = 'https://nav.fetion.com.cn/ssiportal/SSIAppSignIn.aspx'
FETION_CONFIG_URL = 'http://nav.fetion.com.cn/nav/getsystemconfig.aspx'
FETION_SIPP = 'SIPP'

DEBUG = False

class Fetion:
    ssic = ''
    sid = ''
    domain = ''

    call = 0
    seq = 0
    guid = None

    contacts = []

    def __init__(self, mobileno, password):
        self.mobileno = mobileno
        self.password = password
        self.http_tunnel = FETION_URL
        self.sipc_proxy = FETION_SIPC

    def login(self):
        re_ssic = re.compile('ssic=(.*?);')
        re_sid = re.compile('sip:(\d+)@(.+);')
        
        login_url = FETION_LOGIN_URL
        data = {'mobileno' : self.mobileno, 'pwd' : self.password}
        conn = urllib2.urlopen(login_url, urllib.urlencode(data))

        # Get ssic
        headers = str(conn.headers)
        res = re_ssic.findall(headers)
        if res:
            ssic = res[0]
            
        response = conn.read()

        # Get other attribs from response
        xmldoc = ET.XML(response)
        status_code = xmldoc.attrib['status-code']
        user_node = xmldoc.find('user')
        uri = user_node.attrib['uri']
        mobile_no = user_node.attrib['mobile-no']
        user_status = user_node.attrib['user-status']

        # get sid and domain from uri
        res = re_sid.findall(uri)
        if res:
            sid, domain = res[0]

        self.ssic = ssic
        self.sid = sid
        self.domain = domain

    def http_register(self):
        arg= '<args><device type="PC" version="0" client-version="3.1.0480" /><caps value="fetion-im;im-session;temp-group" /><events value="contact;permission;system-message" /><user-info attributes="all" /><presence><basic value="400" desc="" /></presence></args>'

        _call = self.next_call()

        # request 1
        _url = self.next_url('i')
        response = self.send_request(_url, FETION_SIPP)

        # request 2
        msg = self.create_sip_data('R fetion.com.cn SIP-C/2.0', (('F',self.sid), ('I',_call), ('Q','1 R')), arg) + FETION_SIPP
        _url = self.next_url()
        response = self.send_request(_url, msg)

        # request 3
        _url = self.next_url()
        response = self.send_request(_url, FETION_SIPP)
        re_nonce = re.compile('nonce="(\w+)"')
        nonce = re_nonce.findall(response)[0]

        # request 4
        _cnonce = self.calc_cnonce() # calculate cnonce
        _response = self.calc_response(nonce, _cnonce) # calculate response
        _salt = self.calc_salt()  # calculate salt
        msg = self.create_sip_data('R fetion.com.cn SIP-C/2.0', (('F', self.sid), ('I',_call), ('Q', '2 R'), ('A', 'Digest algorithm="SHA1-sess",response="%s",cnonce="%s",salt="%s"' % (_response, _cnonce, _salt))), arg) + FETION_SIPP
        _url = self.next_url()
        response = self.send_request(_url, msg)

        # request 5
        _url = self.next_url()
        response = self.send_request(_url, FETION_SIPP)

    def get_contacts_list(self):
        arg = '<args><contacts><buddy-lists /><buddies attributes="all" /><mobile-buddies attributes="all" /><chat-friends /><blacklist /></contacts></args>'
        _call = self.next_call()
        msg = self.create_sip_data('S fetion.com.cn SIP-C/2.0', (('F',self.sid), ('I',_call), ('Q','1 S'), ('N','GetContactList')), arg) + FETION_SIPP
        _url = self.next_url()
        self.send_request(_url, msg)
        _url = self.next_url()
        response = self.send_request(_url, FETION_SIPP)

        re_contacts = re.compile('uri="(sip[^"]+)"')
        res = re_contacts.findall(response)

        return res

    def get_contacts_info(self, contacts_list):
        if contacts_list:
            arg = '<args><contacts attributes="all">'
            for contact in contacts_list:
                arg += '<contact uri="%s" />' % contact
            arg += '</contacts></args>'

            _call = self.next_call()
            msg = self.create_sip_data('S fetion.com.cn SIP-C/2.0', (('F',self.sid), ('I',_call), ('Q','1 S'), ('N','GetContactsInfo')), arg) + FETION_SIPP
            _url = self.next_url()
            self.send_request(_url, msg)
            _url = self.next_url()
            response = self.send_request(_url, FETION_SIPP)

            re_info = re.compile('uri="([^"]+)".*?mobile-no="([^"]+)"')
            res = re_info.findall(response)

            for contact in contacts_list:
                if not filter(lambda x: x[0] == contact, res):
                    res.append((contact, ''))

            self.contacts = res

    def get_contact_sid(self, info):
        sid = None

        if info[:4] == 'sip:':
            sid = filter(lambda x: x[0] == info, self.contacts)
        elif len(info) == 9:
            sid = filter(lambda x: x[0][4:13] == info, self.contacts)
        elif len(info) == 11:
            sid = filter(lambda x: x[1] == info, self.contacts)

        return sid and sid[0][0] or None

    def get_system_config(self):
        msg = '<config><user mobile-no="%s" /><client type="PC" version="3.2.0540" platform="W5.1" /><servers version="0" /><service-no version="0" /><parameters version="0" /><hints version="0" /><http-applications version="0" /></config>' % self.mobileno
        request = urllib2.Request(FETION_CONFIG_URL, data=msg)
        conn = urllib2.urlopen(request)
        response = conn.read()

        xmldoc = ET.parse(StringIO.StringIO(response))
        result = xmldoc.find('//http-tunnel').text
        if result:
            self.http_tunnel = result
        result = xmldoc.find('//sipc-proxy').text
        if result:
            self.sipc_proxy = result

    def send_sms(self, to, content):
        _call = self.next_call()
        msg = self.create_sip_data('M fetion.com.cn SIP-C/2.0', (('F',self.sid), ('I',_call), ('Q','1 M'), ('T',to), ('N','SendSMS')), content) + FETION_SIPP
        _url = self.next_url()
        self.send_request(_url, msg)
        _url = self.next_url()
        response = self.send_request(_url, FETION_SIPP)

        if 'Send SMS OK' in response:
            return True
        else:
            return False

    def send_cat_sms(self, to, content):
        _call = self.next_call()
        msg = self.create_sip_data('M fetion.com.cn SIP-C/2.0', (('F',self.sid), ('I',_call), ('Q','1 M'), ('T',to), ('N','SendCatSMS')), content) + FETION_SIPP
        _url = self.next_url()
        self.send_request(_url, msg)
        _url = self.next_url()
        response = self.send_request(_url, FETION_SIPP)

        if 'Send SMS OK' in response:
            return True
        else:
            return False

    def send_request(self, url, data):
        if not self.guid:
            self.guid = str(uuid.uuid1())
        headers = {
                'User-Agent' : 'IIC2.0/pc 3.1.0480', 
                'Cookie':'ssic=%s' % self.ssic,
                'Content-Type' : 'application/oct-stream',
                'Pragma' : 'xz4BBcV%s' % self.guid,
                }
        request = urllib2.Request(url, headers=headers, data=data)
        conn = urllib2.urlopen(request)
        response = conn.read()
        if DEBUG:
            print 'DEBUG'.center(78, '*')
            print 'URL:', url
            print 'Data:', data
            print 'Response:', response
            print 'DEBUG'.center(78, '*')
            print

        return response

    def create_sip_data(self, invite, fields, arg=''):
        sip = invite + '\r\n'
        for k, v in fields:
            sip += '%s: %s\r\n' % (k, v)
        sip += 'L: %s\r\n\r\n%s' % (len(arg), arg)

        return sip


    def next_call(self):
        self.call += 1

        return self.call

    def next_url(self, t='s'):
        self.seq += 1

        return '%s?t=%s&i=%s' % (self.http_tunnel, t, self.seq)

    def calc_cnonce(self):
        md5 = hashlib.md5()
        md5.update(str(uuid.uuid1()))

        return md5.hexdigest().upper()

    def hash_password(self):
        salt = '%s%s%s%s' % (chr(0x77), chr(0x7A), chr(0x6D), chr(0x03))
        sha1 = hashlib.sha1()
        sha1.update(self.password)
        src = salt + sha1.digest()
        sha1 = hashlib.sha1()
        sha1.update(src)

        return '777A6D03' + sha1.hexdigest().upper()

    def calc_response(self, nonce, cnonce):
        hashpassword = self.hash_password()
        binstr = binascii.unhexlify(hashpassword[8:])
        sha1 = hashlib.sha1()
        sha1.update('%s:%s:%s' % (self.sid, self.domain, binstr))
        key = sha1.digest()
        md5 = hashlib.md5()
        md5.update('%s:%s:%s' % (key, nonce, cnonce))
        h1 = md5.hexdigest().upper()
        md5 = hashlib.md5()
        md5.update('REGISTER:%s' % self.sid)
        h2 = md5.hexdigest().upper()
        md5 = hashlib.md5()
        md5.update('%s:%s:%s' % (h1, nonce, h2))

        return md5.hexdigest().upper()

    def calc_salt(self):
        return self.hash_password()[:8]

def main():
    # create a options parser
    parser = OptionParser()
#    parser.add_option('-m', '--mobile', dest='mobile', type='string',
#                      help='mobile phone number')
#    parser.add_option('-p', '--password', dest='password', type='string',
#                      help='login password')
#    parser.add_option('-t', '--to', dest='to', type='string',
#                      help='SMS to')
    parser.add_option('-b', '--body', dest='body', type='string',
                      help='SMS body')
    parser.add_option('-l', '--long-body', dest='lbody', type='string',
                      help='SMS long body')

    (options, args) = parser.parse_args()

    # handle options
#    if not options.mobile:
#        parser.error('-m option is required')

    mobile = account.mobile
    if not account.password:
        password = getpass()
    else:
        password = account.password

    fetion = Fetion(mobile, password)
    fetion.get_system_config()
    fetion.login()
    fetion.http_register()
    fetion.get_contacts_info(fetion.get_contacts_list())

    if account.to:
        sid = fetion.get_contact_sid(account.to)

        if not sid:
            sid = account.to

        if sid:
            if options.body:
                if fetion.send_sms(sid, options.body):
                    print 'Sent SMS'
                else:
                    print 'Error occurs'
            elif options.lbody:
                if fetion.send_cat_sms(sid, options.lbody):
                    print 'Sent SMS'
                else:
                    print 'Error occurs'

if __name__ == '__main__':
    main()

