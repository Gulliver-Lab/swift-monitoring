import os

db_config = {
    "host": os.getenv("DB_HOST", default="127.0.0.1"),
    "user": os.getenv("SLURM_DB_USER", default="remote_user"),
    "password": os.getenv("SLURM_DB_PASSWORD"),
    "database": os.getenv("SLURM_DB_NAME", default="slurm_acct_db"),
    "port": int(os.getenv("MARIADB_PORT", default=3306)),
}

# node8 is 128 CPUs, 250 ram
cpus_per_partition = {"ludocpu": 512, "newcpu": 480, "oldcpu": 480}
ram_per_partition_gb = {"ludocpu": 1028, "newcpu": 1028, "oldcpu": 899}
gpu_per_node = {
    "node5": "RTX",
    "node7": "V100",
    "node9": "L40",
    "node10": "L4",
    "node11": "L4",
    "node12": "L4",
}
id_qos_name = {1: "Not Ludovic", 3: "Ludovic"}
