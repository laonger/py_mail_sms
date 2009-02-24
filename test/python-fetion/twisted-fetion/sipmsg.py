import re

class SIPMsgRequest:
    def __init__(self, fetion, method, extras, body='', new_call=True):
        self.method = method
        self.body = body
        self.headers = {'F': fetion.sid,
                        'I': new_call and fetion.next_callid() or fetion.callid,
                        'Q': '%d %s' % (fetion.next_seq(), method)}
        if extras:
            for k, v in extras.items():
                self.headers[k] = v

    def to_string(self):
        msg = '%s fetion.com.cn SIP-C/2.0\r\n' % self.method
        for k, v in self.headers.items():
            msg += '%s: %s\r\n' % (k, v)
        msg += 'L: %s\r\n\r\n%s' % (len(self.body), self.body)

        return msg


class SIPMsgResponse:
    def __init__(self, message):
        self.parse_message(message)

    def create_message(self, code, text, body=''):
        self.code = code
        self.status = text
        self.body = body
        del self.headers['L']
		

    def get_nonce(self):
        re_nonce = re.compile('nonce="(\w+)"')
        return re_nonce.findall(self.headers['W'])[0]

    def parse_message(self, message):
        temp, self.body = message.split('\r\n\r\n', 1)
        temp = temp.split('\r\n')
        first_heard = temp[0].split(' ', 2)
        if first_heard[0] == 'SIP-C/2.0':
            self.protocol, self.code, self.status = first_heard
        else:
            self.method, self.sid, self.protocol = first_heard
        self.headers = dict(i.split(': ') for i in temp[1:])

    def remove_header(self, key):
        if self.headers.has_key(key):
            del self.headers[key]

    def to_string(self):
        msg = 'SIP-C/2.0 %s %s\r\n' % (self.code, self.status)
        for k, v in self.headers.items():
            msg += '%s: %s\r\n' % (k, v)
        msg += 'L: %s\r\n\r\n%s' % (len(self.body), self.body)

        return msg

