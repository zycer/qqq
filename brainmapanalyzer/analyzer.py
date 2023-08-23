#!/usr/bin/env python3
'''
Author: qiupengfei@rxthinking.com
Date: 2022-02-15 19:34:58

'''
from os import supports_effective_ids
from typing import Optional, Union
from brainmapanalyzer.keywords.keywords import Keyword
from brainmapanalyzer.keywords.operators import Operator
from iyoudoctor.hosp.search.data_pb2 import Query, CompareQuery, AndQuery, OrQuery, NotQuery
