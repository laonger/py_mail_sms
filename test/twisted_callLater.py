#!/usr/bin/env python
# encoding: utf-8

from twisted.internet import protocol,reactor
from twisted.protocols import basic
import time
tim=0
class testProtocol(basic.LineReceiver):
	def connectionMade(self):
		self.transport.write('connectioned\n')
		self.loop()
	def lineReceived(self,data):
		print "get messege: ",data
	def loop(self):
		global tim
		tim=tim+5
		print tim
		reactor.callLater(5,self.loop)

class testFactory(protocol.ServerFactory):
	protocol=testProtocol

reactor.listenTCP(1079,testFactory())
print 'Server Opened'
reactor.run()

