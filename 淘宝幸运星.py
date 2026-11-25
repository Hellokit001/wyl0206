# 当前脚本来自于 http://script.345yun.cn 脚本库下载！
# 当前脚本来自于 http://2.345yun.cn 脚本库下载！
# 当前脚本来自于 http://2.345yun.cc 脚本库下载！
# 脚本库官方QQ群1群: 429274456
# 脚本库官方QQ群2群: 1077801222
# 脚本库官方QQ群3群: 433030897
# 脚本库中的所有脚本文件均来自热心网友上传和互联网收集。
# 脚本库仅提供文件上传和下载服务，不提供脚本文件的审核。
# 您在使用脚本库下载的脚本时自行检查判断风险。
# 所涉及到的 账号安全、数据泄露、设备故障、软件违规封禁、财产损失等问题及法律风险，与脚本库无关！均由开发者、上传者、使用者自行承担。

# # 当前脚本来自于 http://script.nnioj.com/ 脚本库下载！
# # 当前脚本来自于 http://script.nnioj.com/ 脚本库下载！
# # 当前脚本来自于 http://script.nnioj.com/ 脚本库下载！
# # 脚本库中的所有脚本文件均来自热心网友上传和互联网收集。
# # 脚本库仅提供文件上传和下载服务，不提供脚本文件的审核。
# # 您在使用脚本库下载的脚本时自行检查判断风险。
# # 所涉及到的 账号安全、数据泄露、设备故障、软件违规封禁、财产损失等问题及法律风险，与脚本库无关！均由开发者、上传者、使用者自行承担。

"""
cron: 30 8 * * *
new Env('南昌工会');

南昌工会自动签到任务
每日自动完成: 签到 / 浏览 / 点赞 / 评论 / 视频学习 / 答题

环境变量:
  NCGH_TOKENS  账号 Authorization (eyJ... 开头), 多账号用 & 或换行分隔
"""

import os
import sys
import json
import time
import base64
import random
import requests
import urllib3

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
except ImportError:
    print("缺少依赖, 请执行: pip install pycryptodome requests")
    sys.exit(1)

urllib3.disable_warnings()

# ============== 配置 ==============
BASE_URL = "https://ncgh.org.cn/nczhgh.interface"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
      "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI "
      "MiniProgramEnv/Windows WindowsWechat/WMPF")

RSA_PUB = ("MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC0lvxLoTo4OnnHldcIon"
           "uq/W7ywppxTqsK4IxHcPvSNd7U3vC7l8IHM5dNUElN31X6vWcxKIUmgVW9"
           "qZfF9AdSEXzoN5uQwUNsP+8V5NR745N7Cgb+x/+CSYs95/JVqp3EWF1Nyq"
           "q/YZJeAnrU7kHqsYqdOjL5oC/LozDMiQil0wIDAQAB")

TOPIC_IDS = [
    "2042499665899081730",
    "2044957160479444994",
    "2067055408752910337",
]

COMMENT_LIST = [
    "支持工会工作,加油!",
    "学习到了,很有收获",
    "感谢工会组织的活动",
    "内容很实用,收藏了",
    "转发给身边的朋友",
]

VIDEO_CATEGORIES = [175, 176, 177, 182, 184, 185]
NEWS_CATEGORY = 6

TASK_LIMIT = 3
WATCH_TASK_LIMIT = 45
SLEEP_BETWEEN = 1.0
SLEEP_AFTER_TASK = 0.5
SLEEP_WATCH = 1.0


# ============== 工具函数 ==============
_RSA_KEY = None


def get_rsa_key():
    global _RSA_KEY
    if _RSA_KEY is None:
        pem = "-----BEGIN PUBLIC KEY-----\n" + RSA_PUB + "\n-----END PUBLIC KEY-----"
        _RSA_KEY = RSA.importKey(pem)
    return _RSA_KEY


def rsa_encrypt(plain):
    cipher = PKCS1_v1_5.new(get_rsa_key())
    return base64.b64encode(cipher.encrypt(plain.encode("utf-8"))).decode()


def rsa_encrypt_long(plain):
    cipher = PKCS1_v1_5.new(get_rsa_key())
    data = plain.encode("utf-8")
    enc = b""
    for i in range(0, len(data), 117):
        enc += cipher.encrypt(data[i:i + 117])
    return base64.b64encode(enc).decode()


