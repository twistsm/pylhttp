# -*- coding:utf-8 -*-
__author__="Anton Gorunov"
"""
Python Light HTTP client.

Main features:
1. Simplicity! PylHttp().request('http://www.google.com/')
2. GET and POST requests
3. Redirect handler
4. GZIP
5. Cookie
6. Custom headers
7. Proxy or custom IP interface
8. Browsing history and Referer if needed
9. Smart timeout
10. Response info
"""

import urllib
import urllib2
import httplib
import cookielib
import socket
import StringIO
import time
import gzip
import random
import pprint

pp = pprint.PrettyPrinter(indent=4).pprint


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
    """Handler allows to bind on specified IP address"""
    def __init__(self, ip):
        urllib2.HTTPHandler.__init__(self)
        if not ip:
            self.customip = socket.gethostbyname_ex(socket.gethostname())[2][0]
        else:
            self.customip = ip
    
    def http_open(self, req):
        return self.do_open(BindableHTTPConnectionFactory(self.customip), req)


class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    """This class handles redirects and memorize status code"""
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



class PylHttpResponse(object):
    """
    Standard http response fields:
        - url
        - status
        - realurl
        - rucode
        - duration
        - content
        - size
        - type
        - charset
        - error_message
    """
    def __init__(self, url, request_time, redirect_handler, response=None, error=None):

        self.url = url
        self.response = response
        self.error = error
        self.duration = time.time() - request_time
        if self.response and not self.error:
            self.processCorrectResponse()
        else:
            self.processErrorResponse()

        self.dict = self.__dict__
        

    def processErrorResponse(self):
        reason = self.error.__dict__.get('reason', '')
        if reason:
            """This is a URL Error -> timeout or no such domain, etc"""
            self.headers = {}
            self.content = ''
            self.status = ''
            self.size = 0
            self.type = ''
            self.realurl = ''
            self.rucode = ''
            self.charset = ''
            if 'timeout' in reason:
                self.error_message = 'timeout'
            else:
                self.error_message = str(reason)
                
        else:
            self.headers = self.error.headers.dict
            """ Error response processing """
            
            #print 'Error code: ', e.code
            """ Handling gzip response
                And retriewing page content """
            try:
                if self.error.headers.dict['content-encoding'] == 'gzip':
                    compressedstream = StringIO.StringIO(self.error.read())
                    gzipper = gzip.GzipFile(fileobj=compressedstream)
                    self.content = gzipper.read()
            except KeyError:
                self.content = self.error.read()

            """ Identify status codes of redirects and errors """
            if self.url != self.error.url and redirect_handler.statusCode:
                self.status = redirect_handler.statusCode
            else:
                self.status = self.error.code
            self.size = len(self.content)
            try:
                self.type = self.error.dict['headers']['content-type'].split(';')[0]
            except:
                self.type = ''
            self.realurl = self.error.url
            self.rucode = self.error.code
            self.charset = ''
            self.error_message = str(self.error.code)

    
    def processCorrectResponse(self):

        self.headers = self.response.headers.dict
        self.error_message = ''
        
        """ Handling gzip response
            And retriewing page content """
        try:
            if self.response.headers.dict['content-encoding'] == 'gzip':
                compressedstream = StringIO.StringIO(self.response.read())
                gzipper = gzip.GzipFile(fileobj=compressedstream)
                self.content = gzipper.read()
        except KeyError:
            self.content = self.response.read()
        

        """ Let's get HTTP response status code """
        try:
            self.status = self.response.status
        except:
            self.status = 200

        """ Calculate content size """
        try:
            self.size = len(self.content)
        except TypeError:
            self.size = 0

        """ Get content type """
        try:
            self.type = self.response.headers.dict['content-type'].split(';')[0].lower()
        except:
            self.type = ''

        """ Get page charset """
        try:
            self.charset = self.response.headers.dict['content-type'].split('charset=')[1].lower()
        except:
            self.charset = ''

        self.realurl = self.response.url
        self.rucode  = self.response.code



class PylHttp(object):
    """ Simple light-weight HTTP client """
    def __init__(self, proxy=None, ip_address=None, user_agent=None, timeout=20, tries=1):
        """Init HTTP client"""
        if not user_agent:
            user_agent = self.get_user_agent()

        self.history = []
        self.tries = tries
        self.timeout = timeout        
        self.user_agent = user_agent
        self.cookiejar = cookielib.CookieJar()
        self.smartRedirectHandler = SmartRedirectHandler()
        self.proxy = self.makeproxy(proxy)
        self.proxyHandler = urllib2.ProxyHandler(proxy)

        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar),
            self.smartRedirectHandler,
            BindableHTTPHandler(ip_address),
            urllib2.HTTPSHandler(),
            self.proxyHandler
        )

    
    def get_user_agent(self):
        user_agents = (
            'Mozilla/5.0 (Windows; U; Windows NT 6.1; ru; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10',
            'Mozilla/5.0 (Windows; U; Windows NT 6.1; ru; rv:1.9.2.10) Gecko/20100914 Firefox/3.7.10',
        )
        return random.choice(user_agents)

    
    def makeproxy(self, proxystring, proxytype='http'):
        """
        Splits default proxy as 255.255.255.255:3128 into urllib format
        """
        try:
            ip, port = proxystring.split(':')
        except AttributeError:
            ip, port = None, None
        
        if ip and port:
            proxy = {proxytype: 'http://{ip}:{port}/'.format(ip=ip, port=port)}
        else:
            proxy = None
        return proxy

    
    def request(self, url, params=None, timeout=None, proxy=None, referer=None, headers=None):
        """ Main request function
            Returns html or empty content """
        if not headers:
            headers = []
        if timeout:
            current_timeout = timeout
        else:
            current_timeout = self.timeout

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
        request.add_header('User-Agent', self.user_agent)
        request.add_header('Accept-encoding', 'gzip')
        for h in headers:
            request.add_header(h[0], h[1])
        
        if referer == 'auto' and self.history:
            request.add_header('Referer', self.history[-1]['response'].realurl)
        elif referer:
            request.add_header('Referer', referer)
            
        request_time = time.time()
       
        try:
            """ Trying to open URL """
            response = self.opener.open(request, timeout=current_timeout)
            self.response = PylHttpResponse(url=url, request_time=request_time, 
                            redirect_handler=self.smartRedirectHandler, response=response)
        except urllib2.URLError as e:
            self.response = PylHttpResponse(url=url, request_time=request_time, 
                            redirect_handler=self.smartRedirectHandler, error=e)
        # Memorize browsing data
        self.history.append({'request': request, 'response': self.response})
        return self.response


if __name__ == "__main__":
    '''
    import gevent 
    import gevent.monkey
    gevent.monkey.patch_socket()
    
    bot = PylHttp()
    threads = [
        gevent.spawn(bot.request, 'http://www.google.com.ua/'),
        gevent.spawn(bot.request, 'http://www.google.com/'),
        gevent.spawn(bot.request, 'http://google.com.ua/'),
    ]
    gevent.joinall(threads)
    print bot.history
    '''

