import fcntl
import json
import logging
import os
import sys
import tempfile

from drive_client import DriveClient
from google_auth import get_credentials
from youtube_client import YouTubeClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(BASE_DIR, ".run.lock")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("shorts-uploader")


def load_config():
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return {"posted": []}


def save_state(state_file, state):
    tmp = state_file + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_file)


def title_from_filename(filename):
    name, _ = os.path.splitext(filename)
    return name.replace("_", " ").replace("-", " ").strip()


def run(config):
    if config["drive_folder_id"].startswith("PUT_YOUR"):
        log.error("config.json still has a placeholder drive_folder_id. Edit it first.")
        sys.exit(1)

    state_file = os.path.join(BASE_DIR, config["state_file"])
    creds = get_credentials(
        os.path.join(BASE_DIR, config["credentials_file"]),
        os.path.join(BASE_DIR, config["token_file"]),
        interactive=False,
    )

    drive = DriveClient(creds)
    youtube = YouTubeClient(creds)

    files = drive.list_videos(config["drive_folder_id"], config["video_extensions"])
    if config.get("order", "oldest_first") == "oldest_first":
        files.sort(key=lambda f: f.get("createdTime", ""))
    else:
        files.sort(key=lambda f: f.get("createdTime", ""), reverse=True)

    state = load_state(state_file)
    posted_ids = set(state["posted"])
    candidates = [f for f in files if f["id"] not in posted_ids]

    if not candidates:
        log.info("No new videos to post. Drive folder has %d video(s), all already posted.", len(files))
        return

    to_upload = candidates[: config["videos_per_run"]]
    log.info("Found %d new video(s); uploading %d this run.", len(candidates), len(to_upload))

    failures = 0
    for f in to_upload:
        try:
            title = config["title_template"].format(filename=title_from_filename(f["name"]))
            description = config["description_template"]
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_path = os.path.join(tmp_dir, f["name"])
                log.info("Downloading '%s' (%s)...", f["name"], f["id"])
                drive.download(f["id"], local_path)

                log.info("Uploading '%s' to YouTube...", title)
                video_id = youtube.upload_short(
                    local_path,
                    title,
                    description,
                    config.get("tags", []),
                    config["category_id"],
                    config["privacy_status"],
                )
                log.info("Uploaded: https://youtube.com/shorts/%s", video_id)

            state["posted"].append(f["id"])
            save_state(state_file, state)

            if config.get("delete_from_drive_after_upload"):
                drive.delete(f["id"])
                log.info("Deleted '%s' from Drive.", f["name"])
        except Exception:
            failures += 1
            log.exception("Failed to process '%s' (%s); skipping it this run.", f["name"], f["id"])

    if failures:
        log.error("%d of %d video(s) failed this run.", failures, len(to_upload))
        sys.exit(1)


def main():
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.warning("Another run is already in progress. Exiting.")
        sys.exit(0)

    try:
        config = load_config()
        run(config)
    except Exception:
        log.exception("Run failed.")
        sys.exit(1)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