def make_token(jwt):
    plain = json.dumps({"token": jwt, "timestamp": int(time.time() * 1000)},
                       separators=(",", ":"))
    return rsa_encrypt_long(plain)


def get_accounts():
    raw = os.environ.get("NCGH_TOKENS", "").strip()
    if not raw:
        print("未配置环境变量 NCGH_TOKENS")
        print("请在青龙面板 -> 环境变量 中添加:")
        print("  名称: NCGH_TOKENS")
        print("  值:   账号的 Authorization (多账号用 & 或换行分隔)")
        return []
    tokens = [t.strip() for t in raw.replace("\n", "&").split("&") if t.strip()]
    accounts = []
    for i, t in enumerate(tokens, 1):
        accounts.append({"name": f"账号{i}", "authorization": t})
    return accounts


# ============== 主类 ==============
class NCGH:
    TASK_NAMES = {"view": "浏览", "watch": "视频", "like": "点赞", "comment": "评论"}

    def __init__(self, account):
        self.name = account["name"]
        self.jwt = account["authorization"]
        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update({
            "Authorization": self.jwt,
            "token": make_token(self.jwt),
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Referer": "https://servicewechat.com/wxd4304a23e648be81/189/page-frame.html",
        })
        self.user_info = None
        self.gain = 0

    def _refresh(self):
        self.s.headers["token"] = make_token(self.jwt)

    def _get(self, path, params=None):
        self._refresh()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for i in range(3):
            try:
                return self.s.get(url, params=params, timeout=20).json()
            except Exception as e:
                if i == 2:
                    return {"code": -1, "msg": str(e)}
                time.sleep(1)

    def _post(self, path, body=None):
        self._refresh()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        for i in range(3):
            try:
                return self.s.post(url, json=body, timeout=20).json()
            except Exception as e:
                if i == 2:
                    return {"code": -1, "msg": str(e)}
                time.sleep(1)

    def log(self, msg):
        print(f"[{self.name}] {msg}")

    @staticmethod
    def _ok(resp):
        if resp.get("code") != 200:
            return False, 0
        d = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        if d.get("changed") == 1:
            return True, d.get("points", 0) or 0
        return False, 0

    @staticmethod
    def _is_correct(ans):
        v = ans.get("check")
        return v is True or str(v).lower() == "true"

    # --------- 信息查询 ---------
    def get_user_info(self):
        d = self._get("pc/userInfoManage/getInfo")
        if d.get("code") != 200:
            self.log(f"获取用户信息失败: {d.get('msg')}")
            return None
        self.user_info = d["data"]["sysUser"]
        return self.user_info

    def get_points(self):
        d = self._get("shop/log/my/points")
        if d.get("code") == 200:
            return d["data"].get("points")
        return None

    # --------- 签到 ---------
    def sign_in(self):
        d = self._get("points/signIn/")
        code = d.get("code")
        msg = d.get("msg", "")
        if code == 200 and ("成功" in msg or "打卡" in msg):
            self.log(f"签到成功: {msg}")
        elif code == 500 and ("已经" in msg or "打过卡" in msg):
            self.log("今日已签到")
        else:
            self.log(f"签到异常: code={code} msg={msg}")

    # --------- 任务进度 ---------
    def get_task_status(self):
        result = {}
        for t in ["view", "watch", "like", "comment"]:
            d = self._get(f"points/task/{t}/count")
            if d.get("code") == 200:
                result[t] = d["data"]
        return result

    # --------- 文章 ---------
    def get_articles(self, cat=None, size=10):
        params = {"pageNum": 1, "pageSize": size, "orderBy": "created"}
        if cat:
            params["categoryId"] = cat
        d = self._get("api/cms/article/list", params)
        if d.get("code") == 200 and d.get("data"):
            return d["data"].get("list", [])
        return []

    def get_videos(self, size=100):
        all_v, seen = [], set()
        for cat in VIDEO_CATEGORIES:
            for v in self.get_articles(cat=cat, size=size):
                if v["id"] not in seen:
                    seen.add(v["id"])
                    all_v.append(v)
            if len(all_v) >= WATCH_TASK_LIMIT:
                break
        return all_v

    # --------- 任务执行 ---------
    def do_view(self, arts, tasks):
        done = (tasks.get("view") or {}).get("count", 0) or 0
        need = max(0, TASK_LIMIT - done)
        if need <= 0:
            self.log(f"浏览任务 {done}/{TASK_LIMIT} 已完成")
            return
        self.log(f"开始浏览任务 ({need} 次)")
        ok = 0
        for a in arts:
            if ok >= need:
                break
            d = self._get(f"points/task/view/{a['id']}")
            success, pts = self._ok(d)
            if success:
                ok += 1
                self.gain += pts
                self.log(f"  浏览 +{pts}")
            time.sleep(SLEEP_AFTER_TASK)

    def do_like(self, arts, tasks):
        done = (tasks.get("like") or {}).get("count", 0) or 0
        need = max(0, TASK_LIMIT - done)
        if need <= 0:
            self.log(f"点赞任务 {done}/{TASK_LIMIT} 已完成")
            return
        self.log(f"开始点赞任务 ({need} 次)")
        ok = 0
        for a in arts:
            if ok >= need:
                break
            d = self._get("points/task/like", {"articleId": a["id"], "status": "true"})
            success, pts = self._ok(d)
            if success:
                ok += 1
                self.gain += pts
                self.log(f"  点赞 +{pts}")
            time.sleep(SLEEP_AFTER_TASK)

    def do_comment(self, arts, tasks):
        done = (tasks.get("comment") or {}).get("count", 0) or 0
        need = max(0, TASK_LIMIT - done)
        if need <= 0:
            self.log(f"评论任务 {done}/{TASK_LIMIT} 已完成")
            return
        self.log(f"开始评论任务 ({need} 次)")
        ok = 0
        for a in arts:
            if ok >= need:
                break
            content = random.choice(COMMENT_LIST)
            d = self._get("points/task/comment", {
                "articleId": a["id"], "pid": "", "content": content,
            })
            success, pts = self._ok(d)
            if success:
                ok += 1
                self.gain += pts
                self.log(f"  评论 +{pts}")
            time.sleep(SLEEP_AFTER_TASK)

    def do_watch(self, videos, tasks):
        done = (tasks.get("watch") or {}).get("count", 0) or 0
        need = max(0, WATCH_TASK_LIMIT - done)
        if need <= 0:
            self.log(f"视频任务 {done}/{WATCH_TASK_LIMIT} 已完成")
            return
        if not videos:
            self.log("无可用视频, 跳过视频任务")
            return
        self.log(f"开始视频任务 ({need} 次, 可用视频 {len(videos)} 个)")
        ok = 0
        fail = 0
        for v in videos:
            if ok >= need:
                break
            d = self._get("points/task/watch/video", {
                "id": rsa_encrypt(v["id"]),
                "points": rsa_encrypt("1"),
            })
            success, pts = self._ok(d)
            if success:
                ok += 1
                fail = 0
                self.gain += pts
                if ok % 10 == 0:
                    self.log(f"  视频进度 {ok}/{need}")
            else:
                fail += 1
                if fail >= 3:
                    self.log(f"  连续失败, 停止 (已完成 {ok}/{need})")
                    break
            if ok < need:
                time.sleep(SLEEP_WATCH)
        self.log(f"视频任务完成 {ok}/{need}")

    # --------- 答题 ---------
    def do_answer(self, topic_id):
        if not self.user_info:
            return
        phone = self.user_info["userName"]
        open_id = self.user_info.get("openId", "")
        self._post("knowledge/user/info", {
            "phone": phone, "userName": phone, "topicId": topic_id,
        })
        time.sleep(SLEEP_BETWEEN)
        cnt = self._get("knowledge/user/info/answer/count", {"topicId": topic_id})
        if cnt.get("code") != 200:
            self.log(f"题库 {topic_id} 查询失败")
            return
        answered = cnt.get("data") or 0
        if answered >= 1:
            self.log(f"题库 {topic_id} 今日已答")
            return
        qs = self._get("knowledge/question/createQuestion", {"topicId": topic_id})
        if qs.get("code") != 200:
            self.log(f"题库 {topic_id} 获取题目失败")
            return
        questions = qs["data"] or []
        if not questions:
            self.log(f"题库 {topic_id} 无题目")
            return
        self.log(f"题库 {topic_id} 共 {len(questions)} 题, 开始答题")
        correct = 0
        for idx, q in enumerate(questions, 1):
            answer_list = []
            for ans in q["answerList"]:
                is_correct = self._is_correct(ans)
                answer_list.append({
                    "value": ans["value"],
                    "text": ans.get("text", ""),
                    "check": ans.get("check", ""),
                    "userCheck": True if is_correct else "",
                    "isOn": False,
                    "errorStatus": False,
                    "correctStatus": True if is_correct else False,
                })
            dto = {
                "answerList": answer_list,
                "type": q.get("type", 2),
                "id": q["id"],
                "correct": 1 if any(self._is_correct(a) for a in q["answerList"]) else 0,
                "answerTime": 6,
            }
            resp = self._post("api/knowledge/question/submit", {
                "dto": [dto],
                "openId": "",
                "topicId": topic_id,
                "userOpenId": open_id,
            })
            data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
            if data.get("failCount", 1) == 0:
                correct += 1
            time.sleep(SLEEP_BETWEEN)
        self._get("knowledge/question/updateAnsweredLog", {"topicId": topic_id})
        self.log(f"题库 {topic_id} 完成: {correct}/{len(questions)} 答对")

    # --------- 主流程 ---------
    def run(self):
        self.log("=" * 50)
        info = self.get_user_info()
        if not info:
            self.log("账号可能已失效, 请检查 Authorization")
            return False
        self.log(f"用户: {info.get('userName')} 积分: {info.get('points', 0)}")
        before = self.get_points()
        self.log(f"当前积分: {before}")
        time.sleep(SLEEP_BETWEEN)

        self.sign_in()
        time.sleep(SLEEP_BETWEEN)

        self.log("-" * 40)
        tasks = self.get_task_status()
        for k, v in tasks.items():
            c = v.get("count", 0) or 0
            limit = WATCH_TASK_LIMIT if k == "watch" else TASK_LIMIT
            self.log(f"  {self.TASK_NAMES.get(k, k)}: {c}/{limit}")

        self.log("-" * 40)
        news = self.get_articles(cat=NEWS_CATEGORY, size=10)
        if news:
            self.do_view(news, tasks)
            time.sleep(SLEEP_BETWEEN)
            self.do_like(news, tasks)
            time.sleep(SLEEP_BETWEEN)
            self.do_comment(news, tasks)
            time.sleep(SLEEP_BETWEEN)
        else:
            self.log("获取文章失败")

        self.log("-" * 40)
        videos = self.get_videos()
        if videos:
            self.do_watch(videos, tasks)
            time.sleep(SLEEP_BETWEEN)
        else:
            self.log("获取视频失败")

        self.log("-" * 40)
        self.log("开始答题任务")
        for tid in TOPIC_IDS:
            self.do_answer(tid)
            time.sleep(SLEEP_BETWEEN)

        after = self.get_points()
        diff = (after or 0) - (before or 0)
        self.log("-" * 40)
        self.log(f"任务完成: 积分 {before} -> {after} ({diff:+d})")
        self.log("=" * 50)
        return True


def main():
    accounts = get_accounts()
    if not accounts:
        return
    print(f"共 {len(accounts)} 个账号\n")
    for acc in accounts:
        try:
            NCGH(acc).run()
        except Exception as e:
            print(f"[{acc['name']}] 执行出错: {e}")
        print()


if __name__ == "__main__":
    main()


# 当前脚本来自于 http://script.345yun.cn 脚本库下载！
# 当前脚本来自于 http://2.345yun.cn 脚本库下载！
# 当前脚本来自于 http://2.345yun.cc 脚本库下载！
# 脚本库官方QQ群1群: 429274456
# 脚本库官方QQ群2群: 1077801222
# 脚本库官方QQ群3群: 433030897
# 脚本库中的所有脚本文件均来自热心网友上传和互联网收集。
# 脚本库仅提供文件上传和下载服务，不提供脚本文件的审核。
# 您在使用脚本库下载的脚本时自行检查判断风险。
# 所涉及到的 账号安全、数据泄露、设备故障、软件违规封禁、财产损失等问题及法律风险，与脚本库无关！均由开发者、上传者、使用者自行承担。