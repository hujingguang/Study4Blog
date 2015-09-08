#!/usr/bin/env python
import cgi
import datetime
import time
import re
import urllib
import threading
import functools
try:
    from CStringIO import StringIO
except:
    from StringIO import StringIO



class Dict(dict):
    def __init__(self,**kw):
        super(Dict,self).__init__(**kw)
    def __getattr__(self,name):
        if not name in self:
            raise "keyerror %s " %name
        return self[name]
    def __setattr__(self,name,value):
        self[name]=value

ctx=threading.local()

_RE_TZ_=re.compile(r'^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')

class UTC(datetime.tzinfo):
    def __init__(self,tz):
        res=_RE_TZ_.match(tz)
        if res:
            r1=res.group(1)
            h=int(res.group(2))
            m=int(res.group(3))
            if r1=='-':
                h,m=(-h),(-m)
            self._utcoffset=datetime.timedelta(hours=h,minutes=m)
            self._tzname="UTC"+tz
        else:
            raise 'UTC format error !'

    def dst(self,dt):
        return datetime.timedelta(0)
    
    def utcoffset(self,dt):
        return self._utcoffset

    def tzname(self,dt):
        return self._tzname


_RESPONE_STATUSES={100:'Continue',101:'Switching Protocols',102:'Processing',200:'OK',201:'Created',202:'Accepted',203:'Non-Authoritative Information',204:'No Content',205:'Reset Content',206:'Partial Content',207:'Multi Status',226:'IM Used',300:'Multiple Choices',301:'Moved Permanently',302:'Found',303:'See Other',304:'Not Modified',305:'Use Proxy',307:'Temporary Redirect',400:'Bad Request',401:'Unauthorized',402:'Payment Required',403:'Forbidden',404:'Not Found',405:'Method Not Allowed',406:'Not Acceptable',407:'Proxy Authentication Required',408:'Request Timeout',409:'Conflict',410:'Gone',411:'Length Required',412:'Precondition Failed',413:'Request Entity Too Large',414:'Request URI Too Long',415:'Unsupported Media Type',416:'Requested Range Not Satisfiable',417:'Expectation Failed',418:"I'm a teapot",422:'Unprocessable Entity',423:'Locked',424:'Failed Dependency',426:'Upgrade Required',500:'Internal Server Error',501:'Not Implemented',502:'Bad Gateway',503:'Service Unavailable',504:'Gateway Timeout',505:'HTTP Version Not Supported',507:'Insufficient Storage',510:'Not Extended'}

_RESPONE_HEADERS=('Accept-Ranges','Age','Allow','Cache-Control','Connection','Content-Encoding','Content-Language','Content-Length','Content-Location','Content-MD5','Content-Disposition','Content-Range','Content-Type','Date','ETag','Expires','Last-Modified','Link','Location','P3P','Pragma','Proxy-Authenticate','Refresh','Retry-After','Server','Set-Cookie','Strict-Transport-Security','Trailer','Transfer-Encoding','Vary','Via','Warning','WWW-Authenticate','X-Frame-Options','X-XSS-Protection','X-Content-Type-Options','X-Forwarded-Proto','X-Powered-By','X-UA-Compatible')

_HEADER_X_POWERED_BY=('X-Powered-By','transp/1.0')
def get_Reheaders():
    d={}
    for v in zip([i.upper() for i in _RESPONE_HEADERS],_RESPONE_HEADERS):
        d[v[0]]=v[1]
    return d
_RESPONE_HEADERS_DICT=get_Reheaders()



class HttpError(Exception):
    def __init__(self,code):
        super(HttpError,self).__init__()
        self.status="%d %s" %(code,_RESPONE_STATUSES[code])

    def header(self,name,value):
        if not hasattr(self,'_headers'):
            self._headers=[_HEADER_X_POWERED_BY]
        self._headers.append((name,value))

    @property
    def headers(self):
        if hasattr(self,'_headers'):
            return self._headers
        return []
    def __str__(self):
        return "HttpError %s " %self.status

class RedirectError(HttpError):
    def __init__(self,code,location):
        super(RedirectError,self).__init__(code)
        self.location=location
    def __str__(self):
        return "RedirecError %s %s" %(self.status,self.location)

def badrequest():
    return HttpError(404)
def unauthorized():
    return HttpError(401)
def forbidden():
    return HttpError(403)
def conflict():
    return HttpError(409)
def internalerror():
    return HttpError(500)
def redirect(location):
    return RedirectError(301,location)
def found(location):
    return RedirectError(302,location)
def seeother(location):
    return RedirectError(303,location)


def _to_str(s):
    if isinstance(s,str):
        return s
    if isinstance(s,unicode):
        return s.encode('utf-8')
    return str(s)

