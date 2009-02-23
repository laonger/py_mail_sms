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

FETION_CONFIG_URL = 'http://nav.fetion.com.cn/nav/getsystemconfig.aspx'

class Fetion:
	callid = 0
	seq = 0

	def __init__(self, mobileno, password):
		self.mobileno = mobileno
		self.password = password

	def next_callid(self):
		self.callid += 1

		return self.callid

	def next_seq(self):
		self.seq += 1
		
		return self.seq

	def get_system_config(self):
		msg = '<config><user mobile-no="%s" /><client type="PC" version="3.2.0540" platform="W5.1" /><servers version="0" /><service-no version="0" /><parameters version="0" /><hints version="0" /><http-applications version="0" /></config>' % self.mobileno
		request = urllib2.Request(FETION_CONFIG_URL, data=msg)
		conn = urllib2.urlopen(request)
		response = conn.read()

		# parse response for getting server related information
		xmldoc = ET.parse(StringIO.StringIO(response))
		result = xmldoc.find('//http-tunnel').text
		self.http_tunnel = result
		result = xmldoc.find('//sipc-proxy').text
		self.sipc_proxy = result.split(':')[0]
		self.sipc_proxy_port = int(result.split(':')[1])
		result = xmldoc.find('//sipc-ssl-proxy').text
		self.sipc_ssl_proxy = result.split(':')[0]
		self.sipc_ssl_proxy_port = int(result.split(':')[1])
		result = xmldoc.find('//ssi-app-sign-in').text
		self.ssi_server = result

	def login_ssi(self):
		re_ssic = re.compile('ssic=(.*?);')
		re_sid = re.compile('sip:(\d+)@(.+);')

		data = {'mobileno' : self.mobileno, 'pwd' : self.password}
		conn = urllib2.urlopen(self.ssi_server, urllib.urlencode(data))

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
		res = re_sid.findall(uri)
		if res:
			sid, domain = res[0]

		self.ssic = ssic
		self.sid = sid
		self.domain = domain
		self.uri = uri

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


