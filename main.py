
import json
import time
import argparse
import os
import logging
from requests import get, post
import datetime
from utils import reserve, get_user_credentials, get_app_credentials


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.datetime.fromtimestamp(record.created)
        ct = ct + datetime.timedelta(hours=8)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return s


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = CustomFormatter(fmt='%(asctime)s  - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_current_time(action): return time.strftime("%H:%M:%S", time.localtime(time.time() + 8*3600)
                                                   ) if action else time.strftime("%H:%M:%S", time.localtime(time.time()))


def get_current_dayofweek(action): return time.strftime("%A", time.localtime(time.time() + 8*3600)
                                                        ) if action else time.strftime("%A", time.localtime(time.time()))


SLEEPTIME = 0
ENDTIME = "20:01:00"
ENABLE_SLIDER = False
MAX_ATTEMPT = 10
RESERVE_NEXT_DAY = True


def get_access_token(action=True):
    app_id, app_secret, wxuserid, template_id = get_app_credentials(action)
    post_url = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}"
                .format(app_id, app_secret))
    access_token = get(post_url).json()['access_token']
    return access_token, wxuserid, template_id


def send_message(wxuid, access_token, template_id, success_list, seatid_choose):
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
    data = {
        "touser": wxuid,
        "template_id": template_id,
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": f"{datetime.date.today() + datetime.timedelta(days=1)}",
            },
            "seatID": {
                "value": f"{seatid_choose}",
            },
            "reserve_1": {
                "value": "失败，请及时检查原因！" if not success_list[0] else "预约成功！",
            },
            "reserve_2": {
                "value": "失败，请及时检查原因！" if not success_list[1] else "预约成功！",
            },
            "reserve_3": {
                "value": "失败，请及时检查原因！" if not success_list[2] else "预约成功！",
            },
            "reserve_4": {
                "value": "失败，请及时检查原因！" if not success_list[3] else "预约成功！",
            }
        }
    }
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    response = post(url, headers=headers, json=data)
    return response


def login_and_reserve(users, usernames, passwords, action, success_list=None):
    logger.info(
        f"Global settings: \nSLEEPTIME: {SLEEPTIME}\nENDTIME: {ENDTIME}\nENABLE_SLIDER: {ENABLE_SLIDER}\nRESERVE_NEXT_DAY: {RESERVE_NEXT_DAY}")
    if action and len(usernames.split(",")) != len(users):
        raise Exception("user number should match the number of config")
    if success_list is None:
        success_list = [False] * len(users)
    current_dayofweek = get_current_dayofweek(action)
    username, password, _, _, _, _ = users[0].values()

    if action:
        username, password = usernames.split(',')[0], passwords.split(',')[0]

    s = reserve(sleep_time=SLEEPTIME, max_attempt=MAX_ATTEMPT,
                enable_slider=ENABLE_SLIDER, reserve_next_day=RESERVE_NEXT_DAY)
    s.get_login_status()
    s.login(username, password)
    s.requests.headers.update({'Host': 'office.chaoxing.com'})

    for index, user in enumerate(users):
        _, _, times, roomid, seatid, daysofweek = user.values()
        seatid_choose = seatid
        if (current_dayofweek not in daysofweek):
            logger.info("Today not set to reserve")
            continue
        if not success_list[index]:
            logger.info(f"------ 第{index+1}次预约 -- {times} -- {seatid} TRY ------")
            suc = s.submit(times, roomid, seatid, action)
            s.max_attempt = MAX_ATTEMPT
            success_list[index] = suc
    return success_list, seatid_choose


