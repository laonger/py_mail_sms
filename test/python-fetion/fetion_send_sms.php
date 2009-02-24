<?php
/**
	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; version 2 of the License.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
 * 
 * @author c.young@xicabin
 * @license GPL
 * @version 1.0
 */

define('FETION_URL', 'http://221.130.44.194/ht/sd.aspx');
define('FETION_LOGIN_URL', 'https://nav.fetion.com.cn/ssiportal/SSIAppSignIn.aspx');
define('FETION_CONFIG_URL', 'http://nav.fetion.com.cn/nav/getsystemconfig.aspx');
define('FETION_SIPP', 'SIPP');

static $fetion_proxy = null;
static $fetion_debug = false;

/**
 * debug output
 * 
 * @msg message
 * @data addtional data
 */
function fetion_debug($msg, $data = null) {
	global $fetion_debug;
	if ($fetion_debug) {
		print "[*] $msg\r\n";
		if (!empty($data)) {
			print_r($data);
		}
	}
}
/**
 * create sip package
 * 
 * @invite sip invite
 * @fields array of fields
 * @arg argument to send
 */
function fetion_sip_create($invite, $fields, $arg = '') {
	$sip = $invite."\r\n";
	foreach ($fields as $k=>$v) {
		$sip .= "$k: $v\r\n";
	}
	$sip .= "L: ".strval(strlen($arg))."\r\n\r\n{$arg}";
	return $sip;
}

/**
 * create a curl handle with fetion option
 * 
 * @url url
 * @ssic user identification
 * @post data to post
 */
function fetion_curl_init($url, $ssic = null, $post = null) {
	// create a new guid, and keep it !
	static $guid = null;
	if ($guid == null) {
		$guid = strtolower(trim(com_create_guid(), "{}"));
	}
	// set headers, e.g. pragma
	$headers = array('Content-Type: application/oct-stream', 'Pragma: xz4BBcV'.$guid);
	$ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, $url);
	curl_setopt($ch, CURLOPT_USERAGENT, 'IIC2.0/PC 3.2.0540');
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
	curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
	// ssic
	if ($ssic != null) {
		curl_setopt($ch, CURLOPT_COOKIE, "ssic=$ssic");
	}
	// post data
	if ($post != null) {
		curl_setopt($ch, CURLOPT_POST, true);
		curl_setopt($ch, CURLOPT_POSTFIELDS, $post);
	}
	// proxy
	global $fetion_proxy;
	if ($fetion_proxy != null) {
		curl_setopt($ch, CURLOPT_PROXY, $fetion_proxy);
	}
	return $ch;
}

/**
 * run a curl query
 * 
 * @see fetion_curl_init
 */
function fetion_curl_exec($url, $ssic = null, $post = null) {
	$ch = fetion_curl_init($url, $ssic, $post);
	$succeed = curl_exec($ch);
	if (!$succeed) {
		error_log(curl_error($ch));
	}
	curl_close($ch);
	return $succeed;
}

/**
 * login
 * 
 * @mobileno mobile number
 * @pwd password
 */
function fetion_login($mobileno, $pwd) {
	$login_url = FETION_LOGIN_URL."?mobileno=$mobileno&pwd=$pwd";
	$ssic_regex = '/ssic\s+(.*)/s';
	$sid_regex = '/sip:(\d+)@(.+);/s';// sid@domain
	$cookie_file = date('YmdHis').'_cookie.txt';// create a tmp file to save cookie
	$return_val = false;

	$ch = fetion_curl_init($login_url, null, null);
	// do not verify host
	curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
	curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
	// save cookie for further process
	curl_setopt($ch, CURLOPT_COOKIEJAR, $cookie_file);
	$succeed = curl_exec($ch);
	// close first, in order to make cookie file written
	curl_close($ch);
	fetion_debug("login to nav.fetion.com.cn");

	if (!$succeed) {
		error_log(curl_error($ch));
		return false;
	}
	// get ssic from cookie
	$ssic = false;
	$matches = array();
	if (!preg_match($ssic_regex, file_get_contents($cookie_file), $matches)) {
		error_log("Fetion Error: No ssic found in cookie");
		return false;
	}
	$ssic = trim($matches[1]);
	fetion_debug("ssic: ".substr($ssic, 0, 10)."...");
	// get other login info from output
	$result_xml = simplexml_load_string($succeed);
	$return_val = array(
		'ssic' => $ssic,
		'status-code' => strval($result_xml['status-code']),
		'uri' => strval($result_xml->user['uri']),
		'mobile-no' => strval($result_xml->user['mobile-no']),
		'user-status' => strval($result_xml->user['user-status'])
	);
	// extract sid and domain for further use
	if (preg_match($sid_regex, $return_val['uri'], $matches)) {
		$return_val['sid'] = $matches[1];
		$return_val['domain'] = $matches[2];
	}
	fetion_debug("sid: {$return_val['sid']}");
	unlink($cookie_file);
	return $return_val;
}

