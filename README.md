# YouTube Shorts auto-poster (Google Drive -> YouTube)

Uploads videos from a Google Drive folder to your YouTube channel as Shorts,
2 per day (1 at 10:00 and 1 at 18:00, via cron), skipping videos already posted.

## 1. Google Cloud setup (one-time, ~5 min)

1. Go to https://console.cloud.google.com/ and create a new project (or reuse one).
2. Enable two APIs for that project (APIs & Services -> Library):
   - **Google Drive API**
   - **YouTube Data API v3**
3. Configure the OAuth consent screen (APIs & Services -> OAuth consent screen):
   - User type: External
   - Add your own Google account under "Test users".
   - **Publish the app** (Publishing status -> "Publish app" -> confirm),
     moving it from "Testing" to "In production". This does **not** require
     Google's verification review for personal/self use — you'll just see an
     "unverified app" warning the one time you authorize it (`setup_auth.py`),
     which is safe to click through since it's your own app.
     **This step matters**: refresh tokens issued while the app is still in
     "Testing" status expire after 7 days, which would silently break the
     automation on a weekly basis. Publishing avoids that.
4. Create credentials (APIs & Services -> Credentials -> Create Credentials ->
   OAuth client ID):
   - Application type: **Desktop app**
   - Download the JSON and save it as:
     `~/youtube-shorts-automation/auth/client_secret.json`

## 2. Get your Drive folder ID

Open the folder in Google Drive in a browser. The URL looks like:
`https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz`
The part after `/folders/` is the folder ID. Put it in `config.json` as
`drive_folder_id`.

## 3. Install and authorize

```bash
cd ~/youtube-shorts-automation
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# edit config.json: set drive_folder_id at minimum
venv/bin/python3 setup_auth.py
```

`setup_auth.py` opens a browser (or prints a URL) for you to log in with the
Google account that owns the Drive folder / YouTube channel, and approve
Drive read-only + YouTube upload access. This is one-time; it saves a
refresh token to `auth/token.json` that later runs use silently.

**If this machine is a headless remote server** (no browser), run
`setup_auth.py` on your local machine once instead, then copy the resulting
`auth/token.json` and `auth/client_secret.json` over to the server — or SSH in
with port forwarding: `ssh -L 8080:localhost:8080 user@server`, then run
`setup_auth.py` on the server and open the printed URL in your local browser.

## 4. Test a single run

```bash
venv/bin/python3 main.py
```

Check the log output and your YouTube Studio uploads page. This will upload
`videos_per_run` (default 1) video(s) from the Drive folder.

## 5. Schedule it (2 videos/day)

You have two options: run it on GitHub Actions (free, no machine to keep on),
or run it via cron on a machine you keep on. GitHub Actions is recommended
unless you already have an always-on box.

### Option A: GitHub Actions (recommended)

A cron-triggered workflow at
[.github/workflows/shorts-upload.yml](.github/workflows/shorts-upload.yml)
runs `main.py` at 04:30 and 12:30 UTC (10:00 and 18:00 IST) and commits the
updated `state.json` back to the repo so posted videos are never re-uploaded,
even though each run starts from a fresh, ephemeral runner.

Setup:

1. Push this repo to GitHub. Keep it **private** — `config.json` and the repo
   contents don't hold secrets, but treat it that way since the workflow
   commits your posting history.
2. Encode your local credential files to base64 (after running `setup_auth.py`
   once, per step 3 above, so `auth/token.json` exists):
   ```bash
   base64 -w0 auth/client_secret.json
   base64 -w0 auth/token.json
   ```
   (On macOS, use `base64 -i auth/client_secret.json` instead of `-w0`.)
3. In the GitHub repo, go to **Settings -> Secrets and variables -> Actions ->
   New repository secret** and add two secrets:
   - `GOOGLE_CLIENT_SECRET_JSON_B64` — output of the first command above
   - `GOOGLE_TOKEN_JSON_B64` — output of the second command above
4. Go to **Settings -> Actions -> General -> Workflow permissions** and select
   **"Read and write permissions"** — the workflow needs this to commit
   `state.json` back after each run.
5. That's it. The workflow runs on its schedule automatically, or trigger it
   manually from the **Actions** tab -> "Upload Shorts to YouTube" -> "Run
   workflow" to test it.

To change the times, edit the two `cron:` lines in the workflow file (times
are UTC).

### Option B: cron on your own always-on machine

```bash
./install_cron.sh
```

This adds two cron entries (10:00 and 18:00 server time) that each run
`main.py` once, uploading `videos_per_run` video(s) per run — 2/day total
with the default config. Logs go to `logs/cron.log`.

Note this only runs while the machine is on — cron has no catch-up for missed
runs, so a run is simply skipped if the machine is off/asleep at that time.

To change the times, edit `install_cron.sh` before running it, or edit your
crontab directly afterwards (`crontab -e`).

To remove the schedule later:
```bash
crontab -l | grep -vF '# youtube-shorts-automation' | crontab -
```

## Configuration (`config.json`)

| Field | Meaning |
|---|---|
| `drive_folder_id` | Folder to pull videos from |
| `videos_per_run` | How many videos each cron run uploads (2 runs/day x this = daily total) |
| `video_extensions` | Which file types count as videos |
| `title_template` | `{filename}` is replaced with the cleaned-up file name |
| `description_template` | Fixed description added to every upload |
| `tags` | YouTube tags applied to every upload |
| `privacy_status` | `public`, `unlisted`, or `private` |
| `category_id` | YouTube category (22 = People & Blogs; see [category list](https://developers.google.com/youtube/v3/docs/videoCategories/list)) |
| `order` | `oldest_first` or `newest_first` — which unposted video gets picked next |
| `delete_from_drive_after_upload` | If `true`, removes the file from Drive once posted (default `false`, since `state.json` already prevents re-posting) |

## Notes on YouTube Shorts

YouTube treats an upload as a Short automatically if it's vertical (9:16) or
square and roughly under 3 minutes (best reliability under 60s). Adding
`#Shorts` in the title/description (already in the default config) reinforces
this. If your Drive videos aren't already vertical/short, YouTube will still
accept the upload but it may land as a regular video, not a Short.

## State tracking

`state.json` records the Drive file IDs already posted, so re-running never
double-posts. Delete an ID from that file (or the whole file) if you want a
video to be eligible for re-upload.

## Quota

Each upload costs 1600 units of your default 10,000/day YouTube Data API
quota — 2 uploads/day uses 3,200 units, well within the limit.
