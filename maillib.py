#!/usr/bin/env python
# encoding: utf-8
"""
maillib.py

use for get mails' list, mail, send mail.

Created by la.onger <yuelang85@gmail.com> on 2009-02-19.
Copyright (c) 2009 la.onger All rights reserved.

"""

import poplib, smtplib, string, email, os, time
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

class mail:
	"""
	
	"""

	def __init__(self, ):
		"""
		Constructor.
		"""
		self.content = ""
	
	def _update_txt_last_mail(self, nMail, uidl):
		"""
		此函数用于更新last_mail.txt
		
		nMail -- str 最新一封邮件的编号
		uidl -- str 最新一封邮件的uidl
		"""
		txt_last_mail=open('last_mail.txt','r')
		last_mail=txt_last_mail.readlines()	#last_mail获得上一次打开程序时收到最后一封邮件的num和uidl。
		txt_last_mail.close()
		last_mail[1]=nMail+"\n"
		last_mail[2]=uidl+"\n"
		txt_last_mail=open('last_mail.txt','w')
		txt_last_mail.write(string.join(last_mail))
		txt_last_mail.close()
		
	def _connect_pop(self,):
		"""
		此函数用于得到邮件的邮件头或者整封邮件
		"""
		#先尝试登陆
		try:
			if account.ifssl == 1:
				serv = poplib.POP3_SSL(account.pophost)
			elif account.ifssl == 0:
				serv = poplib.POP3(account.pophost)
			serv.user(account.username)
			serv.pass_(account.email_password)
			return serv
		except:
			return "Can Not connect mail server"
		
	def _mail_head_item_convert(self,item):
		"""
		此函数被get_mail_haed调用，用于将邮件头中的每项转换成可读的形式
		
		item -- str
		"""
		return encoder(email.Header.decode_header(item)[0][0]\
				  ,email.Header.decode_header(item)[0][1])
		

	def _get_mail_head(self,which_mail):
		"""
		此函数用于得到编号为which_mail的邮件的头
		
		which_mail -- str 需要得到邮件头的邮件的编号
		"""
		conn = self._connect_pop()
		head = conn.top(which_mail,'0')[1]
		mail_uidl = conn.uidl(which_mail).split( " " )[-1]
		conn.quit()

		head = email.message_from_string(string.join(head,'\n'))
		head_date = self._mail_head_item_convert(head.get('date'))
		head_subject = self._mail_head_item_convert(head.get('subject'))
		head_from = self._mail_head_item_convert(head.get('from'))
		#print type(which_mail),type(head_date),type(head_from),type(head_subject)
		mail_head = "NO."+which_mail\
				+" At "+head_date[:-6]\
				+"\nF: "+head_from\
				+"\nSub: "+head_subject

		return mail_head, mail_uidl
	

	def new_mail_notice(self, ifauto=1):
		"""
		检查新邮件，并生成由邮件标题，日期，发信人，编号组成的邮件列表
		
		ifauto -- int 判断是否手动检查邮件，如果是，则ifauto==0，否则为1
		"""
		conn = self._connect_pop()
	
		newest_mail_num = str(conn.stat()[0]) #获得服务器上最新的邮件的编号
		if newest_mail_num == "0":
			notice = "there is no new mail."
		else:
			newest_mail_uidl = conn.uidl(newest_mail_num).split(" ")[-1] #获得服务器上最新邮件的uidl
			conn.quit()

			txt_last_mail = open( 'last_mail.txt','r' )
			last_mail = txt_last_mail.readlines() #last_mail获得上一次打开程序时收到的最后一封邮件
			txt_last_mail.close()

			if last_mail[1] in ["-1\n"," -1\n"]: #如果这是第一次打开程序
				self._update_txt_last_mail(newest_mail_num,newest_mail_uidl) #将服务器上最新的邮件的num和uidl记录进last_mail.txt
				notice = "There is no new mail"
			else:
				notice = ""
				last_mail_num=last_mail[1][1:-1]
				last_mail_uidl=last_mail[2][1:-1]
				if last_mail_num == newest_mail_num:
					notice = "There is no new mail"
				elif int(last_mail_num) > int(newest_mail_num):
					last_mail_num = newest_mail_num
					notice = self._get_mail_head( last_mail_num )[0]
				else:
					for mail_num in range(int( last_mail_num )+1,int(newest_mail_num)+1):
						mail_head = self._get_mail_head(str(mail_num))
						#print mail_head
						notice = mail_head[0]+"\n"+notice
					self._update_txt_last_mail(newest_mail_num, last_mail_uidl) #将服务器上最新邮件的num和uidl更新到last_mail.txt中
		notice = "\n"+notice
		if ifauto == 1:
			if notice == "\nThere is no new mail":
				pass
			else:
				return notice
		elif ifauto == 0:
			return notice

	def _content_parser(self, content):
		"""
		此函数用于使邮件内容可读
		
		content -- obj 要转换的邮件的内容
		"""
		if content.is_multipart():
			for part in content.get_payload():
				self._content_parser(part)
		else:
			if content.get_content_type() in ['text/plain','Text/plain','Text/Plain','text/Plain']:
				self.content = self.content + encoder(content.get_payload(decode=True),content.get_charsets()[0])
			else:
				self.content = self.content + '[\\'+content.get_content_type()+'/]'

	def get_whole_mail(self, mail_num):
		"""
		此函数用于得到和生成整个邮件
			
		mail_num -- str 想要得到的邮件的编号
		"""
		conn = self._connect_pop()
		msg = conn.top(mail_num, '-1' )[1]
		conn.quit()
		msg = email.message_from_string(string.join(msg, '\n'))
		self._content_parser(msg)
		msg = "\n"+self._get_mail_head(mail_num)[0]+"\nMSG:\n"+self.content
		self.content = ''
		return msg
		
	def send_mail(self,got_sms):
		got_sms=got_sms.split("\n",3)
		print got_sms
		msg=email.Message.Message()

		#获得并组织邮件头，包括收信人（to），寄信人（from），时间（date），主题（subject）。
		msg['to']=got_sms[0].split(":",1)[1].encode('utf-8')
		msg['from']=account.email
		msg['date']=time.ctime()
		print msg
		msg['subject']=email.Header.Header(got_sms[1].split(":",1)[1],'utf-8')
		#获得并组织邮件内容	
		print msg
		body=email.MIMEText.MIMEText(got_sms[3],_subtype='plain',_charset='utf-8')
		print body
		#生成邮件
		whole_msg=msg.as_string()[:-1]+body.as_string()
		#return whole_msg
		print whole_msg
		#发送邮件
		try:
			print "sending mail...."
			serv=smtplib.SMTP(account.smtphost)
			print "connect"
			serv.login(account.username,account.email_password)
			print "login"
			serv.sendmail(msg['from'],msg['to'],whole_msg)
			return "mail sent"
		except:
			return "sending mail failed"

if __name__ == '__main__':
	"""
	main
	"""
	getmail = mail()
	print getmail.new_mail_notice()
	print getmail.get_whole_mail('44')
	print "T:yuelang85@gmail.com\nSub:这是标题\nMSG:\n这是正文第一行\n这是正文第二行\n"
	

