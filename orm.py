import db
import time
import logging
class Field(object):
    count=0
    def __init__(self,**kw):
        self.name=kw.get('name',None)
        self.primary_key=kw.get('primary_key',False)
        self.nullable=kw.get('nullable',False)
        self.updatable=kw.get('updatable',True)
        self.insertable=kw.get('insertable',True)
        self._default=kw.get('default',None)
        self.ddl=kw.get('ddl',None)
        self.order=Field.count
        Field.count=Field.count+1

    @property
    def default(self):
        d=self._default
        return d() if callable(d) else d

class StringField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=''
        if not 'ddl' in kw:
            kw['ddl']="varchar(255)"
        super(StringField,self).__init__(**kw)

class InterField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=0
        if not 'ddl' in kw:
            kw['ddl']='bigint'
        super(InterField,self).__init__(**kw)

class BoolField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = False
        if not 'ddl' in kw:
            kw['ddl']='bool'
        super(BoolField,self).__init__(**kw)

class FloatField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] =0.0
        if not 'ddl' in  kw:
            kw['ddl']='real'
        super(FloatField,self).__init__(**kw)

class TextField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default']=''
        if not 'ddl' in  kw:
            kw['ddl'] = 'text'
        super(TextField,self).__init__(**kw)
class VersionField(Field):
    def __init__(self,name=None):
        super(VersionField,self).__init__(name=name,default=0,ddl='bigint')



def _gen_sql(table_name,mapping):
    L=[]
    pk=None
    sql="create table %s (" %table_name
    for f in sorted(mapping.values(),lambda x,y:cmp(x.order,y.order)):
        if f.primary_key:
            pk=f.name
        if not f.ddl:
            raise 'no ddl'
        if f.nullable:
            L.append("%s %s" %(f.name,f.ddl))
        else:
            L.append("%s %s not null" %(f.name,f.ddl))
    L.append("primary key(%s)" %pk)
    sql=sql+','.join(L)+');'
    return sql


_tragger=frozenset(["pre_insert","pre_delete","pre_upate"])


class MetaClass(type):
    def __new__(cls,name,bases,attrs):
        primary_key=None
        args=[]
        mapping={}
        if name == "Model":
            return type.__new__(cls,name,bases,attrs)
        if not hasattr(cls,"subclass"):
            cls.subclass={}
        if name not in cls.subclass:
            cls.subclass[name]=name
        for k,v in attrs.iteritems():
            if  isinstance(v,Field):
                if v.name is None:
                    v.name=k
                if v.primary_key:
                    if not primary_key:
                        primary_key=v
                    else:
                        raise "has been exsit primary key"
                    if v.nullable:
                        logging.warning("the primary key must be not null")
                        v.nullable=False
                    if v.updatable:
                        logging.warning("the primary key must be not update")
                        v.updatable=False
                mapping[v.name]=v
                args.append(k)
         
        if not primary_key:
            raise 'table has not primary key!'
        #delete  the Model subclass attribute that extends from Field
        for k in args:
            attrs.pop(k)
        if not '__table__' in attrs:
            attrs['__table__']=name.lower()
        attrs['__mapping__']=mapping
        attrs['__pri_key__']=primary_key
        attrs['__sql__']=_gen_sql(attrs['__table__'],mapping)
        for tragger in _tragger:
            if not hasattr(cls,tragger):
                attrs[tragger]=None
        return type.__new__(cls,name,bases,attrs)


class Model(dict):
    __metaclass__=MetaClass
    def __init__(self,**kw):
        super(Model,self).__init__(**kw)
    
    def __getattr__(self,name):
        if not name in self:
            raise 'not attribute !!'
        return self[name]

    def __setattr__(self,name,value):
        self[name]=value

    @classmethod
    def get(cls,key):
        sql="select * from %s where %s='?' " %(cls.__table__,cls.__pri_key__.name)
        d=db.select_one(sql,key)
        return cls(**d) if d else None
    def update(self):
        sql="update %s set %s where %s=?"
        L=[]
        args=[]
        pk=self.__pri_key__.name
        for k,v in self.__mapping__.iteritems():
            if v.updatable:
                if hasattr(self,v.name):
                    L.append("%s=?" %v.name)
                    args.append(self[k])
                else:
                    setattr(self,v.name,v.default)
                    L.append("%s=?" %k)
                    args.append(getattr(self,k))
        args.append(self[pk])
        sql=sql %(self.__table__,','.join(L),pk)
        db.update(sql,*args)
    
    def insert(self):
        L=[]
        args={}
        for k,v in self.__mapping__.iteritems():
            if v.insertable:
                if not hasattr(self,k):
                    setattr(self,k,v.default)
                args[k]=getattr(self,k)
        db.insert_table(self.__table__,**args)
    
    def delete(self):
        pk=self.__pri_key__.name
        if pk is None:
            raise 'no pri_key vaules'
        kid=getattr(self,pk)
        sql="delete from %s where %s=? " %(self.__table__,pk)
        print sql
        kid=(kid,)
        db.update(sql,*kid)
        return self

if __name__ == '__main__':
     db.create_engine('hu','hu','hu','127.0.0.1',3306)
     maps=dict(id=StringField(primary_key=True,nullable=True,ddl='varchar(50)'),name=StringField(ddl='varchar(50)'),create_at=FloatField(updatable=False))
     table_name='users'
     print _gen_sql(table_name,maps)

        



    

























