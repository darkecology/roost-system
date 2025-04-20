mkdir bounding_boxes
for station in KTLX KCBW KCXX KGYX KTYX KBUF KENX KBGM KBOX KCCX KDIX KLWX KDOX KAKQ KRAX KMHX KLTX KOKX; do
  scp -r wenlongzhao@doppler.cs.umass.edu:/scratch2/wenlongzhao/roostui/data/us_sunrise_v3/tracks_${station}* bounding_boxes
done