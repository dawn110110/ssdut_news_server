#!/usr/bin/env python

import db
import models
if __name__ == "__main__":
    db.init_db()
    models.kv.db_inited = ''
