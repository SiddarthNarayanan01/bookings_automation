from datetime import datetime, date, timedelta
import logging
import sys
from time import sleep
import requests
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def log(msg):
    logging.info(f"[{datetime.now().strftime('%m/%d/%y @ %H:%M:%S')}] {msg}")


def book(request):
    # Session to keep cookies, and other data
    r = requests.Session()

    # Logging in
    login = r.post(
        url="[REDACTED]",
        data={
            "username": os.environ["username"],
            "password": os.environ["password"],
            "api_key": "no_limits",
            "course_id": os.environ["course_id"]
        }
    ).json()
    # Authentication purposes
    bearer_token = login["jwt"]

    log("Successfully logged in: Received Bearer Token")

    headers = {
        'api-key': 'no_limits',
        'x-authorization': f"Bearer {bearer_token}"
    }

    # Getting all available tee times
    all_times = []
    next_week = (date.today() +
                 timedelta(days=int(os.environ["timedelta"]))).strftime("%m-%d-%Y")
    log(f"Reserving for {next_week}")

    start_time = datetime.strptime(os.environ["start_time"], '%H:%M').time()
    end_time = datetime.strptime(os.environ["end_time"], '%H:%M').time()

    # Sleeps till :58 seconds so that the refreshing won't occur too many times
    # sleep_time = 58 - datetime.now().second
    sleep_time = 58 - datetime.now().second + 60 * (59 - datetime.now().minute)
    if sleep_time > 0:
        log(f"Sleeping for {sleep_time} seconds")
        sleep(sleep_time)

    max_refreshes = 50
    refreshes = 0
    while not all_times and refreshes < max_refreshes:
        all_times = r.get(
            url="[REDACTED]",
            params={
                "time": 'all',
                "date": next_week,
                "holes": 18,
                "players": os.environ['min_players'],
                "schedule_id": os.environ['schedule_id'],
                "booking_class": os.environ['booking_class'],
            },
            headers=headers
        ).json()
        refreshes += 1
        sleep(0.1)
    log(all_times)
    log(f"Successfully fetched tee times: {[time['time'] for time in all_times]}")

    for tt in all_times:
        raw_time = tt["time"]
        log(f"Trying {raw_time}")
        parsed_time = datetime.strptime(raw_time.split(" ")[1], "%H:%M").time()
        if not (start_time <= parsed_time <= end_time):
            log("Not in preferred time range")
            continue

        pending_res = requests.post(
            url='[REDACTED]',
            headers=headers,
            data={
                'time': raw_time,
                'holes': '18',
                'players': tt['available_spots'],
                'carts': False,
                'schedule_id': os.environ["schedule_id"],
                'course_id': os.environ["course_id"],
                'booking_class_id': os.environ['booking_class'],
                'duration': '1',
            }
        ).json()
        if not pending_res['success']:
            log(f"Failed to reserve 5-min slot {tt['time']}")
            if "jwt" in pending_res:
                del pending_res['jwt']
            log(pending_res)
            continue
        log(f"Successfully reserved 5-min slot {tt['time']}")
        reservation_id = pending_res['reservation_id']

        additional_info = {
            "players": tt['available_spots'],
            "carts": False,
            "promo_code": "",
            "promo_discount": 0,
            "player_list": False,
            "duration": 1,
            "hide_prices": False,
            "show_course_name": False,
            "min_players": tt['minimum_players'],
            "max_players": tt['available_spots'],
            "notes": [],
            "customer_message": "",
            "total": int(tt['green_fee']) * tt['available_spots'],
            "purchased": False,
            "pay_players": tt['available_spots'],
            "pay_carts": False,
            "pay_total": int(tt['green_fee']) * tt['available_spots'],
            "pay_subtotal": int(tt['green_fee']) * tt['available_spots'],
            "paid_player_count": 0,
            "discount_percent": 0,
            "discount": 0,
            "details": "",
            "pending_reservation_id": reservation_id,
            "allow_mobile_checkin": 0,
            "foreup_trade_discount_information": [],
            "airQuotesCart": [
                {
                    "type": "item",
                    "description": "Green Fee",
                    "price": tt['green_fee'],
                    "quantity": tt['available_spots'],
                    "subtotal": int(tt['green_fee']) * tt['available_spots']
                }
            ],
            "preTaxSubtotal": int(tt['green_fee']) * tt['available_spots'],
            "estimatedTax": 0,
            "subtotal": int(tt['green_fee']) * tt['available_spots'],
            "available_duration": pending_res['available_duration'],
            "increment_amount": pending_res['increment_amount']
        }

        valid = r.post(
            url="[REDACTED]",
            json={
                'validate_only': True,
                **tt,
                **additional_info,
            },
            headers=headers
        ).json()
        if "valid" in valid and not valid['valid']:
            log("[FAILED] Reservation was not valid")
            log(valid)
            continue
        reserve = r.post(
            url="[REDACTED]",
            json={
                **tt,
                **additional_info,
            },
            headers=headers
        ).json()
        log(reserve)

        delete = r.delete(
            url="[REDACTED]",
            headers=headers
        ).json()

        log(delete)
        log("Reservation succeeded")
        break

    r.close()
    log("Terminated program\n")
    return '{"status":"200", "data": "OK"}'
