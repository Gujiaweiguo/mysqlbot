import importlib


def get_excel_column_count(file_path: str, sheet_name: str) -> int:
    """获取Excel文件的列数"""
    pandas = importlib.import_module("pandas")
    df_temp = pandas.read_excel(
        file_path, sheet_name=sheet_name, engine="calamine", header=0, nrows=0
    )
    return len(df_temp.columns)
