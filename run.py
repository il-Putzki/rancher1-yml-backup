from minio import Minio
import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import sys


today = datetime.now().strftime('%Y-%m-%d')


# Get ENVs from Rancher
def get_envs():
    envs = requests.get(envs_url, auth=auth, headers=headers)
    return envs.json()["data"]


# Get STACKs from taken ENVs
def get_stacks(env_id):
    stacks = requests.get("{}/projects/{}/stacks".format(main_url, env_id), auth=auth,
                          headers=headers)
    return stacks.json()["data"]


# Get config YMLs from each STACK
def get_compose_confs(env_id, stack_id):
    comp = requests.post("{}/projects/{}/stacks/{}/?action=exportconfig".
                         format(main_url, env_id, stack_id),
                         auth=auth, headers=headers)
    return comp.json()


# Save config YMLs in files
def write_conf(conf, stack_name, env_name):
    ranch_comp = "{}/{}.{}.yml".format(env_name, stack_name, "rancher")
    if not os.path.exists(env_name):
        os.makedirs(env_name)
    with open(ranch_comp, 'w') as file:
        file.write(conf["rancherComposeConfig"])
    print("{}: saved {}-stack rancherComposeConfig".format(env_name, stack_name))

    dock_comp = "{}/{}.{}.yml".format(env_name, stack_name, "docker")
    with open(dock_comp, 'w') as file:
        file.write(conf["dockerComposeConfig"])
    print("{}: saved {}-stack dockerComposeConfig".format(env_name, stack_name))


# Put saved YMLs to Minio S3
def put_s3(env_name):
    minio_url = os.getenv("MINIO_URL")
    minio_ak = os.getenv("MINIO_AK")
    minio_sk = os.getenv("MINIO_SK")
    minio_b_name = os.getenv("MINIO_B_NAME")
    mc = Minio(minio_url, minio_ak, minio_sk, secure=True)
    print("Putting configs to Minio S3")
    cur_dir = os.getcwd() + "/" + env_name
    for files in os.walk(cur_dir):
        for file in files[2]:
            with open(env_name + "/" + file, 'rb') as file_data:
                file_stat = os.stat(env_name + "/" + file)
                mc.put_object(minio_b_name, today + "/" + env_name + "/" + file, file_data, file_stat.st_size)
            os.remove(env_name + "/" + file)


def make_yml(minio=None):
    if minio is not None:
        print("backup with minio")
        for env in get_envs():
            for stack in get_stacks(env_id=env["id"]):
                write_conf(get_compose_confs(env["id"], stack["id"]), stack["name"], env["name"])
            put_s3(env["name"])
    else:
        for env in get_envs():
            for stack in get_stacks(env_id=env["id"]):
                write_conf(get_compose_confs(env["id"], stack["id"]), stack["name"], env["name"])


if __name__ == "__main__":
    if ("CATTLE_URL" and "CATTLE_ACCESS_KEY" and "CATTLE_SECRET_KEY") in os.environ:
        main_url = os.getenv("CATTLE_URL")
        ak = os.getenv("CATTLE_ACCESS_KEY")
        sk = os.getenv("CATTLE_SECRET_KEY")
        headers = {'Content-type': 'application/json'}
        auth = HTTPBasicAuth(ak, sk)
        envs_url = main_url + "/projects"
        main_response = requests.get(main_url, auth=auth, headers=headers)
        if len(sys.argv) > 1:
            if sys.argv[1] == "minio":
                make_yml(minio=True)
            else:
                print("Something else is set")
        else:
            make_yml(minio=None)
    else:
        print("\"CATTLE_URL\", \"CATTLE_ACCESS_KEY\" or \"CATTLE_SECRET_KEY\" is not set")