def _to_unicode(s,encoding='utf-8'):
    return s.decode(encoding)

def _quote(url):
    return urllib.quote(url.encode('utf-8'))

def _unquote(url):
    return urllib.unquote(url).decode('utf-8')

def get(path):
    def wrapper(func):
        func.__web_route__=path
        func.__web_method__='GET'
        return func
    return wrapper

def post(path):
    def wrapper(func):
        func.__web_route__=path
        func.__web_method__='POST'
        return func
    return wrapper

_RE_PATH=re.compile(r'(\:[a-zA-Z_]\w*)')

def _build_re(path):
    flag=False
    re_list=['^',]
    l=_RE_PATH.split(path)
    for k in l:
        word=''
        if not flag:
            for w in k:
                if w >='a' and w<='z':
                    word=word+w
                elif w>='A' and w<='Z':
                    word=word+w
                elif w>='0' and w<='9':
                    word=word+w
                else:
                    word=word+"\\"+w
            re_list.append(word)
        else:
            fn=k[1:]
            fn=r'(?P<%s>[^\/]+)' %fn
            re_list.append(fn)
        flag=not flag
    re_list.append('$')
    return ''.join(re_list)

class Route(object):
    def __init__(self,func):
        self.func=func
        self.path=func.__web_route__
        self.method=func.__web_method__
        self.is_static=_RE_PATH.search(self.path) is None
        if not self.is_static:
            self.route=_build_re(self.path)

    def match(self,url):
        m=self.route.match(url)
        if m:
            return m.groups()
        return None
    def __call__(self,*args):
        return self.func(*args)
    
def _generic_static_file(fpath):
    BLOCK_SIZE=8190
    with open(fpath,'rb') as f:
        block=f.read(BLOCK_SIZE)
        while block:
            yield block
            block=f.read(BLOCK_SIZE)

class StaticFileRoute(object):
    def __init__(self):
        self.method='GET'
        self.is_static=False
        self.route=re.compile('^/static/(.+)$')
    def match(self,url):
        res=url.startswith('/static')
        if res:
            return url[1:]
        return None
    def __call__(self,*args):
        fpath=os.path.join(ctx.application.document_root,args[0])
        if not os.path.isfile(fpath):
            raise nofound()
        fext=os.path.splitext(fpath)[1]
        ctx.response.content_type=mimetypes.type_map.get(fext.lower(),'application/octet-stream')
        return _generic_static_file(fpath)
def favicon_handler():
    return static_file_handler('/favicon.ico')

class MultiFile(object):
    def __init__(self,storage):
        self.filename=storage.filename
        self.file=sotrage.file

class Request(object):
    def __init__(self,environ):
        self.environ=environ
    def _parse_input(self):
        inputs={}
        def convert(item):
            li=[]
            if isinstance(item,list):
                return [_to_unicode(k.value) for k in item]
            if item.filename:
                return MultipartFile(item)
            return _to_unicode(item.value)
        fs=cgi.FieldStorage(fp=self.environ['wsgi.input'],environ=self.environ,keep_blank_values=True)
        for k in fs:
            inputs[k]=convert(fs[k])
        return inputs
    def _get_raws_input(self):
        if not hasattr(self,'_raw_inputs'):
            self._raw_inputs=self._parse_input()
        return self._raw_inputs
    def _getitem_(self,key):
        res=self._get_raws_input()[key]
        if isinstance(res,list):
            return res[0]
        return res
    def get(self,key,default=None):
        res=self._get_raws_input().get(key,default)
        if isinstance(res,list):
            return res[0]
        return res
    def gets(self,key):
        res=self._get_raws_input()[key]
        if isinstance(res,list):
            return res[:]
        return res
    def inputs(self,**args):
        tmp=self._get_raws_input()
        inp=dict(**args)
        for k,v in tmp.iteritems():
            inp[k]=v[0] if isinstance(v,list) else v
        return inp
    def get_body(self):
        body=self.environ['wsgi.input']
        return body.read()
    @property
    def remote_addr(self):
        return self.environ.get('REMOTE_ADDR','0.0.0.0')
    @property
    def documtent_root(self):
        return self.environ.get('DOCUMENT_ROOT','')
    @property
    def query_string(self):
        return self.environ.get('QUERY_STRING','')
    @property
    def environs(self):
        return self.environ
    @property
    def request_method(self):
        return self.environ.get('REQUEST_METHOD','')
    @property
    def path_info(self):
        return urllib.unquote(self.environ.get('PATH_INFO',''))
    @property
    def host(self):
        return self.environ.get('HTTP_HOST','localhost')
    def _get_headers(self):
        if not hasattr(self,'_headers'):
            hdrs={}
            for k,v in self.environ.iteritems():
                if k.starswith('HTTP_'):
                    hdrs[k[5:].replace('_','-').upper()]=v.decode('utf-8')
            self._headers=hdrs
        return self._headers

    def headers(self):
        d=self._get_headers()
        return dicti(**d)

    def _get_cookies(self):
        if not hasattr(self,'_cookies'):
            li={}
            cookies=self.environ.get('HTTP_COOKIE',None)
            if cookies:
                for k in cookies.split(';'):
                    pos=k.find('=')
                    li[k[:pos].strip()]=k[pos+1:].strip()
            self._cookies=li
        return self._cookies

    @property
    def cookies(self):
        d=_get_cookies()
        return dict(**d)
    def cookie(self,name,default=None):
        return self._get_cookies().get(name,default)

    
