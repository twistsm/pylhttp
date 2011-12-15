# -*- coding:utf-8 -*-
__author__="twistsm"

import urllib
import urllib2
import httplib
import cookielib
import socket
import StringIO
import time
import gzip
import sys

def urldecode(query):
   d = {}
   a = query.split('&')
   for s in a:
      if s.find('='):
         k,v = map(urllib.unquote, s.split('='))
         try:
            d[k].append(v)
         except KeyError:
            d[k] = [v]
   return d

class BindableHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        """Connect to the host and port specified in __init__."""
        self.sock = socket.socket()
        if not self.source_ip.startswith('127.0'):
            self.sock.bind((self.source_ip, 0))
        if isinstance(self.timeout, float):
                self.sock.settimeout(self.timeout)
        self.sock.connect((self.host,self.port))

def BindableHTTPConnectionFactory(source_ip):
    def _get(host, port=None, strict=None, timeout=0):
        bhc=BindableHTTPConnection(host, port=port, strict=strict, timeout=timeout)
        bhc.source_ip=source_ip
        return bhc
    return _get

class BindableHTTPHandler(urllib2.HTTPHandler):
    def __init__(self, ip):
        urllib2.HTTPHandler.__init__(self)
        if not ip:
            self.customip = socket.gethostbyname_ex(socket.gethostname())[2][0]
        else:
            self.customip = ip
        print 'Client IP: '+self.customip+' >>>'
    def http_open(self, req):
        return self.do_open(BindableHTTPConnectionFactory(self.customip), req)

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def __init__(self):
        self.statusCode = ''

    def http_error_301(self, req, fp, code, msg, headers):
        self.statusCode = code
        result = urllib2.HTTPRedirectHandler.http_error_301(
            self, req, fp, code, msg, headers
        )
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        self.statusCode = code
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers
        )
        result.status = code
        return result

    def http_error_303(self, req, fp, code, msg, headers):
        self.statusCode = code
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers
        )
        result.status = code
        return result

    def http_error_307(self, req, fp, code, msg, headers):
        self.statusCode = code
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers
        )
        result.status = code
        return result

class PylHttp:
    """ Simple light-weight HTTP client """
    def __init__(self, proxy=None,
                user_agent='Mozilla/5.0 (Windows; U; Windows NT 6.1; ru; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10',
                ip_address=None):

        self.cj  = cookielib.CookieJar()
        self.smartRedirectHandler = SmartRedirectHandler()
        """ Init handlers """
        if proxy:
            self.opener = urllib2.build_opener(
                urllib2.HTTPCookieProcessor(self.cj),
                self.smartRedirectHandler,
                urllib2.HTTPHandler(),
                urllib2.HTTPSHandler(),
                urllib2.ProxyHandler(proxy)
            )
        else:
            self.opener = urllib2.build_opener(
                urllib2.HTTPCookieProcessor(self.cj),
                self.smartRedirectHandler,
                BindableHTTPHandler(ip_address),
                urllib2.HTTPSHandler(),
                urllib2.ProxyHandler()
            )
        """ Init class params """
        self._userAgent   = user_agent

    def request(self, url, params={}, timeout=10):
        """ Main request function
            Returns html or empty content """

        # Set default socket timeout
        socket.setdefaulttimeout(timeout)

        # Checking for GET or POST request
        if params:
            """ POST REQUEST """
            params  = urllib.urlencode(params)
            request = urllib2.Request(url, params)
        else:
            """ GET REQUEST """
            request = urllib2.Request(url)

        """ Add user agent and notify server
            that we can handle gzip response """
        request.add_header('User-Agent', self._userAgent)
        request.add_header('Accept-encoding', 'gzip')

        try:
            """ Trying to open URL """
            # 1. Define page load time
            startTime = time.time()
            response  = self.opener.open(request)
            duration  = time.time() - startTime

            # Getting response headers dictionary
            self.headers = response.headers.__dict__

            """ Handling gzip response
                And retriewing page content """
            try:
                if self.headers['dict']['content-encoding'] == 'gzip':
                    compressedstream = StringIO.StringIO(response.read())
                    gzipper          = gzip.GzipFile(fileobj=compressedstream)
                    content     = gzipper.read()
            except KeyError:
                content = response.read()

            """ Let's get HTTP response status code """
            try:
                status = response.status
            except:
                status = 200

            """ Calculate content size """
            try:
                size = len(content)
            except TypeError:
                size = 0

            """ Get content type """
            try:
                type = self.headers['type']
            except:
                type = ''

            """ Get page charset """
            try:
                charset = self.headers['plist'][0].lower().replace('charset=','')
            except:
                charset = ''

            realurl = response.url
            rucode  = response.code
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                """ Timeout processing """
                print 'Fail reason: ', e.reason
                duration = time.time() - startTime
                content  = ''
                status   = self.smartRedirectHandler.statusCode
                size     = 0
                type     = ''
                realurl  = ''
                rucode   = ''
                charset  = ''

                """ When you get timeout you may
                    try again to fetch url with longer timeout max - 21 sec"""
                if timeout < 120:
                    if params:
                        responseDict = self.request(url, urldecode(params), timeout+5)
                    else:
                        responseDict = self.request(url, '', timeout+20)
                else:
                    print 'Timeout > 120 sec. Stopping script!'
                    sys.exit()
                return responseDict
            elif hasattr(e, 'code'):
                """ Error response processing """
                print 'Error code: ', e.code
                duration = time.time() - startTime
                content  = e.read()

                """ Identify status codes of redirects and errors """
                if url != e.url and self.smartRedirectHandler.statusCode:
                    status   = self.smartRedirectHandler.statusCode
                else:
                    status   = e.code
                size     = len(content)
                try:
                    type = e.__dict__['headers'].__dict__['type']
                except:
                    type = ''
                realurl  = e.url
                rucode   = e.code
                charset  = ''

        """ Resume: """
        responseDict = {
            'url'      : url,
            'duration' : duration,
            'content'  : content,
            'status'   : status,
            'size'     : size,
            'type'     : type,
            'realurl'  : realurl,
            'code'     : rucode,
            'charset'  : charset
        }

        return responseDict

if __name__ == "__main__":
   bot = PylHttp()
   result = bot.request('http://www.google.com/')
   print (result['code'])
