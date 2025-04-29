set dotenv-load := true

default:
  @just --list

test *args:
  #!/bin/bash
  set -a
  . ./.env
  poetry run pytest {{args}}

coverage *args:
  just test -vv --cov --cov-report term --cov-report html:_reports/coverage-html {{args}}

coverage-serve:
  python -m http.server 7777 -d _reports/coverage-html

# Run Django manage.py with the right environment
manage *args:
  #!/bin/bash
  set -a
  . ./.env
  poetry run ./manage.py {{args}}