UTC_0=UTC('+00:00')

class Response(object):
    def __init__(self):
        self._headers={'CONTENT-TYPE':'text/html;charset=utf-8'}
        self.status='200 OK'

    @property
    def headers(self):
        L=[(_RESPONE_HEADERS_DICT.get(k,k),v) for k,v in self._headers.iteritems()]
        if hasattr(self,'_cookies'):
            for v in self._cookies.iteritems():
                L.append(('Set-cookie',v))
        L.append(_HEADER_X_POWERED_BY)
        return L

    def header(self,name):
        tmp_name=name.upper()
        if not tmp_name in _RESPONE_HEADERS_DICT:
            tmp_name=name
        return self._headers.get(tmp_name,None)

    def set_header(self,name,value):
        tmp_name=name.upper()
        if not tmp_name in _RESPONSE_HEADERS_DICT:
            tmp_name=name
        self._headers[tmp_name]=_to_str(value)
    
    def unset_header(self,name):
        tmp_name=name.upper()
        if not tmp_name in _RESPONSE_HEADERS_DICT:
            tmp_name=name
        if tmp_name in self._headers:
            del self._headers[tmp_name]

    @property
    def content_type(self):
        return self.header('CONTENT_TYPE')
    @content_type.setter
    def content_type(self,value):
        self.set_header('CONTENT_TYPE',_to_str(value))
    @property
    def content_length(self):
        return self.header('CONTENT_LENGTH')
    @content_length.setter
    def content_length(self,value):
        self.set_header('CONTENT_LENGTH',_to_str(value))
    def set_cookies(self,name,value,max_age=None,expires=None,path='/',domain=None,secure=False,http_only=True):
        if not hasattr(self,'_cookies'):
            self._cookies={}
        L=["%s=%s" %(name,value)]
        L.append('Path=%s' %path)
        if secure:
            L.append('Secure')
        if http_only:
            L.append('HttpOnly')
        if domain:
            L.append('Domain=%s' %domain)
        if isinstance(max_age,(int,long)):
            L.append('Max-Age=%s' %max_age)
        if expires:
            if isinstance(expires,(int,long)):
                L.append('Expires=%s' %datetime.datetime.fromtimestamp(expires,UTC_0).strftime("%a %d-%b-%Y %H:%M:%S GMT"))
            if isinstance(expires,(datetime.datetime,datetime.date)):
                L.append('Expires=%s' %expires.astimezone(UTC_0).strftime('%a %d-%b-%Y %H:%M:%S GMT'))
        self._cookies[name]=';'.join(L)
    def unset_cookies(self,name):
        if hasattr(self,'_cookies'):
            if name in self._cookies:
                del self._cookies[name]
    @property
    def status_code(self):
        return int(self.status[:3])

    @property
    def status(self):
        return self.status

    @status.setter
    def status(self,value):
        re_stat=re.compile(r'(^[0-9]{3})\s(.+)$')
        res=re_stat.match(value)
        if isinstance(value,(int,long)):
            if value >=100 and value<=999:
                if value in _RESPONSE_STATUSES:
                    self.status='%d %s' %(value,_RESPONSE_STATUSES[value])
                else:
                    self.status=str(value)
        elif isinstance(value,basestring):
            if isinstance(value,unicode):
                value=value.encode('utf-8')
            if res:
                self.status=value
            else:
                raise TypeError('bad status code')
        else:
            raise TypeError('bad status code')

class Template(object):
    def __init__(self,template_name,**args):
        self.mode=dict(**args)
        self.template_name=templat_name

class TemplateEngine(object):
    def __call__(self,path,model):
        return 'templat content'

