#!/usr/bin/env python3    # -*- coding: utf-8 -*

"""
main.py 南科大TIS喵课助手

@CreateDate 2021-1-9
@UpdateDate 2022-2-12
"""

import _thread
import requests
from os import path
from re import findall
from json import loads
from colorama import init
from getpass import getpass

head = {
    "user-agent": "Mozilla/5.0",
    "x-requested-with": "XMLHttpRequest"
}


def cas_login(user_name, pwd):
    """ 用于和南科大CAS认证交互，拿到tis的有效cookie
    输入用于CAS登录的用户名密码，输出tis需要的全部cookie内容(返回头Set-Cookie段的route和jsessionid)
    我的requests的session不吃CAS重定向给到的cookie，不知道是代码哪里的问题，所以就手动拿了 """
    token = requests.session()
    print("[\x1b[0;36m!\x1b[0m] " + "测试CAS链接...")
    try:  # Login 服务的CAS链接有时候会变
        login_url = "https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Ftis.sustech.edu.cn%2Fcas"
        req = token.get(login_url)
        assert (req.status_code == 200)
        print("[\x1b[0;32m+\x1b[0m] " + "成功连接到CAS...")
    except:
        print("[\x1b[0;31mx\x1b[0m] " + "不能访问CAS, 请检查您的网络连接状态")
        return "", ""
    print("[\x1b[0;36m!\x1b[0m] " + "登录中...")
    data = {  # execution大概是CAS中前端session id之类的东西
        'username': user_name,
        'password': pwd,
        'execution': str(req.text).split('''name="execution" value="''')[1].split('"')[0],
        '_eventId': 'submit',
    }
    req = token.post(login_url, data=data, allow_redirects=False)
    if "Location" in req.headers.keys():
        print("[\x1b[0;32m+\x1b[0m] " + "登录成功")
    else:
        print("[\x1b[0;31mx\x1b[0m] " + "用户名或密码错误，请检查")
        return "", ""
    req = token.get(req.headers["Location"], allow_redirects=False)
    route_ = findall('route=(.+?);', req.headers["Set-Cookie"])[0]
    jsessionid = findall('JSESSIONID=(.+?);', req.headers["Set-Cookie"])[0]
    return route_, jsessionid


def getinfo(semester_data):
    """ 用于向tis请求当前学期的课程ID，得到的ID将用于选课的请求
    输入当前学期的日期信息，返回的json包括了课程名和内部的ID """
    data = {
        "p_xn": semester_data['p_dqxn'],  # 当前学年
        "p_xq": semester_data['p_dqxq'],  # 当前学期
        "p_xnxq": semester_data['p_dqxnxq'],  # 当前学年学期
        "p_chaxunpylx": 3,
        "mxpylx": 3,
        "p_sfhltsxx": 0,
        "pageNum": 1,
        "pageSize": 2000  # 每学期总共开课在1000左右，所以2000可以包括学期的全部课程
    }
    req = requests.post('https://tis.sustech.edu.cn/Xsxktz/queryRwxxcxList', data=data, headers=head)
    return req.text


def submit(semester_data, course):
    """ 用于向tis发送喵课的请求
    本段函数会在多线程中调用，因为我不知道python神奇的GIL到底会在什么时候干预，所以尽量不用全局变量会共享的变量
    （什么，购物车是怎么回事？那首先排除教务系统是个魔改的电商项目）"""
    data = {
        "p_pylx": 1,
        "p_xktjz": "rwtjzyx",  # 提交至，可选任务，rwtjzgwc提交至购物车，rwtjzyx提交至已选 gwctjzyx购物车提交至已选
        "p_xn": semester_data['p_dqxn'],
        "p_xq": semester_data['p_dqxq'],
        "p_xnxq": semester_data['p_dqxnxq'],
        "p_xkfsdm": "bxxk",  # 补选选课
        "p_id": course,  # 课程id
        "p_sfxsgwckb": 1,  # 固定
    }
    req = requests.post('https://tis.sustech.edu.cn/Xsxk/addGouwuche', data=data, headers=head)
    if "成功" in req.text:
        print("[\x1b[0;34m{}\x1b[0m]".format("=" * 50), flush=True)
        print("[\x1b[0;34m█\x1b[0m]\t\t\t" + loads(req.text)['message'], flush=True)
        print("[\x1b[0;34m{}\x1b[0m]".format("=" * 50), flush=True)
    else:
        print("[\x1b[0;30m-\x1b[0m]\t\t\t" + loads(req.text)['message'], flush=True)


