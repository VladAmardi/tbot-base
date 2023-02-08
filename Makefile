_env = $(shell bash -c 'if [ -f .env ]; then source .env; echo $$_ENV; fi')
deploy_dst = $(shell bash -c 'if [ -f make.cnf ]; then source make.cnf; echo $$deploy_dst; fi')
deploy_folder = $(shell bash -c 'if [ -f make.cnf ]; then source make.cnf; echo $$deploy_folder; fi')
name = $(shell basename $$(pwd -P))
container_part = $(shell bash -c 'if [ -f make.cnf ]; then source make.cnf; [[ ! -z $$C  ]] && echo $$C || echo $$container; fi')
container = "${name}${container_part}"
project_dir = $(shell bash -c 'cd "$(dirname $(dirname "$0"))" ; pwd -P ')
root_dir = $(shell bash -c 'cd $(project_dir) ; cd .. ; pwd -P ')
define makeRemote
    ssh -t $(deploy_dst) "cd $(deploy_folder) && make $(1)"
endef
_configs = --compatibility
_CI_COMMIT_SHA = latest
ifneq ("$(wildcard ./docker-compose.yml)","")
    _configs += -f docker-compose.yml
endif
ifeq ($(_env),Production)
    ifneq ("$(wildcard production.yml)","")
        _configs += -f production.yml
    endif
    _env_name = Production
endif
ifeq ($(_env),Development)
    ifneq ("$(wildcard development.local.yml)","")
        _configs += -f development.local.yml
    else ifneq ("$(wildcard development.yml)","")
        _configs += -f development.yml
    endif
endif
ifeq ($(_env),Test)
    ifneq ("$(wildcard test.local.yml)","")
        _configs += -f test.local.yml
    else ifneq ("$(wildcard test.yml)","")
        _configs += -f test.yml
    endif
endif

ifeq ($(deploy_dst),)
    $(error "Seems, you doesn't specify 'deploy_dst' in make.cnf")
endif
ifeq ($(deploy_folder),)
    $(error "Seems, you doesn't specify 'deploy_folder' in make.cnf")
endif

list:
	@echo "Commands:"
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | xargs

remote:
	@echo "Working with production"

containers-rebuild: containers-down containers-build containers-up

#upgrade: update

#update: pull containers-up-build web-build restart_workers

start: containers-up

stop: containers-down

deploy:
	@echo "Deploy"
	$(call makeRemote, pull)
	$(call makeRemote, migrate)
	$(call makeRemote, containers-upbuild)
	$(call makeRemote, uds-restart)

ifeq (remote,$(firstword $(MAKECMDGOALS)))
containers-build:
	$(call makeRemote, containers-build)
network:
	$(call makeRemote, network)
set-development:
	$(call makeRemote, set-development)
set-production:
	$(call makeRemote, set-production)
set-test:
	$(call makeRemote, set-test)
containers-down:
	$(call makeRemote, containers-down)
containers-up:
	$(call makeRemote, containers-up)
containers-upbuild:
	$(call makeRemote, containers-upbuild)
containers-restart:
	$(call makeRemote, containers-restart)
help:
	$(call makeRemote, help)
pull:
	$(call makeRemote, pull)
ps:
	$(call makeRemote, ps)
migrate:
	$(call makeRemote, migrate)
get-env:
	$(call makeRemote, get-env)
shell:
	$(call makeRemote, shell)
uds-log:
	$(call makeRemote, uds-log)
uds-restart:
	$(call makeRemote, uds-restart)
else

get-env:
ifeq ($(_env),)
	$(error You should set environment before! Commands: "make set-development" or "make set-production" or "make set-test")
else
	@echo "Environment:" $(_env)
endif

containers-build: get-env
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) build

containers-push: get-env
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) push

set-development:
	echo '_ENV=Development' > .env
#	echo "_UID=$(shell id -u)" >> .env
#	echo "_GID=$(shell id -g)" >> .env
#	echo "_UID=1000" >> .env
#	echo "_GID=50" >> .env

set-production:
	echo '_ENV=Production' > .env
#	echo "_UID=$(shell id -u)" >> .env
#	echo "_GID=$(shell id -g)" >> .env

set-test:
	echo '_ENV=Test' > .env
#	echo "_UID=1000" >> .env
#	echo "_GID=50" >> .env
#	echo "_UID=$(shell id -u)" >> .env
#	echo "_GID=$(shell id -g)" >> .env

containers-down: get-env
ifeq ($(_env),Production)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) down --remove-orphans
endif
ifeq ($(_env),Development)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) down --remove-orphans
endif
ifeq ($(_env),Test)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) down --remove-orphans
endif

containers-up: get-env
ifeq ($(_env),Production)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --remove-orphans
endif
ifeq ($(_env),Test)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --remove-orphans
endif
ifeq ($(_env),Development)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --remove-orphans
endif

containers-restart: get-env
ifeq ($(_env),Production)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) restart
endif
ifeq ($(_env),Test)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) restart
endif
ifeq ($(_env),Development)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) restart
endif

containers-upbuild: get-env
ifeq ($(_env),Production)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --build --remove-orphans
endif
ifeq ($(_env),Test)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --build --remove-orphans
endif
ifeq ($(_env),Development)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) up -d --build --remove-orphans
endif

ps: get-env
ifeq ($(_env),Production)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) ps
endif
ifeq ($(_env),Test)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) ps
endif
ifeq ($(_env),Development)
	CI_COMMIT_SHA=$(_CI_COMMIT_SHA) docker-compose $(_configs) ps
endif

help: list
	@echo "Config will be:"
	@echo $(_configs)

pull:
	@echo "Updating codebase..."
	git pull
	@echo "Done"

uds-log:
	docker logs -f --tail="200" ${name}_user_data_streams_1

uds-restart:
	docker restart ${name}_user_data_streams_1

ssh:
	@bash -c '\
		session_name=$$(whoami);\
		session_name="_$${session_name}";\
		remote_cmd="\
			cd /code/dca1; \
			bash \
		"; \
		ssh -t $(deploy_dst) $${remote_cmd} \
		'

migrate:
	@echo 'Connecting to docker...'
	@sh -c 'docker exec $(container) bash -c "python manage.py migrate"'
#ifeq ($(_env),Production)
#	@echo "(Production) Installing crontab..."
#	crontab crontab
#	@echo "Done"
#endif
#ifeq ($(_env),Test)
#	@echo "(Test) Installing crontab..."
#	crontab crontab
#	@echo "Done"
#endif

shell:
	@bash -c 'echo -en "\033]0; $(container) \a"'
	$(eval E := $(shell if [ "$$(tty 2>&1)" != "not a tty" ]; then \
		echo "-it -e COLUMNS=$$(tput cols) -e LINES=$$(tput lines)"; \
	else \
		echo "-it"; \
	fi))
	@sh -c 'docker exec $(E) $(container) bash -c "\
	 [[ -d /code ]] && cd /code; \
     /bin/bash; \
     "'
	@bash -c 'echo -en "\033]0; \a"'

endif
