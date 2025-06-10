from lxml import etree
import time
import datetime
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
import requests
import re
import os
import threading
from queue import Queue
import queue
from datetime import datetime
import replace
import fileinput
from tqdm import tqdm
from pypinyin import lazy_pinyin
from opencc import OpenCC
import base64
import cv2
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from translate import Translator  # 导入Translator类,用于文本翻译

# 定义请求头
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

import requests
from lxml import etree

def via_tonking(url):
    headers = {
        'Referer': 'http://tonkiang.us/hotellist.html',
        'User-Agent': header["User-Agent"],
    }
    try:
        # 提取 IP 地址部分，去除协议
        ip_address = url.split("//")[-1]
        response = requests.get(
            url=f'https://tonkiang.us/hoteliptv.php?page=1&iphone1=北京市&code=',
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        et = etree.HTML(response.text)
        div_text = et.xpath('//div[@class="result"]/div/text()')[1]
        return "暂时失效" not in div_text
    except Exception as e:
        print(f"验证 IP 时发生错误: {e}")
        return False


# 从tonkiang获取可用IP
def get_tonkiang(keyword):
    data = {
        "saerch": f"{keyword}",
        "Submit": " "
    }
    try:
        resp = requests.post(
            "http://tonkiang.us/hoteliptv.php",
            headers=header,
            data=data,
            timeout=10
        )
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        et = etree.HTML(resp.text)
        divs = et.xpath('//div[@class="tables"]/div')
        result_urls = []
        for div in divs:
            try:
                status = div.xpath('./div[3]/div/text()')[0]
                if "暂时失效" not in status:
                    # 尝试提取IP地址或域名
                    ip_or_domain = div.xpath('./div[1]/a/b/text()')[0].strip()
                    # 解析IP地址或域名
                    parsed_url = urlparse(f'http://{ip_or_domain}')
                    if parsed_url.scheme and parsed_url.netloc:
                        if via_tonking(parsed_url.geturl()):
                            result_urls.append(parsed_url.geturl())
            except (IndexError, ValueError, AttributeError):
                continue
        return result_urls
    except Exception as e:
        print(f"获取IP时发生错误: {e}")
        return []

# 定义频道分类规则
def classify_channel(channel_name):
    guangdong_channels = ['广州综合', '广州新闻', '广东珠江', '广州影视频道', '广东综艺', '广东影视']
    hkgmta_channels = ['翡翠台', '凤凰中文', '凤凰资讯', '明珠台', '娱乐新闻台', '无线新闻台', '有线新闻', '中天新闻', '星空卫视']
    if channel_name.startswith('CCTV'):
        return '央视频道'
    elif any(province in channel_name for province in ['北京', '江苏', '浙江', '东方', '深圳', '安徽', '河南', '黑龙江', '山东', '天津', '四川', '重庆', '湖北', '江西', '贵州', '东南', '云南', '河北', '海南', '吉林', '辽宁']):
        return '地方卫视'
    elif any(channel in channel_name for channel in guangdong_channels):
        return '广东频道'
    elif any(channel in channel_name for channel in hkgmta_channels):
        return '港澳台频道'
    else:
        return '其他频道'

def add_channel_classification(file_path):
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 初始化分类字典
    classified_channels = {
        '央视频道': [],
        '地方卫视': [],
        '广东频道': [],
        '港澳台频道': [],
        '其他频道': []
    }

    # 对每一行进行分类
    for line in lines:
        parts = line.split(',', 1)
        if len(parts) >= 2:
            channel_name = parts[0].strip()
            category = classify_channel(channel_name)
            classified_channels[category].append(line)

    # 重新组织文件内容
    new_lines = []
    for category, channels in classified_channels.items():
        if channels:
            new_lines.append(f'{category},#genre#\n')
            new_lines.extend(channels)

    # 将处理后的内容写回文件
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)

def gen_files(valid_ips, province, isp):
    # 生成节目列表 省份运营商.txt
    index = 0
    print(valid_ips)
    udp_filename = f'rtp/{province}_{isp}.txt'
    with open(udp_filename, 'r', encoding='utf-8') as file:
        data = file.read()
    txt_filename = f'playlist/{province}{isp}.txt'
    with open(txt_filename, 'a', encoding='utf-8') as new_file:
        new_file.write(f'{province}{isp},#genre#\n')
        for url in valid_ips:
            if index < 15:
                # 确保 url 是一个完整的 URL 字符串，并且以 'http://' 开头
                base_url = "rtp://"
                if not url.startswith("http://"):
                    url = "http://" + url  # 如果 url 不是以 'http://' 开头，则添加它
                new_data = data.replace(base_url, url + "/rtp/")  # 替换并添加斜杠
                new_file.write(new_data.replace(" ", ""))  # 替换后去掉末尾的空格
                new_file.write('\n')
                index += 1
            else:
                break  # 替换 continue 为 break，因为你只需要前10个 IP
    print(f'已生成播放列表，保存至{txt_filename}')

