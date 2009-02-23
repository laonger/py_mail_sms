#sr/bin/env python
# encoding: utf8
"""
send_mail.py

Created by la.onger <yuelang85@gmail.com> on 2008-1-2.
Copyright (c) 2008 la.onger All rights reserved.
"""

import smtplib,email,time
from account import account

def encoder(doc, codec):
	"""
	转换编码，如果编码是utf-8则不转换
	
	doc -- str 要转换编码的字串
	codec -- str 被转换的编码的编码
	"""
	if codec == None:
		pass
	else:
		if not codec == 'utf-8':
			doc = unicode(doc,codec)
			doc = doc.encode('utf-8')
		elif codec == 'utf-8':
			pass
	return doc


def send_mail(got_sms):
	got_sms=got_sms.split("\n",3)
	#print got_sms
	msg=email.Message.Message()

	#获得并组织邮件头，包括收信人（to），寄信人（from），时间（date），主题（subject）。
	msg['to']=got_sms[0].split(":",1)[1].encode('utf-8')
	msg['from']=account.email
	msg['date']=time.ctime()
	#print got_sms[2][8:]
	msg['subject']=email.Header.Header(got_sms[1].split(":",1)[1],'utf-8')
	#获得并组织邮件内容	
	#print got_sms[4]
	body=email.MIMEText.MIMEText(got_sms[3],_subtype='plain',_charset='utf-8')
	#print body
	#生成邮件
	whole_msg=msg.as_string()[:-1]+body.as_string()
	#return whole_msg
	print whole_msg
	#发送邮件
	try:	
		serv=smtplib.SMTP(account.smtphost)
		print "connect"
		serv.login(account.username,account.email_password)
		print "login"
		serv.sendmail(msg['from'],msg['to'],whole_msg)
		print "sending...."
		return "mail sent"
	except:
		return "sending mail failed"


if __name__ == '__main__':
	print send_mail("T:yuelang85@gmail.com\nSub:这是标题\nMSG:\n这是正文第一行\n这是正文第二行\n")
