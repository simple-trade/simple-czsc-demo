import yaml
import os

def conf():
    filepath = os.path.dirname(__file__)
    # yamlpath = os.path.abspath(os.path.join(filepath,'../../config'))
    yaml_file = os.path.join(filepath, "conf.yaml")
    file = open(yaml_file, 'r', encoding="utf-8")
    file_data = file.read()
    file.close()
    # 将字符串转化为字典或列表
    data = yaml.safe_load(file_data)
    return data

conf=conf()
# print(conf())
