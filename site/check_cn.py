#!/usr/bin/env python3
"""Check that a page of www.ahaolearn.com opens from mainland China.

Uses the free Globalping API (no account, no captcha): ten probes in China fetch the page over HTTPS,
and each result says whether the response is really our page (the expected text is in the body).

    python3 site/check_cn.py                 # home page
    python3 site/check_cn.py /05/ "拖延对症"   # a path and a piece of text that must be on it
"""
import json
import sys
import time
import urllib.request

API = "https://api.globalping.io/v1/measurements"
HOST = "www.ahaolearn.com"


def call(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"), strict=False)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/"
    expect = sys.argv[2] if len(sys.argv) > 2 else "AI 时代的成长说明书"
    m = call(API, {"type": "http", "target": HOST, "locations": [{"country": "CN", "limit": 10}],
                   "measurementOptions": {"protocol": "HTTPS", "request": {"path": path, "method": "GET"}}})
    for _ in range(20):
        time.sleep(2)
        res = call(f"{API}/{m['id']}")
        if res["status"] == "finished":
            break
    ok = 0
    for r in res["results"]:
        p, x = r["probe"], r["result"]
        good = x.get("statusCode") == 200 and expect in (x.get("rawBody") or "")
        ok += good
        detail = "本站内容" if good else (x.get("rawOutput") or "")[:70].replace("\n", " ")
        total = (x.get("timings") or {}).get("total")
        print(f"{p['city']:<12} {p.get('network', '')[:26]:<26} {x.get('statusCode')} {total}ms {x.get('resolvedAddress')}  {detail}")
    print(f"\n{ok}/{len(res['results'])} 个中国大陆节点拿到了本站页面（{HOST}{path}）")
    sys.exit(0 if ok >= len(res["results"]) * 0.8 else 1)


if __name__ == "__main__":
    main()