# 遍历rtp文件夹中的所有文件
rtp_folder = 'rtp'
playlist_folder = 'playlist'

# 确保playlist目录存在
os.makedirs(playlist_folder, exist_ok=True)

for filename in os.listdir(rtp_folder):
    if filename.endswith(".txt"):
        province_isp = filename[:-4]  # 获取不包含扩展名的文件名
        keyword = province_isp.replace('_', '')  # 假设文件名格式为"省份_运营商"
        valid_ips = get_tonkiang(keyword)  # 搜索有效IP
        if valid_ips:
            print(f"找到有效IP，正在生成文本文件: {province_isp}")
            gen_files(valid_ips, province_isp.split('_')[0], province_isp.split('_')[1])  # 生成文本文件
        else:
            print(f"未找到有效IP: {province_isp}")

print('对playlist文件夹里面的所有txt文件进行去重处理')
def remove_duplicates_keep_order(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            lines = set()
            unique_lines = []
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line not in lines:
                        unique_lines.append(line)
                        lines.add(line)
            # 将保持顺序的去重后的内容写回原文件
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(unique_lines)
# 使用示例
folder_path = 'playlist'  # 替换为你的文件夹路径
remove_duplicates_keep_order(folder_path)
print('文件去重完成！移除存储的旧文件！')

######################################################
#####################################################
######################################################################################################################

#################################################################################
###############检测playlist文件夹内所有txt文件内的组播
###############检测playlist文件夹内所有txt文件内的组播
###############检测playlist文件夹内所有txt文件内的组播

import os
import cv2
import time
from tqdm import tqdm
import sys

# 初始化字典以存储IP检测结果
detected_ips = {}

def get_ip_key(url):
    """从URL中提取IP地址，并构造一个唯一的键"""
    start = url.find('://') + 3
    end = url.find('/', start)
    if end == -1:
        end = len(url)
    return url[start:end].strip()

# 设置固定的文件夹路径
folder_path = 'playlist'

# 确保文件夹路径存在
if not os.path.isdir(folder_path):
    print("指定的文件夹不存在。")
    sys.exit()

# 遍历文件夹中的所有.txt文件
for filename in os.listdir(folder_path):
    if filename.endswith('.txt'):
        file_path = os.path.join(folder_path, filename)
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # 准备写回文件
        with open(file_path, 'w', encoding='utf-8') as output_file:
            # 使用 tqdm 显示进度条
            for line in tqdm(lines, total=len(lines), desc=f"Processing {filename}"):
                parts = line.split(',', 1)
                if len(parts) >= 2:
                    channel_name, url = parts
                    channel_name = channel_name.strip()
                    url = url.strip()
                    ip_key = get_ip_key(url)
                    
                    # 检查IP是否已经被检测过
                    if ip_key in detected_ips:
                        # 如果之前检测成功，则写入该行
                        if detected_ips[ip_key]['status'] == 'ok':
                            output_file.write(line)
                        continue  # 无论之前检测结果如何，都不重新检测
                    
                    # 初始化帧计数器和成功标志
                    frame_count = 0
                    success = False
                    # 尝试打开视频流
                    cap = cv2.VideoCapture(url)
                    start_time = time.time()
                    while (time.time() - start_time) < 3:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame_count += 1
                        # 如果在3秒内读取到63帧以上，设置成功标志
                        if frame_count >= 60:
                            success = True
                            break
                    cap.release()
                    
                    # 根据检测结果更新字典
                    if success:
                        detected_ips[ip_key] = {'status': 'ok'}
                        output_file.write(line)
                    else:
                        detected_ips[ip_key] = {'status': 'fail'}

# 打印检测结果
for ip_key, result in detected_ips.items():
    print(f"IP Key: {ip_key}, Status: {result['status']}")

# 增加频道分类
for filename in os.listdir(folder_path):
    if filename.endswith('.txt'):
        file_path = os.path.join(folder_path, filename)
        add_channel_classification(file_path)


######################################################################################################################
######################################################################################################################

#  获取远程直播源文件,打开文件并输出临时文件
urls = [
    "https://raw.githubusercontent.com/frxz751113/AAAAA/main/IPTV/汇汇.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/JunTV/refs/heads/main/output/result.m3u",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/咪咕直播"
]
combined_content = ""
for url in urls:
    try:
        r = requests.get(url)
        combined_content += r.text
    except Exception as e:
        print(f"获取 {url} 时发生错误: {e}")

with open('综合源.txt', 'w', encoding='utf-8') as f:
    f.write(combined_content)

#简体转繁体#
#简体转繁体
# 创建一个OpenCC对象,指定转换的规则为繁体字转简体字
converter = OpenCC('t2s.json')#繁转简
#converter = OpenCC('s2t.json')#简转繁
# 打开txt文件
with open('综合源.txt', 'r', encoding='utf-8') as file:
    traditional_text = file.read()
