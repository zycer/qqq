# sqlalchemylib

sqlalchemy的一些工具封装

使用方法参考test/test_connection.py


### sqlalchemy

使用 declarative_base() 定义 Base，创建的所有映射数据表的类都继承自该基类，该基类用于维护所有映射类的元信息

基类 Base 已经包含了一个 metadata 实例，metadata 包含了和DDL相关的所有信息，基于 Base 定义的映射类都会被自动加入到这个 metadata 中，通过 Base.metadata 可以来访问这个 metadata


### 自动迁移 auto migrate

使用 `alembic` 生成目标数据库与 models 中定义的映射数据表结构 metadata 的迁移脚本(`alembic.MigrationScript`)


