# -*- coding: utf-8 -*-
"""
DuckDB数据库工具模块 - 替代大CSV文件的读写操作
"""
import duckdb
import pandas as pd
import os
from pathlib import Path
from quant_infra.const import *
def init_db():
    """初始化数据库连接
    如果数据库文件不存在，会自动创建
    1、解析路径，2、定位到父目录，3、创建父目录（如果不存在），4、如果存在也不报错
    """
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    try:
        return duckdb.connect(DB_PATH)
    except duckdb.IOException as e:
        wrong_message = str(e)
        if any(keyword in wrong_message for keyword in ('Could not set lock', 'already open', '另一个程序', 'resource temporarily unavailable')):
            raise RuntimeError(
                f"数据库文件 '{DB_PATH}' 正被其他程序占用，请先关闭后重试。\n({wrong_message.splitlines()[0]})"
            ) from None
        raise
def read_sql(query):
    """
    执行SQL查询并返回DataFrame
    
    Args:
        query: SQL查询语句
        
    Returns:
        DataFrame
    """
    conn = init_db()
    try:
        result = conn.execute(query).fetch_df()
        return result
    finally:
        conn.close()

def write_to_db(df, table_name, save_mode ='replace'):
    """
    将DataFrame写入数据库
    
    Args:
        df: DataFrame
        table_name: 目标表名
        save_mode: 'replace'|'append'
    """
    conn = init_db()
    try:
        conn.register('temp_df', df)
        # 检查表格是否存在
        table_exists_query = f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
        ## 取第一行.fetchone()的第一列[0]，如果大于0说明表格存在
        table_exists = conn.execute(table_exists_query).fetchone()[0] > 0

        if table_exists:
            if save_mode == 'replace':
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            else:  # append
                conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
        else:
            # 如果表格不存在，直接创建
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        print(f"{table_name}新增数据：{len(df)} 行")
    finally:
        conn.close()

def _normalize_imported_factor_df(df, factor_column='factor'):
    # 1. 校验列名
    required = ['ts_code', 'trade_date', factor_column]
    if not set(required).issubset(df.columns):
        missing = set(required) - set(df.columns)
        raise ValueError(f'因子文件缺少必要列: {missing}')

    # 2. 链式清洗逻辑
    return (df[list(required)]
            .rename(columns={factor_column: 'factor'})
            .assign(
                # 统一转为字符串并去空格
                ts_code=lambda x: x['ts_code'].astype(str).str.strip(),
                # 统一日期格式
                trade_date=lambda x: pd.to_datetime(x['trade_date'].astype(str)).dt.strftime('%Y%m%d'),
                # 强制转数值
                factor=lambda x: pd.to_numeric(x['factor'], errors='coerce')
            )
            .dropna(subset=['ts_code', 'trade_date', 'factor'])
            .query("ts_code != ''")
            .drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
            .sort_values(['trade_date', 'ts_code'])
            .reset_index(drop=True))


def import_factor_table(file_path, table_name, factor_column='factor', save_mode='append'):
    """通用导入函数，支持自动识别格式。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'文件不存在: {file_path}')

    # 1. 自动识别读取逻辑
    ext = os.path.splitext(file_path)[1].lower()
    read_map = {'.csv': pd.read_csv, '.parquet': pd.read_parquet, '.pq': pd.read_parquet}
    
    if ext not in read_map:
        raise ValueError(f'不支持的格式: {ext}')
    
    # 2. 读取并标准化
    raw_df = read_map[ext](file_path)
    result = _normalize_imported_factor_df(raw_df, factor_column)

    if result.empty:
        return result

    write_to_db(result, table_name, save_mode=save_mode)
    print(f"✅ 导入成功: {table_name} | 行数: {len(result)} | 时间范围: {result['trade_date'].min()}~{result['trade_date'].max()}")
    return result