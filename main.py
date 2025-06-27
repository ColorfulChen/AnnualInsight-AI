import requests
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
from datetime import datetime
import openpyxl
from openpyxl import Workbook
load_dotenv()   

def payload_generate(
    question,
    file_ids,
    recall_num: int = 40,
    file_sections_num: int = 200
):
    payload = {}
    payload["question"] = question
    payload["file_ids"] = file_ids
    payload["recall_num"] = recall_num
    payload["file_sections_num"] = file_sections_num
    return json.dumps(payload)

#sleep 5 seconds between requests to avoid rate limiting
def rag_result(payload):
    url = os.environ.get("BASE_RAG_API_URL")
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text

def load_prompt(prompt_path):
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def chat(prompt):
    client = OpenAI(api_key=os.environ.get("DEEPSEEK_API"), base_url="https://api.deepseek.com")
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. You must respond with valid JSON format only."},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            
            content = response.choices[0].message.content.strip()
            
            # 处理可能包含代码块格式的JSON
            json_content = content
            if "```json" in content:
                # 提取代码块中的JSON内容
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    json_content = content[start:end].strip()
            elif "```" in content:
                # 处理没有json标识的代码块
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    json_content = content[start:end].strip()
            
            # 尝试解析JSON
            result = json.loads(json_content)
            
            # 验证返回的JSON格式是否包含score字段且值在0-10之间
            if "score" in result and isinstance(result["score"], int) and 0 <= result["score"] <= 10:
                return result
            else:
                raise ValueError("Invalid score format or value out of range")
                
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Attempt {attempt + 1} failed: {e} ,{content}")
            if attempt == max_retries - 1:
                print("Max retries reached. Unable to get valid JSON response.")
                return {"score": -1}  # 返回错误标识
            # 在重试时添加更明确的提示
            prompt += f"\n请确保严格按照JSON格式输出: {{\"score\": 数字(0-10)}}"
            time.sleep(1)  # 短暂延迟后重试
    
    return {"score": -1}  # 如果所有重试都失败，返回错误标识

def nest_reg_result(rag_res):
    # 将返回的结果按照文档进行嵌套
    for doc in rag_res:
        doc['sections'] = sorted(
            doc['sections'],
            key=lambda s: int(s['section_document']['sequence'])
        )
    
    string = f"相关的内容如下：\n\n文章标题：{rag_res[0]['title']}\n文章发表时间：{rag_res[0]['publish_date']}\n"
    string += "文章内容：\n"
    string += rag_res[0]['sections'][0]['section_document']['text'] + '\n'
    last_sequence = rag_res[0]['sections'][0]['section_document']['sequence']

    for res in rag_res[0]['sections'][1:]:
        if res['section_document']['sequence'] == (last_sequence + 1):
            string += res['section_document']['text'] + '\n'
        else:
            string += '......\n' + res['section_document']['text'] + '\n'

        if len(string) > 15000:
            break

    return string

def generate_prompt(rag_res,question):
    prompt = "你是一个风险评估师，根据以下内容对该公司年报的风险进行评估。相关内容如下：\n"
    # print(json.dumps(rag_res, ensure_ascii=False, indent=2))
    prompt += rag_res
    prompt += "请根据以上内容回答以下问题：\n"
    prompt += question + "\n"
    prompt += "输出严格按照json格式输出一个准确的分数，不要输出推理过程和任何其他内容。{\"score\": \"0-10(int)\"}\n"
    return prompt

def analysis(file_id):
    rag_file = []
    rag_file.append(file_id)
    questions = load_prompt('_prompt\\prompt.json')
    wb = Workbook()
    ws = wb.active
    ws.append(['cnt','id', 'file_id', 'file_name', '问题一级维度', '二级维度', '具体问题', '返回文档','分数'])
    cnt = 0
    for question in questions:
        cnt = cnt + 1
        print(f'{cnt}/{len(questions)}')
        payload = payload_generate(question=question['提示词'],file_ids=rag_file)
        rag_res = []
        max_tries = 10
        tries = 0
        while rag_res == [] and tries < max_tries:
            try:
                rag_res = json.loads(rag_result(payload=payload))
                time.sleep(5)
            except Exception as e:
                tries += 1

        if tries >= max_tries:
            print(f"问题: {question['提示词']} 无法生成有效的提示（尝试次数超过限制）")
            continue
        else:
            reg_result = nest_reg_result(rag_res)
            prompt = generate_prompt(reg_result, question['提示词'])
            score = chat(prompt)
        try:
            ws.append([
                cnt,
                file_id,
                file_id,
                rag_res[0]['title'],
                question["一级维度"],
                question["二级维度"],
                question["提示词"],
                reg_result,
                score['score']
            ])
        except Exception as e:
            print(f"问题: {question['提示词']} 的结果写入Excel失败: {e}")
    timestamp = int(datetime.now().timestamp())
    wb.save(f"_result/exp-{rag_res[0]['title']}-{timestamp}.xlsx")


def rag_exp(file_id):
    rag_file = []
    rag_file.append(file_id)
    questions = load_prompt('_prompt\\prompt.json')
    wb = Workbook()
    ws = wb.active
    ws.append(['id', 'file_id', 'file_name', '问题一级维度', '二级维度', '具体问题', '返回文档'])

    cnt = 0
    for question in questions[:3]:
        cnt = cnt + 1
        print(f'{cnt}/{len(questions)}')
        payload = payload_generate(question=question['提示词'],file_ids=rag_file)
        rag_res = []
        max_tries = 10
        tries = 0
        while rag_res == [] and tries < max_tries:
            try:
                rag_res = json.loads(rag_result(payload=payload))
                time.sleep(5)
            except Exception as e:
                tries += 1

        if tries >= max_tries:
            print(f"问题: {question['提示词']} 无法生成有效的提示（尝试次数超过限制）")
            continue
        try:
            ws.append([
                file_id,
                file_id,
                rag_res[0]['title'],
                question["一级维度"],
                question["二级维度"],
                question["提示词"],
                nest_reg_result(rag_res)
            ])
        except Exception as e:
            print(f"问题: {question['提示词']} 的结果写入Excel失败: {e}")
    wb.save(f"exp{file_id}.xlsx")
            

                     
if __name__ == "__main__":
    file_id2 = 97485300
    analysis(file_id=file_id2)