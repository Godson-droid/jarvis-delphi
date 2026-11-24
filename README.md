# Jarvis: evidence mining for the Gensyn Agent Arena

Jarvis is the personal AI agent of Godson (GitHub: Godson-droid), registered for the Gensyn Agent Arena on Delphi prediction markets. The competition opens on 25 November 2026 and runs to 11 December 2026.

## What Jarvis does

Jarvis reads live Delphi markets and looks for public information the market has not priced in yet. When it finds some, it submits that evidence to the market it belongs to, backing one outcome. Rewards follow when the evidence moves the forecaster, and again when the market settles the same way.

## The evidence standard

Every submission Jarvis makes follows the same standard.

1. Public sources only. News reports, official statements and primary data that anyone can open and check.
2. Dated sources only. Every evidence item carries the date its source was published. Undated material is never submitted.
3. Verbatim quotes. Every item includes a quote copied word for word from the source, next to a short summary and the source link, so a judge can verify it in seconds.
4. One side only. Jarvis never submits evidence for both sides of the same market. The two sides cancel each other out, and a record built that way would be worthless anyway.
5. No fabrication and no copying. Evidence is gathered fresh for each market. Nothing is invented and nothing is taken from another entrant.
6. Honest confidence. Each submission states a confidence score that reflects how strong the evidence actually is, not how strong Jarvis wishes it were.

## The toolkit

The toolkit folder holds the local machinery that builds and checks each submission before anything is sent anywhere.

1. rules.py holds every competition limit in one clearly marked place: which markets are eligible, how often one market can receive a submission, and the daily cap.
2. submission.py builds a submission and validates it against those rules, item by item.
3. state.py keeps the local record of submissions already sent, so the hourly limit, the daily cap and the one side rule hold across sessions.
4. cli.py validates a submission file from the command line and prints either PASS or the exact reasons it fails.
5. sender.py is the sending layer. It is a deliberate stub for now. The Delphi API spec ships with the official agent guide, and the wiring lands in this file the moment that guide is published and read.

The test suite lives in toolkit/tests and runs with pytest. An example submission sits at toolkit/example_submission.json.

## Status

The competition opens on 25 November 2026 and registration is complete. The API integration lands when the official agent guide publishes on opening day. Until then the toolkit validates everything locally and sends nothing.

## Licence note

Under the competition rules, each submission grants Gensyn a perpetual licence to use it for model training and evaluation.
