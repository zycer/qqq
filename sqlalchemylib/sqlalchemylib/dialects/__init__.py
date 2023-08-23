#!/usr/bin/env python3
from sqlalchemylib.sqlalchemylib.dialects.doris import DorisDialect
from sqlalchemylib.sqlalchemylib.dialects.seabox import SeaboxDialect
from sqlalchemylib.sqlalchemylib.dialects.intersystems import IntersystemsDialect

SeaboxDialect.register()
DorisDialect.register()
IntersystemsDialect.register()
