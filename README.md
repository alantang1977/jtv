<div align="center">
  <img src="https://raw.githubusercontent.com/alantang1977/X/main/Pictures/333.png" alt="logo"/>
  <h1 align="center">jtv</h1>
</div>

<div align="center">该仓库 jtv 是一个用于整理和生成网络直播频道列表的项目，主要包含频道数据解析、匹配及自动化更新功能。</div>
<br>
<p align="center">
  <a href="https://github.com/alantang1977/jtv/releases">
    <img src="https://img.shields.io/github/v/release/alantang1977/jtv" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-%20%3D%203.13-47c219" />
  </a>
  <a href="https://github.com/alantang1977/jtv/releases">
    <img src="https://img.shields.io/github/downloads/alantang1977/jtv/total" />
  </a>
  <a href="https://github.com/alantang1977/jtv">
    <img src="https://img.shields.io/github/stars/alantang1977/jtv" />
  </a>
  <a href="https://github.com/alantang1977/jtv/fork">
    <img src="https://img.shields.io/github/forks/alantang1977/jtv" />
  </a>
</p>



* https://dash.cloudflare.com/sign-up
* 云部署需要注意
***
git仓库部署后直接分配域名后面加文件名即可访问
***
如要自定义域名，域名格式必须为 自定义别名.x.x.x
***
自己域名站添加CNAME记录时 名称：自定义别名 数据：x.x.x. 最后必须加上. 否则CNAME配置失败
***
# 安装运行库清华源附加代码
 *python.exe -m pip install --upgrade pip
          pip install selenium requests futures eventlet opencv-python Beautifulsoup4 translate termcolor func_timeout replace input opencc pypinyin pytz tqdm -i https://pypi.tuna.tsinghua.edu.cn/simple -i https://pypi.tuna.tsinghua.edu.cn/simple

***
 # py打包exe代码
* pyinstaller -F -c *.py   无图标
***
* pyinstaller -F -c -i *.ico *.py   带图标
* 
