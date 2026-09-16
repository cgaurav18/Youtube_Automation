import json
import sys

from google_auth import get_credentials


def main():
    with open("config.json") as f:
        config = json.load(f)

    creds = get_credentials(
        config["credentials_file"], config["token_file"], interactive=True
    )
    print(f"Authorization successful. Token saved to {config['token_file']}")
    print("You can now run 'python3 main.py' or install the cron schedule.")


if __name__ == "__main__":
    sys.exit(main())