def load_course():
    """ 用于加载本地要喵的课程
    如果存在文件就读文件里的，不存在就手动录入
    有些(我忘了是哪些了)情况会在文件头会有几个不可见字符，但是会被python读进来，所以第一行建议忽略留空"""
    cache_path = "Class.txt"
    classes = []
    if path.exists(cache_path) and path.isfile(cache_path):
        print("[\x1b[0;36m!\x1b[0m] " + "读取规划课表...")
        with open(cache_path, "r", encoding="utf8") as f:
            classes = f.readlines()
        print("[\x1b[0;32m+\x1b[0m] " + "规划课表读取完毕")
    else:
        print("[\x1b[0;33m-\x1b[0m] " + "没有找到规划课表，请手动输入课程信息，输入-1结束录入")
        while True:
            s = input()
            if s == "-1":
                break
            else:
                classes.append(s)
        s = input("[\x1b[0;36m!\x1b[0m] " + "是否保存录入的信息（y/N）？")
        if s == "Y" or s == "y":
            with open(cache_path, "w", encoding="utf8") as f:
                f.write("===本文件是待喵课程的列表，一行输入一个课程名字==请勿删除本行===\n")
                for course in classes:
                    f.write(course + "\n")
                f.close()
    return classes


if __name__ == '__main__':
    init(autoreset=True)  # 某窗口系统的优质终端并不直接支持如下转义彩色字符，所以需要一些库来帮忙
    classList = load_course()  # 读取本地待喵的课程
    # 下面是CAS登录
    route, JSESSIONID = "", ""
    while route == "" or JSESSIONID == "":
        userName = input("请输入您的学号：")  # getpass在PyCharm里不能正常工作，请改为input或写死
        passWord = getpass("请输入CAS密码（密码不显示，输入完按回车即可）：")
        route, JSESSIONID = cas_login(userName, passWord)
        if route == "" or JSESSIONID == "":
            print("[\x1b[0;33m-\x1b[0m] " + "请重试...")
    head['cookie'] = f'route={route}; JSESSIONID={JSESSIONID};'
    # 下面先获取当前的学期
    classData = {}
    print("[\x1b[0;36m!\x1b[0m] " + "从服务器获取当前喵课时间...")
    semester_info = loads(requests.post('https://tis.sustech.edu.cn/Xsxk/queryXkdqXnxq', headers=head).text)
    print("[\x1b[0;32m+\x1b[0m] " + f"当前学期是{semester_info['p_dqxn']}学年第{semester_info['p_dqxq']}学期")
    # 下面获取课程信息
    print("[\x1b[0;36m!\x1b[0m] " + "从服务器下载课程信息...")
    rawClassData = loads(getinfo(semester_info))
    for i in rawClassData['rwList']['list']:
        classData[i['rwmc']] = i['id']
    print("[\x1b[0;32m+\x1b[0m] " + "课程信息读取完毕")
    print("[\x1b[0;34m{}\x1b[0m]".format("=" * 25))
    # 下面分析要喵课程的ID
    postList = []
    for name in classList:
        name = name.strip()
        if name in classData.keys():
            postList.append(classData[name])
            print(name)
    print("[\x1b[0;34m{}\x1b[0m]".format("=" * 25))
    print("[\x1b[0;32m+\x1b[0m] " + "成功读入以上信息")
    # 喵课主逻辑
    while True:
        print("[\x1b[0;32m+\x1b[0m] " + "按一下回车喵三次，多按同时喵多次")
        input()
        for c_id in postList:
            try:
                for _ in range(3):
                    _thread.start_new_thread(submit, (semester_info, c_id))
            except:
                print("线程异常")

"""
# timming is everything!
    import datetime,time
    start = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '12:55', '%Y-%m-%d%H:%M')
    end = datetime.datetime.strptime(str(datetime.datetime.now().date()) + '13:05', '%Y-%m-%d%H:%M')
    while True:
        n_time = datetime.datetime.now()
        if start < n_time < end:
            for c_id in postList:
                try:
                    _thread.start_new_thread(submit, (semester_info, c_id))
                except:
                    pass
            time.sleep(0xdeadbeef)
        time.sleep(0xc0febabe)
"""