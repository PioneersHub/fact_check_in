import json

import requests

from app.config import account_slug, event_slug, TOKEN, CONFIG

headers = {
    "Accept": "application/json",
    "Authorization": f"Token token={TOKEN}",
}

headers_post = {k: v for k, v in headers.items()}
headers_post["Content-Type"] = "application/json"


def get_all_orders(from_cache=False):
    """ """
    _file = CONFIG.datadir / "registrants.json"
    if from_cache and _file.exists():
        return json.load(_file.open())
    _all = []
    payload = {"page": 1}

    while payload["page"]:
        print("getting page:", payload["page"])
        url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/registrations"
        res = requests.get(url, headers=headers, params=payload)
        resj = res.json()
        _all.extend(resj["registrations"])
        payload["page"] = resj["meta"]["next_page"]
    json.dump(_all, _file.open("w"))
    return _all


def get_all_tickets(from_cache=False):
    """ """
    _file = CONFIG.datadir / "tickets.json"
    if from_cache and _file.exists():
        print("using cached file for tickets")
        return json.load(_file.open())
    print("loading for tickets from API")
    _all = []
    payload = {"page": 1}

    while payload["page"]:
        print("getting page:", payload["page"])
        url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/tickets"
        res = requests.get(url, headers=headers, params=payload)
        resj = res.json()
        _all.extend(resj["tickets"])
        payload["page"] = resj["meta"]["next_page"]
    json.dump(_all, _file.open("w"))
    return _all


def get_all_ticket_offers():
    """
    At tito: releases
    """
    _file = CONFIG.datadir / "ticket_offers.json"
    _all = []
    payload = {"page": 1}

    while payload["page"]:
        print("getting page:", payload["page"])
        url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/releases"
        res = requests.get(url, headers=headers, params=payload)
        resj = res.json()
        _all.extend(resj["releases"])
        payload["page"] = resj["meta"]["next_page"]
    json.dump(_all, _file.open("w"), indent=4)
    return _all


def get_ticket_offer(ticket_offer_slug):
    # at tito: releases
    _file = CONFIG.datadir / f"ticket_offer_{ticket_offer_slug}.json"
    url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/releases/{ticket_offer_slug}"
    res = requests.get(url, headers=headers)
    resj = res.json()
    json.dump(resj["release"], _file.open("w"), indent=4)


if __name__ == "__main__":
    get_all_tickets()
