# AstraGuard Chrome Guide Extension

This extension gives proactive on-page guidance on:
- KFintech CAS page (`mfs.kfintech.com`)
- TRACES/Form16 pages (`tdscpc.gov.in`)

It is isolated from backend core logic and does not change existing APIs.

## Load locally
1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select folder:
   - `/Users/theankit/Documents/AK/AstraGuard/tools/chrome_guide_extension`

## Use
1. Open KFin CAS or TRACES page.
2. Click extension icon.
3. Select guide type.
4. Click `Start Guide`.

The extension highlights target elements and shows step instructions.
If target cannot be detected, it falls back to manual assist text.
Guide progress is persisted and auto-resumed across page loads/navigation on the same target host.

## Optional live status from backend
- Enter backend URL (default `http://127.0.0.1:8000`) and user id in popup.
- Extension listens to `ws://.../ws/{user_id}` and shows latest job state in overlay.

## Language support
- English (default)
- Hinglish
- Hindi

## Notes
- This is guided assistance, not full unattended automation.
- Existing backend flows remain unchanged.

## Locked target URLs for demo
- KFin CAS: `https://mfs.kfintech.com/investor/General/ConsolidatedAccountStatement`
- TRACES: `https://www.tdscpc.gov.in/`
