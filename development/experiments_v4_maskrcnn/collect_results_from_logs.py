EXP_GROUP_NAME = "10"
CKPTS = range(24999, 150000, 25000)

EVAL_SETTINGS = [
    (f"10_3_seed1_resnet101-FPN_detptr_anc10_linadap_chnl{i}_imsz1000_lr0.001_it150k", 3) for i in range(1, 11)
]
EVAL_SETTINGS.extend([
    (f"10_3_seed1_mrcnn-r101-FPN_detptr_anc10_linadap_chnl{i}_imsz1000_lr0.001_it150k", 3) for i in range(1, 10)

])

outputs = []
exp_names = []
for (exp_name, test_dataset) in EVAL_SETTINGS:
    outputs.append("\t".join([
        open(f"{EXP_GROUP_NAME}/logs/{exp_name}/eval{test_dataset}_ckpt{i}_strt1/eval.log", "r").readlines()[
            -1].split("|")[2][1:-1]
        for i in CKPTS
    ]) + "\n")
    exp_names.append(exp_name + "\n")

with open(f"{EXP_GROUP_NAME}/logs/collected_results.txt", "w") as f:
    f.writelines(outputs)
with open(f"{EXP_GROUP_NAME}/logs/collected_exp_names.txt", "w") as f:
    f.writelines(exp_names)
