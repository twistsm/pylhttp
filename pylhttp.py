# -*- coding:utf-8 -*-
__author__="Anton Gorunov"
"""
Python Light HTTP client.

Main features and advantages:
1. Simplicity! All hard thing done by me :-)
2. GET and POST requests support
3. Redirect handler and memorizer
4. GZIP support implemented -> faster way to get your webpages
5. Cookie processing in current session
6. Custom headers
7. Proxy or custom IP interface
8. Browsing history and Referer if needed (download a lot of pages without extra code)
9. Usable Response information
10. Can be asynchonous easy with gevent monkey patch. Or you can use it with threads.

All examples you can find at the end of this file in __main__ section
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



class Client(object):
    """ Simple light-weight HTTP client """

    @staticmethod
    def beforeCallback(this):
        pass

    @staticmethod
    def afterCallback(this):
        pass

    def __init__(self, proxy=None, ip_address=None, user_agent=None, timeout=20, savehistory=False):
        """Init HTTP client"""
        if not user_agent:
            user_agent = self.get_user_agent()

        self.current_url = ''
        self.savehistory = savehistory
        self.history = []
        self.timeout = timeout
        self.user_agent = user_agent
        self.cookiejar = cookielib.CookieJar()
        self.smartRedirectHandler = SmartRedirectHandler()
        self.proxy = self.makeproxy(proxy)
        self.proxyHandler = urllib2.ProxyHandler(self.proxy)
        self.bindableHttpHandler = BindableHTTPHandler(ip_address)
        self.httpsHandler = urllib2.HTTPSHandler()
        self.cookiesHandler = urllib2.HTTPCookieProcessor(self.cookiejar)

        self.opener = urllib2.build_opener(
            self.cookiesHandler,
            self.smartRedirectHandler,
            self.bindableHttpHandler,
            self.httpsHandler,
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
        self.current_url = url
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

        if proxy:
            self.proxyHandler = urllib2.ProxyHandler(self.makeproxy(proxy))

            self.opener = urllib2.build_opener(
                self.cookiesHandler,
                self.smartRedirectHandler,
                self.bindableHttpHandler,
                self.httpsHandler,
                self.proxyHandler
            )

        request_time = time.time()

        self.beforeCallback(self)
        try:
            """ Trying to open URL """
            response = self.opener.open(request, timeout=current_timeout)
            self.response = PylHttpResponse(url=url, request_time=request_time,
                            redirect_handler=self.smartRedirectHandler, response=response)
        except urllib2.URLError as e:
            self.response = PylHttpResponse(url=url, request_time=request_time,
                            redirect_handler=self.smartRedirectHandler, error=e)

        # Memorize browsing data
        if self.savehistory:
            self.history.append({'request': request, 'response': self.response})
        self.afterCallback(self)

        self.current_url = ''
        return self.response


if __name__ == "__main__":
    bot = Client()
    html = bot.request(url='http://my-ip-address.com/', proxy='62.243.224.180:1080').content
    print html

    """
    # FOA sorry for my English - I'm not native speaker!

    # All hard thing done by me :-) Now your bots may be happy.

    html = Client().request('http://www.google.com.ua/').content
    print html

    # Or you can do something like that:
    bot = Client(savehistory=True)
    response = bot.request('http://google.com')
    print response.url
    print response.status
    print response.realurl
    print response.rucode
    # You see - we following redirects and save all information about source and dest URL

    # Let's make some requests on random sites
    bot.request('http://atape.net/')
    bot.request('http://github.com/')
    bot.request('http://yahoo.com/')

    # When you travelling the web with Client object, you have cookies and browsing history if last enabled
    print bot.cookiejar

    # Note that history is simple list, that contains Request and Response objects for each webpage visited.
    print bot.history

    # If you want to get headers of last visited page do the following:
    print bot.history[-1]['response'].headers
    # Or if you want to remember first requested(visited) url:
    print bot.history[0]['response'].url

    # Request object is standard urllib2.Request - I don't know why you need it :-)
    print isinstance(bot.history[0]['request'], urllib2.Request)


    # You can initiate any number of separate clients. It can be useful, for example for bots under proxies
    #bot1 = Client(user_agent='BOT1', timeout=10, proxy='100.255.255.1:3128', savehistory=True)
    #bot2 = Client(user_agent='BOT2', timeout=30, proxy='200.255.255.2:3128', savehistory=True)
    #bot3 = Client(user_agent='BOT3', timeout=60, proxy='300.255.255.3:3128', savehistory=True)
    # Now you can browse the web via 3 different clients.

    # You can get all properties of response object by this call:
    # Client().request method returns PylHttpResponse object
    response_object = Client().request('http://www.google.com.ua/')
    print response_object.dict.keys()
    ''' Here short description
    [
        'url',               - requested url
        'status',            - status code of your url -> 200/404/301/302, anything else
        'realurl',           - redirected url
        'rucode',            - realurl status code -> 200/404/301/302, anything else
        'charset',           - charset from headers
        'error_message',     - your custom error message. 'timeout' for example
        'content',           - html content decoded to unicode
        'headers',           - dictionary of response headers
        'duration',          - page load duration
        'type',              - content type of the page from headers
        'response',          - response object from urllib2
        'error',             - error object from urllib2 (URLError instance)
        'size'               - content size calculated in symbols
        'dict',              - all this properties in dictionary-like style
    ]
    '''

    # POST requests easy as piece of cake ->
    url = 'http://www.google.com/'
    post = {
        'var1': 'value1',
        'var2': 'value2'
    }
    bot.request(url, params=post)

    # You can add any custom headers to your request
    headers = [('header1', 'value'), ('header2', 'value')]
    bot.request(url, params=post, headers=headers)


    # If you have not proxies, but your server have custom IP interfaces
    # you can specify just IP address
    # bot = Client(ip_address='111.255.255.255')

    # Some times it is important to provide referer information in headers
    # you can specify this referer manually or use 'auto' keyword - it will be last visited url
    bot.request(url, referer='auto')


    # and.... this awesome thing can be asynchonous with gevent monkey patch.

    import gevent
    import gevent.monkey
    gevent.monkey.patch_socket()

    print "start gevent threads"
    multibot = Client(savehistory=True)
    threads = [
        gevent.spawn(multibot.request, 'http://www.google.com.ua/'),
        gevent.spawn(multibot.request, 'http://test.com/'),
        gevent.spawn(multibot.request, 'http://facebook.com/'),
        gevent.spawn(multibot.request, 'http://google.com/'),
        gevent.spawn(multibot.request, 'http://google.ru/'),
        gevent.spawn(multibot.request, 'http://yahoo.com/'),
        gevent.spawn(multibot.request, 'http://bing.com/'),
        gevent.spawn(multibot.request, 'http://i.ua/'),
    ]
    gevent.joinall(threads)
    for d in multibot.history:
        response = d['response']
        print "%s : %s --> %s : %s === %s %s" % (response.status, response.url, response.rucode,
                            response.realurl,  response.content[:15]+"...", response.duration)

    # If you want to have some additional pre/post processing behaviour, you can add custom callbacks:
    def before(this):
        # here you have access to whole HTTP Client (this) object before request
        print 'Now i will make request'
        print this.current_url
        print this.user_agent


    def after(this):
        # here you have access to whole HTTP Client (this) object after request
        print 'Request completed: response status codes:'
        print this.response.status
        print this.response.rucode

    bot  = Client()
    # Note, that callbacks are staticmethods.
    bot.beforeCallback = before
    bot.afterCallback = after
    bot.request('http://google.com')
    """
