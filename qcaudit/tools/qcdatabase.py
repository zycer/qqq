# coding=utf-8
from contextlib import contextmanager
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker


class TableModels(object):
    """通过反射获取数据库中的表
    """
    __TABLE_TO_REFLECT__ = ('qcGroup', 'qcCategory', 'qcItem', 'qcCateItems', 'configItem',
                            'emrInfo', 'documents', 'doctor', 'emrContent',
                            'score_report_template', 'score_report_qcitems', 'diagnosis_dict', 'department',
                            'medicalAdvice', 'labInfo', 'labContent', 'examInfo', 'examContent', 'fpoperation',
                            'fpdiagnosis', 'mz_diagnosis', 'normal_dict')

    def __init__(self, engine):
        self.engine = engine
        metadata = MetaData()
        metadata.reflect(engine, only=self.__TABLE_TO_REFLECT__)
        Base = automap_base(metadata=metadata)
        Base.prepare()
        self._tables = {}
        for table_name in self.__TABLE_TO_REFLECT__:
            tcls = getattr(Base.classes, table_name)
            self._tables[table_name] = tcls

    def __getattr__(self, key):
        if key in self._tables:
            return self._tables[key]
        else:
            raise AttributeError("attribute not found")

    def __getitem__(self, key):
        return self._tables[key]


class QCDataBaseManager(object):

    def __init__(self, url):
        self.engine = create_engine(url)
        self._Session = sessionmaker(bind=self.engine)

        self.models = TableModels(self.engine)

    @contextmanager
    def session(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()