from transwrap.db import *
from transwrap.web import *
import os
import functools

server=WSGIApplication(os.path.dirname(os.path.abspath(__file__)))

engine=Jinja2TemplateEngine(os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates'))

server.engine=engine

create_engine('hu','hu','hu','127.0.0.1',3306)
import urls

server.add_module('urls')

if __name__=='__main__':
    server.run(host='wikiki.cn',port=9001)
