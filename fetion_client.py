#!/usr/bin/env python
# -*- coding: utf8 -*-

from getpass import getpass
from optparse import OptionParser

from twisted.application import internet
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.web import server, resource

from fetion import Fetion
from sipmsg import SIPMsgRequest, SIPMsgResponse

from maillib import *
import re

INTERVAL = 30


class FetionClient(LineReceiver):
	
	def __init__(self):
		pass
		#self.callTime=5
	
	def connectionMade(self):
		global fetion_reconnected
		#print fetion_reconnected
		self._do_login()
		print "connectionMade"
		reactor.callLater(15,self.check_mail)
		#self.check_mail()
		
	#def connectionLost(self,reason):
		#if vars().has_key('self.call_later'):
		#self.call_later.cancel()
		#print self.call_later
		#print "lost"
	
	def check_mail(self):
		print "check mail"
		checkmail=mail()
		sms=checkmail.new_mail_notice()
		print sms
		if sms == None:
			print "\nThere is no new mail."
		else:
			#print sms
			self.sendLongSMS(sms)
			print "send"
		self.call_later=reactor.callLater(5,self.check_mail)
		
	
	def _do_login(self):
		fetion = self.factory.fetion
		msg = SIPMsgRequest(fetion, 'R', None, '<args><device type="PC" version="0" client-version="3.1.0480" /><caps value="fetion-im;im-session;temp-group" /><events value="contact;permission;system-message" /><user-info attributes="all" /><presence><basic value="400" desc="" /></presence></args>').to_string()
		self.sendLine(msg)

	def _do_register(self):
		fetion = self.factory.fetion
		_cnonce = fetion.calc_cnonce()
		_response = fetion.calc_response(fetion.nonce, _cnonce)
		_salt = fetion.calc_salt()
		msg = SIPMsgRequest(fetion, 'R', {'A': 'Digest algorithm="SHA1-sess",response="%s",cnonce="%s",salt="%s"' % (_response, _cnonce, _salt)}, '<args><device type="PC" version="0" client-version="3.1.0480" /><caps value="fetion-im;im-session;temp-group" /><events value="contact;permission;system-message" /><user-info attributes="all" /><presence><basic value="400" desc="" /></presence></args>', False).to_string()
		self.sendLine(msg)

	def _accept_invite(self, response):
		fetion = self.factory.fetion
		my_ip, my_port = self.transport.realAddress
		msg = 'v=0\r\no=-0 0 IN %s:%d\r\ns=session\r\nc=IN IP4 %s:%d\r\nt=0 0\r\nm=message %d sip %s\r\n' % (my_ip, my_port, my_ip, my_port, my_port, fetion.uri)
		response.create_message('200', 'OK', msg)
		self.sendLine(response.to_string())

	def _accept_message(self, response):
		fetion = self.factory.fetion
		response.remove_header('C')
		response.remove_header('D')
		response.remove_header('K')
		response.remove_header('XI')
		response.create_message('200', 'OK')
		self.sendLine(response.to_string())

	def dataReceived(self, data):
		fetion = self.factory.fetion
		#print data
		response = SIPMsgResponse(data)
		if (hasattr(response, 'code')):
			if (response.code == '401'):
				fetion.nonce = response.get_nonce()
				self._do_register()
				# use _do_register for keeping alive
				s = internet.TimerService(INTERVAL, self._do_register)
				s.startService()
			elif (response.code == '200'):
				pass
			elif (response.code == '280'):
				print 'Sent SMS to %s' % response.headers['T']
			else:
				print 'Code: %s, Error: %s' % (response.code, response.status)
		elif (response.method == 'I'):
			self._accept_invite(response)
		
		elif (response.method == 'M'):
			
			if response.headers['F'] in account.to:
				getmail = mail()
				
				if re.match("^get\s+\d",response.body,re.I):
					sms=getmail.get_whole_mail(re.findall("[\d]+",response.body)[0])
					self.sendLongSMS(sms)
				
				elif re.match("^[T:]",response.body,re.I):
					#and re.match("^[Sub:]",response.body,re.I) \
					#and re.match("^[MSG:]",response.body,re.I):
					print "try to send...."
					print type(response.body)
					self.sendLongSMS(getmail.send_mail(response.body))
				
				elif re.match("^[check]",response.body,re.I):
					self.sendLongSMS(getmail.new_mail_notice(ifauto=0))
						
			print 'From:', response.headers['F']
			if (response.body == 'hi'):
				print 'True'
			print 'Got message:', response.body
			self._accept_message(response)

	def sendSMS(self, body):
		fetion = self.factory.fetion
		to=account.to[0]
		msg = SIPMsgRequest(fetion, 'M', {'T': to, 'N': 'SendSMS'}, body, True).to_string()
		print msg
		self.sendLine(msg)

	def sendLongSMS(self, body):
		#print "sending"
		to = account.to[0]
		fetion = self.factory.fetion		
		msg = SIPMsgRequest(fetion, 'M', {'T': to, 'N': 'SendCatSMS'}, body, True).to_string()
		#print "send"
		self.sendLine(msg)

class FetionClientFactory(ClientFactory):
	protocol = FetionClient
	client = None

	def __init__(self, fetion):
		self.fetion = fetion

	def buildProtocol(self, addr):
		p = self.protocol()
		p.factory = self
		self.client = p
		return p
		
	def connectionMade(self):
		"""docstring for connectionMade"""
		pass
	
	def clientConnectionFailed(self, connector, reason):
		print 'connection failed:', reason.getErrorMessage()
		reactor.stop()

	def clientConnectionLost(self, connector, reason):
		print 'connection lost:', reason.getErrorMessage()
		self.client.call_later.cancel()
		print "lost"
		try:
			connector.connect()
			print "reconnected"
		except:
			print "reconnect failed"

def main():

	mobile = '15001195207'
	hostname = 'localhost'
	port = 8765
	password = '829508ll'

	fetion = Fetion(mobile, password)
	fetion.get_system_config()
	try:
		fetion.login_ssi()
		print "get it"
	except:
		print "fail"

	factory = FetionClientFactory(fetion)
	reactor.connectTCP(fetion.sipc_proxy, fetion.sipc_proxy_port, factory)
	print 'Connected to %s:%s' % (fetion.sipc_proxy, fetion.sipc_proxy_port)
	reactor.run()

if __name__ == '__main__':
	main()

