import requests
import time
import datetime
from requests import get, post
from utils import get_user_credentials, get_app_credentials


def get_current_time(): return time.strftime("%H:%M:%S", time.localtime(time.time() + 8*3600))


def get_access_token(action=True):
    app_id, app_secret, wxuserid, template_id = get_app_credentials(action)
    post_url = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}"
                .format(app_id, app_secret))
    access_token = get(post_url).json()['access_token']
    return access_token, wxuserid, template_id


def send_message(wxuid, access_token, template_id, wxmessage):
    status = wxmessage.split('：')[-1]
    schloc = wxmessage.split('：')[0][:9]
    seatloc = wxmessage.split('：')[0][9:]
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
    data = {
        "touser": wxuid,
        "template_id": template_id,
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": f"{time.strftime('%Y-%m-%d', time.localtime(time.time() + 8*3600))}",
            },
            "time": {
                "value": f"{time.strftime('%H:%M:%S', time.localtime(time.time() + 8*3600))}",
            },
            "schloc": {
                "value": f"{schloc}",
            },
            "seatloc": {
                "value": f"{seatloc}座位",
            },
            "status": {
                "value": f"{status}",
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


class Library:
    def __init__(self, phone, password):
        self.today = time.strftime("%Y-%m-%d", time.localtime(time.time() + 8*3600))
        self.tomorrow = time.strftime("%Y-%m-%d", time.localtime(time.time() + 8*3600 + 24*3600))
        self.acc = phone
        self.pwd = password
        self.deptIdEnc = None
        self.deptId = None
        self.status = {
            '0': '待履约',
            '1': '学习中',
            '2': '已履约',
            '3': '暂离中',
            '5': '被监督中',
            '7': '已取消',
        }
        self.room = None
        self.room_id_capacity = {}
        self.room_id_name = {}
        self.all_seat = []
        self.emptyInfo = []
        self.session = requests.session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 '
                          '(KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
        }
        self.login()

    @classmethod
    def t_time(cls, timestamp):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(str(timestamp)[0:10])))
    
    @classmethod
    def t_time_hms(cls, timestamp):
        return time.strftime("%H:%M:%S", time.localtime(int(str(timestamp)[0:10])))

    @classmethod
    def get_date(cls):
        return time.strftime('%a %b %d %Y %I:%M:%S GMT+0800 ', time.localtime(time.time())) + '(中国标准时间)'

    @classmethod
    def t_second(cls, timestamp):
        if timestamp:
            m, s = divmod(int(str(timestamp)[0:-3]), 60)
            h, m = divmod(m, 60)
            if m:
                if h:
                    return str(h) + "时" + str(m) + "分" + str(s) + "秒"
                return str(m) + "分" + str(s) + "秒"
            return str(s) + "秒"
        return "0秒"

    def login(self):
        c_url = 'https://passport2.chaoxing.com/mlogin?' \
                'loginType=1&' \
                'newversion=true&fid=&' \
                'refer=http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Findex'
        self.session.get(c_url).cookies.get_dict()
        data = {
            'fid': '-1',
            'uname': self.acc,
            'password': self.pwd,
            'refer': 'http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Findex',
            't': 'true',
            'forbidotherlogin': 0,
            'validate': 0,
            'doubleFactorLogin': 0,
            'independentId': 0,
        }
        self.session.post('https://passport2.chaoxing.com/fanyalogin', data=data)
        s_url = 'https://office.chaoxing.com/front/third/apps/seat/index'
        self.session.get(s_url)

    # 历史座位预定情况
    def get_seat_reservation_info(self):
        status_0 = []
        status_1 = []
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/reservelist?'
                                        'indexId=0&'
                                        'pageSize=100&'
                                        'type=-1').json()['data']['reserveList']
        for index in response:
            if index['type'] == -1:
                # print(index['seatNum'], index['id'], index['firstLevelName'], index['secondLevelName'],
                #       index['thirdLevelName'], self.t_time(index['startTime']), self.t_time(index['endTime']),
                #       self.t_second(index['learnDuration']), self.status[str(index['status'])])
                if index['status'] == 0 : # 待履约
                    status_0.append(index)
                elif index['status'] == 1 : # 学习中
                    status_1.append(index)
                
                return status_0, status_1
            else:
                # 违约记录
                # print(index['seatNum'], index['id'], index['firstLevelName'], index['secondLevelName'],
                #       index['thirdLevelName'], self.t_time(index['startTime']), self.t_time(index['endTime']),
                #       self.t_second(index['learnDuration']), '违约')
                return [], []

    # 签到
    def sign(self):
        info = self.get_my_seat_id()
        data_i = []
        for index in info:
            if index['status'] == 1:
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
                return "已经签过到了，快学习吧~"
            if index['status'] == 0 or index['status'] == 3 or index['status'] == 5:
                data_i.append(index)
                continue
        location = None
        id = None
        seatnum = None
        roomid = None
        if data_i:
            if len(data_i) >= 2:
                index = data_i[0]
                id = index['id']
                seatnum = index['seatNum']
                roomid = index['roomId']
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
            else:
                id = data_i[-1]['id']
                seatnum = data_i[-1]['seatNum']
                roomid = data_i[-1]['roomId']
                location = data_i[-1]['firstLevelName'] + data_i[-1]['secondLevelName'] + \
                    data_i[-1]['thirdLevelName'] + data_i[-1]['seatNum']

            sign_data = {
                'id': id,
                'seatNum': seatnum,
                'roomId': roomid
            }
            response = self.session.get(
                url='https://office.chaoxing.com/data/apps/seat/sign', params=sign_data)
            # print(response.text)
            if response.json()['success']:
                # print(self.acc, '签到', '成功', location)
                wxmessage = "{}：签到成功".format(location)
                accessToken, wxuserid, template_id = get_access_token()
                wxuid = wxuserid.split(',')
                tpl_id = template_id.split(',')
                for i in range(len(wxuid)):
                    send_message(wxuid[i], accessToken, tpl_id[1], wxmessage)
                return "{}位置：签到成功".format(location[9:])
            return "{}位置：{}".format(location[9:], response.json()['msg'])
        return "没有座位可以签到"

    # 暂离
    def leave(self):
        info = self.get_my_seat_id()
        for index in info:
            if index['status'] == 1:
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
                response = self.session.get(
                    url='https://office.chaoxing.com/data/apps/seat/leave?id={}'.format(index['id']))
                if response.json()['success']:
                    return "{}：暂离成功".format(location)
                return "{}：{}".format(location, response.json()['msg'])
        return "当前没有座位可暂离"

    # 退座
    def signback(self):
        info = self.get_my_seat_id()
        for index in info:
            if index['status'] == 1 or index['status'] == 3 or index['status'] == 5:
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
                response = self.session.get(
                    url='https://office.chaoxing.com/data/apps/seat/signback?id={}'.format(index['id']))
                if response.json()['success']:
                    wxmessage = "{}：退出成功".format(location)
                    accessToken, wxuserid, template_id = get_access_token()
                    wxuid = wxuserid.split(',')
                    tpl_id = template_id.split(',')
                    for i in range(len(wxuid)):
                        send_message(wxuid[i], accessToken, tpl_id[1], wxmessage)
                    return "{}位置：退出成功".format(location[9:])
                return "{}位置：{}".format(location[9:], response.json()['msg'])
        return "当前没有座位可退"

    # 取消
    def cancel(self):
        info = self.get_my_seat_id()
        for index in info:
            if index['status'] == 0 or index['status'] == 3 or index['status'] == 5:
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
                response = self.session.get(
                    url='https://office.chaoxing.com/data/apps/seat/cancel?id={}'.format(index['id']))
                if response.json()['success']:
                    return "{}：座位已取消".format(location[9:])
                return "{}：{}".format(location[9:], response.json()['msg'])
        return "当前没有座位可取消"

    # 获取最近预约的座位ID
    def get_my_seat_id(self):
        response = self.session.get(url='https://office.chaoxing.com/data/apps/seat/reservelist?'
                                        'indexId=0&'
                                        'pageSize=100&'
                                        'type=-1').json()['data']['reserveList']
        result = []
        for index in response:
            if index['today'] == self.today or index['today'] == self.tomorrow:
                result.append(index)
        return result


if __name__ == '__main__':
    usernames, passwords = get_user_credentials(action=True)
    username, password = usernames.split(',')[0], passwords.split(',')[0]

    lib = Library(username, password)
    status_0, status_1 = lib.get_seat_reservation_info()
    current_time = get_current_time()

    if '07:45:00' <= current_time <= '08:15:00':
        print(lib.sign())
    elif '19:45:00' <= current_time <= '19:55:00':
        print(lib.signback())
    else:
        print("Warning: 非正常预约时间进行操作.")
        if len(status_0) + len(status_1) > 1:
            print("Warning: 存在多个预定采用测试流程.")
            study_endtime = lib.t_time_hms(status_1[0]['endTime'])
            if '11:55:00' <= study_endtime <= '12:05:00' or '15:55:00' <= study_endtime <= '16:05:00':
                print(lib.signback())
                print(lib.sign())
        else:
            print("Success: 已不存在多个预定.")