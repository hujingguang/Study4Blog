#!/usr/bin/python
import logging,time,uuid,threading
import functools


class Dict(dict):
    def __init__(self,names=(),vaules=(),**args):
        super(Dict,self).__init__(**args)
        for k,v in zip(names,vaules):
            self[k]=v
    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' have not this key %s" %key)
    def __setattr__(self,key,value):
        self[key]=value

def next_id(t=None):
    if t is None:
        t=time.time()
    return "%015d%s000" %(int(t*1000),uuid.uuid4().hex)



engine=None


class _Connectionctx(object):
    def __enter__(self):
        global _dbctx
        self.Flag=False
        if _dbctx.is_init() is None:
            _dbctx.init()
            self.Flag=True
    def __exit__(self,exctype,excvalue,traceback):
        global _dbctx
        if self.Flag:
            _dbctx.cleanup()



def connection():
    return _Connectionctx()


def with_connection(func):
    functools.wraps(func)
    def wrapper(*args,**kw):
        with _Connectionctx():
            return func(*args,**kw)
    return wrapper

class _Transaction(object):
    def __enter__(self):
        global _dbctx
        self.should_close_conn=False
        if _dbctx.is_init() is None:
            _dbctx.init()
            self.should_close_conn=True
        _dbctx.transaction=_dbctx.transaction+1 
        return self

    def __exit__(self,exctype,excvalue,trancback):
        global _dbctx
        _dbctx.transaction=_dbctx.transaction-1
        try:
            if _dbctx.transaction == 0:
                if exctype is None:
                    self.commit()
                else:
                    self.rollback()
        except:
            self.rollback()
            raise
        finally:
            if self.should_close_conn:
                _dbctx.cleanup()

    def commit(self):
        global _dbctx
        try:
            _dbctx.connection.commit()
        except:
            _dbctx.connection.rollback()
            raise
    def rollback(self):
        global _dbctx
        _dbctx.connection.rollback()
        

def transaction():
    return _Transaction()

def with_transaction(func):
    functools.wraps(func)
    def wrapper(*args,**kw):
        with _Transaction():
            return func(*args,**kw)
    return wrapper


@with_connection
def _select(sql,first,*args):
    global _dbctx
    cursor=None
    sql=sql.replace('?','%s')
    sql=sql %(args)
    try:
        cursor=_dbctx.connection.getcursor()
        cursor.execute(sql)
        if cursor.description:
            names=[x[0] for x in cursor.description]
        if first:
            values=cursor.fetchone()
            if not values:
                return None
            return Dict(names,values)
        return [Dict(names,x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()

def _select_int(sql,*args):
    global _dbctx
    d=_select(sql,*args)
    if len(d) != 1:
        raise "Outof Border"
    return d.values[0]


def select_one(sql,*args):
    return _select(sql,True,*args)

def select(sql,*args):
    return _select(sql,False,*args)

def select_int(sql,*args):
    return _selet_int(sql,*args)

@with_connection
def _update(sql,*args):
    global _dbctx
    cursor=None
    sql=sql.replace('?','"%s"')
    sql=sql %args
    try:
        cursor=_dbctx.connection.getcursor()
        cursor.execute(sql)
        r=cursor.rowcount
        if _dbctx.transaction == 0:
            _dbctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()

def insert_table(table,**kw):
    sql="insert into %s (%s) values(%s)"
    names,args=zip(*kw.iteritems())
    names=','.join(names)
    print names
    values=','.join(['?' for i in range(0,len(args))])
    print values
    sql=sql %(table,names,values)
    print '---------------'
    print sql
    print '---------------'
    #_update(sql)
    return _update(sql,*args)

def update(sql,*args):
    return _update(sql,*args)




class _DbCtx(threading.local):
    def __init__(self):
        self.connection=None
        self.transaction=0

    def is_init(self):
        if self.connection is None:
            return None
        return True

    def init(self):
        if self.connection is None:
            self.connection=_LasyConnection()

    def getcursor(self):
        return self.connection.getcursor()
    
    def cleanup(self):
        self.connection.cleanup()
        self.connection=None

_dbctx=_DbCtx()

class _LasyConnection(object):
    def __init__(self):
        self.connection=None
    def getcursor(self):
        if self.connection is None:
            self.connection=engine.getconnect()
        return self.connection.cursor()
    def commit(self):
        self.connection.commit()
    def rollback(self):
        self.connection.rollback()
    def cleanup(self):
        if self.connection:
            connection=self.connection
            self.connection=None
            connection.close()


class _Engine(object):
    def __init__(self,**params):
        self._params=params
    def getconnect(self):
        import mysql.connector
        conn=mysql.connector.connect(**self._params)
        if conn:
            return conn
        return None

def create_engine(user,password,database,host,port,**args):
    import mysql.connector
    global engine
    if engine is not None:
        raise "DB has been init"
    params=dict(user=user,password=password,database=database,host=host,port=port)
    default=dict(use_unicode=True,charset="utf8",collation='utf8_general_ci',autocommit=False)
    for k,v in default.iteritems():
        params[k]=args.pop(k,v)
    params.update()
    params['buffered']=True
    engine=_Engine(**params)

if __name__=='__main__':
    create_engine('hu', 'hu', 'hu','127.0.0.1',3306)
    with connection():
        insert('user',**dict(id=119988810,name='Joy',email='ww@wikiki.cn',last_modified=time.time(),passwd='123123'))
        #print select('select ?,? from user where name="?"','id','name','Joy')
        #update('delete from user where id=?',1)
        #print hex(id(_dbctx.connection))



