#!/usr/bin/env python
# encoding: utf8
"""
account.py

Created by la.onger <yuelang85@gmail.com> on 2008-12-26.
Copyright (c) 2008 la.onger All rights reserved.
"""
class account:
	
	#email account:
	pophost = '' #邮箱的pop服务器
	smtphost = '' #邮箱的smtp服务器
	username = '' #邮箱的帐户
	email_password = '' #邮箱的密码
	email = '' #发信用的邮箱地址
	ifssl = 0 #如果服务器需要使用ssl加密，则选择此项.
	fresh_time=15 #检查邮件的周期，单位是秒

	#Fetion account:
	mobile="" #用来登陆飞信的手机号
	password="" #飞信密码
	to=["sip:接收信息的手机的飞信帐号@fetion.com.cn;p=这里填上手机号码的前6位与134099的差","接收信息的手机号码"] #sip=Fetion_account_number@fetion.com.cn;
                                        	#p=(first_six_number_of_mobilephone)-(134099)
