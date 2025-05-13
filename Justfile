set dotenv-load := true

# List available commands
list:
  @just --list

# Set up - install development dependencies
setup:
  poetry install --all-extras

# Publish to PyPI (with the right credentials)
publish:
  poetry build
  poetry publish

# Run all automated tests
test *args:
  poetry run pytest {{args}}

# Run tests with coverage
coverage *args:
  just test -vv --cov --cov-report term --cov-report html:_reports/coverage-html {{args}}

# Serve the coverage HTML reports
coverage-serve:
  python -m http.server 7777 -d _reports/coverage-html

# Run Django management commands for the sample project
manage *args:
  poetry run django-admin {{args}}

# Run the sample project
sample-app:
  just manage migrate
  just manage runserver
