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

INTERVAL = 30

class FetionClient(LineReceiver):
    def connectionMade(self):
        self._do_login()

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
            print 'From:', response.headers['F']
            print 'Got message:', response.body
            self._accept_message(response)

    def sendSMS(self, to, body):
        fetion = self.factory.fetion
        msg = SIPMsgRequest(fetion, 'M', {'T': to, 'N': 'SendSMS'}, body, True).to_string()
        self.sendLine(msg)

    def sendLongSMS(self, to, body):
        fetion = self.factory.fetion
        msg = SIPMsgRequest(fetion, 'M', {'T': to, 'N': 'SendCatSMS'}, body, True).to_string()
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

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed:', reason.getErrorMessage()
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print 'connection lost:', reason.getErrorMessage()
        reactor.stop()

class HTTPDaemon(resource.Resource):
    isLeaf = True

    def __init__(self, fetion_client):
        self.fetion_client = fetion_client

    def render_GET(self, ctx):
        return """<form action="/" method="post">
                    To: <input name="to" type="text" /><br />
                    Body: <textarea name="body"></textarea><br />
                    <input type="submit" value="Send" />
                  </form>"""

    def render_POST(self, ctx):
        if ctx.args.has_key('to') and ctx.args.has_key('body'):
            self.fetion_client.client.sendSMS(ctx.args['to'][0], ctx.args['body'][0])
        elif ctx.args.has_key('to') and ctx.args.has_key('lbody'):
            self.fetion_client.client.sendLongSMS(ctx.args['to'][0], ctx.args['lbody'][0])
        return 'Sent SMS\n'

def main():
    # create a options parser
    parser = OptionParser()
    parser.add_option('-m', '--mobile', dest='mobile', type='string',
                      help='mobile phone number')
    parser.add_option('-p', '--password', dest='password', type='string',
                      help='login password')
    parser.add_option('-H', '--host', dest='hostname', type='string',
                      default='localhost',
                      help='specify hostname to run on, default is localhost')
    parser.add_option('-P', '--port', dest='port', type='int',
                      default=8765, help='port number to run on, default is 8765')

    (options, args) = parser.parse_args()

    # handle options
    if not options.mobile:
        parser.error('-m option is required')

    mobile = options.mobile
    hostname = options.hostname
    port = options.port
    if not options.password:
        password = getpass()
    else:
        password = options.password

    fetion = Fetion(mobile, password)
    fetion.get_system_config()
    fetion.login_ssi()

    factory = FetionClientFactory(fetion)
    daemon = server.Site(HTTPDaemon(factory))
    reactor.connectTCP(fetion.sipc_proxy, fetion.sipc_proxy_port, factory)
    print 'Connected to %s:%s' % (fetion.sipc_proxy, fetion.sipc_proxy_port)
    reactor.listenTCP(port, daemon, interface=hostname)
    print 'Listening %s:%s' % (hostname, port)
    reactor.run()

if __name__ == '__main__':
    main()

