import pulumi_docker as docker

# Shared network — alle Container können sich per Name erreichen (wie bei docker-compose)
network = docker.Network("pixplore-net", name="pixplore")