class Jinja2TemplateEngine(TemplateEngine):
    def __init__(self,temp_dir,**args):
        from jinja2 import FileSystemLoader,Environment
        if not 'autoescape' in args:
            args['autoescape']=True
        self._env=Environment(loader=FileSystemLoader(temp_dir),**args)
    def add_filter(self,name,func):
        self._env.filters[name]=func

    def __call__(self,path,model):
        return self._env.get_template(path).render(**model).encode('utf-8')

def view(path):
    def wrapper(func):
        @functools.wraps(func)
        def wrapper2(*args,**kw):
            r=func(*args,**kw)
            if isinstance(r,dict):
                return Template(path,**r)
            else:
                raise 'return is not a dict'
        return wrapper2
    return wrapper

_RE_START_PATH=re.compile(r'^([^\*\?]+)\*?$')
_RE_END_PATH=re.compile(r'^\*([^\*\?]+)$')

def _build_re_fn(path):
    m=_RE_START_PATH.match(path)
    if m:
        return lambda p:p.startswith(m.group(1))
    m=_RE_END_PATH.match(path)
    if m:
        return lambda p:p.endswith(m.group(1))

def intercept(path):
    def wrapper(func):
        func.__intercept__=_build_re_fn(path)
        return func
    return wrapper

def build_intercept(fn,next):
    def wrapper():
        if fn.__intercept__(ctx.request.path_info):
            return fn(next)
        else:
            return next()
    return wrapper

def build_intercept_chain(target,*intercept_list):
    L=list(intercept_list)
    L.reverse()
    fn=target
    for f in L:
        fn=build_intercept(f,fn)
    return fn

def load_module(module_name):
    m=module_name.rfind('.')
    if m== (-1):
        return __import__(module_name)
    from_module=module_name[:m]
    import_module=module_name[m+1:]
    attr=__import__(from_module,globals(),locals(),[import_module])
    return getattr(attr,import_module)


class WSGIApplication(object):
    def __init__(self,document_root=None):
        self.document_root=document_root
        self._get_static_route={}
        self._post_static_route={}
        self._dynamic_get=[]
        self._dynamic_post=[]
        self._intercept=[]
        self.engine=None
    
    def add_intercept(self,func):
        self._intercept.append(func)

    def add_urls(self,func):
        path=func.__web_route__
        route=Route(func)
        if route.is_static:
            if route.method=='get':
                self._get_static_route[path]=route
            else:
                self._post_static_route[path]=route
        else:
            if route.method=='get':
                self._dynamic_get.append(route)
            else:
                self.dynamic_post.append(route)
    @property
    def template_engine(self):
        return self.engine

    @template_engine.setter
    def template_engine(self,engine):
        self.engine=engine


    def add_module(self,mod):
        import types
        m=mod if type(mod)==types.ModuleType else load_module(mod)
        for k in dir(m):
            attr=getattr(m,k)
            if callable(attr) and hasattr(attr,'__web_route__') and hasattr(attr,'__web_method__'):
                self.add_urls(attr)

    def run(self,host,port):
        from wsgiref.simple_server import make_server
        s=make_server(host,port,self.get_wsgi_application())
        s.serve_forever()

    def get_wsgi_application(self):
        _application=Dict(document_root=self.document_root)

        def fn_route():
            path_info=ctx.request.path_info
            method=ctx.request.request_method
            if method=='GET':
                if path_info in self._get_static_route:
                    fn=self._get_static_route[path_info]
                    return fn()
                for fn in self._dynamic_get:
                    args=fn.match(path_info)
                    if args:
                        return fn(*args)
                raise nofound()
            if method=='POST':
                fn=self._get_post_route.get(path_info,None)
                if fn:
                    return fn()
                for fn in self._dynamic_post:
                    args=k.match(path_info)
                    if args:
                        return fn(*args)
                raise nofound()
            raise badrequest()
        fexec=build_intercept_chain(fn_route,*self._intercept)

        def wsgi(env,start_response):
            request=ctx.request=env
            response=ctx.response=Response()
            ctx.application=_application
            try:
                t=fexec()
                if isinstance(t,Template):
                    t=self.engine(t.template_name,t.model)
                if t is None:
                    t=[]
                if isinstance(t,unicode):
                    t=t.encode('utf-8')
                    print '--------'
                    print response.status
                start_response(response.status,response.headers)
                return t
            except HttpError,e:
                start_response(e.status,response.headers)
                return ['<html><body>',e.status,'<body></html>']
            except RedirectError,e:
                response.set_header('Location',e.location)
                start_response(e.status,response.headers)
                return []
            except Exception,e:
                start_response('500 internal server error',[])
                return ['<html><body>500 internal server error']
            finally:
                del ctx.response
                del ctx.application
                del ctx.request
        return wsgi

if __name__=='__main__':
    s=_build_re('/test/file/:hello/sss:xixi/hehe/file/doc/:haha')

