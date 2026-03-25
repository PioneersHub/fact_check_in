from http import HTTPStatus
from urllib.parse import urlencode

import requests
from fastapi.encoders import jsonable_encoder

from app import in_dummy_mode, interface, log
from app.config import CONFIG, TOKEN, account_slug, event_slug
from app.errors import NotOk

headers = {
    "Accept": "application/json",
    "Authorization": f"Token token={TOKEN}",
}

headers_post = dict(headers.items())
headers_post["Content-Type"] = "application/json"


def minimize_data(data: list[dict]) -> list[dict]:
    """Remove all data that is not relevant to run the application.

    Removes tickets not relevant for the use case.
    """
    opt_in_attributes = {
        "email",
        "created_at",
        "updated_at",
        "state",
        "reference",
        "registration_id",
        "release_id",
        "first_name",
        "last_name",
        "name",
        "assigned",
    }
    log.debug("minimizing data footprint")
    return [{k: v for k, v in x.items() if k in opt_in_attributes} for x in data]


def filter_valid_activities(data: list[dict]) -> list[dict]:
    """Filter out tickets not relevant for the application.

    Tickets like for social events, workshops, etc. are not relevant.
    """
    return [x for x in data if set(x["activities"]) & set(CONFIG.include_activities)]


def response_is_not_ok(response):
    content = "response is not OK"
    try:
        log.info("error", response.status_code)
        content = jsonable_encoder({response.status_code: response.json()})
    except Exception as e:  # noqa: BLE001
        log.info("error", e)
        content = jsonable_encoder({response.status_code: str(e)})
    finally:
        raise NotOk(status_code=response.status_code, content=content)


def get_all_tickets():
    """Load all tickets from the Tito API."""
    if in_dummy_mode:
        return
    log.info("Loading all tickets from API")
    collect = []
    payload = {"page": 1}

    while payload["page"]:
        log.info(f"getting page:{payload['page']}")
        url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/tickets"
        res = requests.get(url, headers=headers, params=payload, timeout=30)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)
        res_j = res.json()
        data = minimize_data(res_j["tickets"])
        collect.extend(data)
        payload["page"] = res_j["meta"]["next_page"]
    interface.all_sales = {x["reference"].upper(): x for x in collect}


def get_all_ticket_offers():
    """Get all ticket types offered for sale.

    At Tito these are called releases.
    """
    if in_dummy_mode:
        return
    collect = []
    payload = {"page": 1}

    while payload["page"]:
        log.info(f"getting page:{payload['page']}")
        # activities requires API version=3.1
        url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/releases?expand=activities&version=3.1"
        log.info(url)
        res = requests.get(url, headers=headers, params=payload, timeout=30)
        if res.status_code != HTTPStatus.OK:
            response_is_not_ok(res)
        res_j = res.json()

        def mangler(k, v):
            # only 'name' of activities is needed
            if k == "activities":
                return [y["name"] for y in v]
            return v

        filtered_data = [{k: mangler(k, v) for k, v in x.items() if k in {"id", "title", "activities"}} for x in res_j["releases"]]
        collect.extend(filtered_data)
        payload["page"] = res_j["meta"]["next_page"]
    interface.all_releases = {str(x["title"]).upper(): x for x in collect}


def search_reference(reference):
    log.debug(f"searching for reference: {reference}")
    if in_dummy_mode:
        return interface.all_sales.get(reference)

    params = {"search[q]": reference}
    url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/tickets?{urlencode(params)}"
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != HTTPStatus.OK:
        log.debug(f"the request reference: {reference} returned status code: {res.status_code}")
        response_is_not_ok(res)
    res_j = res.json()
    log.debug(f"success: the request {reference} returned {len(res_j['tickets'])} tickets.")
    return res_j["tickets"]


def search(search_for: str):
    log.debug(f"searching for {search_for}")
    if in_dummy_mode:
        res = [x for x in interface.all_sales.values() if search_for.casefold().strip() in x["email"].casefold().strip()]
        if res:
            return res
        return [{"email": search_for}]

    params = {"search[q]": search_for}
    url = f"https://api.tito.io/v3/{account_slug}/{event_slug}/tickets?{urlencode(params)}"
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != HTTPStatus.OK:
        log.debug(f"the request {search_for} returned status code: {res.status_code}")
        response_is_not_ok(res)
    res_j = res.json()
    log.debug(f"success: the request {search_for} returned {len(res_j['tickets'])} tickets.")
    return res_j["tickets"]


if __name__ == "__main__":
    pass
