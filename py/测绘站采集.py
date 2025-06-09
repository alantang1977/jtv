#本程序主体构造如下
#搜素有效IP并生成文件追加写入到相应列表文件后去重
#检测组播列表所有文件中IP有效性
#合并整理自用直播源，与组播无关
#合并所有组播文件并过滤严重掉帧的视频以保证流畅性
#提取检测后的频道进行分类输出优选组播源
#提取优选组播源中分类追加到自用直播源
#后续整理
#没了！！！！！！！！！！！！
# -*- coding: utf-8 -*-
import os
import time
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import base64
import re
from tqdm import tqdm
from pypinyin import lazy_pinyin
from opencc import OpenCC
from fake_useragent import UserAgent

# 配置参数
DELAY_RANGE = (3, 6)
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

def get_random_header():
    """生成随机请求头"""
    return {
        'User-Agent': UserAgent().random,
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://fofa.info/'
    }

def safe_request(url):
    """带重试机制的请求函数"""
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(*DELAY_RANGE))
            response = requests.get(url, headers=get_random_header(), timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                print(f"遇到反爬机制，等待30秒后重试")
                time.sleep(30)
                continue
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"请求失败（第{attempt+1}次重试）: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise

def validate_video(url, mcast):
    """验证视频流有效性"""
    video_url = f"{url}/rtp/{mcast}"
    print(f"正在验证: {video_url}")
    try:
        response = requests.get(video_url, headers=get_random_header(), timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        content_length = 0
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                content_length += len(chunk)
                if content_length >= 64:
                    break
        return content_length >= 16
    except Exception as e:
        print(f"视频验证异常: {str(e)}")
        return False

def classify_channel(channel_name):
    """频道分类"""
    rules = {
        '央视频道': lambda name: name.startswith('CCTV'),
        '地方卫视': lambda name: any(province in name for province in ['北京', '广东', '江苏', '浙江', '东方', '深圳', '安徽', '河南', '黑龙江', '山东', '天津', '四川', '重庆']),
        '广东频道': lambda name: '广东' in name,
        '港澳台频道': lambda name: any(region in name for region in ['香港', '澳门', '台湾'])
    }
    for cat, rule in rules.items():
        if rule(channel_name):
            return cat
    return '其他频道'

def add_channel_classification(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    classified = {
        '央视频道': [],
        '地方卫视': [],
        '广东频道': [],
        '港澳台频道': [],
        '其他频道': []
    }
    for line in lines:
        parts = line.split(',', 1)
        if len(parts) >= 2:
            channel_name = parts[0].strip()
            category = classify_channel(channel_name)
            classified[category].append(line)
    new_lines = []
    for cat, items in classified.items():
        if items:
            new_lines.append(f'{cat},#genre#\n')
            new_lines.extend(items)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)

def remove_duplicates_keep_order(folder_path):
    """去重且保持顺序"""
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            seen = set()
            unique_lines = []
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line not in seen:
                        unique_lines.append(line)
                        seen.add(line)
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(unique_lines)

def get_ip_key(url):
    start = url.find('://') + 3
    end = url.find('/', start)
    if end == -1:
        end = len(url)
    return url[start:end].strip()

def main():
    # 创建输出目录
    os.makedirs('playlist', exist_ok=True)

    # 获取需要处理的文件列表
    if not os.path.exists('rtp'):
        print('rtp文件夹不存在')
        return
    files = [f.split('.')[0] for f in os.listdir('rtp') if f.endswith('.txt')]
    print(f"待处理频道列表: {files}")

    for filename in files:
        province_isp = filename.split('_')
        if len(province_isp) != 2:
            continue
        province, isp = province_isp
        print(f"\n正在处理: {province}{isp}")
        try:
            with open(f'rtp/{filename}.txt', 'r', encoding='utf-8') as f:
                mcast = f.readline().split('rtp://')[1].split()[0].strip()
        except Exception as e:
            print(f"文件读取失败: {str(e)}")
            continue

        search_txt = f'"udpxy" && country="CN" && region="{province}"'
        encoded_query = base64.b64encode(search_txt.encode()).decode()
        search_url = f'https://fofa.info/result?qbase64={encoded_query}'
        try:
            html = safe_request(search_url)
        except Exception as e:
            print(f"搜索失败: {str(e)}")
            continue

        soup = BeautifulSoup(html, 'html.parser')
        pattern = re.compile(r"http://(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|\w[\w.-]*\w):\d+")
        found_urls = set(pattern.findall(html))
        print(f"找到{len(found_urls)}个有效地址")

        valid_urls = [url for url in found_urls if validate_video(url, mcast)]
        print(f"验证通过{len(valid_urls)}个有效地址")

        if valid_urls:
            output_file = f'playlist/{province}{isp}.txt'
            with open(f'rtp/{filename}.txt', 'r', encoding='utf-8') as src, open(output_file, 'a', encoding='utf-8') as dst:
                original_content = src.read()
                for url in valid_urls:
                    modified = original_content.replace('rtp://', f'{url}/rtp/')
                    dst.write(modified + '\n')
            print(f"已生成播放列表: {output_file}")

    print('对playlist文件夹里面的所有txt文件进行去重处理')
    remove_duplicates_keep_order('playlist')
    print('文件去重完成！')

    # IP 有效性检测
    detected_ips = {}
    for filename in os.listdir('playlist'):
        if filename.endswith('.txt'):
            file_path = os.path.join('playlist', filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            with open(file_path, 'w', encoding='utf-8') as output_file:
                for line in tqdm(lines, total=len(lines), desc=f"Processing {filename}"):
                    parts = line.split(',', 1)
                    if len(parts) >= 2:
                        channel_name, url = parts
                        channel_name = channel_name.strip()
                        url = url.strip()
                        ip_key = get_ip_key(url)
                        if ip_key in detected_ips:
                            if detected_ips[ip_key]['status'] == 'ok':
                                output_file.write(line)
                            continue
                        success = False
                        start_time = time.time()
                        try:
                            with requests.get(url, stream=True, timeout=8) as r:
                                r.raise_for_status()
                                downloaded = 0
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        downloaded += len(chunk)
                                        if downloaded >= 1024 * 1024:
                                            success = True
                                            break
                                    if time.time() - start_time > 8:
                                        break
                        except Exception:
                            pass
                        detected_ips[ip_key] = {'status': 'ok' if success else 'fail'}
                        if success:
                            output_file.write(line)
    for ip_key, result in detected_ips.items():
        print(f"IP Key: {ip_key}, Status: {result['status']}")

    # 频道分类
    for filename in os.listdir('playlist'):
        if filename.endswith('.txt'):
            file_path = os.path.join('playlist', filename)
            add_channel_classification(file_path)

if __name__ == '__main__':
    main()
