# coding=utf-8
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import datetime
import logging

logging.basicConfig(level=logging.INFO)


class TableModels(object):
    """通过反射获取数据库中的表
    """
    __TABLE_TO_REFLECT__ = ('case', 'emrInfo', 'caseProblem', 'qcItem')

    def __init__(self, engine):
        self.engine = engine
        metadata = MetaData()
        metadata.reflect(engine, only=self.__TABLE_TO_REFLECT__)
        Base = automap_base(metadata=metadata)
        Base.prepare()
        self._tables = {}
        # print list(Base.classes)
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

    def exportNotOpenProblem(self, startTime, filename):
        counting_filename = 'counting_problem.csv'
        if not startTime:
            startTime = datetime.datetime.now().strftime('%Y-%m-%d')
        # 导出未开启的问题列表
        with open(filename, 'w') as df, open(counting_filename, 'w') as cf:
            with self.session() as session:
                # 查询质控点信息
                qcitem_sql = 'select id, code, requirement from qcItem'
                query = session.execute(qcitem_sql)
                queryset = query.fetchall()
                qcitems = {}
                for row in queryset:
                    qcitems[row[0]] = (row[1], row[2])
                print('查询质控点列表完成')

                # 按时间条件查询第一条数据的id
                first_row_sql = "select id from caseProblem where created_at > '%s' limit 1" % startTime
                query = session.execute(first_row_sql)
                queryset = query.fetchone()
                if not queryset:
                    logging.error('first row not found')
                    return
                first_row_id = queryset[0]
                print('查找满足时间条件的第一条记录id = %d' % first_row_id)

                # 统计质控点频次
                print('统计显示的质控点问题频次')
                counting_sql = "select qcItemId, count(*) from caseProblem where id > {} and created_at > '{}' and is_deleted = 0 group by qcItemId ".format(
                    first_row_id, startTime)
                query = session.execute(counting_sql)
                queryset = query.fetchall()
                counting_dict = {}
                for row in queryset:
                    counting_dict[row[0]] = row[1]
                    cf.write('%s, %d\n' % (qcitems.get(row[0], ('', ''))[0], row[1]))

                # 查询上线的质控点问题列表
                df.write('质控点编号,质控点名称,caseId,patientId,出院科室,文书id,文书名称,文书书写时间,reason,问题创建时间,是否ai,是否开启\n')
                problem_sql = '''select cp.caseId, c.patientId, c.outDeptName, cp.docId, ce.documentName, 
                              ce.recordTime, cp.reason, cp.created_at, cp.from_ai from caseProblem cp 
                              left join emrInfo ce on cp.caseId = ce.caseId and cp.docId = ce.docId 
                              left join `case` c on c.caseId = cp.caseId 
                              where cp.id > {} and cp.created_at > '{}' and cp.qcItemId = {} '''
                for k, v in counting_dict.items():
                    qcitem = qcitems.get(k, ('', ''))
                    print('开始查询质控点[%s]问题列表' % qcitem[0])
                    query = session.execute(problem_sql.format(first_row_id, startTime,
                                                               k) + 'and cp.is_deleted = 0 order by cp.id desc limit 40 ')
                    queryset = query.fetchall()
                    for row in queryset:
                        df.write('%s, %s,' % (qcitem[0], qcitem[1]))
                        df.write('%s,' % row[0])
                        df.write('%s,' % row[1])
                        df.write('%s,' % row[2])
                        df.write('%s,' % (row[3] or '无'))
                        df.write('%s,' % (row[4] or '无'))
                        df.write('%s,' % (row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '无'))
                        df.write('%s,' % row[6].replace('\t', ' ').replace('\n', ' ').replace(',', ' '))
                        df.write('%s,' % (row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else '无'))
                        df.write('%s,' % ('是' if row[8] else '否'))
                        df.write('开启\n')

                # 统计未显示的质控点
                print('统计未显示的质控点问题频次')
                counting_sql = "select qcItemId, count(*) from caseProblem where id > {} and created_at > '{}' and notOpen = 1 group by qcItemId ".format(
                    first_row_id, startTime)
                query = session.execute(counting_sql)
                queryset = query.fetchall()
                counting_dict = {}
                for row in queryset:
                    counting_dict[row[0]] = row[1]
                    cf.write('%s, %d\n' % (qcitems.get(row[0], ('', ''))[0], row[1]))

                # 查询未显示的数据
                for k, v in counting_dict.items():
                    qcitem = qcitems.get(k, ('', ''))
                    print('开始查询质控点[%s]问题列表' % qcitem[0])
                    query = session.execute(problem_sql.format(first_row_id, startTime,
                                                               k) + 'and cp.notOpen = 1 order by cp.id desc limit 40 ')
                    queryset = query.fetchall()
                    for row in queryset:
                        df.write('%s, %s,' % (qcitem[0], qcitem[1]))
                        df.write('%s,' % row[0])
                        df.write('%s,' % row[1])
                        df.write('%s,' % row[2])
                        df.write('%s,' % (row[3] or '无'))
                        df.write('%s,' % (row[4] or '无'))
                        df.write('%s,' % (row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else '-'))
                        df.write('%s,' % row[6].replace('\t', ' ').replace('\n', ' ').replace(',', ' '))
                        df.write('%s,' % (row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else '-'))
                        df.write('%s,' % ('是' if row[8] else '否'))
                        df.write('未开启\n')
        print("导出完成")


def main():
    from argparse import ArgumentParser, RawTextHelpFormatter
    def getArgs():
        parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
        parser.add_argument('-f', dest='filename', default='problems_export.csv', help='输出文件, Default: %(default)s')
        parser.add_argument('--db-url', dest='dbUrl', help='数据库url, Default:%(default)s',
                            default='mysql+pymysql://root:rxthinkingmysql@mysql.infra-default:3306/qcmanager?charset=utf8mb4')
        sub_parsers = parser.add_subparsers(dest='action')
        export_parser = sub_parsers.add_parser('export', help='导出未开启问题列表到文件')
        export_parser.add_argument('-t', dest='startTime', help='问题创建时间的开始时刻')

        return parser.parse_args()

    args = getArgs()
    db = QCDataBaseManager(args.dbUrl)
    if args.action == 'export':
        db.exportNotOpenProblem(args.startTime, args.filename)


if __name__ == '__main__':
    main()
