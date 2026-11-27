"""Update the bot's checkup comment using the workflow's default token."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

marker = "<!-- honestenv-checkup -->"
body = Path(os.environ["REPORT_PATH"]).read_text(encoding="utf-8")
base = f"{os.environ['GITHUB_API_URL']}/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{os.environ['PR_NUMBER']}/comments"
headers = {"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"}
try:
    page = 1
    comment_id = None
    while True:
        with urlopen(Request(f"{base}?per_page=100&page={page}", headers=headers)) as response:
            comments = json.load(response)
        for comment in comments:
            if marker in comment["body"] and comment["user"]["login"] == "github-actions[bot]":
                comment_id = comment["id"]
                break
        if comment_id or len(comments) < 100:
            break
        page += 1
    url = f"{os.environ['GITHUB_API_URL']}/repos/{os.environ['GITHUB_REPOSITORY']}/issues/comments/{comment_id}" if comment_id else base
    request = Request(url, data=json.dumps({"body": body}).encode(), headers=headers, method="PATCH" if comment_id else "POST")
    with urlopen(request):
        pass
except HTTPError as error:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    fork = event.get("pull_request", {}).get("head", {}).get("repo", {}).get("fork", False)
    if error.code == 403 and fork:
        print("Could not post checkup (token may be read-only for a fork PR).", flush=True)
    else:
        raise
