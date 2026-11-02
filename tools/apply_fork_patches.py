#!/usr/bin/env python3
"""Apply this fork's changes to an upstream Bazzite Containerfile.

The build workflow checks out upstream ublue-os/bazzite (main) and runs this
script on its Containerfile, so the fork only carries a small, explicit patch
instead of a diverging copy of the whole tree.

Patches (added as one RUN at the end of the bazzite-deck stage, so the
bazzite-nvidia stage built FROM it inherits them):

1. gamescope-session device-quirks: AIR_LIST ends with a ":" so
   ":$AIR_LIST:" contains "::". Boards with an empty DMI product_name
   (e.g. Intel DZ77GA-70K) give SYS_ID="", ":$SYS_ID:" == "::" matches, and a
   desktop on a TV gets the AYANEO AIR quirk (rotated "internal" panel).
2. Enable uupd.timer so the system stages OS updates in the background.
   Deck images ship it disabled and rely on Steam's "Check for updates" button.
   The deck finalize step disables it again, so that line is removed there.
3. Boot splash: use the SteamOS Plymouth theme instead of "bgrt", which
   repeats the motherboard's firmware logo during boot. The initramfs is
   rebuilt later in the build, so the theme lands in it. "steamos" is a
   script theme, so plymouth-plugin-script is installed too.
4. steamcouch dashboard (github.com/SupercaliG/steamcouch): latest release
   installed to /usr/lib/steamcouch, with its session script and the
   gamescope-session-plus hook that runs it in place of the Steam UI.
"""

import sys
from pathlib import Path

MARKER = "# Fork (bazzite-deck-nvidia-lts) patches"

PATCH = MARKER + r"""
# 1. device-quirks: empty DMI product_name must not match the AYANEO AIR quirk.
# 2. Stage OS updates automatically in the background (uupd.timer).
# 3. Console-style boot splash (SteamOS logo, not the motherboard logo).
RUN --mount=type=cache,dst=/var/cache \
    --mount=type=cache,dst=/var/log \
    --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=tmpfs,dst=/tmp \
    test -f /usr/share/gamescope-session-plus/device-quirks && \
    sed -i \
        -e 's|^AIR_LIST="AIR:AIR Pro:AIR Plus:SLIDE:"|AIR_LIST="AIR:AIR Pro:AIR Plus:SLIDE"|' \
        -e '/^SYS_ID=/a [ -n "$SYS_ID" ] || SYS_ID="unknown-desktop"' \
        /usr/share/gamescope-session-plus/device-quirks && \
    grep -qF '|| SYS_ID="unknown-desktop"' /usr/share/gamescope-session-plus/device-quirks && \
    systemctl enable uupd.timer && \
    dnf5 -y install plymouth-plugin-script && \
    plymouth-set-default-theme steamos && \
    test "$(plymouth-set-default-theme)" = steamos && \
    /ctx/cleanup

# 4. steamcouch: PS5-style dashboard as the Gaming Mode session client.
RUN --mount=type=tmpfs,dst=/tmp \
    curl -fsSL --retry 3 -o /tmp/steamcouch.tgz \
        https://github.com/SupercaliG/steamcouch/releases/latest/download/steamcouch-linux-x64.tar.gz && \
    mkdir -p /usr/lib/steamcouch && \
    tar -xzf /tmp/steamcouch.tgz -C /usr/lib/steamcouch --strip-components=1 --no-same-owner && \
    chmod -R go-w /usr/lib/steamcouch && \
    test -x /usr/lib/steamcouch/app/steamcouch && \
    install -m 0755 /usr/lib/steamcouch/steamcouch-session /usr/libexec/steamcouch-session && \
    install -D -m 0644 /usr/lib/steamcouch/ogui-steam.session-override \
        /etc/gamescope-session-plus/sessions.d/ogui-steam && \
    echo "steamcouch $(cat /usr/lib/steamcouch/BUILD)"

"""

DECK_STAGE = "FROM bazzite AS bazzite-deck"
DECK_FINALIZE = "\n# Cleanup & Finalize\n"
UUPD_DISABLE = "    systemctl disable uupd.timer && \\\n"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "Containerfile")
    text = path.read_text(encoding="utf-8")

    if MARKER in text:
        print(f"{path}: fork patches already applied")
        return 0

    stage = text.find(DECK_STAGE)
    if stage < 0:
        sys.exit(f"{path}: deck stage '{DECK_STAGE}' not found; upstream layout changed")

    finalize = text.find(DECK_FINALIZE, stage)
    next_stage = text.find("\nFROM ", stage + len(DECK_STAGE))
    if finalize < 0 or (next_stage >= 0 and finalize > next_stage):
        sys.exit(f"{path}: '# Cleanup & Finalize' not found in deck stage; upstream layout changed")

    # The deck stage's finalize step runs `systemctl disable uupd.timer` after
    # this patch, which would undo patch 2. Drop that one line from it.
    end = next_stage if next_stage >= 0 else len(text)
    deck_finalize = text[finalize:end]
    if UUPD_DISABLE not in deck_finalize:
        sys.exit(f"{path}: '{UUPD_DISABLE.strip()}' not found in deck finalize; upstream layout changed")
    deck_finalize = deck_finalize.replace(UUPD_DISABLE, "", 1)

    insert_at = finalize + 1  # keep the newline before the finalize comment
    text = text[:finalize] + deck_finalize + text[end:]
    path.write_text(text[:insert_at] + PATCH + text[insert_at:], encoding="utf-8")
    print(f"{path}: fork patches applied to deck stage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
