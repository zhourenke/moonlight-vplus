#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Diagnostic patch: make touch / pen MOVE events RELIABLE so that they are no
longer dropped by ENet's packetThrottle.

Background
----------
In moonlight-common-c's InputStream.c, touch MOVE and pen MOVE packets are
created with enetPacketFlags = 0 (unreliable). ENet's packetThrottle only
applies to unreliable packets: when RTT jitter exceeds a threshold it starts
destroying a percentage of them outright (see enet/protocol.c,
enet_protocol_send_outgoing_commands). The practical effect is that touch
input periodically collapses while video bitrate fluctuates, whereas mouse
input (which uses the reliable channel) is unaffected.

Marking these packets ENET_PACKET_FLAG_RELIABLE moves them onto the reliable
channel, where packetThrottle does not apply.

This changes the build output only; the submodule commit is left untouched.

Usage:
    patch-touch-reliable.py <path to InputStream.c>
"""

import sys
from pathlib import Path

# (description, original, replacement)
TARGETS = [
    (
        "LiSendTouchEvent / LiSendControllerTouchEvent2 - screen touch",
        "holder->enetPacketFlags = TOUCH_EVENT_IS_BATCHABLE(eventType) ? 0 : ENET_PACKET_FLAG_RELIABLE;",
        "holder->enetPacketFlags = ENET_PACKET_FLAG_RELIABLE;",
    ),
    (
        "LiSendPenEvent - stylus",
        "holder->enetPacketFlags = (TOUCH_EVENT_IS_BATCHABLE(eventType) && !(penButtons ^ currentPenButtonState)) ? 0 : ENET_PACKET_FLAG_RELIABLE;",
        "holder->enetPacketFlags = ENET_PACKET_FLAG_RELIABLE;",
    ),
]

# Must be gone after patching: touch/pen paths still marked unreliable.
RESIDUE = "TOUCH_EVENT_IS_BATCHABLE(eventType) ? 0"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch-touch-reliable.py <path to InputStream.c>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print("ERROR: file not found: %s" % path, file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    original = text
    applied = []

    for desc, old, new in TARGETS:
        count = text.count(old)
        print("[%d hit(s)] %s" % (count, desc))
        if count == 0:
            print(
                "ERROR: target string not found; the submodule may have changed.\n"
                "  expected: %s" % old,
                file=sys.stderr,
            )
            return 1
        text = text.replace(old, new)
        applied.append((desc, count))

    if text == original:
        print("ERROR: nothing changed", file=sys.stderr)
        return 1

    path.write_text(text, encoding="utf-8")

    print("")
    print("Applied:")
    for desc, count in applied:
        print("  - %s x%d" % (desc, count))

    residue = [i + 1 for i, line in enumerate(text.splitlines()) if RESIDUE in line]
    if residue:
        print(
            "ERROR: touch still marked unreliable on line(s): %s" % residue,
            file=sys.stderr,
        )
        return 1

    print("")
    print("OK: all touch/pen MOVE paths are now reliable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
