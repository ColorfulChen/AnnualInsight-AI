import pandas as pd
import json
import os

def excel_to_json(excel_file_path, json_file_path=None):
    """
    读取Excel文件并转换为JSON格式
    
    Args:
        excel_file_path (str): Excel文件路径
        json_file_path (str, optional): 输出JSON文件路径，如果为None则自动生成
    
    Returns:
        dict: 转换后的数据字典
    """
    try:
        if not os.path.exists(excel_file_path):
            raise FileNotFoundError(f"Excel文件不存在: {excel_file_path}")
        df = pd.read_excel(excel_file_path)
        data = df.to_dict('records')
        if json_file_path is None:
            base_name = os.path.splitext(excel_file_path)[0]
            json_file_path = f"{base_name}.json"
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
        
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    excel_path = "_prompt/prompt.xlsx"
    json_path = "_prompt/prompt.json"
    result = excel_to_json(excel_path, json_path)