def main(users, action=False):
    logger.info(f"当前系统时间为：{get_current_time(action=False)}")
    while get_current_time(action) < "19:59:50":
        if get_current_time(action) < "19:59:40":
            logger.info(f"正在等待执行，当前时间为：{get_current_time(action)}")
            time.sleep(5)
        elif "19:59:40" <= get_current_time(action) < "19:59:50":
            logger.info(f"正在等待执行，当前时间为：{get_current_time(action)}")
            time.sleep(2)
    if get_current_time(action) >= ENDTIME:
        logger.info(f"---停止执行---\n超过执行时间，当前时间为：{get_current_time(action)}")
        return 0
    logger.info(f"start time {get_current_time(action)}, action {'on' if action else 'off'}")
    attempt_times = 0
    usernames, passwords = None, None
    if action:
        usernames, passwords = get_user_credentials(action)
    success_list = None
    current_dayofweek = get_current_dayofweek(action)
    today_reservation_num = sum(1 for d in users if current_dayofweek in d.get('daysofweek'))
    current_time = get_current_time(action)
    while current_time < ENDTIME:
        attempt_times += 1
        success_list, seatid_choose = login_and_reserve(users, usernames, passwords, action, success_list)
        print(f"attempt time {attempt_times}, time now {current_time}, success list {success_list}")
        current_time = get_current_time(action)
        if sum(success_list) == today_reservation_num:
            print(f"reserved successfully!")
            accessToken, wxuserid, template_id = get_access_token()
            wxuid = wxuserid.split(',')
            tpl_id = template_id.split(',')
            for i in range(len(wxuid)):
                send_message(wxuid[i], accessToken, tpl_id[0], success_list, seatid_choose)
            return 0
    accessToken, wxuserid, template_id = get_access_token()
    tpl_id = template_id.split(',')
    wxuid = wxuserid.split(',')
    for i in range(len(wxuid)):
        send_message(wxuid[i], accessToken, tpl_id[0], success_list, seatid_choose)
    return 0


def debug(users, action=False):
    logger.info(
        f"Global settings: \nSLEEPTIME: {SLEEPTIME}\nENDTIME: {ENDTIME}\nENABLE_SLIDER: {ENABLE_SLIDER}\nRESERVE_NEXT_DAY: {RESERVE_NEXT_DAY}")
    suc = False
    logger.info(f" Debug Mode start! , action {'on' if action else 'off'}")
    if action:
        usernames, passwords = get_user_credentials(action)
    current_dayofweek = get_current_dayofweek(action)
    for index, user in enumerate(users):
        username, password, times, roomid, seatid, daysofweek = user.values()
        if type(seatid) == str:
            seatid = [seatid]
        if action:
            username, password = usernames.split(',')[index], passwords.split(',')[index]
        if (current_dayofweek not in daysofweek):
            logger.info("Today not set to reserve")
            continue
        logger.info(f"------ 第{index+1}次预约 -- {times} -- {seatid} TRY ------")
        s = reserve(sleep_time=SLEEPTIME,  max_attempt=MAX_ATTEMPT, enable_slider=ENABLE_SLIDER)
        s.get_login_status()
        s.login(username, password)
        s.requests.headers.update({'Host': 'office.chaoxing.com'})
        suc = s.submit(times, roomid, seatid, action)
        if suc:
            return


def get_roomid(args1, args2):
    username = input("username: ")
    password = input("password: ")
    s = reserve(sleep_time=SLEEPTIME, max_attempt=MAX_ATTEMPT, enable_slider=ENABLE_SLIDER, reserve_next_day=RESERVE_NEXT_DAY)
    s.get_login_status()
    s.login(username=username, password=password)
    s.requests.headers.update({'Host': 'office.chaoxing.com'})
    encode = input("deptldEnc: ")
    s.roomid(encode)


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    parser = argparse.ArgumentParser(prog='Chao Xing seat auto reserve')
    parser.add_argument('-u', '--user', default=config_path, help='user config file')
    parser.add_argument('-m', '--method', default="reserve", choices=["reserve", "debug", "room"], help='for debug')
    parser.add_argument('-a', '--action', action="store_true", help='use --action to enable in github action')
    args = parser.parse_args()
    func_dict = {"reserve": main, "debug": debug, "room": get_roomid}
    with open(args.user, "r+") as data:
        usersdata = json.load(data)["reserve"]
    func_dict[args.method](usersdata, args.action)
