import requests
import json
from pathlib import Path
SCRIPT_DIR = str(Path(__file__).parent.absolute())

# ==================================== #
# ========= ED/SLACK CONFIG ========== #
# ==================================== #

ED_COURSE_ID = 0000
ED_AUTH_TOKEN = "YOUR_ED_AUTH_TOKEN_HERE"
SLACK_WEBHOOK_URL = "YOUR_SLACK_BOT_INCOMING_WEBHOOK_URL_HERE"
JSON_FILEPATH = str(Path(SCRIPT_DIR) / "cache.json")

# ==================================== #
# ========== REQUEST CONFIG ========== #
# ==================================== #

SORT = "new"
LIMIT = "20" # must be <= 100
REQUEST_URL = f"https://us.edstem.org/api/courses/{ED_COURSE_ID}/threads?sort={SORT}&limit={LIMIT}"
REQUEST_HEADERS = {'x-token': ED_AUTH_TOKEN}

# ==================================== #
# ============ END CONFIG ============ #
# ==================================== #

# Read in cached data
try:
    with open(JSON_FILEPATH, 'r') as json_file:
        cache = json.load(json_file)
        cached_thread_ids = set(cache['thread_ids'])
except:
    cache = {}
    cached_thread_ids = set()

response = requests.get(REQUEST_URL, headers=REQUEST_HEADERS)
threads = response.json()['threads']
new_threads = [thread for thread in threads if thread['id'] not in cached_thread_ids]

for thread in new_threads:
    cached_thread_ids.add(thread['id'])

# Write updated cache data to cache json
new_cache = {
    'thread_ids': sorted(cached_thread_ids)
}
with open(JSON_FILEPATH, 'w') as json_file:
    json.dump(new_cache, json_file)

# Send slack notifs
if cache != {}:
    for thread in new_threads:
        formatted_title = f"(#{thread['number']}) {thread['title']}"
        author = "Anonymous" if thread['is_anonymous'] else thread['user']['name']
        post_text = thread['document'].strip()
        full_category = thread['category'] + (f": {thread['subcategory']}" if thread['subcategory'] else "")
        thread_url = f"https://edstem.org/us/courses/{thread['course_id']}/discussion/{thread['id']}"

        slack_request_json = {
            "text": formatted_title + ": " + post_text,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": formatted_title,
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": post_text,
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"📒 *Category:*\n{full_category}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"👤 *Posted by:*\n{author}"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔗 Open in Ed",
                                "emoji": True
                            },
                            "url": thread_url
                        }
                    ]
                }
            ]
        }

        r = requests.post(SLACK_WEBHOOK_URL, json=slack_request_json)
        if(r.status_code != 200):
            print(f"Received status code {r.status_code} when trying to post notification for Post #{thread['number']} (ID {thread['id']}).")
