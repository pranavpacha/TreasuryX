# scripts/

Reserved for operational scripts. The one script this project actually ships is
[`backend/app/data/generate_demo_data.py`](../backend/app/data/generate_demo_data.py) (run via
`python -m app.data.generate_demo_data` from `backend/`), kept inside the backend package since it
imports nothing external and is part of the app's own data layer. No additional scripts were needed
for this build.