/**
 * get fetion system config, not used
 */
function fetion_get_system_config() {
	$post_fields = '<config><client type="PC" version="3.2.0540" platform="W5.1" /><client-config version="0" /></config>';
	return fetion_curl_exec(FETION_CONFIG_URL, null, $post_fields);
}

/**
 * hex to binary
 *
 * @hex string hex code
 */
function fetion_hex2bin($hex) {
	$bin = '';
	$len = strlen($hex);
	for ($I = 0; $I < $len; $I += 2) {
		$bin .= chr(hexdec(substr($hex, $I, 2)));
	}
	return $bin;
}

/**
 * get hash password
 * 
 * @password real password
 */
function fetion_hash_password($password) {
	// in fact, salt is constant value
	$salt = chr(0x77).chr(0x7A).chr(0x6D).chr(0x03);
	$src = $salt.hash('sha1', $password, true);
	return strtoupper(bin2hex($salt.sha1($src, true)));
}

/**
 * create a random cnonce
 */
function fetion_calc_cnonce() {
	return sprintf("%04X%04X%04X%04X%04X%04X%04X%04X",
		rand() & 0xFFFF, rand() & 0xFFFF, rand() & 0xFFFF,
		rand() & 0xFFFF, rand() & 0xFFFF, rand() & 0xFFFF,
		rand() & 0xFFFF, rand() & 0xFFFF);
}

/**
 * get salt from real password
 * 
 * @password real password
 */
function fetion_calc_salt($password) {
	return substr(fetion_hash_password($password), 0, 8);
}

/**
 * calculate response
 * 
 * @sid fetion id
 * @domain domain
 * @password real password
 * @nonce nonce from server
 * @cnonce cnonce
 */
function fetion_calc_response($sid, $domain, $password, $nonce, $cnonce) {
	$password = fetion_hash_password($password);
	$str = fetion_hex2bin(substr($password, 8));
	$key = sha1("$sid:$domain:$str", true);
	$h1 = strtoupper(md5("$key:$nonce:$cnonce"));
	$h2 = strtoupper(md5("REGISTER:$sid"));
	$res = strtoupper(md5("$h1:$nonce:$h2"));
	return $res;
}

/**
 * get url with next request number
 * 
 * @t i don't known
 */
function fetion_next_url($t = 's') {
	static $seq = 0;
	++$seq;
	return FETION_URL."?t=$t&i=$seq";
}

/**
 * get next call id
 */
function fetion_next_call() {
	static $call = 0;
	++$call;
	return $call;
}

/**
 * register to server
 * 
 * @ssic user identification
 * @sid fetion id
 * @domain domain
 * @password real password
 */
function fetion_http_register($ssic, $sid, $domain, $password) {
	$nonce_regex = '/nonce="(\w+)"/s';
	$ok_regex = '/OK/s';
	$arg = '<args><device type="PC" version="44" client-version="3.2.0540" />';
	$arg .= '<caps value="simple-im;im-session;temp-group;personal-group" />';
	$arg .= '<events value="contact;permission;system-message;personal-group" />';
	$arg .= '<user-info attributes="all" /><presence><basic value="400" desc="" /></presence></args>';

	fetion_debug("begin register");
	$call = fetion_next_call();
	fetion_curl_exec(fetion_next_url(), $ssic, FETION_SIPP);
	$msg = fetion_sip_create('R fetion.com.cn SIP-C/2.0', array('F'=>$sid, 'I'=>$call, 'Q'=>'1 R'), $arg).FETION_SIPP;
	fetion_curl_exec(fetion_next_url('i'), $ssic, $msg);
	$msg = fetion_curl_exec(fetion_next_url(), $ssic, FETION_SIPP);
	fetion_debug("recv nonce...");
	$matches = array();
	if (!preg_match($nonce_regex, $msg, $matches)) {
		error_log('Fetion Error: no nonce found');
		return false;
	}
	$nonce = $matches[1];
	$salt = fetion_calc_salt($password);
	$cnonce = fetion_calc_cnonce();
	$response = fetion_calc_response($sid, $domain, $password, $nonce, $cnonce);
	fetion_debug("nonce: $nonce");
	fetion_debug("salt: $salt");
	fetion_debug("cnonce: $cnonce");
	fetion_debug("response: $response");
	$msg = fetion_sip_create('R fetion.com.cn SIP-C/2.0', array('F'=>$sid, 'I'=>$call, 'Q'=>'2 R', 'A'=>"Digest algorithm=\"SHA1-sess\",response=\"$response\",cnonce=\"$cnonce\",salt=\"$salt\""), $arg).FETION_SIPP;
	fetion_debug("send response...");
	fetion_curl_exec(fetion_next_url(), $ssic, $msg);
	$msg = fetion_curl_exec(fetion_next_url(), $ssic, FETION_SIPP);
	return preg_match($ok_regex, $msg);
}

