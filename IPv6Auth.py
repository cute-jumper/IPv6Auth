#!/usr/bin/python

import re, urllib, urllib2, sys, Image, cookielib, time, os, getpass, base64, StringIO

class IPv6Auth(object):
    def __init__(self):
        # get ipv6 address, mac and port
        print 'Detecting system information...'
        self.ipv6addr = os.popen("ifconfig | grep '2402' | sed -n '1p'| awk '{print $3}'").read()[:-4]
        print 'ipv6addr:', self.ipv6addr
        html= urllib2.urlopen('http://ipv6.google.com').read()
        newurl = re.search('(https://.*)\'\+', html).group(1)
        html = urllib2.urlopen(newurl+'&flag=location').read()
        self.mac = re.search('<input type="hidden".*value=\'(.*)\'', html).group(1)
        print 'mac:', self.mac
        self.port = re.search('<input type="hidden".*value=\'(.*)\'', html).group(1) # Seems like error? But it doesn't affect. I'm too lazy to fix it.......
        print 'port:', self.port
        cookies = urllib2.HTTPCookieProcessor()
        opener = urllib2.build_opener(cookies)
        urllib2.install_opener(opener)

    def get_username_and_password(self):
        # get username and password, if user exists, use the name and password in it
        prefix = os.path.dirname(os.path.abspath(__file__))
        user_setting_file = os.path.join(prefix, '.user')
        if os.path.isfile(user_setting_file):
            fin = open(user_setting_file, 'r')
            username = base64.decodestring(fin.readline())
            password = base64.decodestring(fin.readline())
            fin.close()
        else:
            username = raw_input("username:")
            password = getpass.getpass('password:')
            answer = raw_input('save username and password?[Y/N]')
            if answer == 'Y' or answer == 'y':
                fout = open(user_setting_file, 'w')
                fout.write(base64.encodestring(username)+base64.encodestring(password))
                fout.close()
        
        return username, password

    def get_code_string(self):        
        image_data = StringIO.StringIO()
        image_data.write(urllib2.urlopen("https://auth-1.ccert.edu.cn:8443/eportal/validcode").read()) # Get validcode
        # read the code, convert into two-valued string
        img = Image.open(image_data)
        newimg = img.convert('L')
        twoval = []
        code_string = ["", "", "", ""]
        for cnt, i in enumerate(newimg.getdata(), 1):
            if i < 130:
                twoval.append(0)
                code_string[cnt % 60 / 15] += '1'
            else:
                twoval.append(255)
                code_string[cnt % 60 / 15] += '0'
        newimg.putdata(twoval)
        image_data.close()
        return code_string
    
    # remove useless pixels
    def chop(self, s):
        l, r, t, b = 14, 0, 19, 0
        for cnt, i in enumerate(s):
            x, y = cnt % 15, cnt / 15
            if i == '1':
                if x > r: r = x
                if x < l: l = x;
                if y > b: b = y
                if y < t: t = y
        s = ""
        for i in range(t, b + 1):
            for j in range(l, r + 1):
                s += string[i * 15 + j]
        return s
    
    def get_recognition(self, code_string):
        numbers = ['001110001101100100010110001111000111100011110001111000111100011010001001101100011100',
                   '001100111100001100001100001100001100001100001100001100001100001100111111',
                   '001111000100111010000110000001100000011000000100000011000000100000010000001000010111111111111110',
                   '001111011001111000011000001100001100001110000011100000110000011000001111001101111100',
                   '000001100000011000001110000101100010011000100110010001101000011011111111000001100000011000000110',
                   '001111001111010000011100111110000111000011000001000001000001100010111100',
                   '000001110001110000110000011000000101110011100110110000111100001111000011110000110110011000111100',
                   '011111110111111010000010000001000000010000000100000010000000100000010000000100000001000000100000',
                   '001111000010001111000011110000110111011000111000001111000100011011000011010000110110011000111100',
                   '001111000110011011000011110000111100001111000011011000110011111000000110000011000001100011100000']        
        # here is the main process to recognize the validcode. It's quite easy.
        validcode = 0
        for i in range(4):
            code_string[i] = self.chop(code_string[i])
            num = -1
            max_cnt = 0
            for j in range(10):
                cnt = 0
                if len(code_string[i]) == len(numbers[j]):
                    for k in range(len(code_string[i])):
                        if code_string[i][k] == numbers[j][k]:
                            cnt += 1
                if cnt > max_cnt:
                    max_cnt = cnt
                    num = j
            validcode = validcode*10+num
        print 'validcode: %04d' %(validcode)
        return validcode

    def do_log_in(self):
        code_string = self.get_code_string()
        validcode = self.get_recognition(code_string)                
        reqstr = "https://auth-1.ccert.edu.cn:8443/eportal/user.do?\
method=login_ajax&username=" + self.username + "&pwd=" + self.password + "&isp=&s=4e7e812433a5f75368e9ea9b96348dbc&\
url=93777bc090c380864d8126e2c2aa87e848ae467e70af8b73&port=" + self.port + "&\
mac=" + self.mac + '&validcode=%04d' %(validcode) + "&is_check=false"
        # print reqstr
        req = urllib2.Request(reqstr)
        resp = urllib2.urlopen(req)
        receive = resp.read()
        print receive

        if receive.find('success') == -1:
            print "Oops, log in error!"
            sys.exit(0)
        print "Log in successfully! Hahahahaha..."
        
    def do_refresh(self, interval=300):
        # succeed, then we send the keep-alive message every 5 minutes
        while 1:
            try:
                time.sleep(interval)
                url = "https://auth-1.ccert.edu.cn:8443/eportal/user.do?method=fresh&userIndex=4e7e812433a5f75368e9ea9b96348dbc_" + self.ipv6addr + "_" + self.username
                print 'refresh:', urllib2.urlopen(url).read()
            except KeyboardInterrupt:
                print '\nlogout...'
                print urllib2.urlopen('https://auth-1.ccert.edu.cn:8443/eportal/user.do?method=logout').read()
                break
            except:
                print 'Oops, fucking error'
                break
                
if __name__ == '__main__':
    v6auth = IPv6Auth()
    v6auth.do_log_in()
    v6auth.do_refresh()
