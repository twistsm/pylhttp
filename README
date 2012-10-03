This is light one-file python http client.
    
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