/**
 * send sms use http
 * 
 * @ssic user identification
 * @sid fetion id
 * @to receiver mobile number or sid
 * @content sms content
 */
function fetion_http_send_sms($ssic, $sid, $to, $content) {
	$ok_regex = '/Send SMS OK/s';
	$msg = fetion_sip_create('M fetion.com.cn SIP-C/2.0', array('F'=>$sid, 'I'=>fetion_next_call(), 'Q'=>'1 M', 'T'=>$to, 'N'=>'SendSMS'), $content).FETION_SIPP;
	fetion_debug("send sms...");
	fetion_curl_exec(fetion_next_url(), $ssic, $msg);
	$msg = fetion_curl_exec(fetion_next_url(), $ssic, FETION_SIPP);
	return preg_match($ok_regex, $msg);
}

/**
 * get buddy list
 * 
 * @ssic user identification
 * @sid fetion id
 */
function fetion_get_buddy_list($ssic, $sid) {
	$buddy_regex = '/.*?\r\n\r\n(.*)'.FETION_SIPP.'\s*$/is';
	$arg = '<args><contacts><buddy-lists /><buddies attributes="all" /><mobile-buddies attributes="all" /><chat-friends /><blacklist /></contacts></args>';
	$msg = fetion_sip_create('S fetion.com.cn SIP-C/2.0', array('F'=>$sid, 'I'=>fetion_next_call(), 'Q'=>'1 S', 'N'=>'GetContactList'), $arg).FETION_SIPP;
	fetion_curl_exec(fetion_next_url(), $ssic, $msg);
	$msg = fetion_curl_exec(fetion_next_url(), $ssic, FETION_SIPP);
	$matches = array();
	if (!preg_match($buddy_regex, $msg, $matches)) {
		error_log("Fetion Error: No buddy list found");
		return false;
	}
	$buddy_list = simplexml_load_string($matches[1]);
	$buddies = array();
	foreach ($buddy_list->contacts->buddies->buddy as $buddy) {
		$buddies[strval($buddy['uri'])] = strval($buddy['local-name']);
	}
	foreach ($buddy_list->contacts->{'mobile-buddies'}->{'mobile-buddy'} as $buddy) {
		$buddies[strval($buddy['uri'])] = strval($buddy['local-name']);
	}
	return $buddies;
}

/**
 * usage
 */
function usage() {
	echo "Usage: fetion [options] user_mobile password\r\n";
	echo "       fetion [options] user_mobile password sendto_sid content\r\n";
	echo "\r\n";
	echo "  if no sendto_sid specified, all available sid will be displayed\r\n";
	echo "  -p <proxy[:port]>   Proxy\r\n";
	echo "  -d                  Debug output\r\n";
}

/**
 * main
 * 
 * @args command line args
 */
function main($argc, $argv) {
	global $fetion_proxy;
	global $fetion_debug;
	$user_mobile = null;
	$password = null;
	$sendto_sid = null;
	$content = null;

	if ($argc < 2) {
		usage();
		return 1;
	}
	for ($I = 1; $I < $argc; ++$I) {
		if ($argv[$I] == '-p') {
			$fetion_proxy = $argv[++$I];
		} else if ($argv[$I] == '-d') {
			$fetion_debug = true;
		} else {
			$user_mobile = $argv[$I++];
			$password = $argv[$I++];
			if (isset($argv[$I])) {
				$sendto_sid = $argv[$I++];
				$content = $argv[$I];
			}
			break;
		}
	}

	$login_info = fetion_login($user_mobile, $password);
	if ($login_info === false) {
		print "[*] login failed\r\n";
		return 1;
	}
	$ssic = $login_info['ssic'];
	$sid = $login_info['sid'];
	$domain = $login_info['domain'];
	print "[*] login successful\r\n";
	$ok = fetion_http_register($ssic, $sid, $domain, $password);
	if ($ok === false) {
		print "[*] register failed\r\n";
		return 1;
	}
	print "[*] register successful\r\n";

	if (empty($sendto_sid) || empty($content)) {
		$buddies = fetion_get_buddy_list($ssic, $sid);
		if ($buddies === false) {
			print "[*] get buddy list failed\r\n";
		} else {
			print "                                [sid]    [name]\r\n";
			foreach ($buddies as $sid=>$name) {
				printf("  %35s => %s\r\n", $sid, $name);
			}
		}
	} else {
		$ok = fetion_http_send_sms($ssic, $sid, $sendto_sid, $content);
		print "[*] send sms ".strval($ok ? 'successful' : 'failed')."\r\n";
	}
}

main($argc, $argv);
?>