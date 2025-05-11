# Run this on Unity
# copy checkpoints from unity to swarm
for station in KAPX KBUF KCLE KDLH KDTX KGRB KGRR KLOT KMKX KMQT KTYX KIWX; do
  for ckpt_idx in 10 20 30 40; do
    ssh wenlongzhao@swarm.cs.umass.edu mkdir -p /mnt/nfs/home/wenlongzhao/work1/roost-system/active_measurement/${station}_${ckpt_idx}
    scp -r /scratch3/workspace/jmhamilton_umass_edu-roosts/finetune_models_v2/${station}_${ckpt_idx}/model_final.pth wenlongzhao@swarm.cs.umass.edu:/mnt/nfs/home/wenlongzhao/work1/roost-system/active_measurement/${station}_${ckpt_idx}/
  done
done
