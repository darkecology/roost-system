for model_name in init KAPX_10 KBUF_10 KCLE_10 KDLH_10 KDTX_10 KGRB_10 KGRR_10 KLOT_10 KMKX_10 KTYX_10 KIWX_10; do
  scp -r wenlongzhao@doppler.cs.umass.edu:/scratch2/wenlongzhao/roostui/data/${model_name} ${model_name}/sweep_counts
done

for model_name in init KAPX_10 KBUF_10 KCLE_10 KDLH_10 KDTX_10 KGRB_10 KGRR_10 KLOT_10 KMKX_10 KTYX_10 KIWX_10; do
  echo "${model_name}..."
  ls -l ${model_name}/sweep_counts | wc -l
done