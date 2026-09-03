web: export SKIP_SCHEMA_INIT=1 && python migrate.py && python sync_repo_posts_cli.py && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
