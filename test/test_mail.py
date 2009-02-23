#!/usr/bin/env python
# encoding: utf-8

import poplib, string, time, email

def encoder(doc,codec):
	"""转换编码，如果是gb2312，则先转化为unicode编码，再转为utf-8
	"""
	if codec==None:
		pass
	else:
		if not codec=='utf-8' or 'UTF-8':
			doc=unicode(doc,codec)
			doc=doc.encode('utf-8')
		elif codec=='utf-8' or 'UTF-8':
			pass
	return doc

def showmessage(mail):
	if mail.is_multipart():
		#n=0
		for part in mail.get_payload():
			showmessage(part)
				#pass
			#print part,'\n@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n\n\n\n\n\n\n\n\n\n'
			#print mail.get_content_subtype(),mail.get_content_type()
		#	n=n+1
		#print n
		#print mail.get_payload()[1]
		#print encoder(mail.get_payload()[0].get_payload(decode=True),mail.get_charsets()[1])
		#print encoder(mail.get_payload()[0].get_payload(),mail.get_charsets()[1])
	else:
		#print mail
		#print True
		#print mail.get_content_type()
		#print mail.get_payload(decode=True),mail.get_charsets()
		if mail.get_content_type() in ['text/plain','Text/plain','Text/Plain','text/Plain']:
			print encoder(mail.get_payload(decode=True),mail.get_charsets()[0])
		else:
			print '[\\',mail.get_content_type(),'/]'
		#print unicode(mail.get_payload(),'gb2312')
		#type=mail.get_content_charset()
		#if type==None:
		#	print mail.get_payload()
		#else:
		#	try:
		#		print unicode(mail.get_payload('base64'),type)
		#	except UnicodeDecodeError:
		#		print mail

serv = poplib.POP3('mail.long-er.name')
serv.user('laonger@long-er.name') 
serv.pass_('2101021')


#print serv.getwelcome()

#nMail = serv.stat()[0]

#mail=serv.retr(40)[1]
mail=serv.top('44','-1')[1]
#print mail
serv.quit()

mail=email.message_from_string(string.join(mail,'\n'))
#print dir(mail)
#print mail.get_charset(),mail.get_charsets(),mail.get_content_charset(),mail.get_content_maintype(),mail.get_content_subtype(),mail.get_content_type(),mail.get_default_type()
#print mail,"\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n###############################\n"
#mail['date']=mail.get('date')
#mail['subject']=mail.get('subject')
#mail['from']=mail.get('from')
#print mail.get_payload()
#print mail
#
showmessage(mail)

