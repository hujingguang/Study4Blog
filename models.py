#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Models for user, blog, comment.
'''

import time, uuid

from transwrap.db import next_id
from transwrap.orm import Model, StringField, BoolField, FloatField, TextField

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    email = StringField(updatable=False, ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BoolField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    create_at = FloatField(updatable=False, default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    blog_id = StringField(updatable=False, ddl='varchar(50)')
    user_id = StringField(updatable=False, ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)
