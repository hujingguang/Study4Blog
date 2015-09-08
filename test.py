


import os
from transwrap.db import *
import models
from transwrap.orm import *
import time
if __name__=='__main__':
    db.create_engine('hu','hu','hu','127.0.0.1',3306)
    users=models.User()
    users.id='123144444'
    users.name='Joy'
    users.email='haha'
    users.create_at=time.time()
    users.admin=False
    users.image='444123123123'
    print users.__sql__
    print models.Blog.__sql__
    print models.Comment.__sql__
