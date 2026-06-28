.PHONY: help run dev test check clean

help:
	@printf "Targets:\n"
	@printf "  run    Start the CLI with Python\n"
	@printf "  dev    Alias for run\n"
	@printf "  test   Run the unit test suite\n"
	@printf "  check  Compile sources with py_compile\n"
	@printf "  clean  Remove bytecode caches\n"

run:
	@python3 odev_main.py

dev: run

test:
	@python3 -m unittest discover -s tests -p 'test_*.py'

check:
	@python3 -m compileall odev odev_main.py

clean:
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
